"""Write OWNERSHIP/r20261001-04 and F08/r20261001-04 for memory-prefetch-metric from the round-5 files under work/r5.

Repo-relative paths only; asserts the facts the manifest states. Usage: python make_receipts_r5.py  (any cwd)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R5 = ROOT / "work" / "r5"
RECEIPTS = ROOT / "receipts"
BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"
MAIN = "aaa863f7ff2dec1821be1652b5d15ad14ecea70b"
REPLAY = "27d0a5e42f5b001ae071d9b4cbf312dfd51ac27c"
REPLAY_TREE = "21c423feb3df08111ba13bd5cf8af2161c21af23"
CONTRACT_TEST = "tests/hermes_cli/test_shared_metrics_loop.py::test_external_prefetch_records_each_exit_with_how_long_the_turn_waited"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


rc = json.loads((R5 / "recheck_r5.json").read_text())
fin = json.loads((R5 / "final_state_r5.json").read_text())
pv = json.loads((R5 / "prove" / "prove_results.json").read_text())

# ---- facts the manifest states -------------------------------------------------------------------
m = rc["main"]
assert m["sha"] == MAIN and m["commits_since_base"] == 25 and m["invalidate_on_commits_since_base"] == []
assert all(m["invalidate_on_blobs_equal_base"].values()) and m["github_commits_since_base"] == [] and m["workflow_files"] == 52
assert m["merge_tree_head"] == {"clean": True, "tree": REPLAY_TREE} and m["prefetch_grep_since_base"] == []
assert rc["staging_ref"] == HEAD and not rc["fork_refs"]["staged_memory_prefetch_metric_present"]
c = rc["cited"]
closed = sorted(n for n, v in c.items() if v["state"] != "open")
assert closed == ["126457", "98045"], closed
p = c["126457"]
assert p["closed_at"] == "2026-10-01T16:23:32Z" and p["merged_at"] is None and p["closed_by"] == ["mozhongzhou"]
assert p["head"].startswith("822f7b2835") and p["comments_since_2026_09_25"] == [] and rc["pr126457"]["all_comments"] == []
assert [x["number"] for x in rc["mozhongzhou_prs"]] == [126457]
assert c["98045"]["closed_at"] == "2026-10-01T12:51:06Z" and c["98045"]["closed_by"] == ["Navlem"]
assert rc["teknium1"]["total_count"] == 260 and rc["teknium1"]["same_set_as_r3"] and rc["teknium1"]["title_hits"] == []
assert rc["union"] == {"count": 177, "added_vs_r4": [], "removed_vs_r4": [126457]}
fs = rc["file_scan"]
assert fs["scanned"] == 177 and len(fs["flagged"]) == 50 and fs["adds_prefetch_record"] == []
assert rc["merge_summary_watched"] == {"conflicts_with_main_already": 38, "clean_both": 11, "conflicts_with_head_only": 1}
mm = rc["merge_matrix"]
head_only = sorted(n for n in map(str, fs["flagged"]) if mm[n]["class"] == "conflicts_with_head_only")
assert head_only == ["92118"]
clean = sorted((n for n in map(str, fs["flagged"]) if mm[n]["class"] == "clean_both"), key=int)
fn_changed = sorted(n for n in clean if mm[n]["merged_fn"]["changed_vs_head"])
assert fn_changed == ["124151", "125881"] and mm["125881"]["merged_fn"]["returns"] == rc["head_fn"]["returns"] + 1
assert all(mm[n]["merged_fn"]["records"] == 4 for n in clean)
assert rc["vs_r4_watched"] == {"left": [126457], "entered": [], "class_changed": {}, "head_changed": []}
assert all(mm[str(n)]["head_unchanged"] for n in (124151, 120042, 92118, 87028, 86948, 65329, 125802, 125881, 108965, 15412))
assert rc["fork"]["404"] == {"state": "open", "title": rc["fork"]["404"]["title"], "table_rows": 39, "mentions_prefetch": False}

# final check (the last thing before the manifest was written)
fm = fin["main"]
assert fm["invalidate_on_commits_since_base"] == [] and fm["merge_tree_head"]["clean"] and fm["github_commits_since_base"] == []
assert fin["staging_ref"] == HEAD and not fin["fork_branch_present"]
assert all(v["state"] == ("closed" if n in ("98045", "126457") else "open") for n, v in fin["cited"].items()), fin["changed_since_recheck_r5"]

# F08 replay
r = pv["runs"]
assert pv["head"] == REPLAY and pv["base"] == MAIN and pv["head_tree"] == REPLAY_TREE
assert r["red"]["failed"] == [CONTRACT_TEST] and "15 tests passed, 1 failed" in r["red"]["summary"]
assert all("16 tests passed, 0 failed" in g["summary"] and not g["flaky_retry_printed"] for g in r["green"]) and len(r["green"]) == 3
assert all(s["failed"] == [CONTRACT_TEST] and "15 tests passed, 1 failed" in s["summary"] for s in r["sabotage"]) and len(r["sabotage"]) == 10
assert "16 tests passed, 0 failed" in r["stall_amended_1500ms"]["summary"]
assert r["stall_round2_150ms"]["failed"] == [CONTRACT_TEST]
assert "12 files, 330 tests passed, 0 failed" in r["adjacent_base"]["summary"]
assert "12 files, 331 tests passed, 0 failed" in r["adjacent_head"]["summary"]

# ---- OWNERSHIP/r20261001-04 ------------------------------------------------------------------------
own = {
    "schema": "xf.receipt.v1",
    "id": "OWNERSHIP/r20261001-04",
    "experiment": ("P2 ownership and PR-state refresh taken after #126457 closed (2026-10-01T16:23:32Z): state of every "
                   "upstream PR/issue the manifest, PR_BODY.md and OWNERSHIP r03 cite, #126457's close and the author's "
                   "other PRs, the 10 prefetch queries (all result pages), the teknium1 open-PR set, a changed-file scan of "
                   "every open search hit, a merge-tree matrix of the hits that touch the prefetch or shared-metrics files "
                   "against current main and the staging head, and a final state check just before manifest r5 was written"),
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu (gh read-only; git ls-remote, fetch by SHA with --no-write-fetch-head, merge-tree on the local object store)",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "main_revision": MAIN,
    "results": {
        "main_recheck": {
            "ls_remote_at": m["ls_remote_at"],
            "main": MAIN,
            "main_committer_date": m["committer_date"],
            "base_is_ancestor": m["base_is_ancestor"],
            "commits_since_base": m["commits_since_base"],
            "commits_since_r03_main_44a1ce9724": m["commits_since_r4_main"],
            "invalidate_on_commits_since_base": [],
            "invalidate_on_blobs_equal_base": "all 8",
            "merge_tree_head_vs_main": {"clean": True, "tree": REPLAY_TREE[:10]},
            "prefetch_grep_since_base": 0,
            "workflows": "0 commits under .github/ since the base; 52 workflow files, so the 0/52 push-trigger scan in MERGE/r20261001-03 stands",
            "fork_branch_name": f"staged/memory-prefetch-metric absent on the fork at {rc['fork_refs']['checked_at']} (5 other staged/* refs and the legacy staging ref exist); local ref still at the head",
            "f08_replay": "F08/r20261001-04 replays the head's diff on this main: tree equals the merge-tree result",
        },
        "cited_state_checked_at": rc["cited_checked_at"],
        "cited_state": {n: {k: (v[:10] if k == "head" and v else v) for k, v in row.items()
                            if k in ("state", "state_reason", "is_pr", "author", "head", "closed_at", "merged_at", "mergeable_state")}
                        for n, row in c.items()},
        "closed_of_cited": {"98045": "closed 2026-10-01T12:51:06Z by Navlem as a duplicate of #87028 (as in r03)",
                            "126457": "closed 2026-10-01T16:23:32Z by its author mozhongzhou, unmerged (new since r03)"},
        "pr126457": {
            "state": "CLOSED, not merged",
            "closed_at": p["closed_at"],
            "closed_by": "mozhongzhou (the author)",
            "head": p["head"][:10],
            "head_unchanged_since_MERGE_r03": True,
            "issue_comments": 0,
            "review_activity": "4 Copilot bot reviews with 6 inline comments, all on 2026-09-28; no human comment or review",
            "close_reason_given": None,
            "replacement": "none: the author's only PR in the repo (search is:pr author:mozhongzhou, all states) is #126457 itself; no cross-reference in its timeline",
            "files": rc["pr126457"]["files"],
            "effect": ("no longer an open adjacent PR; the head-only conflict count drops from 2 to 1 (#92118). r03 recorded it as "
                       "open at 16:14:25Z, nine minutes before the close; manifest r4 (16:35Z) and PR_BODY.md still listed it"),
        },
        "teknium1_open_prs": {"count": 260, "same_set_as_r01_r03": True, "added": [], "removed": [], "title_hits": []},
        "prefetch_search": {
            "searched_at": rc["searched_at"],
            "queries": {k: v["total_count"] for k, v in rc["queries"].items()},
            "vs_r03": "union 177 (r03: 178); only #126457 left ('memory prefetch' 153->152, 'external prefetch' 61->60, 'prefetch timeout' 55->54); nothing added",
            "command": "gh api -X GET --paginate search/issues -f q='repo:NousResearch/hermes-agent is:pr is:open <query>' -f per_page=100",
        },
        "file_scan": {
            "unique_open_prs": fs["scanned"],
            "watch_regex": fs["watch_regex"],
            "touch_watched_files": len(fs["flagged"]),
            "add_a_prefetch_record_call": [],
            "note": ("added lines naming shared_metrics/telemetry/metric appear only as prose, tables or unrelated telemetry "
                     "(#34521, #45743, #78584, #92118 'no telemetry', #115109, #115694, #124151, #125881); none records a prefetch row"),
        },
        "merge_matrix_watched": {
            "checked_at": rc["finished_at"],
            "main": MAIN[:10],
            "summary": {"already_conflict_with_main": 38, "clean_with_main_and_head": 11, "conflict_with_head_only": 1},
            "conflict_with_head_only": {n: {"author": mm[n]["author"], "files": mm[n]["extra_conflicts_with_head"]} for n in head_only},
            "clean_with_main_and_head": {n: f"{mm[n]['author']}: {mm[n]['title']}" for n in clean},
            "clean_set_prefetch_provider_changes": {
                "124151": "per-provider bound only; 4 record calls, 4 returns, as on the head",
                "125881": ("adds a governance check after the success/empty record call that can return '' (5 returns vs 4 on "
                           "the head); still one row per exit, but a context the check blocks is recorded as success. "
                           "Count of returns from the merged tree; not run"),
            },
            "vs_r03": "the same 50 PRs minus #126457 (closed); no PR entered; no class changed; no head changed",
            "closed_pr126457_for_reference": {"class_while_open": "conflicts_with_head_only", "files": mm["126457"]["extra_conflicts_with_head"]},
            "adjacent_heads_unchanged": "all 10 open adjacent heads in the manifest (#124151, #120042, #92118, #87028, #86948, #65329, #125802, #125881, #108965, #15412) are unchanged",
        },
        "fork": {k: {"state": v["state"], "table_rows": v["table_rows"]} for k, v in rc["fork"].items()},
        "fork_prefetch_hits": rc["fork_prefetch_hits"],
        "final_state_check": {
            "window": f"{fin['started_at']} .. {fin['finished_at']}",
            "main": fm["sha"],
            "commits_since_base": fm["commits_since_base"],
            "invalidate_on_commits_since_base": fm["invalidate_on_commits_since_base"],
            "merge_tree_head_vs_main": {"clean": fm["merge_tree_head"]["clean"], "tree": (fm["merge_tree_head"]["tree"] or "")[:10]},
            "cited_changed_since_recheck": fin["changed_since_recheck_r5"],
            "query_totals_changed": fin["query_totals_changed"],
            "fork": fin["fork"],
            "fork_branch_present": fin["fork_branch_present"],
            "staging_ref": fin["staging_ref"],
        },
    },
    "verdict": ("OURS (no open PR adds a prefetch counter); demand from #124151, #120042 and the field evidence on #87028; "
                "one open PR conflicts with the head (#92118); #98045 and #126457 closed; risk: teknium1 may land the same row himself"),
    "label": "OBSERVED",
    "provenance": "self",
    "privacy": "public-aggregate (public PR metadata only)",
    "raw_artifacts": {
        name: {"path": rel(R5 / f), "sha256": sha(R5 / f)}
        for name, f in [("recheck", "recheck_r5.json"), ("recheck_script", "recheck_r5.py"), ("recheck_log", "recheck_r5.log"),
                        ("final_state", "final_state_r5.json"), ("final_state_script", "final_state_r5.py")]
    },
    "supersedes": {
        "id": "OWNERSHIP/r20261001-03",
        "path": "receipts/OWNERSHIP-r20261001-03.json",
        "sha256_as_written": sha(RECEIPTS / "OWNERSHIP-r20261001-03.json"),
        "why": "recorded #126457 as open at 16:14:25Z (closed 16:23:32Z by its author); its head-only conflict count (2) is now 1",
    },
}

# ---- F08/r20261001-04 (replay on current main) -------------------------------------------------------
def cell(x):
    return {"observed": x["summary"], "failed": x["failed"], "log_sha256": x["log_sha256"]}


f08 = {
    "schema": "xf.receipt.v1",
    "id": "F08/r20261001-04",
    "experiment": ("F08 replay on current main: the staging head's diff applied onto main aaa863f7ff (25 commits after its "
                   "parent 040b6df2c4) as a temporary, unreferenced commit, then RED, GREEN x3, the 10 per-hunk sabotage "
                   "cells, the two stall cells and the 12-file adjacent run with the unchanged round-3 driver. It checks that "
                   "the proof in F08/r20261001-03 still holds on the newest main; it does not replace it"),
    "tier": "T1",
    "cost_usd": 0.0,
    "lane": "cpu",
    "spec": {"path": None, "prereg_commit": None, "note": "same oracle and cells as F08/r20261001-03"},
    "runner_revision": {"driver": f"work/r3/mpm_prove_r3.py (sha256 {sha(ROOT / 'work' / 'r3' / 'mpm_prove_r3.py')}, unchanged)",
                        "test_runner": "scripts/run_tests.sh"},
    "staging": "memory-prefetch-metric",
    "base_revision": MAIN,
    "head_revision": HEAD,
    "replay": {
        "commit": REPLAY,
        "parent": MAIN,
        "tree": REPLAY_TREE,
        "equals_merge_tree_of_head_and_main": True,
        "patch_id_equals_head": True,
        "changed_file_blobs_equal_head": True,
        "how": "git cherry-pick of the head onto main in a detached worktree (committer identity passed with -c); the worktree was removed and no ref points at the commit",
        "why_not_moved": "the branch stays at the head: no invalidate_on path changed since its parent, and moving it would change the exact head the verifier read",
    },
    "env": {"host": "<host>", "python": "3.11.14 (<read-only py3.11 venv>, used read-only as HERMES_PYTHON)",
            "nemo_relay_native": True,
            "sandbox": "no bwrap; HOME/HERMES_HOME forced to a scratch test home; run_tests.sh clean env",
            "network": "none used by tests", "load1_at_start": round(pv["load1_at_start"], 2),
            "load1_at_end": round(pv["load1_at_end"], 2), "window": f"{pv['started']} .. {pv['finished']}"},
    "command": "HOME=<scratch>/testhome-sf3-memory-prefetch-metric HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<read-only py3.11 venv>/bin/python bash scripts/run_tests.sh -j 2 tests/hermes_cli/test_shared_metrics_loop.py -q",
    "gates": {
        "red": {"arm": "main aaa863f7ff with the head's test file (the 5 production files from main)", "result": "PASS",
                "assertion": [ln for ln in r["red"]["assertion_lines"] if "AssertionError" in ln][0], **cell(r["red"])},
        "green": [{"rep": i + 1, **cell(g)} for i, g in enumerate(r["green"])],
        "green_reps_agree": "3/3",
        "sabotage": {"per_hunk": [{"mutation": s["label"].removeprefix("sabotage_"), "file": s["mutation"]["file"],
                                   "red_again": s["failed"] == [CONTRACT_TEST], **cell(s)} for s in r["sabotage"]],
                     "result": "10/10 re-RED on exactly the contract test"},
        "stall_tolerance": {"amended_test_1500ms_stall": {"result": "PASS (expected PASS)", **cell(r["stall_amended_1500ms"])},
                            "round2_test_150ms_stall": {"result": "FAIL (expected FAIL)", **cell(r["stall_round2_150ms"])}},
        "adjacent": {"files": 12, "base": r["adjacent_base"]["summary"], "head": r["adjacent_head"]["summary"],
                     "base_failed": r["adjacent_base"]["failed"], "head_failed": r["adjacent_head"]["failed"],
                     "identical": True, "note": "330 of 330 on main, 331 of 331 with the replay (+1 = the new test)",
                     "log_sha256": {"base": r["adjacent_base"]["log_sha256"], "head": r["adjacent_head"]["log_sha256"]}},
        "flaky": False,
    },
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["real provider backends", "py3.14 CI matrix", "Windows/macOS"],
    "limitations": ["host load1 about 10 to 13 (shared host)", "same limitations as F08/r20261001-03"],
    "verdict": "KEEP",
    "provenance": "self",
    "privacy": "public-aggregate",
    "ai_assistance": "Claude Code (Opus 5.5) ran the replay and wrote this receipt",
    "raw_artifacts": {"results": {"path": rel(R5 / "prove" / "prove_results.json"), "sha256": sha(R5 / "prove" / "prove_results.json")},
                      "stdout": {"path": rel(R5 / "prove_stdout.txt"), "sha256": sha(R5 / "prove_stdout.txt")}},
    "complements": {"id": "F08/r20261001-03", "why": "r03 proves the branch commit on its own parent and stays current; this replays it on the newest main"},
}

for rid, obj in (("OWNERSHIP-r20261001-04", own), ("F08-r20261001-04", f08)):
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    for bad in ("/home/", "/tmp/", "/mnt/", "/workspace/", "zer0", "<local-host>"):
        assert bad not in text, (rid, bad)
    out = RECEIPTS / f"{rid}.json"
    assert not out.exists(), "write-once"
    out.write_text(text, encoding="utf-8")
    print(out.name, hashlib.sha256(text.encode()).hexdigest())
