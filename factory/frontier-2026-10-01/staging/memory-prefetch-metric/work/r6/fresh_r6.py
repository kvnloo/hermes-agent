"""Freshness, overlap and fork-state refresh for memory-prefetch-metric (polish round, manifest r6).

Read-only: git on the local mirror (merge-tree --write-tree writes only loose tree objects), gh api GET.
Writes work/r6/fresh_r6.json (raw) and receipts/FRESH-r20261001-01.json, placeholders only.
"""
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys

import yaml

G = sys.argv[1]          # bare mirror
STAGE = sys.argv[2]      # staging/<id> dir
SCRATCH = sys.argv[3]    # scratch dir for patch dry-runs
REPO = "NousResearch/hermes-agent"
FORK = "kvnloo/hermes-agent"
BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
PREV_MAIN = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b"
MAIN = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
ARM = "e23dcd91fa9aa46882c4c3689122e38f75fafdd9"   # refs/xf/w0/memory-prefetch-metric = MAIN + head commit
INVALIDATE_ON = [
    "agent/memory_manager.py", "hermes_cli/observability/shared_metrics_loop.py",
    "hermes_cli/observability/shared_metrics_contract.py",
    "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
    "tests/hermes_cli/test_shared_metrics_loop.py", "website/docs/developer-guide/relay-shared-metrics.md",
    "agent/memory_provider.py", "agent/turn_context.py",
]
ADJ = {124151: "3ee6189dba", 120042: "641f6b94c5", 92118: "2ad5cc73fa", 125881: "d3fdffcf82", 65329: "c868eaaa02",
       87028: "f63bfa2a5c", 86948: "cc1c2a1f2c", 125802: "543af5de19", 108965: "39dd41fe68", 15412: "69c5a41321"}
