#!/usr/bin/env python3
"""Aggregate raw/<run>/summary.json into the public F05 receipt and the RED/GREEN/NEG proof receipt.

usage: chs_receipts.py <run-id> <main_sha> <base_commit>
Writes receipts/F05-<run-id>.json and receipts/PROOF-<run-id>.json (xf.receipt.v1 subset, OBSERVED).
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
run, main_sha, base_commit = sys.argv[1:4]
raw = ST / "raw" / run
summary = json.loads((raw / "summary.json").read_text())
EXPECT_FIRE = {"rotated", "in_place", "manual_deferred"}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reps(cells, kind):
    cs = [c for c in cells if c["kind"] == kind]
    if not cs:
        return None
    return {
        "reps": len(cs),
        "per_rep": [f'{c["passed"]} passed / {c["failed"]} failed' for c in cs],
        "reps_agree": len({(c["passed"], c["failed"], tuple(c["failing"])) for c in cs}) == 1,
        "failing": cs[0]["failing"], "assertions": cs[0]["assertions"],
        "all_green": all(c["failed"] == 0 and (c["passed"] or 0) > 0 for c in cs),
        "logs": [c["log"] for c in cs],
    }


def clauses(rows):
    by = {r["scenario"]: r for r in rows}
    out = {}
    for name, r in by.items():
        ev = r["events"][0] if r["events"] else {}
        hook_i = [i for i, e in enumerate(r["order"]) if e == "hook"]
        commit_end = [i for i, e in enumerate(r["order"]) if e.endswith(":end")]
        summ = [i for i, e in enumerate(r["order"]) if e == "summary"]
        timing = None
        if hook_i:
            h = hook_i[0]
            if summ and h < summ[0]:
                timing = "before_summary"
            elif commit_end and h > commit_end[0]:
                timing = "after_durable_commit"
            else:
                timing = "after_summary_before_commit"
        out[name] = {
            "fires": r["fires"], "expect_fire": r["expect_fire"],
            "ok_count": (r["fires"] == 1) if r["expect_fire"] else (r["fires"] == 0),
            "timing": timing, "order": r["order"],
            "fires_before_host_finalize": r["fires_before_finalize"] if name.startswith("manual") else None,
            "durable_at_fire": ev.get("durable_by_live_sid") if ev else None,
            "payload_keys": ev.get("keys") if ev else None,
            "compaction_committed_baseline": r["baseline_committed"],
            "compaction_committed_with_subscriber": r["observed_committed"],
            "output_identical_with_raising_and_directive_subscribers": r["output_identical"],
            "raised": r["raised"],
        }
    return out


arms_out = {}
for arm, rec in summary["arms"].items():
    a = {"commit": rec["commit"], "tree": rec["tree"], "hook_subscribed": rec["hook"] or "on_compression_complete",
         "contract_as_committed": reps(rec["cells"], "contract"),
         "contract_adapted_to_carrier_hook": reps(rec["cells"], "adapted")}
    if "probe" in rec:
        a["probe"] = {"passed": rec["probe"]["passed"], "failed": rec["probe"]["failed"],
                      "clauses": clauses(rec["probe"]["rows"])}
    patch = ST / "patches" / f"arm-{arm.replace('-pre', '')}.patch"
    if patch.exists():
        a["arm_patch"] = {"path": str(patch.relative_to(ST)), "sha256": sha256(patch)}
    arms_out[arm] = a

receipt = {
    "schema": "xf.receipt.v1",
    "id": f"F05/{run}",
    "label": "OBSERVED",
    "staging": "compaction-hook-salvage",
    "base_revision": main_sha,
    "staging_commit": base_commit,
    "harness": {"contract_test": "tests/agent/test_compaction_observer_hook_contract.py",
                "probe": "tools/chs_clause_probe.py", "runner": "tools/chs_ab_runner.py",
                "probe_sha256": sha256(ST / "tools" / "chs_clause_probe.py"),
                "runner_sha256": sha256(ST / "tools" / "chs_ab_runner.py")},
    "env": {"python": "<hermes-home>/hermes-agent/venv/bin/python (interpreter only)",
            "home": "isolated scratch HOME + HERMES_HOME; run_tests.sh env -i",
            "network": "loopback-only socket guard via tools/chs_loopback_guard.py (canary: raw/guard-canary.log)"},
    "arms": arms_out,
    "raw_dir": str(raw.relative_to(ST)),
    "summary_sha256": sha256(raw / "summary.json"),
}
(ST / "receipts").mkdir(exist_ok=True)
out = ST / "receipts" / f"F05-{run}.json"
out.write_text(json.dumps(receipt, indent=1))
print(out, sha256(out))
