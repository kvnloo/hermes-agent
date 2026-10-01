import json, re, subprocess, sys
import yaml
G, ref, branch = sys.argv[1], sys.argv[2], sys.argv[3]
sha = subprocess.check_output(["git", "-C", G, "rev-parse", ref], text=True).strip()
files = [l for l in subprocess.check_output(["git", "-C", G, "ls-tree", "--name-only", sha, ".github/workflows/"], text=True).split() if l.endswith((".yml", ".yaml"))]
def glob_re(p):
    out = ""
    i = 0
    while i < len(p):
        if p[i:i+2] == "**": out += ".*"; i += 2
        elif p[i] == "*": out += "[^/]*"; i += 1
        elif p[i] == "?": out += "[^/]"; i += 1
        else: out += re.escape(p[i]); i += 1
    return re.compile("^" + out + "$")
push, matches = [], []
for f in files:
    doc = yaml.safe_load(subprocess.check_output(["git", "-C", G, "show", f"{sha}:{f}"], text=True)) or {}
    on = doc.get("on", doc.get(True))
    if isinstance(on, str): on = {on: None}
    if isinstance(on, list): on = {k: None for k in on}
    if not isinstance(on, dict) or "push" not in on: continue
    p = on["push"] or {}
    br, bi, tg = p.get("branches"), p.get("branches-ignore"), p.get("tags")
    push.append({"file": f, "branches": br, "branches-ignore": bi, "tags": tg})
    if br is None and bi is None and tg is None:
        matches.append(f); continue
    if br is not None:
        ok = any(glob_re(x).match(branch) for x in br if not x.startswith("!"))
        neg = any(glob_re(x[1:]).match(branch) for x in br if x.startswith("!"))
        if ok and not neg: matches.append(f)
    elif bi is not None:
        if not any(glob_re(x).match(branch) for x in bi): matches.append(f)
print(json.dumps({"ref": ref, "ref_sha": sha, "branch": branch, "push_workflows": push, "matching_branch_push": matches, "workflow_push_matches": len(matches)}, indent=1))
