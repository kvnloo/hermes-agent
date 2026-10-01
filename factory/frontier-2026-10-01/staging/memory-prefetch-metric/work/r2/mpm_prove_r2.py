"""Proof driver (round 2, rebased head) for memory-prefetch-metric: RED, GREEN x3, per-hunk sabotage, adjacent.

Same cells and mutations as work/mpm_prove.py (round 1); only the locations are parameters now, and the
base arm is the commit's own parent (HEAD~1) instead of the moving `main` ref.

Usage:
  python mpm_prove_r2.py --wt <worktree at the staging commit> --out <results dir> \
      --test-home <scratch test home> --hermes-python <python for run_tests.sh>

Runs only scripts/run_tests.sh on targeted files with HOME/HERMES_HOME forced to the scratch test home.
Mutations are exact string replacements, undone with `git checkout HEAD -- .`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--wt", type=Path, required=True)
ap.add_argument("--out", type=Path, required=True)
ap.add_argument("--test-home", type=Path, required=True)
ap.add_argument("--hermes-python", required=True)
ap.add_argument("--green-reps", type=int, default=3)
ARGS = ap.parse_args()
WT, OUT, TH, PY = ARGS.wt, ARGS.out, ARGS.test_home, ARGS.hermes_python

TEST = "tests/hermes_cli/test_shared_metrics_loop.py"
PROD = [
    "agent/memory_manager.py",
    "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
    "hermes_cli/observability/shared_metrics_contract.py",
    "hermes_cli/observability/shared_metrics_loop.py",
    "website/docs/developer-guide/relay-shared-metrics.md",
]
ADJACENT = [
    "tests/agent/test_memory_provider.py",
    "tests/agent/test_memory_async_sync.py",
    "tests/agent/test_memory_session_switch.py",
    "tests/agent/test_memory_skill_scaffolding.py",
    "tests/agent/test_memory_sync_interrupted.py",
    "tests/agent/test_turn_context.py",
    "tests/hermes_cli/test_relay_shared_metrics.py",
    "tests/hermes_cli/test_relay_shared_metrics_runtime.py",
    "tests/hermes_cli/test_shared_metrics_signals.py",
    "tests/hermes_cli/test_shared_metrics_efficiency.py",
    "tests/hermes_cli/test_shared_metrics_harness.py",
]
MM = "agent/memory_manager.py"
LOOP = "hermes_cli/observability/shared_metrics_loop.py"
CONTRACT = "hermes_cli/observability/shared_metrics_contract.py"
PREFETCH_FIELDS_OLD = '''        "outcome": outcome_value if outcome_value in MEMORY_PREFETCH_OUTCOMES else "failed",
        "provider": memory_provider_name(provider),'''
PREFETCH_FIELDS_NEW = '''        "outcome": outcome_value if outcome_value in MEMORY_PREFETCH_OUTCOMES else "failed",
        "provider": _norm(provider),'''
SABOTAGE = [
    ("S1-skip-exit", MM, '            record_memory_prefetch(provider.name, "skipped", started)\n', ""),
    ("S2-timeout-exit", MM, '            record_memory_prefetch(provider.name, "timed_out", started)\n', ""),
    ("S3-error-exit", MM, '            record_memory_prefetch(provider.name, "failed", started)\n', ""),
    ("S4-success-empty-exit", MM,
     '        record_memory_prefetch(provider.name, "success" if result and result.strip() else "empty", started)\n', ""),
    ("S5-mark-to-metric-mapping", CONTRACT, "    MEMORY_PREFETCH_MARK: MEMORY_PREFETCH_METRIC,\n", ""),
    ("S6-provider-rule-raw-name", LOOP, PREFETCH_FIELDS_OLD, PREFETCH_FIELDS_NEW),
    ("S7-outcome-vocabulary-drift", MM, '"timed_out", started)', '"timeout", started)'),
    ("S8-latency-not-measured", LOOP, "waited_ms=(time.monotonic() - started) * 1000,", "waited_ms=0,"),
]


def env() -> dict[str, str]:
    e = {k: v for k, v in os.environ.items() if not k.startswith("HERMES_") and k != "__HERMES_ACTIVATED"}
    e.update(HOME=str(TH), HERMES_HOME=str(TH / ".hermes"), HERMES_PYTHON=PY)
    return e


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=WT, check=True, capture_output=True, text=True).stdout.strip()


def run_tests(files: list[str], label: str) -> dict:
    log = OUT / f"{label}.log"
    cmd = ["bash", "scripts/run_tests.sh", "-j", "2", *files, "-q"]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=WT, env=env(), capture_output=True, text=True, timeout=1500)
    text = proc.stdout + proc.stderr
    log.write_text(text, encoding="utf-8")
    summary = next((ln.strip() for ln in text.splitlines() if ln.startswith("=== Summary")), None)
    failed = sorted(set(re.findall(r"FAILED (tests/\S+::\S+)", text)))
    errors = sorted({ln.strip().lstrip("║").strip() for ln in text.splitlines() if re.match(r"\s*(║\s*)?E\s+", ln)})
    return {
        "label": label, "cmd": " ".join(cmd), "rc": proc.returncode, "wall_s": round(time.monotonic() - t0, 1),
        "summary": summary, "failed": failed, "assertion_lines": errors[:12], "log": log.name,
        "log_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def restore() -> None:
    git("checkout", "HEAD", "--", ".")
    assert git("status", "--porcelain") == "", "worktree not clean after restore"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    head, base = git("rev-parse", "HEAD"), git("rev-parse", "HEAD~1")
    restore()
    results: dict = {"head": head, "base": base, "head_tree": git("rev-parse", "HEAD^{tree}"),
                     "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "load1_at_start": os.getloadavg()[0], "runs": {}}
    git("checkout", base, "--", *PROD)  # RED: new test against the parent's production files
    results["runs"]["red"] = run_tests([TEST], "red")
    restore()
    results["runs"]["green"] = [run_tests([TEST], f"green_{i}") for i in range(1, ARGS.green_reps + 1)]
    results["runs"]["sabotage"] = []
    for name, path, old, new in SABOTAGE:
        p = WT / path
        src = p.read_text(encoding="utf-8")
        assert src.count(old) == 1, (name, src.count(old))
        p.write_text(src.replace(old, new), encoding="utf-8")
        r = run_tests([TEST], f"sabotage_{name}")
        r.update(mutation={"file": path, "old": old, "new": new})
        results["runs"]["sabotage"].append(r)
        restore()
    git("checkout", base, "--", *PROD, TEST)
    results["runs"]["adjacent_base"] = run_tests(ADJACENT + [TEST], "adjacent_base")
    restore()
    results["runs"]["adjacent_head"] = run_tests(ADJACENT + [TEST], "adjacent_head")
    restore()
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results["load1_at_end"] = os.getloadavg()[0]
    (OUT / "prove_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("red:", results["runs"]["red"]["summary"], results["runs"]["red"]["failed"],
          results["runs"]["red"]["assertion_lines"][:2])
    for g in results["runs"]["green"]:
        print(g["label"], g["summary"])
    for s in results["runs"]["sabotage"]:
        print(s["label"], s["summary"], s["failed"])
    print("adj base:", results["runs"]["adjacent_base"]["summary"], results["runs"]["adjacent_base"]["failed"])
    print("adj head:", results["runs"]["adjacent_head"]["summary"], results["runs"]["adjacent_head"]["failed"])


if __name__ == "__main__":
    sys.exit(main())
