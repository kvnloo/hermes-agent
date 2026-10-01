"""Round-5 recheck for memory-prefetch-metric (read-only on GitHub; git fetch by SHA with --no-write-fetch-head,
so no ref is written; merge-tree on the local object store).

Taken after #126457 closed (2026-10-01T16:23:32Z), so every state below post-dates that close.

1. current upstream main (ls-remote), commits since the staging base, invalidate_on and .github changes, merge-tree of
   the staging head against it;
2. state, head and close details of every upstream PR/issue that STAGING.md, PR_BODY.md or OWNERSHIP r03 cites, plus
   the fork threads and the fork branch name;
3. #126457: close event, comments, head, cross-references, and the author's other PRs (replacement check);
4. the 10 open-PR prefetch queries (all pages) and the teknium1 open-PR set;
5. changed files of every open search hit, flagged against the prefetch / shared-metrics files;
6. merge-tree of every flagged PR head against current main and the staging head, diffed against round 4
   (OWNERSHIP r03's matrix), and the _prefetch_provider record/return counts in each clean merged tree.

Usage: python recheck_r5.py <h.git> <out json>
"""
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path

hg, out = sys.argv[1:]
HERE = Path(__file__).resolve().parent
R3, R4 = HERE.parent / "r3", HERE.parent / "r4"
REPO = "NousResearch/hermes-agent"
BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
INVALIDATE_ON = ["agent/memory_manager.py", "hermes_cli/observability/shared_metrics_loop.py",
                 "hermes_cli/observability/shared_metrics_contract.py",
                 "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
                 "tests/hermes_cli/test_shared_metrics_loop.py", "website/docs/developer-guide/relay-shared-metrics.md",
                 "agent/memory_provider.py", "agent/turn_context.py"]
WATCH = re.compile(r"^(agent/memory_manager\.py|agent/memory_provider\.py|agent/turn_context\.py|"
                   r"hermes_cli/observability/shared_metrics[^/]*\.py|hermes_cli/observability/schemas/.*shared_metrics.*)$")
QUERIES = ["prefetch metric", "prefetch telemetry", "memory prefetch", "prefetch_provider", "prefetch shared metrics",
           "memory.prefetch", "record_memory_prefetch", "external prefetch", "prefetch timeout", "prefetch latency"]
# every upstream number STAGING.md, PR_BODY.md and OWNERSHIP r03 cite (r03's 19, the 11 clean pairs, #98703)
CITED = [98045, 87028, 124151, 120042, 47119, 21566, 92118, 126457, 86948, 65329, 125802, 15412, 113678, 78584,
         127373, 127374, 127375, 127332, 127228,
         125881, 108965, 129620, 64421, 68903, 81582, 84360, 115109, 115694, 98703,
         58597, 63759, 84412, 101580]
ADJ = {124151: "3ee6189dba", 120042: "641f6b94c5", 92118: "2ad5cc73fa", 126457: "822f7b2835",
       87028: "f63bfa2a5c", 86948: "cc1c2a1f2c", 65329: "c868eaaa02", 125802: "543af5de19", 125881: "d3fdffcf82",
       108965: "39dd41fe68", 15412: "69c5a41321"}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(*a, check=True):
    p = subprocess.run(list(a), capture_output=True, text=True)
    if check and p.returncode:
        raise SystemExit(f"{a}: {p.returncode} {p.stderr}")
    return p


def gh(path, *fields, paginate=False, accept=None, raw=False):
    args = ["gh", "api", "-X", "GET", path]
    for f in fields:
        args += ["-f", f]
    if accept:
        args += ["-H", f"Accept: {accept}"]
    if paginate:
        args.append("--paginate")
    for attempt in range(5):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0:
            break
        time.sleep(15 * (attempt + 1))
    else:
        raise SystemExit(f"gh {path}: {p.stderr}")
    if raw:
        return p.stdout
    if paginate:
        dec, s, i, docs = json.JSONDecoder(), p.stdout.strip(), 0, []
        while i < len(s):
            obj, j = dec.raw_decode(s, i)
            docs.append(obj)
            i = j
            while i < len(s) and s[i].isspace():
                i += 1
        return docs
    return json.loads(p.stdout)


def flat(docs):
    out = []
    for d in docs:
        out.extend(d if isinstance(d, list) else d.get("items", []))
    return out


def git(*a, check=True):
    return sh("git", "-C", hg, "-c", "credential.helper=", *a, check=check)


def fetch(shas):
    shas = [s for s in shas if git("cat-file", "-e", f"{s}^{{commit}}", check=False).returncode]
    for i in range(0, len(shas), 20):
        git("fetch", "--no-write-fetch-head", "--no-tags", "--filter=blob:none", "origin", *shas[i:i + 20])


res = {"started_at": now()}

