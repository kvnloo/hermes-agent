"""Naive resolution of the #92118 conflict in agent/memory_manager.py: keep both sides' lines."""
import re, sys
p = "agent/memory_manager.py"
src = open(p, encoding="utf-8").read()
pat = re.compile(r"<<<<<<< [^\n]*\n(?P<ours>.*?)\|\|\|\|\|\|\| [^\n]*\n.*?=======\n(?P<theirs>.*?)>>>>>>> [^\n]*\n", re.S)
blocks = pat.findall(src)
assert len(blocks) == 1, len(blocks)
def keep_both(m):
    ours = [l for l in m["ours"].splitlines(keepends=True) if "record_memory_prefetch" in l]
    return "".join(ours) + m["theirs"]
out = pat.sub(keep_both, src)
assert "<<<<<<<" not in out and ">>>>>>>" not in out
open(p, "w", encoding="utf-8").write(out)
print("resolved:", [l.strip() for l in out.splitlines() if "record_memory_prefetch(provider.name, \"success\"" in l or "isinstance(result, str) and result.strip()" in l])
