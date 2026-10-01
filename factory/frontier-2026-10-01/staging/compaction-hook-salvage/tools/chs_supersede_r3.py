#!/usr/bin/env python3
"""Round-2 fix for the r3 receipts (factory-only, stdlib): re-label them under S16 and mark them superseded by r4.
Idempotent. Measurements are kept as issued; only verdict/validity fields and notes change.

usage: chs_supersede_r3.py

The r3 egress guard refused to start the openrouter-prewarm thread (logged as prewarm_suppressed). That thread is
an egress attempt (one getaddrinfo('openrouter.ai') per pytest worker), and the round-1 contract test itself
triggered it, so "0 dns" in F05 r3 held only because the guard hid it. Every F05 r3 cell logged at least one
prewarm_suppressed line, so under a strict S16 reading every cell had a prevented egress attempt: F05 r3 is
INFRA. E12/OWN r3 already needed the (never accepted) S16 exception, and that exception's bullet "the new
contract test itself makes 0 lookups (F05 r3: 0 dns in 78 cells)" is false. The canary r3 PASS stands for
what it tested, but its suppression design is retired.
"""

from __future__ import annotations

import json
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
SUPERSEDED_BY = {
    "F05-f05-r3.json": "F05/f05-r4", "E12-e12-r3.json": "E12/e12-r4", "OWN-own-r3.json": "OWN/own-r4",
    "PROOF-r3.json": "PROOF/r4", "SANDBOX-guard-canary-r3.json": "SANDBOX/guard-canary-r4",
}
WHY = ("the r3 guard refused to start the openrouter-prewarm thread (prewarm_suppressed), which hid one DNS lookup per "
       "pytest worker; the round-1 contract test itself triggered that thread. Round 2 stubs the metadata prewarm in the "
       "test and uses an r4 guard that suppresses nothing")
BAD_BULLET = "the new contract test itself makes 0 lookups (F05 r3: 0 dns in 78 cells)"


def relabel(name: str, d: dict) -> dict:
    if "verdict_as_issued" not in d:
        d["verdict_as_issued"] = d.get("verdict")
    if name.startswith("F05"):
        d["verdict"] = "INFRA"
        if isinstance(d.get("gates"), dict):
            d["gates"]["validity_as_issued"] = d["gates"].get("validity_as_issued", d["gates"].get("validity"))
            d["gates"]["validity"] = "INFRA"
        cells = d["denominators"]["cells"]
        d["denominators"] = {**d["denominators"], "infra": cells}
        d["s16_round2"] = (f"INFRA under a strict S16 reading: all {cells} cells logged prewarm_suppressed (129 in total), "
                           "i.e. a prevented egress attempt from the openrouter-prewarm thread. Pass/fail counts are kept as history.")
    elif name.startswith(("E12", "OWN")):
        d["verdict"] = "INFRA" if name.startswith("E12") else d.get("verdict")
        if isinstance(d.get("gates"), dict):
            d["gates"]["validity_as_issued"] = d["gates"].get("validity_as_issued", d["gates"].get("validity"))
            d["gates"]["validity"] = "INFRA (strict S16; the recorded exception was never accepted and one of its premises is false)"
        exc = (d.get("egress") or {}).get("s16_exception")
        if isinstance(exc, dict):
            bullets = exc.get("why_results_stand", [])
            exc["why_results_stand"] = [b if b != BAD_BULLET else
                                        b + " [round-2 correction: false. The r3 guard did not start the openrouter-prewarm "
                                            "thread, which the contract test triggered: 1 blocked lookup per pytest worker under "
                                            "a guard that suppresses nothing. See SANDBOX/guard-canary-r4 contract_test_prewarm_check]"
                                        for b in bullets]
            exc["status"] = "recorded exception, never accepted by the owner; superseded by the r4 exception text in E12/e12-r4"
    elif name.startswith("PROOF"):
        d["verdict"] = "INFRA"
        d["verdict_note_round2"] = "aggregates F05/f05-r3 and E12/e12-r3, both INFRA under strict S16 after the round-2 re-label"
    else:  # canary
        d["round2_note"] = ("PASS stands for the five cases it tested, but the suppression it proved (openrouter-prewarm not "
                            "started) is retired: it hid an egress attempt. r4 guard and canary suppress nothing")
    d["superseded_by"] = SUPERSEDED_BY[name]
    d["superseded_why"] = WHY
    return d


def main():
    for name in SUPERSEDED_BY:
        p = ST / "receipts" / name
        d = relabel(name, json.loads(p.read_text()))
        txt = json.dumps(d, indent=1)
        assert "/tmp/" not in txt and "/home/" not in txt and "/mnt/" not in txt and "/workspace/" not in txt, name
        p.write_text(txt + "\n")
        print(name)


if __name__ == "__main__":
    main()
