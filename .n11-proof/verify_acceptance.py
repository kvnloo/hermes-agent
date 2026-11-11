#!/usr/bin/env python3
"""Run the six HN11 acceptance checks with isolated state and exact exit codes."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/plugins/test_handoff_capsule_acceptance.py"
CHECKS = (
    "test_capsule_preserves_open_work_and_private_spill",
    "test_capsule_obeys_even_its_own_character_budget",
    "test_host_adapts_legacy_engine_signature",
    "test_opt_out_status_and_opt_in_dispatch",
    "test_successful_summary_is_capped_and_spilled",
    "test_spill_failure_does_not_return_an_oversized_capsule",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--label", required=True, choices=("base", "branch"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    result_path = args.out / f"{args.label}-results.json"
    if result_path.exists():
        parser.error(f"Refusing to overwrite {result_path}")
    results = {
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": hashlib.sha256((ROOT / ".n11-proof/handoff_capsule.py").read_bytes()).hexdigest(),
        "tests_sha256": hashlib.sha256((ROOT / TEST).read_bytes()).hexdigest(),
        "cwd": str(ROOT),
        "runs": [],
    }
    for name in ("acceptance", *CHECKS):
        target = TEST if name == "acceptance" else f"{TEST}::{name}"
        command = ["venv/bin/python", "-m", "pytest", target, "-q"]
        log = args.out / f"{args.label}-{name}.log"
        with tempfile.TemporaryDirectory(prefix="hn11-") as home:
            temp = Path(home) / "tmp"
            temp.mkdir()
            env = {
                "PATH": f"{ROOT / 'venv/bin'}:/usr/bin:/bin",
                "HOME": home,
                "HERMES_HOME": str(Path(home) / "hermes"),
                "TMPDIR": str(temp),
                "LANG": "C.UTF-8",
                "TZ": "UTC",
                "PYTHONHASHSEED": "0",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
            with log.open("x") as stream:
                stream.write(f"cwd={ROOT}\ncommand={shlex.join(command)}\n")
                stream.flush()
                completed = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
                stream.write(f"\nexit_code={completed.returncode}\n")
        run = {"check": name, "command": shlex.join(command), "exit_code": completed.returncode, "log": str(log)}
        results["runs"].append(run)
        print(json.dumps(run), flush=True)
        if name == "acceptance":
            print(log.read_text(), flush=True)
    result_path.write_text(json.dumps(results, indent=2) + "\n")
    return int(any(run["exit_code"] != 0 for run in results["runs"]))


if __name__ == "__main__":
    raise SystemExit(main())
