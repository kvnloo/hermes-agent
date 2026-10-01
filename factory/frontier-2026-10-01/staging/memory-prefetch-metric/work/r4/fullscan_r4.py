"""Changed-file scan of every open PR returned by the 10 prefetch queries (recheck_r4.json), flagged against the
prefetch / shared-metrics files; for each flagged PR, count added diff lines naming shared_metrics/telemetry/metric
and whether the diff touches _prefetch_provider.  Usage: python fullscan_r4.py <recheck json> <out json>
"""
import datetime, json, re, subprocess, sys, time
src, out = sys.argv[1:]
r = json.load(open(src))
WATCH = re.compile(r["file_scan"]["watch_regex"])
nums = sorted({n for v in r["queries"].values() for n in v["numbers"]})
def run(args):
    for i in range(4):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0: return p.stdout
        time.sleep(15 * (i + 1))
    raise SystemExit(p.stderr)
res = {"started_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "watch_regex": WATCH.pattern, "scanned": len(nums), "prs": {}}
for n in nums:
    files = []
    for line in run(["gh", "api", "--paginate", f"repos/NousResearch/hermes-agent/pulls/{n}/files?per_page=100", "--jq", ".[].filename"]).splitlines():
        files.append(line)
    hits = [f for f in files if WATCH.match(f)]
    row = {"files": len(files), "watch_hits": hits}
    if hits:
        d = run(["gh", "api", f"repos/NousResearch/hermes-agent/pulls/{n}", "-H", "Accept: application/vnd.github.diff"])
        added = [l for l in d.splitlines() if l.startswith("+") and not l.startswith("+++")]
        row["added_metric_lines"] = [l[:160] for l in added if re.search(r"shared_metrics|telemetry|metric", l, re.I)][:8]
        row["touches_prefetch_provider"] = "_prefetch_provider" in d
        print(n, hits, len(row["added_metric_lines"]), row["touches_prefetch_provider"], flush=True)
    res["prs"][str(n)] = row
res["flagged"] = {k: v for k, v in res["prs"].items() if v["watch_hits"]}
res["finished_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
print("scanned", len(nums), "flagged", len(res["flagged"]))