# 1. main ------------------------------------------------------------------------------------------
main = sh("git", "ls-remote", f"https://github.com/{REPO}.git", "refs/heads/main").stdout.split()[0]
res["main"] = {"sha": main, "ls_remote_at": now()}
fetch([main])
m = res["main"]
m["committer_date"] = git("log", "-1", "--format=%cI", main).stdout.strip()
m["base_is_ancestor"] = git("merge-base", "--is-ancestor", BASE, main, check=False).returncode == 0
m["commits_since_base"] = int(git("rev-list", "--count", f"{BASE}..{main}").stdout)
m["commits_since_r4_main"] = int(git("rev-list", "--count", f"44a1ce9724502b9c692faaef00af3054bf11f1a6..{main}").stdout)
m["invalidate_on_commits_since_base"] = git("log", "--format=%h %s", f"{BASE}..{main}", "--", *INVALIDATE_ON).stdout.splitlines()
m["invalidate_on_blobs_equal_base"] = {
    f: git("rev-parse", f"{BASE}:{f}").stdout.strip() == git("rev-parse", f"{main}:{f}").stdout.strip() for f in INVALIDATE_ON}
m["github_commits_since_base"] = git("log", "--format=%h %s", f"{BASE}..{main}", "--", ".github").stdout.splitlines()
m["workflow_files"] = len([x for x in git("ls-tree", "--name-only", f"{main}:.github/workflows").stdout.splitlines() if x.endswith((".yml", ".yaml"))])
mt = git("merge-tree", "--write-tree", main, HEAD, check=False)
m["merge_tree_head"] = {"clean": mt.returncode == 0, "tree": mt.stdout.split()[0] if mt.stdout else None}
m["prefetch_grep_since_base"] = git("log", "--format=%h %s", "-i", "--grep=prefetch", f"{BASE}..{main}").stdout.splitlines()
res["staging_ref"] = git("rev-parse", "refs/heads/staging/memory-prefetch-metric").stdout.strip()
fork_refs = sh("git", "ls-remote", "https://github.com/kvnloo/hermes-agent.git", "refs/heads/staged/*", "refs/heads/staging",
               "refs/heads/staging/*").stdout.splitlines()
res["fork_refs"] = {"checked_at": now(), "refs": [ln.split()[1] for ln in fork_refs],
                    "staged_memory_prefetch_metric_present": any(ln.endswith("refs/heads/staged/memory-prefetch-metric") for ln in fork_refs)}
print("main", main[:10], m["commits_since_base"], m["invalidate_on_commits_since_base"], m["merge_tree_head"], flush=True)

# 2. cited ------------------------------------------------------------------------------------------
res["cited_checked_at"] = now()
cited = {}
for n in CITED:
    d = gh(f"repos/{REPO}/issues/{n}")
    row = {"state": d["state"], "state_reason": d.get("state_reason"), "is_pr": "pull_request" in d,
           "author": d["user"]["login"], "created_at": d["created_at"], "closed_at": d["closed_at"],
           "updated_at": d["updated_at"], "merged_at": (d.get("pull_request") or {}).get("merged_at"),
           "title": d["title"]}
    if row["is_pr"]:
        p = gh(f"repos/{REPO}/pulls/{n}")
        row["head"] = p["head"]["sha"]
        row["mergeable_state"] = p.get("mergeable_state")
    if row["state"] == "closed":
        row["closed_by"] = [e["actor"]["login"] for e in flat(gh(f"repos/{REPO}/issues/{n}/events", paginate=True))
                            if e["event"] == "closed"]
        row["comments_since_2026_09_25"] = [{"user": c["user"]["login"], "at": c["created_at"], "body": c["body"][:600]}
                                            for c in flat(gh(f"repos/{REPO}/issues/{n}/comments", paginate=True))
                                            if c["created_at"] >= "2026-09-25"]
    cited[str(n)] = row
    print(n, row["state"], (row.get("head") or "")[:10], row.get("closed_at"), flush=True)
res["cited"] = cited

