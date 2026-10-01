"""Last state check before manifest r5 is written: upstream main, the merge-tree of the staging head on it, the state and
head of every upstream PR/issue recheck_r5.py checked, the 10 prefetch query totals, and the fork threads. Read-only on
GitHub (gh api GET); git ls-remote; merge-tree on the local object store (main fetched by SHA, no ref written).

Usage: python final_state_r5.py <h.git> <recheck_r5.json> <out json>
"""
import datetime
import json
import subprocess
import sys
import time

hg, src, out = sys.argv[1:]
REPO = "NousResearch/hermes-agent"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
rc = json.load(open(src))


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gh(path, *fields):
    args = ["gh", "api", "-X", "GET", path]
    for f in fields:
        args += ["-f", f]
    for attempt in range(5):
        p = subprocess.run(args, capture_output=True, text=True)
        if p.returncode == 0:
            return json.loads(p.stdout)
        time.sleep(15 * (attempt + 1))
    raise SystemExit(f"gh {path}: {p.stderr}")


def git(*a, check=True):
    p = subprocess.run(["git", "-C", hg, *a], capture_output=True, text=True)
    if check and p.returncode:
        raise SystemExit(f"{a}: {p.stderr}")
    return p


res = {"started_at": now()}
main = subprocess.run(["git", "ls-remote", f"https://github.com/{REPO}.git", "refs/heads/main"], capture_output=True,
                      text=True, check=True).stdout.split()[0]
if git("cat-file", "-e", f"{main}^{{commit}}", check=False).returncode:
    git("fetch", "--no-write-fetch-head", "--no-tags", "--filter=blob:none", "origin", main)
mt = git("merge-tree", "--write-tree", main, HEAD, check=False)
inv = ["agent/memory_manager.py", "hermes_cli/observability/shared_metrics_loop.py",
              "hermes_cli/observability/shared_metrics_contract.py",
              "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
              "tests/hermes_cli/test_shared_metrics_loop.py", "website/docs/developer-guide/relay-shared-metrics.md",
              "agent/memory_provider.py", "agent/turn_context.py"]
res["main"] = {"sha": main, "ls_remote_at": now(),
               "commits_since_base": int(git("rev-list", "--count", f"{BASE}..{main}").stdout),
               "invalidate_on_commits_since_base": git("log", "--format=%h %s", f"{BASE}..{main}", "--", *inv).stdout.splitlines(),
               "github_commits_since_base": git("log", "--format=%h %s", f"{BASE}..{main}", "--", ".github").stdout.splitlines(),
               "merge_tree_head": {"clean": mt.returncode == 0, "tree": mt.stdout.split()[0] if mt.stdout else None}}
res["cited_checked_at"] = now()
cited, changed = {}, {}
for n, old in rc["cited"].items():
    d = gh(f"repos/{REPO}/issues/{n}")
    row = {"state": d["state"], "closed_at": d["closed_at"], "merged_at": (d.get("pull_request") or {}).get("merged_at")}
    if "pull_request" in d:
        row["head"] = gh(f"repos/{REPO}/pulls/{n}")["head"]["sha"]
    cited[n] = row
    diff = {k: [old.get(k), v] for k, v in row.items() if old.get(k) != v}
    if diff:
        changed[n] = diff
res["cited"] = cited
res["changed_since_recheck_r5"] = changed
q = {}
for query in rc["queries"]:
    q[query] = gh("search/issues", f"q=repo:{REPO} is:pr is:open {query}", "per_page=1")["total_count"]
    time.sleep(2.5)
res["query_totals"] = q
res["query_totals_changed"] = {k: [rc["queries"][k]["total_count"], v] for k, v in q.items() if rc["queries"][k]["total_count"] != v}
fork = {}
for n in ["404", "322", "402", "403"]:
    d = gh(f"repos/kvnloo/hermes-agent/issues/{n}")
    table = [ln for ln in (d.get("body") or "").splitlines() if ln.startswith("|")]
    fork[n] = {"state": d["state"], "table_rows": max(len(table) - 2, 0) if table else 0}
res["fork"] = fork
refs = subprocess.run(["git", "ls-remote", "https://github.com/kvnloo/hermes-agent.git", "refs/heads/staged/memory-prefetch-metric"],
                      capture_output=True, text=True, check=True).stdout
res["fork_branch_present"] = bool(refs.strip())
res["staging_ref"] = git("rev-parse", "refs/heads/staging/memory-prefetch-metric").stdout.strip()
res["finished_at"] = now()
open(out, "w").write(json.dumps(res, indent=1) + "\n")
print(json.dumps({k: res[k] for k in ("main", "changed_since_recheck_r5", "query_totals_changed", "fork", "fork_branch_present",
                                       "staging_ref", "finished_at")}, indent=1))
