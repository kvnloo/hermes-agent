"""Round-4 recheck for memory-prefetch-metric (read-only on GitHub and on the repo object store).

1. current upstream main (ls-remote), commits since the staging base, invalidate_on changes, merge-tree of the head;
2. state, head and close reason of every upstream PR/issue the manifest cites, plus the fork refs;
3. the 10 open-PR prefetch queries (all pages) and the teknium1 open-PR set, diffed against round 3;
4. changed files of every search hit that round 3 did not list, flagged against the prefetch/shared-metrics files;
5. merge-tree matrix of the adjacent PR heads against current main and the staging head.

Usage: python recheck_r4.py <h.git> <out json>
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
R3 = HERE.parent / "r3"
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
CITED = [98045, 87028, 124151, 120042, 47119, 21566, 92118, 126457, 86948, 65329, 125802, 15412, 113678, 78584,
         127373, 127374, 127375, 127332, 127228]
ADJ = {124151: "3ee6189dba", 120042: "641f6b94c5", 98045: "77f018b7db", 92118: "2ad5cc73fa", 126457: "822f7b2835",
       87028: "f63bfa2a5c", 86948: "cc1c2a1f2c", 65329: "c868eaaa02", 125802: "543af5de19", 78584: "e7c6f83e8a"}


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(*a, check=True):
    p = subprocess.run(list(a), capture_output=True, text=True)
    if check and p.returncode:
        raise SystemExit(f"{a}: {p.returncode} {p.stderr}")
    return p


def gh(path, *fields, paginate=False):
    args = ["gh", "api", "-X", "GET", path]
    for f in fields:
        args += ["-f", f]
    if paginate:
        args.append("--paginate")
    for attempt in range(4):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0:
            break
        time.sleep(15 * (attempt + 1))
    else:
        raise SystemExit(f"gh {path}: {p.stderr}")
    if paginate:
        # --paginate concatenates JSON documents; split them
        dec, s, i, docs = json.JSONDecoder(), p.stdout.strip(), 0, []
        while i < len(s):
            obj, j = dec.raw_decode(s, i)
            docs.append(obj)
            i = j
            while i < len(s) and s[i].isspace():
                i += 1
        return docs
    return json.loads(p.stdout)


def git(*a, check=True):
    return sh("git", "-C", hg, "-c", "credential.helper=", *a, check=check)


res = {"started_at": now()}

# 1. main and freshness -------------------------------------------------------------------------
ls = sh("git", "ls-remote", f"https://github.com/{REPO}.git", "refs/heads/main").stdout.split()[0]
res["main"] = {"sha": ls, "ls_remote_at": now(),
               "committer_date": git("log", "-1", "--format=%cI", ls).stdout.strip(),
               "base_is_ancestor": git("merge-base", "--is-ancestor", BASE, ls, check=False).returncode == 0,
               "commits_since_base": int(git("rev-list", "--count", f"{BASE}..{ls}").stdout),
               "invalidate_on_commits": git("log", "--format=%h %s", f"{BASE}..{ls}", "--", *INVALIDATE_ON).stdout.splitlines()}
mt = git("merge-tree", "--write-tree", ls, HEAD, check=False)
res["main"]["merge_tree_head"] = {"clean": mt.returncode == 0, "tree": mt.stdout.split()[0][:10] if mt.stdout else None}
res["main"]["prefetch_grep_since_0920"] = git("log", "--format=%h %s", "-i", "--grep=prefetch", "--since=2026-09-20", ls).stdout.splitlines()
res["main"]["prefetch_grep_since_base"] = git("log", "--format=%h %s", "-i", "--grep=prefetch", f"{BASE}..{ls}").stdout.splitlines()
res["staging_ref"] = git("rev-parse", "refs/heads/staging/memory-prefetch-metric").stdout.strip()
print("main", res["main"]["sha"][:10], res["main"]["commits_since_base"], res["main"]["invalidate_on_commits"], res["main"]["merge_tree_head"])

# 2. cited PRs/issues -----------------------------------------------------------------------------
cited = {}
for n in CITED:
    d = gh(f"repos/{REPO}/issues/{n}")
    row = {"state": d["state"], "state_reason": d.get("state_reason"), "is_pr": "pull_request" in d,
           "author": d["user"]["login"], "created_at": d["created_at"], "closed_at": d["closed_at"],
           "updated_at": d["updated_at"], "merged_at": (d.get("pull_request") or {}).get("merged_at")}
    if row["is_pr"]:
        p = gh(f"repos/{REPO}/pulls/{n}")
        row["head"] = p["head"]["sha"][:10]
        row["mergeable_state"] = p.get("mergeable_state")
    if row["state"] == "closed":
        row["closed_by"] = [e["actor"]["login"] for d in gh(f"repos/{REPO}/issues/{n}/events", paginate=True) for e in d if e["event"] == "closed"]
        row["comments_after_2026_09_01"] = [{"user": c["user"]["login"], "at": c["created_at"], "body": c["body"][:600]}
                                            for d in gh(f"repos/{REPO}/issues/{n}/comments", paginate=True) for c in d
                                            if c["created_at"] >= "2026-09-01"]
    cited[str(n)] = row
    print(n, row["state"], row.get("head"), row.get("closed_at"))
res["cited"] = cited
c87028 = [c for d in gh(f"repos/{REPO}/issues/87028/comments", paginate=True) for c in d]
res["pr87028_comments"] = [{"user": c["user"]["login"], "at": c["created_at"], "body": c["body"]} for c in c87028]
fork = {}
for n in [404, 322, 402, 403]:
    d = gh(f"repos/kvnloo/hermes-agent/issues/{n}")
    body = d.get("body") or ""
    table = [ln for ln in body.splitlines() if ln.startswith("|")]
    fork[str(n)] = {"state": d["state"], "title": d["title"],
                    "table_rows": max(len(table) - 2, 0) if table else 0,
                    "mentions_prefetch": "prefetch" in body.lower()}
res["fork"] = fork

# 3. queries and teknium1 ---------------------------------------------------------------------------
r3q = json.loads((R3 / "ownership_prefetch_search_r3.json").read_text())["queries"]
res["searched_at"] = now()
queries, union_r3, union_r4 = {}, set(), set()
for q in QUERIES:
    docs = gh("search/issues", f"q=repo:{REPO} is:pr is:open {q}", "per_page=100", paginate=True)
    items = [it for d in docs for it in d["items"]]
    total = docs[0]["total_count"]
    nums = sorted({it["number"] for it in items})
    old = {it["number"] for it in r3q[q]["items"]}
    old_complete = r3q[q]["total"] == len(r3q[q]["items"])
    union_r3 |= old
    union_r4 |= set(nums)
    queries[q] = {"total_count": total, "listed": len(nums), "numbers": nums,
                  "r3_total": r3q[q]["total"], "r3_listed": len(old), "r3_list_complete": old_complete,
                  "added_vs_r3_list": sorted(set(nums) - old), "removed_vs_r3_list": sorted(old - set(nums)),
                  "titles": {str(it["number"]): [it["user"]["login"], it["title"]] for it in items}}
    print(q, total, len(nums), "added", len(queries[q]["added_vs_r3_list"]), "removed", queries[q]["removed_vs_r3_list"])
    time.sleep(3)
res["queries"] = queries
t3 = {d["number"] for d in json.loads((R3 / "teknium1_open_r3.json").read_text())}
docs = gh("search/issues", f"q=repo:{REPO} is:pr is:open author:teknium1", "per_page=100", paginate=True)
tk = {it["number"]: it["title"] for d in docs for it in d["items"]}
res["teknium1"] = {"total_count": docs[0]["total_count"], "listed": len(tk), "same_set_as_r3": set(tk) == t3,
                   "added": sorted(set(tk) - t3), "removed": sorted(t3 - set(tk)),
                   "title_hits": sorted(n for n, t in tk.items() if re.search(r"prefetch|telemetry|metric", t, re.I))}
print("teknium1", res["teknium1"]["total_count"], res["teknium1"]["same_set_as_r3"], res["teknium1"]["added"], res["teknium1"]["removed"])

# 4. file scan of hits round 3 did not list (plus any new teknium1 PR) ------------------------------
to_scan = sorted((union_r4 - union_r3) | set(res["teknium1"]["added"]))
scan = {}
for n in to_scan:
    files = [f["filename"] for d in gh(f"repos/{REPO}/pulls/{n}/files", "per_page=100", paginate=True) for f in d]
    hit = [f for f in files if WATCH.match(f)]
    scan[str(n)] = {"files": len(files), "watch_hits": hit}
    if hit:
        print("scan hit", n, hit)
res["file_scan"] = {"watch_regex": WATCH.pattern, "scanned": len(scan), "prs": scan,
                    "hits": {k: v["watch_hits"] for k, v in scan.items() if v["watch_hits"]}}

# 5. merge matrix -----------------------------------------------------------------------------------
def mtree(a, b):
    p = git("merge-tree", "--write-tree", "--name-only", a, b, check=False)
    lines = p.stdout.splitlines()
    conf = []
    for ln in lines[1:]:
        if not ln.strip():
            break
        conf.append(ln)
    return {"clean": p.returncode == 0, "conflicts": conf}


matrix = {}
for n, h in ADJ.items():
    cur = cited.get(str(n), {}).get("head")
    matrix[str(n)] = {"recorded_head": h, "current_head": cur, "head_unchanged": cur == h,
                      "vs_main": mtree(res["main"]["sha"], h), "vs_staging_head": mtree(HEAD, h)}
    print("merge", n, matrix[str(n)]["head_unchanged"], matrix[str(n)]["vs_main"]["clean"], matrix[str(n)]["vs_staging_head"])
res["merge_matrix"] = matrix
res["finished_at"] = now()
Path(out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