# 3. #126457 detail and replacement check ---------------------------------------------------------------
tl = flat(gh(f"repos/{REPO}/issues/126457/timeline", "per_page=100", paginate=True))
res["pr126457"] = {
    "timeline": [{"event": e.get("event"), "at": e.get("created_at"),
                  "actor": (e.get("actor") or e.get("user") or {}).get("login"),
                  "source": ((e.get("source") or {}).get("issue") or {}).get("number")} for e in tl],
    "all_comments": [{"user": c["user"]["login"], "at": c["created_at"], "body": c["body"][:600]}
                     for c in flat(gh(f"repos/{REPO}/issues/126457/comments", paginate=True))],
    "review_comments": len(flat(gh(f"repos/{REPO}/pulls/126457/comments", paginate=True))),
    "files": [f["filename"] for f in flat(gh(f"repos/{REPO}/pulls/126457/files", "per_page=100", paginate=True))],
}
auth = flat(gh("search/issues", f"q=repo:{REPO} is:pr author:mozhongzhou", "per_page=100", paginate=True))
res["mozhongzhou_prs"] = []
for it in sorted(auth, key=lambda x: x["number"]):
    row = {"number": it["number"], "state": it["state"], "created_at": it["created_at"], "closed_at": it["closed_at"],
           "title": it["title"]}
    if it["state"] == "open" or it["created_at"] >= "2026-09-25":
        files = [f["filename"] for f in flat(gh(f"repos/{REPO}/pulls/{it['number']}/files", "per_page=100", paginate=True))]
        row["watch_hits"] = [f for f in files if WATCH.match(f)]
    res["mozhongzhou_prs"].append(row)
print("mozhongzhou", [(r["number"], r["state"], r.get("watch_hits")) for r in res["mozhongzhou_prs"]], flush=True)

fork = {}
for n in [404, 322, 402, 403]:
    d = gh(f"repos/kvnloo/hermes-agent/issues/{n}")
    body = d.get("body") or ""
    table = [ln for ln in body.splitlines() if ln.startswith("|")]
    fork[str(n)] = {"state": d["state"], "title": d["title"], "table_rows": max(len(table) - 2, 0) if table else 0,
                    "mentions_prefetch": "prefetch" in body.lower()}
res["fork"] = fork
kv = flat(gh("search/issues", "q=repo:kvnloo/hermes-agent prefetch", "per_page=100", paginate=True))
res["fork_prefetch_hits"] = [it["number"] for it in kv]
time.sleep(3)

# 4. queries and teknium1 -----------------------------------------------------------------------------
res["searched_at"] = now()
queries, union = {}, set()
for q in QUERIES:
    docs = gh("search/issues", f"q=repo:{REPO} is:pr is:open {q}", "per_page=100", paginate=True)
    items = flat(docs)
    nums = sorted({it["number"] for it in items})
    union |= set(nums)
    queries[q] = {"total_count": docs[0]["total_count"], "listed": len(nums), "numbers": nums,
                  "titles": {str(it["number"]): [it["user"]["login"], it["title"]] for it in items}}
    print(q, queries[q]["total_count"], len(nums), flush=True)
    time.sleep(3)
res["queries"] = queries
r4scan = json.loads((R4 / "fullscan_r4.json").read_text())
r4nums = {int(k) for k in r4scan["prs"]}
res["union"] = {"count": len(union), "added_vs_r4": sorted(union - r4nums), "removed_vs_r4": sorted(r4nums - union)}
t3 = {d["number"] for d in json.loads((R3 / "teknium1_open_r3.json").read_text())}
docs = gh("search/issues", f"q=repo:{REPO} is:pr is:open author:teknium1", "per_page=100", paginate=True)
tk = {it["number"]: it["title"] for it in flat(docs)}
res["teknium1"] = {"total_count": docs[0]["total_count"], "listed": len(tk), "same_set_as_r3": set(tk) == t3,
                   "added": sorted(set(tk) - t3), "removed": sorted(t3 - set(tk)),
                   "title_hits": sorted(n for n, t in tk.items() if re.search(r"prefetch|telemetry|metric", t, re.I))}
print("teknium1", res["teknium1"]["total_count"], res["teknium1"]["same_set_as_r3"], res["teknium1"]["added"],
      res["teknium1"]["removed"], flush=True)
tk_scan = {}
for n in res["teknium1"]["added"]:
    files = [f["filename"] for f in flat(gh(f"repos/{REPO}/pulls/{n}/files", "per_page=100", paginate=True))]
    tk_scan[str(n)] = [f for f in files if WATCH.match(f) or "shared_metrics" in f]
res["teknium1"]["added_file_hits"] = tk_scan

# 5. file scan of every open hit -------------------------------------------------------------------------
scan = {}
for n in sorted(union):
    files = [f["filename"] for f in flat(gh(f"repos/{REPO}/pulls/{n}/files", "per_page=100", paginate=True))]
    hits = [f for f in files if WATCH.match(f)]
    row = {"files": len(files), "watch_hits": hits}
    if hits:
        d = gh(f"repos/{REPO}/pulls/{n}", accept="application/vnd.github.diff", raw=True)
        added = [ln for ln in d.splitlines() if ln.startswith("+") and not ln.startswith("+++")]
        row["added_metric_lines"] = [ln[:160] for ln in added if re.search(r"shared_metrics|telemetry|metric", ln, re.I)][:8]
        row["adds_prefetch_record"] = any(re.search(r"record_\w*prefetch|prefetch\.count|PREFETCH_(MARK|METRIC)", ln) for ln in added)
        row["touches_prefetch_provider"] = "_prefetch_provider" in d
    scan[str(n)] = row
