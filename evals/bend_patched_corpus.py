"""Differential Bend proof-corpus qualification for the downstream translator patch."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def classify(result: subprocess.CompletedProcess[str]) -> str:
    if result.returncode == 0 and result.stdout.strip() == "ALL PROOFS CHECK":
        return "pass"
    if result.returncode != 0:
        return "fail"
    return "indeterminate"


def run_one(bun: Path, root: Path, rel: Path, env: dict[str, str], timeout: int) -> dict:
    started = time.monotonic()
    result = subprocess.run(
        [str(bun), str(root / "bend2" / "main.ts"), rel.as_posix(), "--verdict"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "classification": classify(result),
        "exit_code": result.returncode,
        "stdout_head": result.stdout[:1000],
        "stderr_head": result.stderr[:1000],
        "duration_ms": round((time.monotonic() - started) * 1000, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bun", type=Path, required=True)
    parser.add_argument("--base-root", type=Path, required=True)
    parser.add_argument("--patched-root", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    base = args.base_root.resolve()
    patched = args.patched_root.resolve()
    bun = args.bun.resolve()
    files = sorted(
        p.relative_to(base)
        for p in (base / "tests" / "proof").rglob("*.bend")
        if p.is_file()
    )

    host_elan = os.environ.get("ELAN_HOME") or str(Path.home() / ".elan")
    records = []
    mismatches = []
    with tempfile.TemporaryDirectory(prefix="bend-patched-corpus-") as home:
        env = dict(os.environ)
        env.update(
            HOME=home,
            ELAN_HOME=host_elan,
            BEND_NO_TELEMETRY="1",
        )
        first = True
        for repeat in range(args.repeats):
            for rel in files:
                base_result = run_one(bun, base, rel, env, 120 if first else 30)
                first = False
                patched_result = run_one(bun, patched, rel, env, 30)
                record = {
                    "file": rel.as_posix(),
                    "repeat": repeat,
                    "base": base_result,
                    "patched": patched_result,
                }
                records.append(record)
                if (
                    base_result["classification"] != patched_result["classification"]
                    or base_result["exit_code"] != patched_result["exit_code"]
                ):
                    mismatches.append(record)

    durations = [
        result["duration_ms"]
        for record in records
        for result in (record["base"], record["patched"])
    ]
    summary = {
        "proof_file_count": len(files),
        "repeats": args.repeats,
        "experiment_count": len(records) * 2,
        "mismatch_count": len(mismatches),
        "max_ms": max(durations) if durations else None,
        "mismatches": mismatches[:20],
    }
    payload = {"summary": summary, "records": records}
    rendered = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
