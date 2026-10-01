#!/usr/bin/env python3
"""F05 carrier A/B runner for staging/compaction-hook-salvage (factory-only, stdlib).

For each arm commit (pinned under refs/xf/arms/compaction-hook-salvage/<arm>) it checks the arm out in
the one staging worktree, then runs, through scripts/run_tests.sh with an isolated HOME/HERMES_HOME:

  contract  - tests/agent/test_compaction_observer_hook_contract.py exactly as committed (reps N)
  adapted   - the same file with HOOK set to the carrier's own hook name (carriers only, reps N)
  probe     - tools/chs_clause_probe.py once, per-scenario ordering + clause JSONL

Raw logs go to raw/<run_id>/; one JSON summary per run to raw/<run_id>/summary.json.

r3: per-cell egress accounting from the egress guard's log ($TESTHOME/chs-egress.log, see
chs_egress_guard.py). The log is truncated before and read after every cell; any ``connect`` or ``dns``
line marks that cell ``exit_class = "INFRA"`` (FACTORY S16). ``prewarm_suppressed`` lines are counted
separately (a prevention, not a blocked attempt).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
CONTRACT = "tests/agent/test_compaction_observer_hook_contract.py"
ADAPTED = "tests/agent/test_zz_chs_adapted_contract.py"
PROBE = "tests/agent/test_zz_chs_clause_probe.py"
ARM_REF = "refs/xf/arms/compaction-hook-salvage/"


def sh(cmd, cwd, env=None, timeout=900):
    t0 = time.monotonic()
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout + p.stderr, round(time.monotonic() - t0, 1)


def parse(out: str) -> dict:
    m = re.search(r"=== Summary: \d+ files?, (\d+) tests? passed, (\d+) failed", out)
    passed, failed = (int(m.group(1)), int(m.group(2))) if m else (None, None)
    failing = sorted(set(re.findall(r"^FAILED (tests/\S+)", out, flags=re.M)))
    asserts = []
    for line in re.findall(r"^E\s+(AssertionError: .*|[A-Za-z]+Error: .*)$", out, flags=re.M):
        line = re.sub(r"\(valid: .*\)", "(valid: ...)", line)[:240]
        if line not in asserts:
            asserts.append(line)
    return {"passed": passed, "failed": failed, "failing": failing, "assertions": asserts[:8]}


def egress_counts(log: Path) -> dict:
    counts = {"connect": 0, "dns": 0, "prewarm_suppressed": 0}
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            kind = line.split("\t", 1)[0]
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def run_cell(cmd, wt, env, egress_log: Path):
    egress_log.unlink(missing_ok=True)
    rc, out, wall = sh(cmd, wt, env=env)
    eg = egress_counts(egress_log)
    egress_log.unlink(missing_ok=True)
    return rc, out, wall, eg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--arms", required=True, help="comma list arm=commitish[:hook[:boundary]]")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--testhome", required=True)
    ap.add_argument("--python", required=True)
    ap.add_argument("--skip-probe", action="store_true")
    a = ap.parse_args()
    wt = Path(a.worktree)
    raw = ST / "raw" / a.run_id
    raw.mkdir(parents=True, exist_ok=False)
    env = {k: v for k, v in os.environ.items() if k not in ("__HERMES_ACTIVATED", "VIRTUAL_ENV")}
    env.update(HOME=a.testhome, HERMES_HOME=a.testhome + "/.hermes", HERMES_PYTHON=a.python)
    egress_log = Path(a.testhome) / "chs-egress.log"
    summary = {"run_id": a.run_id, "reps": a.reps, "arms": {}}
    for spec in a.arms.split(","):
        arm, _, rest = spec.partition("=")
        parts = rest.split(":")
        commitish, hook = parts[0], (parts[1] if len(parts) > 1 and parts[1] else None)
        boundary = len(parts) > 2 and parts[2] == "boundary"
        rc, out, _ = sh(["git", "checkout", "-q", "--detach", commitish], wt)
        assert rc == 0, out
        assert sh(["git", "status", "--porcelain"], wt)[1].strip() == "", "dirty worktree"
        head = sh(["git", "rev-parse", "HEAD"], wt)[1].strip()
        tree = sh(["git", "rev-parse", "HEAD^{tree}"], wt)[1].strip()
        rec = {"commit": head, "tree": tree, "hook": hook, "boundary_filter": boundary, "cells": []}
        kinds = [("contract", CONTRACT)]
        if hook:
            src = (wt / CONTRACT).read_text(encoding="utf-8")
            src = src.replace('HOOK = "on_compression_complete"', f'HOOK = "{hook}"')
            if boundary:
                src = src.replace(
                    "    def record(**kwargs):\n",
                    "    def record(**kwargs):\n        if kwargs.get(\"boundary_reason\") != \"compression\":\n"
                    "            return None\n")
            (wt / ADAPTED).write_text(src, encoding="utf-8")
            kinds.append(("adapted", ADAPTED))
        for kind, path in kinds:
            for rep in range(1, a.reps + 1):
                cmd = ["bash", "scripts/run_tests.sh", "-j", "2", path, "-q"]
                rc, out, wall, eg = run_cell(cmd, wt, env, egress_log)
                log = raw / f"{arm}-{kind}-rep{rep}.log"
                log.write_text(out, encoding="utf-8")
                parsed = parse(out)
                exit_class = "INFRA" if (eg["connect"] or eg["dns"]) else (
                    "ok" if parsed["passed"] is not None else "harness_error")
                rec["cells"].append({"kind": kind, "rep": rep, "rc": rc, "wall_s": wall, "exit_class": exit_class,
                                     "egress": eg, "cmd": " ".join(cmd), "log": str(log.relative_to(ST)), **parsed})
        if not a.skip_probe:
            probe_hook = hook or "on_compression_complete"
            shutil.copyfile(ST / "tools" / "chs_clause_probe.py", wt / PROBE)
            out_jsonl = raw / f"{arm}-probe.jsonl"
            (wt / PROBE.replace(".py", ".json")).write_text(json.dumps(
                {"hook": probe_hook, "filter_boundary": boundary, "out": str(out_jsonl)}), encoding="utf-8")
            out_jsonl.unlink(missing_ok=True)
            cmd = ["bash", "scripts/run_tests.sh", "-j", "2", PROBE, "-q"]
            rc, out, wall, eg = run_cell(cmd, wt, env, egress_log)
            (raw / f"{arm}-probe.log").write_text(out, encoding="utf-8")
            rows = [json.loads(x) for x in out_jsonl.read_text().splitlines()] if out_jsonl.exists() else []
            rec["probe"] = {"rc": rc, "wall_s": wall, "hook": probe_hook, "egress": eg,
                            "exit_class": "INFRA" if (eg["connect"] or eg["dns"]) else "ok",
                            "rows": rows, **parse(out)}
        for extra in (ADAPTED, PROBE, PROBE.replace(".py", ".json")):
            (wt / extra).unlink(missing_ok=True)
        assert sh(["git", "status", "--porcelain"], wt)[1].strip() == "", "worktree left dirty"
        summary["arms"][arm] = rec
        print(arm, [(c["kind"], c["passed"], c["failed"], c["exit_class"]) for c in rec["cells"]], flush=True)
    (raw / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
