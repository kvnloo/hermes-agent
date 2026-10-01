"""Checks for manifest r7 of memory-prefetch-metric: the message-only v2 commit and the live main.

Read-only: git on the local mirror (show, rev-parse, patch-id, ls-tree), gh api GET.
Writes work/r7/v2_check_r7.json, placeholders only.
Usage: cd <staging>/work/r7 && PYTHONDONTWRITEBYTECODE=1 python3 -B v2_check_r7.py <h.git>
"""
import datetime as dt
import difflib
import json
import re
import subprocess
import sys

import yaml

G = sys.argv[1]
REPO = "NousResearch/hermes-agent"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
V2_REF = "refs/heads/staging/memory-prefetch-metric-v2"
MAIN = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
INVALIDATE_ON = [
    "agent/memory_manager.py", "hermes_cli/observability/shared_metrics_loop.py",
    "hermes_cli/observability/shared_metrics_contract.py",
    "hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json",
    "tests/hermes_cli/test_shared_metrics_loop.py", "website/docs/developer-guide/relay-shared-metrics.md",
    "agent/memory_provider.py", "agent/turn_context.py",
]
BRANCH_NAMES = ["staged/memory-prefetch-metric", "staging/memory-prefetch-metric",
                "staged/memory-prefetch-metric-v2", "staging/memory-prefetch-metric-v2"]


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*a, inp=None):
    r = subprocess.run(["git", "-C", G, *a], capture_output=True, text=True, input=inp)
    if r.returncode != 0:
        raise SystemExit(f"git {a}: {r.stderr}")
    return r.stdout


def gh(path):
    r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"gh {path}: {r.stderr}")
    return json.loads(r.stdout)


def gh_glob(pat):  # same GitHub branch-glob reading as work/r6/fresh_r6.py
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


def push_scan(rev):  # same rules as work/r6/fresh_r6.py, with the -v2 names added
    files = [f for f in git("ls-tree", "-r", "--name-only", rev, ".github/workflows").split()
             if f.endswith((".yml", ".yaml"))]
    with_push, matches = 0, []
    for f in files:
        doc = yaml.safe_load(git("show", f"{rev}:{f}")) or {}
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


def patch_id(rev):
    return git("patch-id", "--stable", inp=git("show", rev)).split()[0]


out = {"id": "v2-check-r7", "item": "memory-prefetch-metric", "started": now(), "label": "OBSERVED"}

v2 = git("rev-parse", V2_REF).strip()
fmt = "%T%n%P%n%an <%ae>%n%ad"
h_meta = git("show", "-s", f"--format={fmt}", "--date=raw", HEAD).splitlines()
v_meta = git("show", "-s", f"--format={fmt}", "--date=raw", v2).splitlines()
h_msg = git("show", "-s", "--format=%B", HEAD).splitlines()
v_msg = git("show", "-s", "--format=%B", v2).splitlines()
out["v2"] = {
    "ref": V2_REF, "sha": v2, "head": HEAD,
    "tree_equal": h_meta[0] == v_meta[0], "tree": v_meta[0][:10],
    "parent_equal": h_meta[1] == v_meta[1], "parent": v_meta[1][:10],
    "author_and_date_equal": h_meta[2:] == v_meta[2:],
    "patch_id_equal": patch_id(HEAD) == patch_id(v2),
    "diff_bytes_head_to_v2": len(git("diff", HEAD, v2)),
    "message_diff": [l for l in difflib.unified_diff(h_msg, v_msg, "head", "v2", lineterm="", n=0)],
    "push_scan": push_scan(v2),
}

live = gh(f"repos/{REPO}/commits/main")
cmp = gh(f"repos/{REPO}/compare/{MAIN}...{live['sha']}")
head_files = git("diff-tree", "-r", "--name-only", f"{HEAD}^", HEAD).split()
changed = {f["filename"]: f for f in cmp["files"]}
wf = {}
for name in changed:
    if name.startswith(".github/workflows/"):
        doc = yaml.safe_load(subprocess.run(
            ["gh", "api", f"repos/{REPO}/contents/{name}?ref={live['sha']}", "-H", "Accept: application/vnd.github.raw"],
            capture_output=True, text=True, check=True).stdout) or {}
        on = doc.get("on", doc.get(True))
        wf[name] = sorted(on) if isinstance(on, dict) else on
tc_commits = gh(f"repos/{REPO}/commits?sha={live['sha']}&path=agent/turn_context.py&since=2026-10-01T17:29:37Z")
out["live_main"] = {
    "sha": live["sha"], "committed": live["commit"]["committer"]["date"], "read_at": now(), "method": "gh api GET compare",
    "commits_since_34f8ec3b40": cmp["total_commits"], "status": cmp["status"], "files_changed": len(cmp["files"]),
    "files_list_complete": len(cmp["files"]) < 300,
    "invalidate_on_changed": sorted(p for p in INVALIDATE_ON if p in changed),
    "head_files_changed_on_main": sorted(p for p in head_files if p in changed),
    "github_changed": sorted(p for p in changed if p.startswith(".github/")),
    "changed_workflow_triggers": wf,
    "turn_context_commits_since_34f8ec3b40": [[c["sha"][:10], c["commit"]["message"].splitlines()[0]] for c in tc_commits],
    "merge_note": "no merge-tree: the live main's objects were not fetched. None of the head's 6 files changed on main, "
                  "so no file is changed on both sides (DERIVED, not an observed merge)",
}
out["finished"] = now()
with open("v2_check_r7.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=1)
    fh.write("\n")
print(json.dumps({k: v for k, v in out["v2"].items() if k != "message_diff"}, indent=1))
print("\n".join(out["v2"]["message_diff"]))
print(json.dumps(out["live_main"], indent=1))
