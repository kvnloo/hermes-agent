"""merge-tree matrix: each open PR that edits the prefetch path vs current main, the staging head and the round-2 head.

Usage: python merge_matrix_r3.py <h.git> <main sha> <staging head sha> <out json>   (read-only on the repo)
"""
import datetime
import json
import subprocess
import sys

hg, main, head, out = sys.argv[1:]
arms = {"main": main, "staging_head": head, "round2_head": "519876fa02f5e5812f5763cef03c5fed054d6cf7"}
prs = {124151: ("kweez007", "3ee6189dbad0485790893c5098b20f00d27a1d51"), 120042: ("Navlem", "641f6b94c5"),
       98045: ("Navlem", "77f018b7db"), 92118: ("seradin", "2ad5cc73fac3e519deec7d4d9ff6eccb494aa953"),
       126457: ("mozhongzhou", "822f7b2835"), 87028: ("richardclawbot", "f63bfa2a5c"), 86948: ("V0v1kkkAssistant", "cc1c2a1f2c"),
       65329: ("Soju06", "c868eaaa02"), 125802: ("Finn763", "543af5de19"), 78584: ("iso2kx", "e7c6f83e8a")}


def mt(a, b):
    p = subprocess.run(["git", "-C", hg, "-c", "credential.helper=", "merge-tree", "--write-tree", "--name-only", a, b],
                       capture_output=True, text=True)
    lines = p.stdout.splitlines()
    conf = []
    for ln in lines[1:]:
        if not ln.strip():
            break
        conf.append(ln)
    return {"clean": p.returncode == 0, "tree": lines[0][:10] if lines else None, "conflicts": conf}


def full(h):
    return subprocess.run(["git", "-C", hg, "rev-parse", h], capture_output=True, text=True).stdout.strip()


res = {"checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "main": main, "arms": arms, "prs": {}}
for n, (author, h) in prs.items():
    row = {"author": author, "pr_head": full(h)}
    for k, v in arms.items():
        row[k] = mt(v, h)
    res["prs"][str(n)] = row
    print(n, author, row["pr_head"][:10], {k: (row[k]["clean"], len(row[k]["conflicts"])) for k in arms})
res["staging_head_vs_main"] = mt(main, head)
print("staging head vs main", res["staging_head_vs_main"])
json.dump(res, open(out, "w"), indent=1)
