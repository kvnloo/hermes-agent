#!/usr/bin/env python3
"""Proof matrix for staging/cu-repeat-input-dedup (E25 re-proof + F07 real-path turn test).

T1 only: loopback fake provider, in-tree no-op computer_use backend, run_tests.sh with an
isolated HOME/HERMES_HOME, HERMES_TEST_FILE_RETRIES=0, and the loopback-only guard plugin.
Writes one JSON line per cell to cells.jsonl and raw logs to raw/.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

S = Path("$S")
H = S / "h.git"
W = Path("$ARTIFACTS/promotion-readiness-2026-10-01/wt/staging/cu-repeat-input-dedup")
TH = S / "testhome-st-cu-repeat-input-dedup"
R = Path("$ARTIFACTS/frontier-2026-10-01/staging/cu-repeat-input-dedup/receipts")
PLUGIN = Path(__file__).with_name("_xf_t1_guard.py")
PY = "<hermes-home>/hermes-agent/venv/bin/python"

MAIN = sys.argv[1]
HEAD = sys.argv[2]
ONLY = set(sys.argv[3:])
DONOR, DONOR_MB = "570dc83ba65fc4ce86efb2c00e89dc84d19bd5ca", "cb3142d3257b15ac42de544bd585793567400d0f"
NEW_TEST = "tests/agent/test_tool_call_dedup_order_significant.py"
GUARD_TEST = "tests/agent/test_agent_guardrails.py"
ADJ = [
    "tests/agent/test_agent_guardrails.py",
    "tests/agent/test_tool_batch_segmentation.py",
    "tests/agent/test_tool_call_guardrail_runtime.py",
    "tests/agent/test_file_mutation_verifier.py",
    "tests/agent/test_run_agent.py",
    "tests/tools/test_computer_use.py",
    "tests/tools/test_computer_use_delivery_ladder.py",
    "tests/tools/test_connector_bridge_wiring.py",
    "tests/tools/test_tool_search.py",
]
MARKER = "AssertionError: assert ['key', 'click'] == ['key', 'key', 'click']"


def git(*a, check=True, input=None):
    return subprocess.run(["git", "-C", str(W), *a], check=check, text=True, capture_output=True, input=input)


def checkout(sha):
    git("checkout", "-q", "-f", "--detach", sha)
    git("clean", "-fdq")


def apply_diff(a, b, *paths):
    d = subprocess.run(["git", "-C", str(H), "diff", a, b, "--", *paths], check=True, text=True,
                       capture_output=True).stdout
    git("apply", "-3", "-", input=d)


def replace(path, old, new):
    p = W / path
    s = p.read_text(encoding="utf-8")
    assert old in s, (path, old)
    p.write_text(s.replace(old, new), encoding="utf-8")


ARMS = {
    "base": lambda: (checkout(MAIN), git("checkout", HEAD, "--", NEW_TEST)),
    "head": lambda: checkout(HEAD),
    "neg-empty-table": lambda: (checkout(HEAD), replace(
        "agent/tool_dispatch_helpers.py", '_ORDER_SIGNIFICANT_ACTIONS = frozenset({("computer_use", "key")})',
        "_ORDER_SIGNIFICANT_ACTIONS = frozenset()")),
    "sab-no-bridge-peel": lambda: (checkout(HEAD), replace(
        "agent/tool_dispatch_helpers.py", "        tool_name, args = _peel_bridge_call(tool_name, args)\n",
        "        pass\n")),
    "sab-facade-revert": lambda: (checkout(HEAD), git("checkout", MAIN, "--", "run_agent.py")),
    "donor-fix+new-test": lambda: (checkout(MAIN), apply_diff(DONOR_MB, DONOR, "run_agent.py"),
                                   git("checkout", HEAD, "--", NEW_TEST)),
    "main+donor-test": lambda: (checkout(MAIN), apply_diff(DONOR_MB, DONOR, GUARD_TEST)),
    "main+donor-full": lambda: (checkout(MAIN), apply_diff(DONOR_MB, DONOR)),
    "head+donor-test": lambda: (checkout(HEAD), apply_diff(DONOR_MB, DONOR, GUARD_TEST)),
    "main": lambda: checkout(MAIN),
    "sab-verdict-confirms": lambda: (checkout(HEAD), replace(
        "tools/computer_use/tool.py",
        '    return {"decision": "verify_fresh_state",  # transport success without semantic proof',
        '    return {"decision": "done",  # transport success without semantic proof')),
}

CELLS = (
    [("F07", "base", [NEW_TEST], r) for r in (1, 2, 3)]
    + [("F07", "head", [NEW_TEST], r) for r in (1, 2, 3)]
    + [("F07", "neg-empty-table", [NEW_TEST], 1), ("F07", "sab-no-bridge-peel", [NEW_TEST], 1),
       ("F07", "sab-facade-revert", [NEW_TEST], 1), ("F07", "donor-fix+new-test", [NEW_TEST], 1),
       ("F07", "sab-verdict-confirms", [NEW_TEST], 1)]
    + [("E25", "main+donor-test", [GUARD_TEST], 1), ("E25", "main+donor-full", [GUARD_TEST], 1),
       ("E25", "head+donor-test", [GUARD_TEST], 1)]
    + [("ADJ", "main", ADJ, 1), ("ADJ", "head", ADJ + [NEW_TEST], 1)]
)


def run_cell(exp, arm, files, rep):
    ARMS[arm]()
    shutil.copy(PLUGIN, W / PLUGIN.name)
    guard_dir = TH / "xf_guard"
    shutil.rmtree(guard_dir, ignore_errors=True)
    (TH / ".hermes").mkdir(parents=True, exist_ok=True)
    git("add", "-A", "--", ".", ":(exclude)" + PLUGIN.name)
    tree = git("write-tree").stdout.strip()
    git("reset", "-q")
    env = {"PATH": os.environ["PATH"], "HOME": str(TH), "HERMES_HOME": str(TH / ".hermes"),
           "HERMES_PYTHON": PY, "HERMES_TEST_FILE_RETRIES": "0"}
    cmd = ["bash", "scripts/run_tests.sh", "-j", "2", *files, "-q", "--tb=short", "-p", "_xf_t1_guard"]
    t0, load1 = time.time(), os.getloadavg()[0]
    p = subprocess.run(cmd, cwd=W, env=env, text=True, capture_output=True)
    wall = round(time.time() - t0, 1)
    out = p.stdout + p.stderr
    label = f"{exp}-{arm}-r{rep}"
    (R / "raw" / f"{label}.log").write_text(out, encoding="utf-8")
    m = re.search(r"=== Summary: (\d+) files, (\d+) tests passed, (\d+) failed", out)
    failed = sorted(set(re.findall(r"FAILED (tests/\S+)", out)))
    guards = [json.loads(f.read_text()) for f in sorted(guard_dir.glob("*.json"))] if guard_dir.exists() else []
    seam = {}
    for g in guards:
        for k, v in g["seam_hits"].items():
            seam[k] = seam.get(k, 0) + v
    cell = {
        "experiment": exp, "arm": arm, "rep": rep, "files": files, "arm_tree": tree,
        "cmd": "HOME=$TH HERMES_HOME=$TH/.hermes HERMES_PYTHON=%s HERMES_TEST_FILE_RETRIES=0 %s" % (PY, " ".join(cmd)),
        "rc": p.returncode, "passed": int(m.group(2)) if m else None, "failed": int(m.group(3)) if m else None,
        "failed_ids": failed, "red_marker_matched": out.count(MARKER),
        "egress_blocked": sum(len(g["egress_blocked"]) for g in guards),
        "loopback_connects": sum(g["loopback_connects"] for g in guards),
        "guard_files": len(guards), "seam_hits": seam,
        "credential_like_env": sorted({k for g in guards for k in g["credential_like_env_at_start"]}),
        "wall_s": wall, "load1_at_start": round(load1, 2), "raw_log": f"raw/{label}.log",
    }
    with open(R / "cells.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(cell) + "\n")
    print(label, "rc", p.returncode, "pass", cell["passed"], "fail", cell["failed"], failed,
          "marker", cell["red_marker_matched"], "egress", cell["egress_blocked"], "seam", seam, f"{wall}s",
          flush=True)


if __name__ == "__main__":
    (R / "raw").mkdir(parents=True, exist_ok=True)
    try:
        for exp, arm, files, rep in CELLS:
            if ONLY and f"{exp}:{arm}" not in ONLY:
                continue
            run_cell(exp, arm, files, rep)
    finally:
        checkout(HEAD)
        (W / PLUGIN.name).unlink(missing_ok=True)
        print("restored", git("rev-parse", "HEAD").stdout.strip(), git("status", "--short").stdout.strip())
