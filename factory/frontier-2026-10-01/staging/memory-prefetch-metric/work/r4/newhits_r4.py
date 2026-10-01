"""Merge-tree and metric-line check of the 7 search hits (round-3 list truncation) that touch watched files.

Usage: python newhits_r4.py <h.git> <out json>   (PR heads fetched beforehand with --no-write-fetch-head)
"""
import datetime, json, re, subprocess, sys
hg, out = sys.argv[1:]
MAIN = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
PRS = [58597, 63759, 64528, 91974, 98768, 108965, 119191]
def gh(*a):
    return json.loads(subprocess.run(["gh", "api", *a], capture_output=True, text=True, check=True).stdout)
def diff(n):
    return subprocess.run(["gh", "api", f"repos/NousResearch/hermes-agent/pulls/{n}", "-H", "Accept: application/vnd.github.diff"],
                          capture_output=True, text=True, check=True).stdout
def mt(a, b):
    p = subprocess.run(["git", "-C", hg, "merge-tree", "--write-tree", "--name-only", a, b], capture_output=True, text=True)
    lines = p.stdout.splitlines(); conf = []
    for ln in lines[1:]:
        if not ln.strip(): break
        conf.append(ln)
    return {"clean": p.returncode == 0, "conflicts": conf} if p.returncode in (0, 1) else {"error": p.stderr.strip()[:200]}
res = {"checked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "main": MAIN, "head": HEAD, "prs": {}}
for n in PRS:
    p = gh(f"repos/NousResearch/hermes-agent/pulls/{n}")
    d = diff(n)
    added = [ln for ln in d.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
    row = {"author": p["user"]["login"], "title": p["title"], "state": p["state"], "created_at": p["created_at"],
           "updated_at": p["updated_at"], "head": p["head"]["sha"][:10],
           "added_lines_matching_shared_metrics_telemetry_metric": sum(bool(re.search(r"shared_metrics|telemetry|metric", l, re.I)) for l in added),
           "touches_prefetch_provider": "_prefetch_provider" in d}
    if n in (58597, 63759, 108965):
        row["vs_main"] = mt(MAIN, p["head"]["sha"]); row["vs_staging_head"] = mt(HEAD, p["head"]["sha"])
    res["prs"][str(n)] = row
    print(n, row["author"], row["head"], row["added_lines_matching_shared_metrics_telemetry_metric"], row["touches_prefetch_provider"],
          {k: (row[k].get("clean"), len(row[k].get("conflicts", []))) for k in ("vs_main", "vs_staging_head") if k in row})
json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
