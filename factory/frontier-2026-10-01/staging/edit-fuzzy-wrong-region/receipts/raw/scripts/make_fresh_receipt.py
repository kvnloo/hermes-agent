"""Polish-round freshness + head-identity receipt for edit-fuzzy-wrong-region.

Read-only against the bare mirror (git cat-file / rev-parse / merge-tree / diff, and
`git apply --cached --check` on a throwaway index file inside this run dir) plus
read-only `gh` queries. Writes one JSON receipt; absolute paths never enter it.
usage: python3 -B make_fresh_receipt.py <bare-repo> <staging-dir> <run-dir> <out.json>
"""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

REPO, SDIR, RUN, OUT = sys.argv[1:5]
UP = "NousResearch/hermes-agent"
MAIN = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
BASE = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
V3 = "fdaaf5b7295125dd2c38bf66980e4016ce3bfb09"
V4REF = "refs/heads/staging/edit-fuzzy-wrong-region-v2"
INVALIDATE_ON = ["tools/fuzzy_match.py", "tools/file_operations.py", "tools/patch_parser.py"]
ADJACENT = [
    "tests/acp_adapter/test_edit_approval.py", "tests/hermes_cli/test_shared_metrics_harness.py",
    "tests/tools/test_file_operations.py", "tests/tools/test_file_operations_delete.py",
    "tests/tools/test_file_operations_edge_cases.py", "tests/tools/test_file_tools.py",
    "tests/tools/test_file_tools_live.py", "tests/tools/test_fuzzy_match.py",
    "tests/tools/test_patch_already_applied.py", "tests/tools/test_patch_multimatch_locations.py",
    "tests/tools/test_patch_parser.py", "tests/tools/test_patch_v4a_gate.py",
    "tests/tools/test_patch_ws_diagnosis.py",
]


def git(*args, env=None, check=True, inp=None):
    p = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True,
                       env=env, input=inp)
    if check and p.returncode != 0:
        raise SystemExit(f"git {args} rc={p.returncode}: {p.stderr}")
    return p.returncode, p.stdout.strip()


def gh(*args):
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"gh {args} rc={p.returncode}: {p.stderr}")
    return p.stdout


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def commit_info(rev):
    _, out = git("show", "-s", "--format=%H%x1f%T%x1f%P%x1f%an%x1f%ad%x1f%cn%x1f%cd", "--date=iso-strict", rev)
    h, t, p, an, ad, cn, cd = out.split("\x1f")
    _, show = git("show", rev)
    _, pid = git("patch-id", "--stable", inp=show + "\n")
    return {"sha": h, "tree": t, "parent": p, "author_name": an, "author_date": ad,
            "committer_name": cn, "committer_date": cd, "patch_id_stable": pid.split()[0]}


def trailer_handles(rev):
    _, body = git("show", "-s", "--format=%B", rev)
    rows = []
    for line in body.splitlines():
        if line.lower().startswith("co-authored-by:"):
            name, _, addr = line.split(":", 1)[1].strip().partition("<")
            addr = addr.rstrip(">")
            form = "github-noreply" if addr.endswith("@users.noreply.github.com") or addr == "noreply@anthropic.com" else "commit-author address (withheld here)"
            rows.append({"name": name.strip(), "address_form": form})
    return body, rows


v4 = git("rev-parse", V4REF)[1]
i3, i4 = commit_info(V3), commit_info(v4)
b3, t3 = trailer_handles(V3)
b4, t4 = trailer_handles(v4)
body_wo_trailers = lambda b: "\n".join(l for l in b.splitlines() if not l.lower().startswith("co-authored-by:"))
same = {k: i3[k] == i4[k] for k in ("tree", "parent", "author_name", "author_date", "patch_id_stable")}

rc, mt_main = git("merge-tree", "--write-tree", MAIN, v4, check=False)
rc_b, mt_base = git("merge-tree", "--write-tree", BASE, v4, check=False)
_, log = git("log", "--format=%h %s", f"{BASE}..{MAIN}")
_, changed = git("diff", "--name-only", f"{BASE}..{MAIN}")
changed = changed.splitlines()
_, inv = git("diff", "--name-only", f"{BASE}..{MAIN}", "--", *INVALIDATE_ON)
_, adj = git("diff", "--name-only", f"{BASE}..{MAIN}", "--", *ADJACENT)
_, tt = git("diff", "--name-only", f"{BASE}..{MAIN}", "--", "tests/tools", ".github", "tools")
blobs = {f: git("rev-parse", f"{MAIN}:{f}")[1] for f in INVALIDATE_ON}

