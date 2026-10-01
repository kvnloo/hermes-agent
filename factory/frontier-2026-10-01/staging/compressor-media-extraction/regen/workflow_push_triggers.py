#!/usr/bin/env python3
"""Read-only: parse every .github/workflows/*.yml at a ref via the contents API; report push triggers
and whether a branch push of `staged/compressor-media-extraction` (no tags) matches any of them."""
import base64, fnmatch, json, re, subprocess, sys
import yaml

ref = sys.argv[1]
BR = "staged/compressor-media-extraction"


def gh(path):
    return json.loads(subprocess.run(["gh", "api", path], capture_output=True, text=True, check=True).stdout)


def glob_match(pat, name):
    # GitHub filter patterns: ** matches any chars incl '/', * matches any chars except '/'
    rx = ""
    i = 0
    while i < len(pat):
        if pat.startswith("**", i):
            rx += ".*"; i += 2
        elif pat[i] == "*":
            rx += "[^/]*"; i += 1
        elif pat[i] == "?":
            rx += "[^/]"; i += 1
        else:
            rx += re.escape(pat[i]); i += 1
    return re.fullmatch(rx, name) is not None


items = gh(f"repos/NousResearch/hermes-agent/contents/.github/workflows?ref={ref}")
wfs = [i for i in items if i["name"].endswith((".yml", ".yaml"))]
rows = []
matches = 0
for it in sorted(wfs, key=lambda x: x["name"]):
    c = gh(f"repos/NousResearch/hermes-agent/contents/.github/workflows/{it['name']}?ref={ref}")
    doc = yaml.safe_load(base64.b64decode(c["content"]))
    on = doc.get(True, doc.get("on")) if isinstance(doc, dict) else None
    push = None
    if isinstance(on, str):
        push = {} if on == "push" else None
    elif isinstance(on, list):
        push = {} if "push" in on else None
    elif isinstance(on, dict) and "push" in on:
        push = on["push"] or {}
    if push is None:
        continue
    br = push.get("branches"); bri = push.get("branches-ignore"); tags = push.get("tags"); tagi = push.get("tags-ignore")
    # branch push: if only tags filters are set (no branches filter), branch pushes do NOT trigger
    if br is None and bri is None and (tags is not None or tagi is not None):
        m = False
    elif br is not None:
        pos = [p for p in br if not p.startswith("!")]
        neg = [p[1:] for p in br if p.startswith("!")]
        m = any(glob_match(p, BR) for p in pos) and not any(glob_match(p, BR) for p in neg)
    elif bri is not None:
        m = not any(glob_match(p, BR) for p in bri)
    else:
        m = True
    matches += m
    rows.append({"workflow": it["name"], "branches": br, "branches_ignore": bri, "tags": tags, "tags_ignore": tagi,
                 "paths": push.get("paths"), "branch_push_matches": m})
print(json.dumps({"ref": ref, "workflows_parsed": len(wfs), "with_push_trigger": rows, "branch_push_matches": matches}, indent=1))
