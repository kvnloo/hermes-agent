#!/usr/bin/env python3
"""Round-1 fix for the r1/r2 receipts (factory-only, stdlib): scrub local paths, add the FACTORY §9.2 fields they
lacked, classify them under S16, and mark them superseded by the r3 receipts. Idempotent.

usage: chs_supersede_r1r2.py

Every r1/r2 cell built an AIAgent against the OpenRouter base URL with the r1 guard (connect() only). Each
agent init made a synchronous model-metadata GET (agent_init._enforce_minimum_context ->
model_metadata.get_model_context_length -> fetch_model_metadata), plus the once-per-process openrouter-prewarm
thread, so every cell had blocked connects and its DNS lookups left the process. Under FACTORY S16 that makes
every cell INFRA and each experiment INFRA. The observed pass/fail counts are kept as history only.
"""

from __future__ import annotations

import json
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
REPLACE = [
    ("$S/testhome-st-compaction-hook-salvage", "$TESTHOME"),
    ("$S", "$S"),
    ("$ARTIFACTS/promotion-readiness-2026-10-01/wt/staging/compaction-hook-salvage", "$WORKTREE"),
    ("$ARTIFACTS/frontier-2026-10-01/staging/compaction-hook-salvage/", ""),
    ("$ARTIFACTS/frontier-2026-10-01/staging/compaction-hook-salvage", "."),
    ("<hermes-home>/hermes-agent/venv/bin/python", "$PY"),
    ("<hermes-home>/hermes-agent/venv", "$VENV"),
    ("/usr/lib/python3.11", "$STDLIB"),
]
MOVED = [("patches/arm-", "patches/r2/arm-"), ("patches/staging-compaction-hook-salvage.patch", "patches/r2/staging-compaction-hook-salvage.patch"),
         ("patches/foldin-", "patches/r2/foldin-"), ("tools/chs_", "tools/r1/chs_")]
SUPERSEDED_BY = {
    "F05-f05-r1.json": "F05/f05-r3", "F05-f05-r2.json": "F05/f05-r3", "E12-e12-r2.json": "E12/e12-r3",
    "OWN-own-r1.json": "OWN/own-r3", "PROOF-r2.json": "PROOF/r3", "SANDBOX-guard-canary.json": "SANDBOX/guard-canary-r3",
}
BASES = {"F05-f05-r1.json": "572e4f4fad32bbdcfc948fb2ec833177ed5734c0"}
S16_INFRA = ("INFRA under FACTORY S16: every cell constructed AIAgent against the OpenRouter base URL; each init made a "
             "synchronous model-metadata GET (agent_init._enforce_minimum_context -> model_metadata.get_model_context_length "
             "-> fetch_model_metadata) and the process started the openrouter-prewarm thread. The r1 guard refused the "
             "connects but not the DNS lookups, which left the process. Every cell therefore had blocked attempts "
             "(infra rate 100% > 10%). Counts below are history only; r3 pins the context window in the test, suppresses "
             "the prewarm thread and guards DNS (0 blocked attempts).")


S16_RUNLEVEL = {
    "E12-e12-r2.json": ("INFRA under FACTORY S16 (unattributable): the r1 guard logged 616 blocked connects to openrouter.ai:443 for "
                        "the whole run, not per harness, and did not guard DNS. No cell can be shown clean, so every cell is "
                        "counted INFRA. Superseded by E12/e12-r3 (per-harness egress logs, 0 blocked attempts)."),
    "OWN-own-r1.json": ("INFRA under FACTORY S16 (unattributable): 928 blocked connects to openrouter.ai:443 logged for the whole "
                        "run, not per cell; DNS not guarded. Every cell is counted INFRA. Superseded by OWN/own-r3."),
    "PROOF-r2.json": ("INFRA: aggregates F05/f05-r1, F05/f05-r2 and E12/e12-r2, which are INFRA under S16. Superseded by PROOF/r3."),
}


def scrub(o):
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    if isinstance(o, str):
        for a, b in REPLACE:
            o = o.replace(a, b)
        for a, b in MOVED:
            if a in o and b not in o:
                o = o.replace(a, b)
        return o
    return o


def count_cells(d):
    n = 0
    for a in (d.get("arms") or {}).values():
        if isinstance(a, dict):
            for key in ("contract_as_committed", "contract_adapted_to_carrier_hook"):
                if isinstance(a.get(key), dict):
                    n += a[key].get("reps", 0)
            n += 1 if "probe" in a else 0
            n += sum(1 for h in ("replay_gates", "ab_checkpoint_preflight", "test_region_scoping", "adjacent") if h in a)
    n += len(d.get("cells") or [])
    return n or None


def main():
    for name, sup in SUPERSEDED_BY.items():
        p = ST / "receipts" / name
        d = scrub(json.loads(p.read_text()))
        canary = name.startswith("SANDBOX")
        n = count_cells(d) if not canary else 2
        d.setdefault("spec", {"path": None, "rev": 1 if "r1" in name or canary else 2, "sha256": None, "prereg_commit": None,
                              "note": "no xf_spec TOML was written"})
        d.setdefault("issue", None)
        d.setdefault("provenance", "self")
        d.setdefault("frozen", None)
        d.setdefault("privacy", "public-aggregate after the round-1 scrub: local paths replaced by placeholders ($S, $TESTHOME, $WORKTREE, $PY)")
        d.setdefault("evidence_class", {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"})
        d.setdefault("policy_revision", {"factory": "FACTORY.md (round 0; not hashed at the time)"})
        if canary:
            d["verdict"] = "PASS (connect() only)"
            d["gates"] = {"validity": "PARTIAL: connect() refused and logged; DNS lookups were not guarded, so 'loopback-only' overstated it"}
            d["denominators"] = {"cells": 2, "errored_scored_zero": 0, "infra_excluded": 0, "infra": 0, "completeness": 1.0}
        else:
            d["verdict"] = "INFRA"
            d.setdefault("gates", {})
            if isinstance(d["gates"], dict):
                d["gates"]["validity"] = "INFRA"
            d["denominators"] = {"cells": n, "errored_scored_zero": 0, "infra_excluded": 0, "infra": n, "completeness": 1.0}
            d["s16"] = S16_INFRA if name.startswith("F05") else S16_RUNLEVEL.get(name, S16_INFRA)
        d["superseded_by"] = sup
        d["round1_note"] = ("scrubbed and re-labelled in round 1 (2026-10-01): r1/r2 tool versions kept under tools/r1/ "
                            "(their sha256 values above still match), r2 patches moved to patches/r2/")
        txt = json.dumps(d, indent=1)
        assert "/tmp/" not in txt and "/home/" not in txt and "/mnt/" not in txt and "/workspace/" not in txt, name
        p.write_text(txt + "\n")
        print(name)


if __name__ == "__main__":
    main()