members = {}
for n in (54575, 125376, 126502, 93717, 111127, 128138, 129645):
    r = f"refs/pr/{n}"
    sha = git("rev-parse", r)[1]
    rc_m, out = git("merge-tree", "--write-tree", "--name-only", MAIN, r, check=False)
    lines = out.splitlines()
    conflicted = [l for l in lines[1:] if l and not l.startswith(("Auto-merging", "CONFLICT"))]
    members[f"#{n}"] = {"head": sha[:10], "merge_tree_on_main": "clean" if rc_m == 0 else "CONFLICTING",
                        "conflicted_files": conflicted}

_, cp_tree = git("merge-tree", "--write-tree", "--merge-base", "5f3f5896a4^", MAIN, "5f3f5896a4")
cp_blob = git("rev-parse", f"{cp_tree}:tools/fuzzy_match.py")[1]
idx = os.path.join(RUN, "fresh.index")
env = dict(os.environ, GIT_INDEX_FILE=idx)
git("read-tree", MAIN, env=env)
apply_main = git("apply", "--cached", "--check", os.path.join(SDIR, "c54575-rebased-on-main.diff"), env=env, check=False)[0]
git("read-tree", cp_tree, env=env)
git("apply", "--cached", os.path.join(SDIR, "c54575-rebased-on-main.diff"), env=env)
git("apply", "--cached", os.path.join(SDIR, "foldin-125376-stripped-guard.diff"), env=env)
_, ov_tree = git("write-tree", env=env)
os.remove(idx)
ov = subprocess.run(["git", "-C", REPO, "cat-file", "blob", f"{ov_tree}:tools/fuzzy_match.py"], capture_output=True).stdout

# body.md round trips
lines = open(os.path.join(SDIR, "body.md"), encoding="utf-8").read().split("\n")
def block(sec, nxt):
    s = next(i for i, l in enumerate(lines) if l.startswith(sec))
    e = next(i for i, l in enumerate(lines) if l.startswith(nxt))
    return [l[2:] if l.startswith("> ") else "" for l in lines[s:e] if l.startswith(">")]
b2, b3q = block("## 2.", "## 3."), block("## 3.", "## 4.")
s = b2.index("```python"); e = b2.index("```", s + 1)
test_txt = ("\n".join(b2[s + 1:e]) + "\n").encode()
s = b3q.index("```diff"); e = len(b3q) - 1 - b3q[::-1].index("```")
diff_txt = ("\n".join(b3q[s + 1:e]) + "\n").encode()

prs = {}
for n in (54575, 125376, 126502, 93717, 111127, 128138, 129645, 124168, 77271, 89660, 128020, 130746):
    d = json.loads(gh("pr", "view", str(n), "--repo", UP, "--json", "number,state,headRefOid,author,createdAt,mergedAt,title"))
    prs[f"#{n}"] = {"state": d["state"], "head": d["headRefOid"][:10], "author": d["author"]["login"],
                    "created": d["createdAt"], "merged": d["mergedAt"], "title": d["title"]}
issues = {}
for n in (54572, 93698, 111116, 130139):
    d = json.loads(gh("issue", "view", str(n), "--repo", UP, "--json", "state"))
    issues[f"#{n}"] = d["state"]
dedupe = {}
for q in ("fuzzy_match", "block_anchor", "context_aware", "wrong region", "fuzzy_find_and_replace", "patch_replace"):
    d = json.loads(gh("search", "prs", "--repo", UP, "--state", "open", q, "--created", ">=2026-09-30",
                      "--json", "number"))
    dedupe[q] = sorted(x["number"] for x in d)
up_main = json.loads(gh("api", f"repos/{UP}/commits/main"))
cmp_ = json.loads(gh("api", f"repos/{UP}/compare/{MAIN}...{up_main['sha']}"))
cmp_files = [f["filename"] for f in cmp_.get("files", [])]

