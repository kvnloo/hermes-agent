"""Append-only status journal for ayo-ledger.json.

Other sessions rewrite ayo-ledger.json from stale copies. Every ayo status change also goes to
ledger-journal.jsonl; replay() re-applies the latest journal entry per row on each render, so a
stale rewrite can't revert a status. Writes are flock-guarded and atomic (tmp + rename).
"""
import fcntl, json, os, time

D = os.path.dirname(os.path.abspath(__file__))
J = os.path.join(D, "ayo-ledger.json")
L = os.path.join(D, "ledger-journal.jsonl")
LOCK = J + ".lock"  # same sidecar lock as intake_ledger_match


def locked(fn):
    def wrap(*a, **k):
        with open(LOCK, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            return fn(*a, **k)
    return wrap


def record(rid, status, evidence="", note=""):
    with open(L, "a") as f:
        f.write(json.dumps({"ts": time.time(), "id": rid, "status": status, "evidence": evidence, "note": note}) + "\n")


def replay(rows):
    latest = {}
    if os.path.exists(L):
        for line in open(L):
            e = json.loads(line)
            latest[e["id"]] = e
    by = {r["id"]: r for r in rows}
    for rid, e in latest.items():
        r = by.get(rid)
        if not r:
            continue
        r["status"] = e["status"]
        if e["evidence"]:
            r["evidence"] = e["evidence"]
        if e["note"]:
            r["note"] = e["note"]
    return rows


def save(rows):
    tmp = J + ".tmp"
    json.dump(rows, open(tmp, "w"), indent=1)
    os.replace(tmp, J)
