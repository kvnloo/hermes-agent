"""Which workflows at the staged commit would a push of refs/heads/staged/<id> trigger? (GitHub reads workflow files from the pushed commit.)"""
import fnmatch, subprocess, sys, yaml
repo, commit, branch = sys.argv[1:4]
g = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
def glob_match(pat, name):  # GitHub filter globs: ** crosses '/', * does not
    import re
    rx = re.escape(pat).replace(r"\*\*", "\0").replace(r"\*", "[^/]*").replace("\0", ".*")
    return re.fullmatch(rx, name) is not None
matches = []
for f in g("ls-tree", "--name-only", f"{commit}:.github/workflows").split():
    d = yaml.safe_load(g("show", f"{commit}:.github/workflows/{f}")) or {}
    on = d.get(True, d.get("on"))
    if isinstance(on, str): on = {on: None}
    if isinstance(on, list): on = {k: None for k in on}
    if not isinstance(on, dict) or "push" not in on: continue
    p = on["push"] or {}
    br, ign, tags = p.get("branches"), p.get("branches-ignore"), p.get("tags")
    if br is None and ign is None and tags is not None: hit = False          # tags-only filter
    elif br is not None: hit = any(glob_match(b, branch) for b in br)
    elif ign is not None: hit = not any(glob_match(b, branch) for b in ign)
    else: hit = True                                                          # bare push: every branch
    print(f"{f}: push={p} -> {'MATCH' if hit else 'no match'}")
    matches += [f] if hit else []
print(f"branch={branch} commit={commit} push-trigger matches={len(matches)} {matches}")
