"""Resolve diff3 conflicts where main deleted a block (ours empty) and the carrier
kept it and added new code next to it: keep main's deletion, keep the carrier's
additions. Refuses anything else so nothing is silently resolved.

usage: resolve_drop_base.py <conflicted file> <out file>
"""
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
pat = re.compile(r"<<<<<<< [^\n]*\n(.*?)\|\|\|\|\|\|\| [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n", re.S)


def resolve(m):
    ours, base, theirs = m.group(1), m.group(2), m.group(3)
    if ours.strip():
        raise SystemExit(f"ours side is not empty; refusing: {ours[:200]!r}")
    if base.strip() not in theirs:
        raise SystemExit("base block not contained in theirs; refusing")
    added = theirs.replace(base.strip(), "", 1)
    return added.strip("\n") + "\n"


out, n = pat.subn(resolve, text)
if "<<<<<<<" in out or ">>>>>>>" in out:
    raise SystemExit("unresolved markers remain")
open(sys.argv[2], "w", encoding="utf-8").write(out)
print(f"resolved {n} conflict(s) -> {sys.argv[2]}")
