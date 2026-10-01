#!/usr/bin/env python3
"""Union the DESC and ASC sweeps, dedupe by PR number, report editors of the target path."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "website/docs/developer-guide/observer-hooks.md"


def load(name):
    rows = {}
    p = os.path.join(HERE, name)
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line:
                r = json.loads(line)
                rows[r["number"]] = r
    return rows


desc, asc = load("prs.jsonl"), load("prs_asc.jsonl")
num = {}
for i in range(4):
    num.update(load(f"prs_num_{i}.jsonl"))
extra = load("prs_rest.jsonl")   # REST re-reads of truncated/null file lists
allr = {**desc, **asc, **num}
opn = set(int(x) for x in open(os.path.join(HERE, "open_numbers.txt")).read().split())
print(f"cursor-desc={len(desc)} cursor-asc={len(asc)} by-number={len(num)} union={len(allr)}")
print(f"open enumerated={len(opn)} covered={len(opn & set(allr))} uncovered={len(opn - set(allr))} "
      f"null-node={sum(1 for r in num.values() if r.get('error'))} "
      f"state!=OPEN at fetch={sum(1 for r in num.values() if r.get('state') not in (None, 'OPEN'))}")
need_rest = sorted(n for n, r in allr.items()
                   if r["paths"] is None or (r["changedFiles"] or 0) > len(r["paths"]))
print(f"need REST file list (null or >100 files): {len(need_rest)}; done: {sum(1 for n in need_rest if n in extra)}")
hits = []
for n, r in sorted(allr.items()):
    paths = extra[n]["paths"] if n in extra else r["paths"]
    if paths and TARGET in paths:
        hits.append((n, r["author"], r["head"][:10], r["changedFiles"]))
print("editors of", TARGET, ":", hits)
if "--need-rest" in sys.argv:
    print(" ".join(str(n) for n in need_rest if n not in extra))
