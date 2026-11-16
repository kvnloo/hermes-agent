"""Wave 4 provenance experiments for the downstream Bend/Hermes adapter.

Tests whether Bend's compiled BendTT cache can be poisoned by another same-user
process, then measures the correctness/latency of fresh HOME directories.

Usage:
  python evals/bend_adapter_provenance.py --attacks 25 --cold-runs 5 --output result.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import statistics
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bend_verify_core_provenance", ROOT / "plugins" / "bend" / "verify_core.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Bend verification core")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

_HOST_ELAN_HOME = os.environ.get("ELAN_HOME") or str(Path.home() / ".elan")

# Bend 2.0.34's TypeScript checker accepts this shared graph, while its
# proven kernel currently exhausts fuel. That makes it a clean discriminator:
# a real kernel fails; a fake "always pass" cached kernel can forge success.
KERNEL_GAP_PROOF = """import Base

def mix(a: U32, b: U32) -> U32:
  (a * 31 + b : U32)

def root_loop(d: Nat, +h: U32) -> U32:
  match d:
    case 0n: h
    case 1n+p: root_loop(p, mix(h, h))

def sq(+h: U32) -> U32:
  mix(h, h)

def root_rec(d: Nat, +x: U32) -> U32:
  match d:
    case 0n: x
    case 1n+p: sq(root_rec(p, x))

def agree_32(+x: U32) -> {root_loop(32n, x) == root_rec(32n, x) : U32}:
  {==}
"""

VALID_PROOF = """import Base

law ok:
  {0n == 0n : Nat}

def ok():
  {==}
"""


def project(root: Path, name: str, proof: str) -> Path:
    path = root / name
    path.mkdir(parents=True)
    (path / "PROOF.bend").write_text(proof, encoding="utf-8")
    return path


def env_with_home(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(home)
    # Keep the already-installed Lean toolchain available while isolating
    # Bend's ~/.bend/bendtt cache under this experiment HOME.
    env["ELAN_HOME"] = _HOST_ELAN_HOME
    return env


def kernel_bins(home: Path) -> list[Path]:
    return sorted((home / ".bend" / "bendtt").glob("*/bendtt"))


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * q) - 1))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attacks", type=int, default=25)
    parser.add_argument("--cold-runs", type=int, default=5)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="bend-hermes-provenance-") as raw:
        root = Path(raw)
        gap = project(root, "kernel-gap", KERNEL_GAP_PROOF)
        valid = project(root, "valid", VALID_PROOF)
        shared_home = root / "shared-home"
        shared_home.mkdir()
        shared_env = env_with_home(shared_home)

        warm = core.verify(str(valid), source_env=shared_env)
        if warm["verdict"] != "pass":
            raise RuntimeError(f"kernel warmup failed: {warm}")
        baseline = core.verify(str(gap), source_env=shared_env)
        if baseline["verdict"] != "fail":
            raise RuntimeError(
                f"kernel-gap discriminator no longer fails closed on this Bend build: {baseline}"
            )
        bins = kernel_bins(shared_home)
        if len(bins) != 1:
            raise RuntimeError(
                f"expected exactly one compiled BendTT kernel after baseline, got {bins}"
            )
        kernel = bins[0]
        backup = kernel.with_name("bendtt.original")
        shutil.copy2(kernel, backup)
        original_sha256 = core.sha256_file(kernel)

        kernel.write_text("#!/bin/sh\necho ALL PROOFS CHECK\nexit 0\n", encoding="utf-8")
        kernel.chmod(0o755)
        poisoned_sha256 = core.sha256_file(kernel)

        poisoned_records = []
        for iteration in range(args.attacks):
            result = core.verify(str(gap), source_env=shared_env)
            poisoned_records.append(
                {
                    "iteration": iteration,
                    "verdict": result["verdict"],
                    "success": result["success"],
                    "duration_ms": result["duration_ms"],
                    "bend_sha256": result.get("bend_sha256"),
                }
            )

        shutil.copy2(backup, kernel)
        restored_sha256 = core.sha256_file(kernel)

        cold_records = []
        for iteration in range(args.cold_runs):
            for label, target, expected in (
                ("kernel-gap", gap, "fail"),
                ("valid", valid, "pass"),
            ):
                home = root / f"cold-{iteration}-{label}"
                home.mkdir()
                result = core.verify(str(target), source_env=env_with_home(home))
                cold_records.append(
                    {
                        "iteration": iteration,
                        "case": label,
                        "expected": expected,
                        "verdict": result["verdict"],
                        "duration_ms": result["duration_ms"],
                    }
                )

    forged = sum(record["verdict"] == "pass" for record in poisoned_records)
    cold_mismatches = [
        record for record in cold_records if record["verdict"] != record["expected"]
    ]
    cold_durations = [record["duration_ms"] for record in cold_records]

    summary = {
        "experiment_count": 2 + len(poisoned_records) + len(cold_records),
        "baseline": {
            "expected": "fail",
            "verdict": baseline["verdict"],
            "duration_ms": baseline["duration_ms"],
        },
        "kernel_cache": {
            "original_sha256": original_sha256,
            "poisoned_sha256": poisoned_sha256,
            "restored_sha256": restored_sha256,
            "restore_matches": restored_sha256 == original_sha256,
        },
        "poison_attack": {
            "attempts": args.attacks,
            "forged_passes": forged,
            "attack_success_rate": forged / args.attacks,
        },
        "fresh_home": {
            "runs": len(cold_records),
            "mismatch_count": len(cold_mismatches),
            "p50_ms": round(statistics.median(cold_durations), 3),
            "p95_ms": round(percentile(cold_durations, 0.95), 3),
            "max_ms": round(max(cold_durations), 3),
        },
    }
    payload = {
        "summary": summary,
        "poisoned_records": poisoned_records,
        "cold_records": cold_records,
        "cold_mismatches": cold_mismatches,
    }
    rendered = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

    # Red phase is observational: a forged pass is evidence for the next fix.
    return 1 if cold_mismatches or restored_sha256 != original_sha256 else 0


if __name__ == "__main__":
    raise SystemExit(main())
