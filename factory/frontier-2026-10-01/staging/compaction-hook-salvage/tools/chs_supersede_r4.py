#!/usr/bin/env python3
"""Round-3 fix for the r4 receipts (factory-only, stdlib): mark them superseded by r5. Idempotent.
Measurements, verdicts and validity fields are kept as issued; only superseded_by / superseded_why are added.

usage: chs_supersede_r4.py

Why: round 3 rebuilt the staging commit on main 44a1ce9724 with a fence/lease clause in the fires-once case (the
observer must run after the attempt has released its commit fence and the session's compression lease: the #118120
hazard), and the offered fold-in moved into a sibling module and delivers the observer after the fence. The r4 fold-in
ran the observer inside the fence, so its GREEN no longer describes the offer. The r4 canary stays the guard's proof:
the egress guard file is unchanged (same sha256), so it is not superseded.
"""

from __future__ import annotations

import json
from pathlib import Path

ST = Path(__file__).resolve().parents[1]
SUPERSEDED_BY = {
    "F05-f05-r4.json": "F05/f05-r5", "E12-e12-r4.json": "E12/e12-r5", "OWN-own-r4.json": "OWN/own-r5",
    "PROOF-r4.json": "PROOF/r5",
}
WHY = ("round 3 rebuilt the staging commit on main 44a1ce9724 with a fence/lease clause (the observer must run after the "
       "attempt releases its commit fence and the session's compression lease, the #118120 hazard) and moved the offered "
       "fold-in into a sibling module that delivers the observer after the fence, as #127058 does for the memory hook. The "
       "r4 fold-in ran the observer inside the fence; re-applied as arm r4-offer-r5 it fails that clause (F05/f05-r5)")


def main() -> int:
    for name, succ in SUPERSEDED_BY.items():
        p = ST / "receipts" / name
        d = json.loads(p.read_text(encoding="utf-8"))
        d["superseded_by"] = succ
        d["superseded_why"] = WHY
        p.write_text(json.dumps(d, indent=1, default=str) + "\n", encoding="utf-8")
        print(name, "->", succ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
