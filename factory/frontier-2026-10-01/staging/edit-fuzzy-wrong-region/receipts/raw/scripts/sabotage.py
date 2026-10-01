"""Per-hunk sabotage of the GREEN arm's tools/fuzzy_match.py (negative control).

usage: sabotage.py <floor|single_line|foldin> <path>
  floor        drop #54575's content-divergence guard in fuzzy_find_and_replace
  single_line  drop #125376's single-line refusal in _strategy_context_aware
  foldin       revert only the fold-in (stripped-pattern test back to n == 1)
"""
import re
import sys

mode, path = sys.argv[1], sys.argv[2]
src = open(path, encoding="utf-8").read()

if mode == "floor":
    pat = re.compile(
        r"\n        if strategy_name in SIMILARITY_STRATEGIES:\n            matches = \[\n.*?\n            if not matches:\n                continue\n",
        re.S)
elif mode == "single_line":
    pat = re.compile(r"\n    if (?:n == 1|len\(pattern\.strip\(\)\.split\('\\n'\)\) == 1):\n(?:        #[^\n]*\n)*        return \[\]\n")
elif mode == "foldin":
    pat = re.compile(r"(?m)^    if len\(pattern\.strip\(\)\.split\('\\n'\)\) == 1:$")
else:
    raise SystemExit(f"unknown mode {mode}")

repl = "\n    if n == 1:" if mode == "foldin" else "\n"
if mode == "foldin":
    new, n = pat.subn("    if n == 1:", src)
else:
    new, n = pat.subn("\n", src)
if n != 1:
    raise SystemExit(f"sabotage {mode}: expected exactly 1 hunk, found {n}")
open(path, "w", encoding="utf-8").write(new)
print(f"sabotage {mode}: reverted 1 hunk in {path}", file=sys.stderr)
