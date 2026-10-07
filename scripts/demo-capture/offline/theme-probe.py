#!/usr/bin/env python3
"""Read the value of CSS custom properties on Tern's root element, through a control endpoint.

probe.py SOCK TOKENS.txt OUT.json [SELECTOR]
Each token is shown as the element's background colour (`ctl css`) and read back from `ctl dump`.
"""
import json, os, subprocess, sys

sock, tokens_file, out = sys.argv[1:4]
selector = sys.argv[4] if len(sys.argv) > 4 else "html"
tokens = [t.strip() for t in open(tokens_file) if t.strip()]
work = os.path.join(os.path.dirname(os.path.abspath(out)), "css-" + os.path.basename(out).split(".")[0])
os.makedirs(work, exist_ok=True)
SENTINEL = "rgba(1, 2, 3, 0.5)"
values = {}
def ctl(*args):
    return subprocess.run(["tern", "ctl", "--control", sock, *args], capture_output=True, text=True).stdout
for i, token in enumerate(tokens):
    path = f"{work}/{i:04d}.css"
    open(path, "w").write(f"{selector} {{ background-color: var({token}, {SENTINEL}) !important; }}\n")
    ctl("css", "zz-probe", path)
    value = json.loads(ctl("dump", selector))["elements"][0]["backgroundColor"]
    if value.replace(" ", "") != SENTINEL.replace(" ", ""):
        values[token] = value
ctl("css", "zz-probe")
json.dump(values, open(out, "w"), indent=1)
print(f"{len(values)} of {len(tokens)} tokens resolve to a colour on {selector} -> {out}")
