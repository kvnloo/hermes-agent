"""Proof driver for staging/memory-prefetch-metric: RED, GREEN x3, per-hunk sabotage (F08), adjacent.

Runs only scripts/run_tests.sh on targeted files, HOME/HERMES_HOME forced to a scratch test home.
Mutations are applied by exact string replacement and undone with `git checkout HEAD -- <file>`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

WT = Path("$ARTIFACTS/promotion-readiness-2026-10-01/wt/staging/memory-prefetch-metric")
OUT = Path("$ARTIFACTS/frontier-2026-10-01/staging/memory-prefetch-metric/work")
TH = Path("$S/testhome-st-memory-prefetch-metric")
PY = "<hermes-home>/hermes-agent/venv/bin/python"
TEST = "tests/hermes_cli/test_shared_metrics_loop.py"
CONTRACT_TEST = "test_external_prefetch_records_each_exit_with_how_long_the_turn_waited"
DISABLED_TEST = "test_disabled_shared_metrics_record_no_loop_rows"
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


def run_tests(files: list[str], label: str, *extra: str) -> dict:
    log = OUT / f"{label}.log"
    cmd = ["bash", "scripts/run_tests.sh", "-j", "2", *files, "-q", *extra]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=WT, env=env(), capture_output=True, text=True, timeout=1500)
    wall = round(time.monotonic() - t0, 1)
    text = proc.stdout + proc.stderr
    log.write_text(text, encoding="utf-8")
    summary = next((ln.strip() for ln in text.splitlines() if ln.startswith("=== Summary")), None)
    failed = sorted(set(re.findall(r"FAILED (tests/\S+::\S+)", text)))
    errors = sorted({ln.strip().lstrip("║").strip() for ln in text.splitlines() if re.match(r"\s*(║\s*)?E\s+", ln)})
    return {
        "label": label, "cmd": " ".join(cmd), "rc": proc.returncode, "wall_s": wall, "summary": summary,
        "failed": failed, "assertion_lines": errors[:12], "log": str(log),
        "log_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


def restore() -> None:
    git("checkout", "HEAD", "--", ".")
    assert git("status", "--porcelain") == "", "worktree not clean after restore"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    head = git("rev-parse", "HEAD")
    base = git("rev-parse", "main")
    restore()
    results: dict = {"head": head, "base": base, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "runs": {}}
    load = os.getloadavg()[0]
    results["load1_at_start"] = load

    # RED: the new tests against main's production code.
    git("checkout", "main", "--", *PROD)
    results["runs"]["red"] = run_tests([TEST], "red")
    restore()

    # GREEN x3.
    results["runs"]["green"] = [run_tests([TEST], f"green_{i}") for i in (1, 2, 3)]

    # Per-hunk sabotage.
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

    # Adjacent: identical pass/fail set on base (main tree for every touched file) and head.
    git("checkout", "main", "--", *PROD, TEST)
    results["runs"]["adjacent_base"] = run_tests(ADJACENT + [TEST], "adjacent_base")
    restore()
    results["runs"]["adjacent_head"] = run_tests(ADJACENT + [TEST], "adjacent_head")
    restore()
    results["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    (OUT / "prove_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "runs"}, indent=2))
    print("red:", results["runs"]["red"]["summary"], results["runs"]["red"]["failed"])
    for g in results["runs"]["green"]:
        print(g["label"], g["summary"])
    for s in results["runs"]["sabotage"]:
        print(s["label"], s["summary"], s["failed"], s["assertion_lines"][:2])
    print("adj base:", results["runs"]["adjacent_base"]["summary"], results["runs"]["adjacent_base"]["failed"])
    print("adj head:", results["runs"]["adjacent_head"]["summary"], results["runs"]["adjacent_head"]["failed"])


if __name__ == "__main__":
    sys.exit(main())
