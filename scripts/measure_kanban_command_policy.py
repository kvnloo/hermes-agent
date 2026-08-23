#!/usr/bin/env python3
"""OX1000 C2 canary measurement — baseline vs post-change kanban worker runs.

Defines and counts the three OX1000 counters over a window of kanban
worker runs (default: the next 100 runs after enabling
``kanban.worker_command_policy``):

1. approval_blocks_per_1k_tool_calls — BLOCKED/denied tool results per
   1000 tool calls (F1 baseline: 1717 blocks / six profiles).
2. identical_command_loop_sessions — sessions repeating one identical
   terminal command >= 4 times (F9 baseline: 736 sessions).
3. patch_loop_sessions — sessions patching the same file >= 3 times
   (F9 baseline: 201 sessions).

Sources of truth (local, deterministic, no telemetry):
- worker logs:    <board-root>/logs/<task-id>.log   (`hermes kanban log`)
- session store:  SessionDB messages for the workers' session ids.

Usage:
  python scripts/measure_kanban_command_policy.py --runs 100 \
      [--kanban-root ~/.hermes/kanban] [--out report.json]

The script NEVER fabricates missing data; runs without a parseable log
are reported under "unparsed" so coverage is explicit. Do not quote any
post-change number until >= 100 real runs exist under the enabled gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BLOCK_RE = re.compile(r"BLOCKED[^\n]*", re.IGNORECASE)
TOOLCALL_RE = re.compile(
    r"(?m)^(?:┊|>)?\s*\[(?:terminal|read_file|write_file|patch|search_files|"
    r"execute_code|web_|browser_|skill_|kanban_)\w*", re.IGNORECASE,
)

# Baselines from OX1000 plan (ox1000-plan.md lines 22-31) and
# first-3-canaries.md lines 18-27.
BASELINE = {
    "approval_blocks_per_1k_tool_calls": None,  # F1: 1717 blocks across profiles
    "identical_command_loop_sessions": {"default": 654, "canary": 82},
    "patch_loop_sessions": 201,
}


def command_fingerprint(cmd: str) -> str:
    return hashlib.sha256(cmd.strip().encode("utf-8")).hexdigest()[:16]


def scan_worker_log(log_path: Path) -> dict:
    """Scan one worker log for the three counters."""
    try:
        text = log_path.read_text("utf-8", errors="replace")
    except OSError as exc:
        return {"log": str(log_path), "error": str(exc)}

    blocks = BLOCK_RE.findall(text)
    tool_call_count = len(TOOLCALL_RE.findall(text))

    # Identical-command loops: normalize each terminal invocation line and
    # count repeats of the same fingerprint within the run.
    cmd_counter: Counter[str] = Counter()
    for line in text.splitlines():
        m = re.search(r"(?:\$|command=|`)([^`\n]{8,400})(?:`|$)", line)
        if m and ("git " in m.group(1) or "python" in m.group(1) or "npm " in m.group(1)):
            cmd_counter[command_fingerprint(m.group(1))] += 1
    identical_loops = sum(1 for c in cmd_counter.values() if c >= 4)

    # Patch loops on same file: track patch target paths.
    patch_targets: Counter[str] = Counter()
    for line in text.splitlines():
        m = re.search(r"patch\(\s*path=['\"]([^'\"]+)", line)
        if m:
            patch_targets[m.group(1)] += 1
    patch_loops = sum(1 for c in patch_targets.values() if c >= 3)

    return {
        "log": str(log_path),
        "tool_call_markers": tool_call_count,
        "approval_blocks": len(blocks),
        "identical_command_loops": identical_loops,
        "patch_loops_same_file": patch_loops,
        "policy_hash_expected": _expected_policy_hash_if_present(text),
    }


def _expected_policy_hash_if_present(text: str) -> str | None:
    """Return the policy hash if this log's prompt carried the block.

    The policy is injected into the system prompt, which isn't logged;
    instead we detect its distinctive header echoed in any prompt dump or
    transcript capture. Absence → None (unknown, not zero).
    """
    return (
        "cmd-policy-present"
        if "# Command policy (pre-warmed)" in text
        else None
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kanban-root", type=Path,
                    default=Path.home() / ".hermes" / "kanban")
    ap.add_argument("--runs", type=int, default=100)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    logs_dir = args.kanban_root / "logs"
    if not logs_dir.is_dir():
        print(json.dumps({"error": f"no logs dir at {logs_dir}"}))
        return 2
    logs = sorted(logs_dir.glob("*.log"),
                  key=lambda p: p.stat().st_mtime, reverse=True)[:args.runs]

    runs = [scan_worker_log(p) for p in logs]
    parsed = [r for r in runs if "error" not in r]
    total_tools = sum(r["tool_call_markers"] for r in parsed)
    total_blocks = sum(r["approval_blocks"] for r in parsed)

    report = {
        "baseline_reference": BASELINE,
        "window_runs_requested": args.runs,
        "logs_found": len(runs),
        "parsed_ok": len(parsed),
        "unparsed": [r["log"] for r in runs if "error" in r],
        "counters": {
            "approval_blocks_per_1k_tool_calls": round(
                total_blocks * 1000 / total_tools, 2) if total_tools else None,
            "total_approval_blocks": total_blocks,
            "total_tool_call_markers": total_tools,
            "identical_command_loop_sessions": sum(
                1 for r in parsed if r["identical_command_loops"] > 0),
            "patch_loop_sessions": sum(
                1 for r in parsed if r["patch_loops_same_file"] > 0),
            "sessions_with_policy_evidence": sum(
                1 for r in parsed if r["policy_hash_expected"]),
        },
        "note": (
            "Do not compare against baseline until >=100 real runs exist "
            "with kanban.worker_command_policy: true."
        ),
        "per_run": parsed,
    }
    out = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(out + "\n")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
