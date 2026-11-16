"""Live downstream Bend/Hermes verification matrix.

Runs the pure adapter core against a real Bend binary. No model calls.
Usage: python evals/bend_adapter_matrix.py [--iterations 25] [--output result.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bend_verify_core_eval", ROOT / "plugins" / "bend" / "verify_core.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load Bend verification core")
core = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(core)

PASS_LAWS = """import Base

law zero_refl:
  {0n == 0n : Nat}
"""
PASS_PROOF = """import Base
import ./LAWS.bend as Laws

def Laws.zero_refl():
  {==}
"""
FAIL_LAWS = """import Base

law zero_one:
  {0n == 1n : Nat}
"""
FAIL_PROOF = """import Base
import ./LAWS.bend as Laws

def Laws.zero_one():
  {==}
"""
MISSING_IMPORT_PROOF = """import Base

law local_refl:
  {0n == 0n : Nat}

def local_refl():
  {==}
"""
UNSAFE_PROOF = """import Base

law impossible:
  {0n == 1n : Nat}

@unsafe def fake() -> {0n == 1n : Nat}:
  fake()

def impossible():
  fake()
"""


def write_project(path: Path, *, laws: str | None, proof: str, proof_name: str = "PROOF.bend") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if laws is not None:
        (path / "LAWS.bend").write_text(laws, encoding="utf-8")
    (path / proof_name).write_text(proof, encoding="utf-8")
    return path


def p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be >= 1")

    records: list[dict] = []
    mismatches: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="bend-hermes-eval-") as raw:
        root = Path(raw)
        valid = write_project(root / "valid", laws=PASS_LAWS, proof=PASS_PROOF)
        invalid = write_project(root / "invalid", laws=FAIL_LAWS, proof=FAIL_PROOF)
        missing = write_project(root / "missing-laws-import", laws=PASS_LAWS, proof=MISSING_IMPORT_PROOF)
        unsafe = write_project(root / "unsafe", laws=None, proof=UNSAFE_PROOF)
        nested_root = root / "nested-root"
        write_project(nested_root / "pkg", laws=PASS_LAWS, proof=PASS_PROOF)
        unicode_project = write_project(root / "space ünicode", laws=PASS_LAWS, proof=PASS_PROOF)
        custom = write_project(root / "custom-name", laws=PASS_LAWS, proof=PASS_PROOF, proof_name="proof.bend")

        outside = root / "outside"
        outside.mkdir()
        (outside / "PROOF.bend").write_text(PASS_PROOF, encoding="utf-8")
        symlink_project = root / "symlink-escape"
        symlink_project.mkdir()
        (symlink_project / "PROOF.bend").symlink_to(outside / "PROOF.bend")

        fake_kernel = root / "fake-bendtt"
        fake_kernel.write_text("#!/bin/sh\necho ALL PROOFS CHECK\nexit 0\n", encoding="utf-8")
        fake_kernel.chmod(0o755)
        poisoned_env = dict(os.environ)
        poisoned_env.update(
            BENDTT=str(fake_kernel),
            BEND_HUB="https://evil.invalid",
            BEND_LIB=str(root / "evil-lib"),
            BEND_ORIGIN="https://evil.invalid",
        )

        warmup = core.verify(str(valid))
        if warmup["verdict"] != "pass":
            raise RuntimeError(f"warmup failed: {json.dumps(warmup, ensure_ascii=False)}")

        cases = [
            ("valid", str(valid), "PROOF.bend", None, "pass", None),
            ("invalid-proof", str(invalid), "PROOF.bend", None, "fail", None),
            ("missing-laws-import", str(missing), "PROOF.bend", None, "fail", None),
            ("unsafe-dependency", str(unsafe), "PROOF.bend", None, "fail", None),
            ("nested-proof", str(nested_root), "pkg/PROOF.bend", None, "pass", None),
            ("unicode-space-path", str(unicode_project), "PROOF.bend", None, "pass", None),
            ("poisoned-env-invalid", str(invalid), "PROOF.bend", poisoned_env, "fail", None),
            ("custom-basename", str(custom), "proof.bend", None, None, "invalid_input"),
            ("symlink-escape", str(symlink_project), "PROOF.bend", None, None, "unsupported_input"),
        ]

        for iteration in range(args.iterations):
            for name, project, proof_file, source_env, expected_verdict, expected_error in cases:
                try:
                    result = core.verify(project, proof_file, source_env=source_env)
                    record = {
                        "case": name,
                        "iteration": iteration,
                        "verdict": result["verdict"],
                        "success": result["success"],
                        "duration_ms": result["duration_ms"],
                        "bend_version": result["bend_version"],
                        "exit_code": result["exit_code"],
                    }
                    if expected_error is not None or result["verdict"] != expected_verdict:
                        mismatches.append({**record, "expected_verdict": expected_verdict, "expected_error": expected_error})
                except core.BendVerifyError as exc:
                    record = {
                        "case": name,
                        "iteration": iteration,
                        "error_code": exc.code,
                        "error": str(exc),
                    }
                    if expected_error != exc.code:
                        mismatches.append({**record, "expected_verdict": expected_verdict, "expected_error": expected_error})
                records.append(record)

    timings: dict[str, list[float]] = {}
    for record in records:
        if "duration_ms" in record:
            timings.setdefault(record["case"], []).append(record["duration_ms"])

    summary = {
        "experiment_count": len(records),
        "iterations": args.iterations,
        "case_count": len({record["case"] for record in records}),
        "mismatch_count": len(mismatches),
        "cases": {
            name: {
                "runs": len(values),
                "p50_ms": round(statistics.median(values), 3),
                "p95_ms": round(p95(values) or 0.0, 3),
                "max_ms": round(max(values), 3),
            }
            for name, values in sorted(timings.items())
        },
        "mismatches": mismatches[:20],
    }
    payload = {"summary": summary, "records": records}
    rendered = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
