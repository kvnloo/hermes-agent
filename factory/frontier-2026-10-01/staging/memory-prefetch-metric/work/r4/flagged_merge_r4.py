"""merge-tree of every flagged PR head (fullscan_r4.json) against current main and the staging head.
A PR that is clean on main but conflicts with the head is one this PR would collide with.
Usage: python flagged_merge_r4.py <h.git> <fullscan json> <out json>
"""
import datetime, json, subprocess, sys
hg, src, out = sys.argv[1:]
MAIN = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
flagged = json.load(open(src))["flagged"]
def head(n):
    import time
    for i in range(4):
        p = subprocess.run(["gh", "api", f"repos/NousResearch/hermes-agent/pulls/{n}", "--jq", "{h:.head.sha,u:.user.login,s:.state,t:.title}"],
                           capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout)
        time.sleep(15 * (i + 1))
    raise SystemExit(p.stderr)
def mt(a, b):
    p = subprocess.run(["git", "-C", hg, "merge-tree", "--write-tree", "--name-only", a, b], capture_output=True, text=True)
    lines = p.stdout.splitlines(); conf = []
    for ln in lines[1:]:
        if not ln.strip(): break
        conf.append(ln)
    if p.returncode not in (0, 1):
        return {"error": p.stderr.strip()[:200]}
    return {"clean": p.returncode == 0, "conflicts": conf}
res = {"checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "main": MAIN, "head": HEAD, "prs": {}}
for n in sorted(flagged, key=int):
    h = head(n)
    a, b = mt(MAIN, h["h"]), mt(HEAD, h["h"])
    cls = ("error" if "error" in a or "error" in b else
           "clean_both" if a["clean"] and b["clean"] else
           "conflicts_with_head_only" if a["clean"] and not b["clean"] else
           "conflicts_with_main_already" if not a["clean"] else "other")
    extra = sorted(set(b.get("conflicts", [])) - set(a.get("conflicts", [])))
    res["prs"][n] = {"author": h["u"], "state": h["s"], "title": h["t"], "pr_head": h["h"][:10], "class": cls,
                     "vs_main": a, "vs_staging_head": b, "extra_conflicts_with_head": extra}
    print(n, h["u"], h["h"][:10], cls, len(a.get("conflicts", [])), extra, flush=True)
res["summary"] = {}
for v in res["prs"].values():
    res["summary"][v["class"]] = res["summary"].get(v["class"], 0) + 1
json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
print(res["summary"])
