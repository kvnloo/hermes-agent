"""Write OWNERSHIP/r20261001-03 for memory-prefetch-metric from the round-4 recheck files under work/r4.

Repo-relative paths only. Usage: python make_receipts_r4.py  (any cwd)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R4 = ROOT / "work" / "r4"
RECEIPTS = ROOT / "receipts"
BASE = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5"
HEAD = "569ad4d84b0f9888ea2598c2a8ea416b2c75bad6"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


rc = json.loads((R4 / "recheck_r4.json").read_text())
fs = json.loads((R4 / "fullscan_r4.json").read_text())
fm = json.loads((R4 / "flagged_merge_r4.json").read_text())
cs = json.loads((R4 / "clean_semantics_r4.json").read_text())

main = rc["main"]
assert main["sha"] == "44a1ce9724502b9c692faaef00af3054bf11f1a6" and main["commits_since_base"] == 21
assert main["invalidate_on_commits"] == [] and main["merge_tree_head"]["clean"] and main["prefetch_grep_since_base"] == []
assert rc["staging_ref"] == HEAD
c = rc["cited"]
assert c["98045"]["state"] == "closed" and c["98045"]["merged_at"] is None and c["98045"]["closed_by"] == ["Navlem"]
assert all(c[n]["state"] == "open" for n in c if n != "98045")
assert rc["teknium1"]["total_count"] == 260 and rc["teknium1"]["same_set_as_r3"] and rc["teknium1"]["title_hits"] == []
assert fm["summary"] == {"conflicts_with_main_already": 38, "clean_both": 11, "conflicts_with_head_only": 2}
head_only = sorted(n for n, v in fm["prs"].items() if v["class"] == "conflicts_with_head_only")
assert head_only == ["126457", "92118"]
clean = sorted((n for n, v in fm["prs"].items() if v["class"] == "clean_both"), key=int)
fn_changed = sorted(n for n, v in cs["prs"].items() if v["fn_changed"])
assert fn_changed == ["124151", "125881"] and cs["prs"]["125881"]["returns"] == cs["head_fn"]["returns"] + 1
navlem = [x for x in c["98045"]["comments_after_2026_09_01"] if x["user"] == "Navlem"][0]
rod87028 = [x for x in rc["pr87028_comments"] if x["user"] == "rodrigogs"][0]
assert "101 of 197" in rod87028["body"]

q = rc["queries"]
receipt = {
    "schema": "xf.receipt.v1",
    "id": "OWNERSHIP/r20261001-03",
    "experiment": ("P2 ownership and PR-state refresh against current main: state of every upstream PR/issue the manifest "
                   "cites, the 10 prefetch queries (all result pages), the teknium1 open-PR set, a changed-file scan of "
                   "every open search hit, and a merge-tree matrix of the hits that touch the prefetch or shared-metrics "
                   "files against current main and the staging head"),
    "tier": "T0",
    "cost_usd": 0.0,
    "lane": "cpu (gh read-only; git ls-remote and merge-tree on the local object store)",
    "staging": "memory-prefetch-metric",
    "base_revision": BASE,
    "head_revision": HEAD,
    "main_revision": main["sha"],
    "results": {
        "main_recheck": {
            "ls_remote_at": main["ls_remote_at"],
            "main": main["sha"],
            "main_committer_date": main["committer_date"],
            "base_is_ancestor": main["base_is_ancestor"],
            "commits_since_base": main["commits_since_base"],
            "invalidate_on_commits_since_base": main["invalidate_on_commits"],
            "merge_tree_head_vs_main": main["merge_tree_head"],
            "prefetch_grep_since_2026_09_20": {"count": len(main["prefetch_grep_since_0920"]),
                                               "since_base": len(main["prefetch_grep_since_base"]),
                                               "note": "the same 15 commits as on a3b56cac95; none meters prefetch"},
            "workflows": "0 commits under .github/ since the base; 52 workflow files, so the 0/52 push-trigger scan in MERGE/r20261001-03 stands",
            "fork_branch_name": "staged/memory-prefetch-metric absent on the fork at 16:28Z (5 other staged/* refs exist); local ref still at the head",
        },
        "cited_state_checked_at": rc["started_at"],
        "cited_state": {n: {k: v for k, v in row.items() if k in ("state", "state_reason", "is_pr", "author", "head", "closed_at", "merged_at", "mergeable_state")}
                        for n, row in c.items()},
        "pr98045": {
            "state": "CLOSED, not merged",
            "closed_at": c["98045"]["closed_at"],
            "closed_by": "Navlem",
            "reason": "duplicate of #87028 (alt-glitch's AI triage flagged it as a duplicate of #87028 on 2026-08-29)",
            "closing_comment": navlem["body"],
            "effect": "no longer an open adjacent PR or a demand signal; r02 recorded it as OPEN at 12:15Z, before the close",
        },
        "pr87028": {
            "state": c["87028"]["state"].upper(),
            "author": "richardclawbot",
            "head": c["87028"]["head"],
            "mergeable_state": c["87028"]["mergeable_state"],
            "field_evidence_comment": {
                "user": "rodrigogs",
                "at": rod87028["at"],
                "summary": ("Bedrock-only Docker gateway, holographic with a local Ollama embedder: the 8 s join fired 4 times "
                            "in about an hour, coinciding with 18.4-47.1 s embeds or a 400 after 60 s; 101 of 197 agent starts "
                            "injected no external memory, which he says he cannot all pin on the 8 s cap; the per-turn skip is "
                            "logged only at DEBUG; he argues a tunable bound matters more than more logging"),
            },
            "use": "demand signal 3 (replaces #98045): field evidence that the drop rate is currently invisible and unattributable; it argues for the bound, not for a counter",
        },
        "teknium1_open_prs": {"count": rc["teknium1"]["total_count"], "same_set_as_r02": True,
                              "added": rc["teknium1"]["added"], "removed": rc["teknium1"]["removed"], "title_hits": []},
        "prefetch_search": {
            "searched_at": rc["searched_at"],
            "queries": {k: v["total_count"] for k, v in q.items()},
            "vs_r02": {
                "removed": "#98045 from 'memory prefetch', 'external prefetch', 'prefetch timeout', 'prefetch latency' (closed)",
                "added": "#129620 to 'external prefetch' (JoaoMarcos44, Anthropic thinking replay; touches agent/turn_context.py, merges cleanly with main and the head); #98703 to 'prefetch latency' (oleg-koval, pre-agent turn routing; touches none of the watched files)",
                "r02_gap": "r02 stored only the first 100 of 152 'memory prefetch' hits; this run lists all 153",
            },
            "command": "gh api -X GET --paginate search/issues -f q='repo:NousResearch/hermes-agent is:pr is:open <query>' -f per_page=100",
        },
        "file_scan": {
            "unique_open_prs": fs["scanned"],
            "watch_regex": fs["watch_regex"],
            "touch_watched_files": len(fs["flagged"]),
            "add_a_prefetch_counter": [],
            "note": ("added lines naming shared_metrics/telemetry/metric appear only as prose, tables or unrelated telemetry words "
                     "(#34521, #45743, #78584, #92118 'no telemetry', #115109, #115694, #124151, #125881); none records a prefetch row"),
        },
        "merge_matrix_watched": {
            "checked_at": fm["checked_at"],
            "summary": {"already_conflict_with_main": 38, "clean_with_main_and_head": 11, "conflict_with_head_only": 2},
            "conflict_with_head_only": {n: {"author": fm["prs"][n]["author"], "files": fm["prs"][n]["extra_conflicts_with_head"]} for n in head_only},
            "clean_with_main_and_head": {n: f"{fm['prs'][n]['author']}: {fm['prs'][n]['title']}" for n in clean},
            "clean_set_prefetch_provider_changes": {
                "124151": "per-provider bound only; one record call per exit kept",
                "125881": ("pstarkgit: adds a governance check after the success/empty record call that can return '' "
                           "(5 returns vs 4 on the head); still one row per exit, but a context the hook blocks is "
                           "recorded as success. Text-only reading of the merged tree; not run"),
            },
            "conflict_with_main_already_includes": ["87028", "86948", "65329", "125802", "78584", "58597", "63759", "84412", "101580", "15412"],
            "pr_heads_vs_MERGE_r03": "all 10 heads in MERGE/r20261001-03 unchanged; their merge results are the same on 44a1ce9724",
        },
        "fork": {k: {"state": v["state"], "table_rows": v["table_rows"]} for k, v in rc["fork"].items()},
    },
    "verdict": "OURS (no open PR adds a prefetch counter); demand from #124151, #120042 and the field evidence on #87028; #98045 closed as a duplicate of #87028 and dropped; risk: teknium1 may land the same row himself",
    "label": "OBSERVED",
    "provenance": "self",
    "privacy": "public-aggregate (public PR metadata only)",
    "raw_artifacts": {
        name: {"path": rel(R4 / f), "sha256": sha(R4 / f)}
        for name, f in [("recheck", "recheck_r4.json"), ("recheck_script", "recheck_r4.py"), ("fullscan", "fullscan_r4.json"),
                        ("fullscan_script", "fullscan_r4.py"), ("flagged_merge", "flagged_merge_r4.json"),
                        ("flagged_merge_script", "flagged_merge_r4.py"), ("clean_semantics", "clean_semantics_r4.json"),
                        ("clean_semantics_script", "clean_semantics_r4.py"), ("newhits", "newhits_r4.json"),
                        ("freshness", "freshness_r4.txt")]
    },
    "supersedes": {
        "id": "OWNERSHIP/r20261001-02",
        "path": "receipts/OWNERSHIP-r20261001-02.json",
        "sha256_as_written": sha(RECEIPTS / "OWNERSHIP-r20261001-02.json"),
        "why": "recorded #98045 as OPEN (closed 12:51Z as a duplicate of #87028); stored only 100 of 152 'memory prefetch' hits and did not merge-test the hits that touch the watched files",
    },
}
text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
for bad in ("/home/", "/tmp/", "/mnt/", "/workspace/", "zer0"):
    assert bad not in text, bad
out = RECEIPTS / "OWNERSHIP-r20261001-03.json"
assert not out.exists(), "write-once"
out.write_text(text, encoding="utf-8")
print(out.name, hashlib.sha256(text.encode()).hexdigest())
