"""Wave 2/3 live experiments for the downstream Bend/Hermes adapter.

Measures verifier concurrency and repeatedly attempts a real Bend TOCTOU attack
by swapping LAWS.bend after verification begins. With snapshot verification,
the attack must never forge a pass.

Usage:
  python evals/bend_adapter_wave2.py --repeats 20 --attacks 25 --output result.json
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import importlib.util
import json
from pathlib import Path
import shutil
import statistics
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bend_verify_core_wave2", ROOT / "plugins" / "bend" / "verify_core.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Bend verification core")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

VALID_LAWS = """import Base

law zero_one:
  {0n == 0n : Nat}
"""
INVALID_LAWS = """import Base

law zero_one:
  {0n == 1n : Nat}
"""
PROOF = """import Base
import ./LAWS.bend as Laws

def Laws.zero_one():
  {==}
"""


def write_project(path: Path, laws: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "LAWS.bend").write_text(laws, encoding="utf-8")
    (path / "PROOF.bend").write_text(PROOF, encoding="utf-8")
    return path


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))]


def concurrency_sweep(valid: Path, invalid: Path, repeats: int) -> dict:
    levels = [1, 2, 4, 8, 16]
    report = {}
    total = 0
    mismatches = []
    for workers in levels:
        jobs = [(valid, "pass"), (invalid, "fail")] * repeats
        started = time.monotonic()
        durations = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(core.verify, str(project)): expected for project, expected in jobs}
            for future in as_completed(futures):
                expected = futures[future]
                result = future.result()
                durations.append(float(result["duration_ms"]))
                if result["verdict"] != expected:
                    mismatches.append(
                        {"workers": workers, "expected": expected, "got": result["verdict"]}
                    )
        wall_ms = (time.monotonic() - started) * 1000
        total += len(jobs)
        report[str(workers)] = {
            "runs": len(jobs),
            "wall_ms": round(wall_ms, 3),
            "throughput_per_s": round(len(jobs) / (wall_ms / 1000), 3),
            "p50_ms": round(statistics.median(durations), 3),
            "p95_ms": round(p95(durations), 3),
            "max_ms": round(max(durations), 3),
        }
    return {"experiment_count": total, "levels": report, "mismatches": mismatches}


def make_wrapper(root: Path, real_bend: str, marker: Path) -> Path:
    wrapper = root / "bend-wrapper"
    wrapper.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys, time\n"
        f"REAL = {real_bend!r}\n"
        f"MARKER = {str(marker)!r}\n"
        "if len(sys.argv) > 1 and sys.argv[1] == 'version':\n"
        "    os.execv(REAL, [REAL, *sys.argv[1:]])\n"
        "open(MARKER, 'w').close()\n"
        "time.sleep(0.20)\n"
        "os.execv(REAL, [REAL, *sys.argv[1:]])\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    return wrapper


def toctou_attack(root: Path, attacks: int) -> dict:
    real_bend = shutil.which("bend")
    if real_bend is None:
        raise RuntimeError("Bend not found")
    project = write_project(root / "toctou", INVALID_LAWS)
    laws = project / "LAWS.bend"
    marker = root / "bend-started"
    wrapper = make_wrapper(root, real_bend, marker)

    forged_passes = 0
    source_change_detections = 0
    records = []
    for iteration in range(attacks):
        laws.write_text(INVALID_LAWS, encoding="utf-8")
        marker.unlink(missing_ok=True)
        mutation = {"swapped": False}

        def swap() -> None:
            deadline = time.monotonic() + 5
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.001)
            if marker.exists():
                laws.write_text(VALID_LAWS, encoding="utf-8")
                mutation["swapped"] = True

        thread = threading.Thread(target=swap)
        thread.start()
        result = core.verify(str(project), which=lambda _: str(wrapper))
        thread.join(timeout=5)
        if result["verdict"] == "pass":
            forged_passes += 1
        if result.get("source_changed_during_verify"):
            source_change_detections += 1
        records.append(
            {
                "iteration": iteration,
                "swapped": mutation["swapped"],
                "verdict": result["verdict"],
                "execution_verdict": result.get("execution_verdict"),
                "success": result["success"],
                "source_changed_during_verify": result.get("source_changed_during_verify"),
                "duration_ms": result["duration_ms"],
            }
        )
        laws.write_text(INVALID_LAWS, encoding="utf-8")

    return {
        "experiment_count": attacks,
        "forged_passes": forged_passes,
        "source_change_detections": source_change_detections,
        "attack_success_rate": forged_passes / attacks,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--attacks", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="bend-hermes-wave2-") as raw:
        root = Path(raw)
        valid = write_project(root / "valid", VALID_LAWS)
        invalid = write_project(root / "invalid", INVALID_LAWS)
        warm = core.verify(str(valid))
        if warm["verdict"] != "pass":
            raise RuntimeError(f"warmup failed: {warm}")

        concurrency = concurrency_sweep(valid, invalid, args.repeats)
        toctou = toctou_attack(root, args.attacks)

    summary = {
        "experiment_count": concurrency["experiment_count"] + toctou["experiment_count"],
        "concurrency": concurrency,
        "toctou": {
            "experiment_count": toctou["experiment_count"],
            "forged_passes": toctou["forged_passes"],
            "source_change_detections": toctou["source_change_detections"],
            "attack_success_rate": toctou["attack_success_rate"],
        },
    }
    payload = {"summary": summary, "toctou_records": toctou["records"]}
    rendered = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

    bad = bool(concurrency["mismatches"]) or toctou["forged_passes"] != 0
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
