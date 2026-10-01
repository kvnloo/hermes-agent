"""Scan .github/workflows for push triggers that would fire for a given branch name (GitHub glob rules)."""
import fnmatch, json, re, sys
from pathlib import Path
import yaml

root, branches = Path(sys.argv[1]), sys.argv[2:]

def gh_glob(pat, name):
    # GitHub filter globs: '*' does not match '/', '**' matches anything; '?','+','[]' rare here.
    rx = ""
    i = 0
    while i < len(pat):
        if pat.startswith("**", i):
            rx += ".*"; i += 2
        elif pat[i] == "*":
            rx += "[^/]*"; i += 1
        elif pat[i] == "?":
            rx += "."; i += 1
        else:
            rx += re.escape(pat[i]); i += 1
    return re.fullmatch(rx, name) is not None

def fires(push, name):
    if push is None:
        return True  # bare 'push' fires on every branch
    if isinstance(push, dict):
        inc, exc = push.get("branches"), push.get("branches-ignore")
        if inc is None and exc is None:
            return "tags" not in push and "tags-ignore" not in push or "paths" in push
        if inc is not None:
            ok = False
            for p in inc:
                if p.startswith("!"):
                    if gh_glob(p[1:], name): ok = False
                elif gh_glob(p, name):
                    ok = True
            return ok
        return not any(gh_glob(p, name) for p in exc)
    return True

rows = []
for f in sorted(list(root.glob(".github/workflows/*.yml")) + list(root.glob(".github/workflows/*.yaml"))):
    d = yaml.safe_load(f.read_text())
    on = d.get(True, d.get("on")) if isinstance(d, dict) else None
    if on is None:
        continue
    if isinstance(on, str):
        on = {on: None}
    elif isinstance(on, list):
        on = {k: None for k in on}
    if "push" not in on:
        continue
    push = on["push"]
    rows.append({"file": f.name, "filter": push, **{b: fires(push, b) for b in branches}})
print(json.dumps({"push_workflows": len(rows), "matches": {b: [r["file"] for r in rows if r[b]] for b in branches},
                  "rows": rows}, indent=1, default=str))