res["file_scan"] = {"watch_regex": WATCH.pattern, "scanned": len(scan), "prs": scan,
                    "flagged": sorted(int(k) for k, v in scan.items() if v["watch_hits"]),
                    "adds_prefetch_record": sorted(int(k) for k, v in scan.items() if v.get("adds_prefetch_record"))}
print("scan", len(scan), "flagged", len(res["file_scan"]["flagged"]), "records", res["file_scan"]["adds_prefetch_record"], flush=True)

# 6. merge matrix ------------------------------------------------------------------------------------------
heads = {}
for n in sorted(set(res["file_scan"]["flagged"]) | set(ADJ)):
    st = cited.get(str(n))
    if st and st.get("head"):
        heads[n] = {"sha": st["head"], "state": st["state"], "author": st["author"], "title": st["title"]}
    else:
        p = gh(f"repos/{REPO}/pulls/{n}")
        heads[n] = {"sha": p["head"]["sha"], "state": p["state"], "author": p["user"]["login"], "title": p["title"]}
fetch(sorted({h["sha"] for h in heads.values()}))


def mtree(a, b):
    p = git("merge-tree", "--write-tree", "--name-only", a, b, check=False)
    if p.returncode not in (0, 1):
        return {"error": p.stderr.strip()[:200]}
    lines = p.stdout.splitlines()
    conf = []
    for ln in lines[1:]:
        if not ln.strip():
            break
        conf.append(ln)
    return {"clean": p.returncode == 0, "tree": lines[0] if lines else None, "conflicts": conf}


def fn(tree):
    s = git("show", f"{tree}:agent/memory_manager.py", check=False).stdout
    mm = re.search(r"\n    def _prefetch_provider\(.*?(?=\n    def )", s, re.S)
    return mm.group(0) if mm else ""


head_fn = fn(HEAD)
res["head_fn"] = {"records": head_fn.count("record_memory_prefetch("), "returns": len(re.findall(r"\breturn\b", head_fn)),
                  "raises": len(re.findall(r"\braise\b", head_fn))}
r4m = json.loads((R4 / "flagged_merge_r4.json").read_text())["prs"]
matrix = {}
for n, h in sorted(heads.items()):
    a, b = mtree(main, h["sha"]), mtree(HEAD, h["sha"])
    cls = ("error" if "error" in a or "error" in b else
           "clean_both" if a["clean"] and b["clean"] else
           "conflicts_with_head_only" if a["clean"] and not b["clean"] else
           "conflicts_with_main_already" if not a["clean"] else "other")
    row = {"author": h["author"], "state": h["state"], "title": h["title"], "pr_head": h["sha"][:10], "class": cls,
           "in_watched_set": n in res["file_scan"]["flagged"],
           "vs_main_conflicts": a.get("conflicts"), "vs_head_conflicts": b.get("conflicts"),
           "extra_conflicts_with_head": sorted(set(b.get("conflicts") or []) - set(a.get("conflicts") or [])),
           "r4": {"class": r4m.get(str(n), {}).get("class"), "pr_head": r4m.get(str(n), {}).get("pr_head")}}
    if cls == "clean_both":
        f = fn(b["tree"])
        row["merged_fn"] = {"changed_vs_head": f != head_fn, "records": f.count("record_memory_prefetch("),
                            "returns": len(re.findall(r"\breturn\b", f)), "raises": len(re.findall(r"\braise\b", f))}
    if n in ADJ:
        row["recorded_head"] = ADJ[n]
        row["head_unchanged"] = h["sha"].startswith(ADJ[n])
    matrix[str(n)] = row
    print("merge", n, h["state"], cls, row["extra_conflicts_with_head"], row.get("merged_fn"), flush=True)
res["merge_matrix"] = matrix
summary = {}
for n in res["file_scan"]["flagged"]:
    c = matrix[str(n)]["class"]
    summary[c] = summary.get(c, 0) + 1
res["merge_summary_watched"] = summary
res["vs_r4_watched"] = {"left": sorted(int(k) for k in r4m if int(k) not in res["file_scan"]["flagged"]),
                        "entered": sorted(n for n in res["file_scan"]["flagged"] if str(n) not in r4m),
                        "class_changed": {k: [r4m[k]["class"], v["class"]] for k, v in matrix.items()
                                          if k in r4m and v["in_watched_set"] and r4m[k]["class"] != v["class"]},
                        "head_changed": sorted(int(k) for k, v in matrix.items()
                                               if k in r4m and v["in_watched_set"] and r4m[k]["pr_head"] != v["pr_head"])}
res["finished_at"] = now()
Path(out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
print("summary", summary, "vs r4", res["vs_r4_watched"])
print("wrote", out)