CITED_PRS = sorted(set(ADJ) | {98045, 126457, 113678, 130788, 104562})
CITED_ISSUES = [47119, 21566, 47021, 85135, 104405, 43891, 84263]
BRANCH_NAMES = ["staged/memory-prefetch-metric", "staging/memory-prefetch-metric"]


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*a, check=True):
    r = subprocess.run(["git", "-C", G, *a], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {a}: {r.stderr}")
    return r


def gh(path, *extra, raw=False):
    r = subprocess.run(["gh", "api", *extra, path], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"gh {path}: {r.stderr}")
    return r.stdout if raw else json.loads(r.stdout)


def merge_tree(a, b):
    r = git("merge-tree", "--write-tree", "--name-only", a, b, check=False)
    lines = r.stdout.splitlines()
    tree = lines[0] if lines else ""
    conflicted = [l for l in lines[1:] if l and not l.startswith(("Auto-merging", "CONFLICT"))]
    return {"clean": r.returncode == 0, "tree": tree[:10], "conflicted_files": conflicted}


def freshness(frm, to):
    log = git("log", "--format=%h", f"{frm}..{to}", "--", *INVALIDATE_ON).stdout.split()
    blobs_equal = sum(git("rev-parse", f"{BASE}:{p}").stdout == git("rev-parse", f"{to}:{p}").stdout for p in INVALIDATE_ON)
    gh_log = git("log", "--format=%h", f"{frm}..{to}", "--", ".github").stdout.split()
    gh_files = git("diff", "--name-only", frm, to, "--", ".github").stdout.split()
    return {"commits": int(git("rev-list", "--count", f"{frm}..{to}").stdout), "invalidate_on_commits": log,
            "invalidate_on_blobs_equal_base": f"{blobs_equal} of {len(INVALIDATE_ON)}",
            "github_commits": len(gh_log), "github_files": gh_files}


def gh_glob(pat):
    out, i = "", 0
    while i < len(pat):
        if pat.startswith("**", i):
            out += ".*"; i += 2
        elif pat[i] == "*":
            out += "[^/]*"; i += 1
        elif pat[i] == "?":
            out += "[^/]"; i += 1
        else:
            out += re.escape(pat[i]); i += 1
    return re.compile(out + r"\Z")


def push_scan(rev):
    files = [f for f in git("ls-tree", "-r", "--name-only", rev, ".github/workflows").stdout.split()
             if f.endswith((".yml", ".yaml"))]
    with_push, matches = 0, []
    for f in files:
        doc = yaml.safe_load(git("show", f"{rev}:{f}").stdout) or {}
        on = doc.get("on", doc.get(True))
        if isinstance(on, str):
            on = {on: None}
        elif isinstance(on, list):
            on = {k: None for k in on}
        if not isinstance(on, dict) or "push" not in on:
            continue
        with_push += 1
        push = on["push"] or {}
        branches, ignore = push.get("branches"), push.get("branches-ignore")
        tags_only = branches is None and ignore is None and ("tags" in push or "tags-ignore" in push)
        for name in BRANCH_NAMES:
            if tags_only:
                hit = False
            elif branches is not None:
                pos = [p for p in branches if not p.startswith("!")]
                neg = [p[1:] for p in branches if p.startswith("!")]
                hit = any(gh_glob(p).match(name) for p in pos) and not any(gh_glob(p).match(name) for p in neg)
            elif ignore is not None:
                hit = not any(gh_glob(p).match(name) for p in ignore)
            else:
                hit = True
            if hit:
                matches.append({"file": f, "branch": name})
    return {"rev": rev[:10], "workflows": len(files), "with_push_trigger": with_push, "matches": matches}


def patch_dry_run(pr):
    files = gh(f"repos/{REPO}/pulls/{pr}/files", "--paginate")
    res = {}
    for f in files:
        fn = f["filename"]
        res[fn] = {}
        for arm, rev in (("main", MAIN), ("head", HEAD)):
            wd = os.path.join(SCRATCH, f"dry{pr}-{arm}")
            os.makedirs(os.path.join(wd, os.path.dirname(fn)), exist_ok=True)
            blob = subprocess.run(["git", "-C", G, "show", f"{rev}:{fn}"], capture_output=True)
            with open(os.path.join(wd, fn), "wb") as fh:
                fh.write(blob.stdout)
            p = f"--- a/{fn}\n+++ b/{fn}\n" + f.get("patch", "") + "\n"
            r = subprocess.run(["patch", "--dry-run", "-p1", "-F0", "-d", wd], input=p.encode(), capture_output=True)
            failed = re.findall(r"Hunk #(\d+) FAILED", r.stdout.decode())
            res[fn][arm] = {"applies": r.returncode == 0, "failed_hunks": [int(x) for x in failed]}
    return res


out = {"checked_at": now()}

# 1. main named by the round (34f8ec3b40)
out["main"] = {"sha": MAIN, "committer_date": git("log", "-1", "--format=%cI", MAIN).stdout.strip(),
               "base_is_ancestor": git("merge-base", "--is-ancestor", BASE, MAIN, check=False).returncode == 0,
               "since_base": freshness(BASE, MAIN), "since_prev_main_aaa863f7ff": freshness(PREV_MAIN, MAIN),
               "merge_tree_head": merge_tree(MAIN, HEAD),
               "arm_tree": git("rev-parse", f"{ARM}^{{tree}}").stdout.strip()[:10],
               "arm_parent": git("log", "-1", "--format=%P", ARM).stdout.strip()[:10]}

# 2. live upstream main (gh read-only), if its objects are in the mirror
live = gh(f"repos/{REPO}/commits/main")
LIVE = live["sha"]
out["live_main"] = {"sha": LIVE, "committer_date": live["commit"]["committer"]["date"], "read_at": now(),
                    "in_mirror": git("cat-file", "-t", LIVE, check=False).returncode == 0}
if out["live_main"]["in_mirror"]:
    out["live_main"].update({"main_is_ancestor": git("merge-base", "--is-ancestor", MAIN, LIVE, check=False).returncode == 0,
                             "since_base": freshness(BASE, LIVE), "since_main_34f8ec3b40": freshness(MAIN, LIVE),
                             "merge_tree_head": merge_tree(LIVE, HEAD)})

# 3. workflow push-trigger scan (head tree is what the fork branch carries; live main for a future rebase)
out["workflow_push_scan"] = [push_scan(HEAD)] + ([push_scan(LIVE)] if out["live_main"]["in_mirror"] else [])

# 4. cited PR/issue state
st = {}
for n in CITED_PRS:
    p = gh(f"repos/{REPO}/pulls/{n}")
    st[str(n)] = {"kind": "pr", "state": p["state"], "merged": p["merged"], "head": p["head"]["sha"][:10],
                  "author": p["user"]["login"], "created_at": p["created_at"], "closed_at": p["closed_at"],
                  "mergeable_state": p.get("mergeable_state")}
for n in CITED_ISSUES:
    i = gh(f"repos/{REPO}/issues/{n}")
    st[str(n)] = {"kind": "issue", "state": i["state"], "author": i["user"]["login"], "created_at": i["created_at"],
                  "title": i["title"]}
out["cited_state"] = st
out["adjacent_heads_unchanged"] = {str(n): st[str(n)]["head"] == h for n, h in ADJ.items()}

# 5. adjacent merge matrix against MAIN and MAIN + head (the F14 arm)
out["adjacent_merge_matrix"] = {}
for n, h in ADJ.items():
    full = git("rev-parse", "--verify", "-q", f"{h}^{{commit}}", check=False).stdout.strip()
    if not full:
        out["adjacent_merge_matrix"][str(n)] = {"head_in_mirror": False}
        continue
    out["adjacent_merge_matrix"][str(n)] = {"main": merge_tree(MAIN, full), "main_plus_head": merge_tree(ARM, full)}

# 6. the new overlap #130788 (head object not in the mirror: patch dry-run of its files-API diff)
out["pr130788"] = {"head_in_mirror": git("cat-file", "-t", st["130788"]["head"], check=False).returncode == 0,
                   "same_head_as_104562": st["130788"]["head"] == st["104562"]["head"],
                   "patch_dry_run": patch_dry_run(130788)}

# 7. delta searches since the r04 full scan (16:53Z): PRs updated since 16:50Z, and open issues (never scanned before)
since = "2026-10-01T16:50:00Z"
out["delta_pr_search"] = {"updated_since": since, "queries": {}}
for q in ["prefetch", "memory.prefetch", "record_memory_prefetch", "prefetch metric", "prefetch telemetry",
          "shared metrics memory"]:
    r = gh("search/issues", "-X", "GET", "-f", f"q=repo:{REPO} is:pr {q} updated:>={since}")
    out["delta_pr_search"]["queries"][q] = {"total": r["total_count"],
                                            "hits": [f"#{x['number']} {x['state']}" for x in r["items"]]}
WATCHED = re.compile(r"^(agent/memory_manager\.py|hermes_cli/observability/.*|tests/hermes_cli/test_shared_metrics_loop\.py|"
                     r"website/docs/developer-guide/relay-shared-metrics\.md|agent/memory_provider\.py|agent/turn_context\.py)$")
METRIC_LINE = re.compile(r"^\+.*(memory\.prefetch|record_memory_prefetch|prefetch.*(count|metric))", re.I | re.M)
hits = sorted({int(h.split()[0][1:]) for q in out["delta_pr_search"]["queries"].values() for h in q["hits"]
               if h.endswith(" open")})
out["delta_hit_file_scan"] = {}
for n in hits:
    files = gh(f"repos/{REPO}/pulls/{n}/files", "--paginate")
    out["delta_hit_file_scan"][str(n)] = {
        "files": len(files), "watched": [f["filename"] for f in files if WATCHED.match(f["filename"])],
        "prefetch_metric_added_lines": sum(len(METRIC_LINE.findall(f.get("patch", ""))) for f in files)}
out["open_issue_search"] = {}
for q in ['"prefetch" timeout memory', "prefetch timed out", "memory prefetch"]:
    r = gh("search/issues", "-X", "GET", "-f", f"q=repo:{REPO} is:issue is:open {q}", "-f", "per_page=30")
    out["open_issue_search"][q] = {"total": r["total_count"], "first_page": [x["number"] for x in r["items"]]}

# 8. fork state
ref = gh(f"repos/{FORK}/git/ref/heads/staged/memory-prefetch-metric")
act = gh(f"repos/{FORK}/activity?per_page=10&ref=refs/heads/staged/memory-prefetch-metric")
staged = gh(f"repos/{FORK}/git/matching-refs/heads/staged/", "--paginate")
iss = gh(f"repos/{FORK}/issues/417")
ledger = gh(f"repos/{FORK}/contents/factory/frontier-2026-10-01/staging/memory-prefetch-metric/receipts?ref=claude/ledger")
lcommit = gh(f"repos/{FORK}/commits?sha=claude/ledger&path=factory/frontier-2026-10-01/staging/memory-prefetch-metric&per_page=1")
out["fork"] = {
    "staged_branch_sha": ref["object"]["sha"], "staged_branch_equals_head": ref["object"]["sha"] == HEAD,
    "branch_activity": [{"type": a["activity_type"], "at": a["timestamp"], "actor": a["actor"]["login"],
                         "after": a["after"][:10]} for a in act],
    "staged_refs": len(staged),
    "issue_417": {"state": iss["state"], "created_at": iss["created_at"], "comments": iss["comments"],
                  "title": iss["title"]},
    "ledger_copy": {"commit": lcommit[0]["sha"][:10], "at": lcommit[0]["commit"]["committer"]["date"],
                    "receipts": len(ledger),
                    "has_F14_receipt": any(x["name"].startswith("F14-") for x in ledger)},
}

os.makedirs(os.path.join(STAGE, "work", "r6"), exist_ok=True)
raw_path = os.path.join(STAGE, "work", "r6", "fresh_r6.json")
text = json.dumps(out, indent=1, sort_keys=False)
for bad in ("home", "mnt", "tmp", "workspace"):  # no absolute local path may land in the raw file
    assert f"/{bad}/" not in text, bad
with open(raw_path, "w") as fh:
    fh.write(text + "\n")
print(text)