receipt = {
    "schema": "xf.receipt.v1 (hand-run; xf executor not built)",
    "id": "FRESH/r20261001-01",
    "staging": "edit-fuzzy-wrong-region",
    "kind": "polish round: message-only rebuild identity + freshness on main 34f8ec3b40; no test was run",
    "measured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    "evidence_class": "OBSERVED (git object reads, merge-tree, apply --check on a throwaway index, read-only gh queries)",
    "head_identity": {
        "v3": i3, "v4": i4, "v4_ref": V4REF, "identical": same,
        "message_change": {
            "body_text_changed": body_wo_trailers(b3) != body_wo_trailers(b4),
            "summary": "paragraph 3: 'It is meant to be folded into the open fixes in #54575 and #125376.' -> it is offered as an optional regression test for them and passes once #54575, the fix commit of #125376 and the stripped-pattern guard line from review on #125376 are applied together. Trailers: KoNit-K and likivik now use GitHub id+login noreply addresses (ids from gh api users/<login>; dbc91693bb and 5444b1a2a8 resolve to those same accounts); the other four trailers are unchanged.",
            "trailers_v3": t3, "trailers_v4": t4,
        },
        "consequence": "same tree, parent, author, author date and stable patch-id: every receipt measured on fdaaf5b729 applies to v4 unchanged",
    },
    "freshness": {
        "main": MAIN, "base": BASE, "commits_base_to_main": len(log.splitlines()), "commits": log.splitlines(),
        "files_changed_base_to_main": changed,
        "invalidate_on": INVALIDATE_ON, "invalidate_on_changed": inv.splitlines(),
        "adjacent_13_changed": adj.splitlines(), "tools_tests_tools_github_changed": tt.splitlines(),
        "edit_path_blobs_on_main": blobs,
        "merge_tree_v4_on_main": {"rc": rc, "tree": mt_main},
        "merge_tree_v4_on_base": {"rc": rc_b, "tree": mt_base},
        "member_heads_on_main": members,
        "c125376_fix_cherry_pick_sim_on_main": {"tree": cp_tree, "tools/fuzzy_match.py_blob": cp_blob},
        "c54575_diff_apply_check_on_main_rc": apply_main,
        "green_overlay_on_main": {"recipe": "main + 5f3f5896a4 (cherry-pick sim) + c54575-rebased-on-main.diff + foldin-125376-stripped-guard.diff",
                                  "tree": ov_tree, "tools/fuzzy_match.py_sha256": sha256(ov),
                                  "equals_F01_r04_both_fold": sha256(ov).startswith("145fb703")},
    },
    "body_round_trip": {
        "section3_diff_sha256": sha256(diff_txt),
        "c54575_diff_file_sha256": sha256(open(os.path.join(SDIR, "c54575-rebased-on-main.diff"), "rb").read()),
        "section2_test_git_blob": hashlib.sha1(b"blob %d\0" % len(test_txt) + test_txt).hexdigest(),
        "commit_test_blob": git("rev-parse", f"{v4}:tests/tools/test_fuzzy_match_wrong_region.py")[1],
    },
    "upstream_read_only": {
        "prs": prs, "issues": issues,
        "dedupe_open_prs_created_since_2026-09-30": dedupe,
        "upstream_main_at_check": up_main["sha"],
        "compare_34f8ec3b40_to_upstream_main": {"ahead_by": cmp_.get("ahead_by"), "behind_by": cmp_.get("behind_by"),
                                               "files": cmp_files,
                                               "invalidate_on_changed": [f for f in cmp_files if f in INVALIDATE_ON],
                                               "adjacent_13_changed": [f for f in cmp_files if f in ADJACENT],
                                               "github_changed": [f for f in cmp_files if f.startswith(".github/")],
                                               "note": "file list from the GitHub compare API only; not fetched, no merge-tree or test run on it"},
    },
    "command": "python3 -B make_fresh_receipt.py <h.git> <staging-dir> <run> <out> (private run dir; read-only git + gh)",
    "not_tested": ["no RED/GREEN/A-B run on 34f8ec3b40 in this round; F01/r20261001-04 (main 44a1ce9724) stays the proof",
                   "#124168, #130746, #77271, #89660, #128020 are recorded from their PR metadata and diffs, not run"],
    "privacy": "handles only; trailer addresses summarised by form, no email addresses, host names or local paths",
    "cost_usd": 0,
}
json.dump(receipt, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
open(OUT, "a").write("\n")
print(sha256(open(OUT, "rb").read()))
