#!/usr/bin/env python3
"""Read-only apply-checks of each open PR's observer-hooks.md hunk against this branch.

usage: apply_checks.py <repo.git> <branch_sha> <main_sha> <base_sha> <pr> [<pr> ...]
Expects pr<N>.diff (from `gh pr diff N`) next to this script. Uses a throwaway index file,
so no worktree and no ref is created. Prints one JSON object.
"""
import hashlib, itertools, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = "website/docs/developer-guide/observer-hooks.md"
INV = {"agent/turn_response_intake.py", "agent/turn_api_request.py", "agent/chat_completion_helpers.py",
       "agent/codex_runtime.py", "agent/conversation_loop.py", "agent/turn_response_check.py",
       "agent/moa_trace.py", "agent/moa_loop.py", "agent/turn_usage.py", "hermes_cli/plugins.py", TARGET}
SEM = re.compile(r"post_api_request|api_start_time|_last_api_first_chunk_at|first_chunk_at|context_length|moa_reference")
FIELDS = re.compile(r"first_chunk_at|context_length|moa_references")
repo, branch, main, base = sys.argv[1:5]
prs = [int(x) for x in sys.argv[5:]]
IDX = os.path.join(HERE, "apply.idx")


def git(*a, env=None, check=True):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, env=e, check=check)


def fresh_index(tree):
    if os.path.exists(IDX):
        os.remove(IDX)
    git("read-tree", tree, env={"GIT_INDEX_FILE": IDX})


def apply(patch_path, check):
    args = ["apply", "--cached", "-v"] + (["--check"] if check else []) + [patch_path]
    r = git(*args, env={"GIT_INDEX_FILE": IDX}, check=False)
    msgs = [l for l in (r.stdout + r.stderr).splitlines() if re.match(r"(Hunk|error|Applied|Checking)", l)]
    return r.returncode, msgs


branch_patch = os.path.join(HERE, "branch.ohd.diff")
open(branch_patch, "w").write(git("diff", base, branch, "--", TARGET).stdout)
out = {"branch": branch, "main": main, "base": base,
       "page_blob": {"base": git("rev-parse", f"{base}:{TARGET}").stdout.strip(),
                     "main": git("rev-parse", f"{main}:{TARGET}").stdout.strip(),
                     "branch": git("rev-parse", f"{branch}:{TARGET}").stdout.strip()},
       "per_pr": [], "combined": None}
hunks = {}
for n in prs:
    t = open(os.path.join(HERE, f"pr{n}.diff")).read()
    parts = re.split(r"(?m)^(?=diff --git )", t)
    files = [re.match(r"diff --git a/(\S+)", p).group(1) for p in parts if p.startswith("diff --git ")]
    sel = [p for p in parts if p.startswith(f"diff --git a/{TARGET} ")]
    assert len(sel) == 1, n
    hp = os.path.join(HERE, f"pr{n}.ohd.diff")
    open(hp, "w").write(sel[0])
    hunks[n] = hp
    pm = [l for l in t.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    sem_hits = []
    cur = None
    for l in t.splitlines():
        if l.startswith("diff --git "):
            cur = l.split()[2][2:]
        elif l[:1] in "+-" and not l.startswith(("+++", "---")) and SEM.search(l):
            sem_hits.append(cur)
    added_doc = [l for l in sel[0].splitlines() if l.startswith("+") and not l.startswith("+++")]
    fresh_index(branch)
    a_rc, a_msg = apply(hp, check=True)
    fresh_index(main)
    b1_rc, b1_msg = apply(hp, check=False)
    b2_rc, b2_msg = apply(branch_patch, check=True) if b1_rc == 0 else (None, [])
    out["per_pr"].append({
        "pr": n,
        "hunk_headers": re.findall(r"(?m)^@@[^@]*@@", sel[0]),
        "hunk_sha256": hashlib.sha256(sel[0].encode()).hexdigest(),
        "files_in_pr": len(files),
        "invalidate_on_paths_touched": sorted(set(files) & INV - {TARGET}),
        "pm_lines_naming_emitter_or_fields": {f: sem_hits.count(f) for f in sorted(set(sem_hits))},
        "added_doc_lines": len(added_doc),
        "added_doc_lines_naming_the_three_fields": sum(1 for l in added_doc if FIELDS.search(l)),
        "order_A_branch_then_pr": {"rc": a_rc, "git": a_msg},
        "order_B_main_then_pr_then_branch": {"pr_rc": b1_rc, "pr_git": b1_msg, "branch_rc": b2_rc, "branch_git": b2_msg},
    })
# every PR hunk stacked on this branch, in PR order; record the first failure and whether
# that pair also fails on plain main (i.e. a conflict between two other PRs, not with this branch)
fresh_index(branch)
stack = []
for n in prs:
    rc, msg = apply(hunks[n], check=False)
    stack.append({"pr": n, "rc": rc, "git": msg})
blob = git("ls-files", "-s", TARGET, env={"GIT_INDEX_FILE": IDX}).stdout.split()
pairs = []
for x, y in itertools.combinations(prs, 2):
    for tree, key in ((main, "on_main"), (branch, "on_branch")):
        fresh_index(tree)
        r1, _ = apply(hunks[x], check=False)
        r2, m2 = apply(hunks[y], check=True) if r1 == 0 else (None, [])
        if r2 not in (0,):
            pairs.append({"pair": [x, y], "tree": key, "second_rc": r2, "git": m2})
out["combined"] = {"stack_on_branch": stack, "final_blob": blob[1] if len(blob) > 1 else None,
                   "pairwise_failures": pairs}
os.remove(IDX)
print(json.dumps(out, indent=1))
