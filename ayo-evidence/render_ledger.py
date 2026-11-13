#!/usr/bin/env python3
"""Render AYO-LEDGER.md from ayo-ledger.json (the source of truth). Usage: render_ledger.py [id status evidence note]"""
import json, sys, os, datetime
D = os.path.dirname(os.path.abspath(__file__))
J = os.path.join(D, "ayo-ledger.json")
sys.path.insert(0, D)
import fcntl, ledger_journal as lj
with open(lj.LOCK, "w") as _lf:
    fcntl.flock(_lf, fcntl.LOCK_EX)
    rows = json.load(open(J))
    if len(sys.argv) >= 3:
        rid, st = sys.argv[1], sys.argv[2]
        if not [r for r in rows if r["id"] == rid]:
            sys.exit(f"no row {rid}")
        lj.record(rid, st, sys.argv[3] if len(sys.argv) > 3 else "", sys.argv[4] if len(sys.argv) > 4 else "")
    rows = lj.replay(rows)
    lj.save(rows)

def cell(s):
    return (s or "").replace("|", "/").replace("\n", " ")

counts = {}
for r in rows:
    counts[r["status"]] = counts.get(r["status"], 0) + 1
out = [f"# AYO-LEDGER (rendered {datetime.datetime.now():%Y-%m-%d %H:%M} CT from ayo-ledger.json)", "",
       "Status: done (evidence checked by ayo) / blocked-kevin / in-progress / open. " +
       ", ".join(f"{k}={v}" for k, v in sorted(counts.items())), "", "## Needs Kevin", ""]
nk = [r for r in rows if r["status"] == "blocked-kevin"]
out += [f"- {r['id']} ({r['owner']}): {cell(r['note'] or r['ask'])}" for r in nk] or ["- none"]
out += ["", "## All rows", "", "| id | owner | ask | done-check | status | evidence | note |", "|---|---|---|---|---|---|---|"]
for r in rows:
    out.append(f"| {r['id']} | {r['owner']} | {cell(r['ask'])} | {cell(r['check'])} | {r['status']} | {cell(r['evidence'])} | {cell(r['note'])} |")
open(os.path.join(D, "AYO-LEDGER.md"), "w").write("\n".join(out) + "\n")
print(", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
