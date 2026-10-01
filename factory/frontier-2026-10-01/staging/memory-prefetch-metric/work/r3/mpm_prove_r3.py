"""Proof driver (round 3, amended head) for memory-prefetch-metric: RED, GREEN x3, per-hunk sabotage,
stall tolerance, adjacent.

Changes from work/r2/mpm_prove_r2.py:
- the contract test no longer pins wall-clock buckets below 2 s (AGENTS.md: "Timing tests must not assume a
  quiet runner: wall-clock bounds >= 2s"); success/empty classification moved into the guarded builder.
- S4/S7 strings follow the new call sites; S9 (empty classification) and S10 (constant latency above the
  timeout) are new hunks/mutations.
- STALL cells: every fake provider sleeps before answering. The amended test must still pass with a 1.5 s
  stall; the round-2 test (from --old-head) is run with a 0.15 s stall to show the flake it had.

Usage:
  python mpm_prove_r3.py --wt <worktree at the staging commit> --out <results dir> \
      --test-home <scratch test home> --hermes-python <python for run_tests.sh> --old-head <round-2 head sha>

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
ap.add_argument("--old-head", required=True)
ap.add_argument("--green-reps", type=int, default=3)
ARGS = ap.parse_args()
WT, OUT, TH, PY = ARGS.wt, ARGS.out, ARGS.test_home, ARGS.hermes_python

TEST = "tests/hermes_cli/test_shared_metrics_loop.py"
CONTRACT_TEST = TEST + "::test_external_prefetch_records_each_exit_with_how_long_the_turn_waited"
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
EMPTY_RULE = '''    if outcome_value == "success" and not (isinstance(recalled, str) and recalled.strip()):
        outcome_value = "empty"
'''
SABOTAGE = [
    ("S1-skip-exit", MM, '            record_memory_prefetch(provider.name, "skipped", started)\n', ""),
    ("S2-timeout-exit", MM, '            record_memory_prefetch(provider.name, "timed_out", started)\n', ""),
    ("S3-error-exit", MM, '            record_memory_prefetch(provider.name, "failed", started)\n', ""),
    ("S4-success-empty-exit", MM, '        record_memory_prefetch(provider.name, "success", started, recalled=result)\n', ""),
    ("S5-mark-to-metric-mapping", CONTRACT, "    MEMORY_PREFETCH_MARK: MEMORY_PREFETCH_METRIC,\n", ""),
    ("S6-provider-rule-raw-name", LOOP, PREFETCH_FIELDS_OLD, PREFETCH_FIELDS_NEW),
    ("S7-outcome-vocabulary-drift", MM, '"timed_out", started)', '"timeout", started)'),
    ("S8-latency-not-measured", LOOP, "waited_ms=(time.monotonic() - started) * 1000,", "waited_ms=0,"),
    ("S9-empty-classification", LOOP, EMPTY_RULE, ""),
    ("S10-constant-latency-above-timeout", LOOP, "waited_ms=(time.monotonic() - started) * 1000,", "waited_ms=2500,"),
]
PREFETCH_METHOD = '''    def prefetch(self, query, *, session_id=""):
        return self._prefetch()
'''


def stalled(seconds: float) -> str:
    return PREFETCH_METHOD.replace("        return self._prefetch()\n",
                                   f'        __import__("time").sleep({seconds})\n        return self._prefetch()\n')


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
        "flaky_retry_printed": "FLAKY" in text, "log_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def restore() -> None:
    git("checkout", "HEAD", "--", ".")
    assert git("status", "--porcelain") == "", "worktree not clean after restore"


def mutate(path: str, old: str, new: str) -> None:
    p = WT / path
    src = p.read_text(encoding="utf-8")
    assert src.count(old) == 1, (path, src.count(old))
    p.write_text(src.replace(old, new), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    head, base = git("rev-parse", "HEAD"), git("rev-parse", "HEAD~1")
    restore()
    results: dict = {"head": head, "base": base, "head_tree": git("rev-parse", "HEAD^{tree}"),
                     "old_head": ARGS.old_head,
                     "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                     "load1_at_start": os.getloadavg()[0], "runs": {}}
    git("checkout", base, "--", *PROD)  # RED: new test against the parent's production files
    results["runs"]["red"] = run_tests([TEST], "red")
    restore()
    results["runs"]["green"] = [run_tests([TEST], f"green_{i}") for i in range(1, ARGS.green_reps + 1)]
    results["runs"]["sabotage"] = []
    for name, path, old, new in SABOTAGE:
        mutate(path, old, new)
        r = run_tests([TEST], f"sabotage_{name}")
        r.update(mutation={"file": path, "old": old, "new": new})
        results["runs"]["sabotage"].append(r)
        restore()
    # Stall tolerance: the amended test with every fake provider 1.5 s slow must still pass ...
    mutate(TEST, PREFETCH_METHOD, stalled(1.5))
    results["runs"]["stall_amended_1500ms"] = run_tests([TEST], "stall_amended_1500ms")
    restore()
    # ... while the round-2 test (old head's 6 files) already fails with a 0.15 s stall.
    git("checkout", ARGS.old_head, "--", *PROD, TEST)
    mutate(TEST, PREFETCH_METHOD, stalled(0.15))
    results["runs"]["stall_round2_150ms"] = run_tests([TEST], "stall_round2_150ms")
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
        print(g["label"], g["summary"], "FLAKY" if g["flaky_retry_printed"] else "")
    for s in results["runs"]["sabotage"]:
        print(s["label"], s["summary"], s["failed"], s["assertion_lines"][:1])
    for k in ("stall_amended_1500ms", "stall_round2_150ms"):
        r = results["runs"][k]
        print(k, r["summary"], r["failed"], r["assertion_lines"][:2])
    print("adj base:", results["runs"]["adjacent_base"]["summary"], results["runs"]["adjacent_base"]["failed"])
    print("adj head:", results["runs"]["adjacent_head"]["summary"], results["runs"]["adjacent_head"]["failed"])


if __name__ == "__main__":
    sys.exit(main())
