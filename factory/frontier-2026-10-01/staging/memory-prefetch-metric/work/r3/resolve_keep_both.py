"""Resolve every conflict block in agent/memory_manager.py by keeping our lines, then theirs."""
import re
p = "agent/memory_manager.py"
src = open(p, encoding="utf-8").read()
pat = re.compile(r"<<<<<<< [^\n]*\n(?P<ours>.*?)\|\|\|\|\|\|\| [^\n]*\n.*?=======\n(?P<theirs>.*?)>>>>>>> [^\n]*\n", re.S)
n = len(pat.findall(src))
out = pat.sub(lambda m: m["ours"] + m["theirs"], src)
assert "<<<<<<<" not in out and ">>>>>>>" not in out
open(p, "w", encoding="utf-8").write(out)
print("blocks resolved:", n)
