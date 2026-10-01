"""Write receipts/F01-r20261001-04.json from r04_parsed.json (round-4 fix). usage: write_r04.py <scratch> <staging dir>"""
import json
import sys
from pathlib import Path

S, D = Path(sys.argv[1]), Path(sys.argv[2])
b = json.load(open(S / "st-edit-fuzzy" / "r04_parsed.json", encoding="utf-8"))
C = "tests/tools/test_fuzzy_match_wrong_region.py"
CONTRACT_IDS = b["red_contract_only"]["failed_ids"]


def strip_rep(r):
    files = dict(r["carrier_tests"])
    files[C] = r["contract"]
    return {"rep": r["rep"], "files": files, "fuzzy_match_sha256_16": r["fuzzy_match_sha256_16"],
            "failed_ids": r["failed_ids"], "log": r["log"]}


ab = {arm: {"contract_passed_of_10": v["contract_passed_of_10"], "contract_failed_of_10": v["contract_failed_of_10"],
            "reps_agree": v["reps_agree"], "carrier_tests_cross_applied": v["carrier_tests_cross_applied"],
            "reps": [strip_rep(r) for r in v["reps"]]} for arm, v in b["ab"].items()}

receipt = {
    "schema": "xf.receipt.v1 (hand-run; xf executor not built)",
    "id": "F01/r20261001-04",
    "staging": "edit-fuzzy-wrong-region",
    "kind": "full carrier-A/B re-proof of the rebased head v3 (phase-3 round-4 fix)",
    "relation": "v3 = the v2 commit (c3af284031, proven in F01/r20261001-02 on aea969677c) cherry-picked onto main 44a1ce9724. This receipt is the full proof for v3 on that main: RED 4 runs, GREEN 3/3, every A/B arm 3 reps, per-hunk sabotage, the 13-file adjacent set, stdlib line coverage, E01, M01 and the direct-call probes. Every count equals r02's, field by field. r02 stays the proof of v2; r03 was a 1-run spot check of v2 re-applied on this main and is superseded by this receipt.",
    "tier": "T1 ($0): real ShellFileOperations + LocalEnvironment (bash in tmp dir), no model, no provider",
    "origin_refs": ["NousResearch/hermes-agent#54572", "NousResearch/hermes-agent#111116", "NousResearch/hermes-agent#93698"],
    "measured_at": "2026-10-01T16:37Z-17:00Z",
    "base_revision": {
        "main": "44a1ce9724502b9c692faaef00af3054bf11f1a6",
        "main_was_current": "git ls-remote refs/heads/main = 44a1ce9724 at 16:34Z and 16:37Z, when the commit was rebased; main had moved to aaa863f7ff by 16:56Z (see freshness_after_proof)",
        "previous_main": "aea969677c60a1bb72fe227fdfb98f196a2092cc",
        "commits_since_previous_main": 29,
        "invalidate_on_unchanged": {"tools/fuzzy_match.py": "a6a439d70e7d31a2ff781db3ab9baa6686ea4ee9",
                                    "tools/file_operations.py": "cc028e89f130b2629cbcb6448203b1a5d770c45a",
                                    "tools/patch_parser.py": "8e6ce92ed7b68d3ca32c57b346a4a1087af0c8bf"},
        "github_workflows_changed_since_previous_main": 0,
    },
    "head_revision": {
        "sha": "fdaaf5b7295125dd2c38bf66980e4016ce3bfb09",
        "version": 3,
        "parent": "44a1ce9724502b9c692faaef00af3054bf11f1a6",
        "tree": "f23cd04b5de44fb2cbe2b9822232203ea42f259d",
        "files": {C: {"added": 106, "removed": 0, "blob": "e059b025c81fe9b4154c201c658d0bd07ce1e5e4"}},
        "previous_head": "c3af284031fcdf95e0f0a05d872d25d84ad45039",
        "made_by": "git cherry-pick c3af284031 onto 44a1ce9724 (clean). Same test blob, message, author, author date and trailers as v2; only the parent, the committer date and the SHA differ (format-patches differ only in the From line).",
        "author": "Kevin Rajan (kvnloo)",
        "trailers": ["Co-authored-by: MaxFreedomPollard", "Co-authored-by: finn763 (Finn763)", "Co-authored-by: KoNit-K",
                     "Co-authored-by: likivik", "Co-authored-by: Enough1122", "Co-Authored-By: Claude Opus 5.5 (AI-assistance disclosure)"],
        "trailers_note": "GitHub handles only; the full trailer lines, with addresses, are in the commit itself (edit-fuzzy-wrong-region.patch, format-patch of fdaaf5b729).",
        "earlier_versions_kept": {
            "refs/archive/staging/edit-fuzzy-wrong-region-v0-build": "01bf8d379e (first build on 572e4f4fad)",
            "refs/archive/staging/edit-fuzzy-wrong-region-v0-cherry": "8375dc3cca (cherry-pick onto 234badf401)",
            "refs/archive/staging/edit-fuzzy-wrong-region-v1": "ea25f06132 (round 0 staged head)",
            "refs/archive/staging/edit-fuzzy-wrong-region-v2": "c3af284031 (rounds 1-3 head)",
        },
    },
    "command": "receipts/raw/scripts/run_all_v4.sh -> run_arm_v4.sh <arm> <rep> <log> <files...> (wraps HOME=$S/testhome-sf3-edit-fuzzy-wrong-region HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<venv-python> bash scripts/run_tests.sh -j 2 <files> -q -m 'not live and not integration'); overlays from receipts/raw/scripts/build_overlay_v4.sh",
    "arms": {
        "base": {"tree": "main 44a1ce9724 + v3 fdaaf5b729", "fuzzy_match_sha256": "71eac9a33f6b8441f0cd1ac787fa08d1018dc0adb04430c17ff7e937253e8790"},
        "both+fold": {"built_on": "v3 fdaaf5b729, from the published files only",
                       "steps": ["git apply c54575-rebased-on-main.diff (clean)", "git diff 5f3f5896a4^ 5f3f5896a4 | git apply (clean)", "git apply foldin-125376-stripped-guard.diff (clean)"],
                       "fuzzy_match_sha256": "145fb70356117a9ab7a9356f8f40f8257d7bdfd5ff045510d19b47cbbf6fc9a7",
                       "numstat_vs_head": {"tools/fuzzy_match.py": [36, 0], "tests/tools/test_fuzzy_match.py": [84, 0], "tests/tools/test_file_tools_live.py": [69, 0]}},
        "overlay_sha256_16": {"c54575": "fc55b3d0563cee1e", "c125376-leaf": "7e80805b0c8a04c5", "both": "f42e75ebd653bf3c",
                               "leaf+fold": "92125b051af75e87", "both+fold": "145fb70356117a9a", "c126502": "a2024727f6c084ed",
                               "c126502+leaf+fold": "89b94ed1dbd9b15c"},
        "overlays_identical_to_r02": True,
        "c126502_built_from": "git merge-tree --write-tree 44a1ce9724 6d4fbff950 (clean, tree a29cb4af0a), its tools/fuzzy_match.py",
    },
    "gates": {
        "red": {
            "arm": "base", "result": "PASS", "label": "OBSERVED",
            "contract_only": {"files": b["red_contract_only"]["files"], "failed_ids": CONTRACT_IDS,
                              "marker_lines": b["red_contract_only"]["marker_lines"], "log": b["red_contract_only"]["log"],
                              "note": "the commit as shipped, main's own tests untouched"},
            "with_carrier_tests_cross_applied": [strip_rep(r) for r in b["ab"]["base"]["reps"]],
            "observed": "contract: 8 of 10 cases fail, 2 pass, in 4 of 4 runs (1 contract-only + 3 with the carrier tests cross-applied); every contract failure carries the marker (block_anchor 2, context_aware 6 per run). With the carriers' tests cross-applied, 3 carrier tests also fail on main (TestContentDivergenceGuard::test_block_anchor_partial_middle_does_not_overwrite, TestEdittoolShapeSingleLineFailLoud::test_wrong_token_single_line_refused, TestPatchReplaceWrongRegionRejected::test_block_anchor_wrong_region_is_rejected), listed apart from the contract ids",
            "marker": "wrong region replaced via block_anchor|context_aware: count=1, error=None",
        },
        "green": {"arm": "both+fold", "result": "PASS", "label": "OBSERVED",
                  "reps": [strip_rep(r) for r in b["ab"]["both+fold"]["reps"]],
                  "observed": "3 of 3 reps: contract 10 of 10 cases pass; carrier tests 61 of 61 and 16 of 16 pass"},
        "sabotage": {m: {**v, "red_again": v["files"][C]["failed"] > 0} for m, v in b["sabotage"].items()},
        "sabotage_summary": "per-hunk revert on the GREEN arm, counted as contract cases failing of 10: #54575 floor -> 2 fail (the block cases); #125376 single-line guard -> 6 fail (the single-line cases); fold-in line only -> 2 fail (the trailing-newline cases), while both carriers' own tests still all pass (61 of 61, 16 of 16), so only the contract test pins the fold-in line",
        "adjacent": {"files": sorted(next(iter(b["adjacent"].values()))["files"]),
                     "per_arm": b["adjacent"],
                     "identical": all(b["adjacent"][a]["total"] == {"passed": 284, "failed": 0, "skipped": 8} for a in ("base", "c54575", "c125376-leaf", "both+fold")),
                     "c126502_identical": False,
                     "note": "main's own versions of the 13 files (carrier tests not cross-applied): 284 passed / 8 skipped / 0 failed on base, c54575, c125376-leaf and both+fold; c126502 282 passed / 8 skipped / 2 failed (the two escape-drift tests)"},
        "single_arm_ab": {"arms": ab,
                          "summary": "3 reps per arm on 44a1ce9724, all reps agree, contract cases passing of 10 (failing): base 2 (8); c54575 4 (6); c125376-leaf 6 (4); both 8 (2); leaf+fold 8 (2); both+fold 10 (0); c126502 4 (6); c126502+leaf+fold 10 (0)",
                          "identical_to_r02": True},
        "e01_m01_probes": {
            "command": "receipts/raw/scripts/run_e01_m01_v4.sh base c54575 c125376-leaf both both+fold; receipts/raw/scripts/probe_{arms,cross,trap_variant}.py over all 8 arms; receipts/raw/probes-r3/probe_floor_reach.py on the c54575 file",
            "result": "E01 (#111127 evals/edittool at 5444b1a2a8): reports and tripwire output byte-identical to r02 on all 5 arms (the JSON differs only in generated_at). main: str_replace 6 of 6 tasks pass, hermes_patch 5 of 6 pass (missing_anchor applied via context_aware); every fixed arm: hermes_patch 5 of 6 pass (missing_anchor no_change through the already-applied check); tripwire ALL PASS on every arm. M01 meter-probe output byte-identical to r02 on all 5 arms. Direct-call probes (residual, cross-application of the #93717/#126502 Markdown repros and escape-drift diagnostics, trap variant) byte-identical to r02 on all 8 arms. Floor probe on #54575's file: byte-identical to r03 (single-line matches score 0.923 and are kept; the block case scores 0.851 and is dropped)",
            "files": {k: v for k, v in b["aux"].items() if not k.startswith("cov-")},
        },
        "coverage_P4": {
            "tool": "stdlib sys.settrace line events (receipts/raw/scripts/cov_probe.py, unchanged); coverage.py is not installed in the test interpreter and nothing was installed into it",
            "result": "landmark lines and per-test seam tags identical to r02 on base (pytest rc 1) and both+fold (pytest rc 0): on base every wrong-region cell reaches the block_anchor ratio line or the context_aware all-lines accept and the write through the seam; on GREEN the floor check and its continue, and the stripped-pattern guard and its return [], run through the seam, then the no-match path",
            "files": {k: v for k, v in b["aux"].items() if k.startswith("cov-")},
        },
        "flaky": False,
        "guards": "F14 standing set NOT run (factory-replay-gate harness not built); P5 stays PENDING",
    },
    "freshness_after_proof": {
        "checked_at": "2026-10-01T16:56Z-17:00Z",
        "main": "aaa863f7ff2dec1821be1652b5d15ad14ecea70b",
        "commits_since_proof_main": 4,
        "changed_paths_since_proof_main": ["agent/model_metadata.py", "tests/agent/test_model_metadata.py", "tests/hermes_cli/test_auth_codex_quota_probe.py", "tests/hermes_cli/test_gpt6_tiers_registration.py"],
        "edit_path_and_13_adjacent_files_byte_identical": True,
        "merge_tree": {"command": "git merge-tree --write-tree aaa863f7ff fdaaf5b729", "tree": "8f651c0238f0aec4ed1a34b5411264a1e19fb80d", "clean": True},
        "spot_check": {"applied_as": "git cherry-pick fdaaf5b729 onto aaa863f7ff in the same throwaway worktree (clean; the logs show its local id 402200d52c); the staging branch stays at fdaaf5b729 on 44a1ce9724",
                       "runs": {k: {"files": v["files"], "marker_lines": v["marker_lines"], "log": v["log"]} for k, v in b["fresh"].items()},
                       "result": "base: contract 8 of 10 cases fail, 2 pass, every failure with the marker; both+fold: contract 10 of 10 pass, carrier tests 61 of 61 and 16 of 16 pass (1 run each)"},
        "note": "main moved while this round ran. The proof stays on 44a1ce9724; rebase again at push time (STAGING.md Next steps)",
    },
    "merge_check": {"main": "44a1ce9724502b9c692faaef00af3054bf11f1a6", "checked_at": "2026-10-01T16:40Z",
                    "command": "git merge-tree --write-tree 44a1ce9724 fdaaf5b729",
                    "tree": "f23cd04b5de44fb2cbe2b9822232203ea42f259d", "clean": True,
                    "note": "the head is one commit on this main, so the merge tree is the head's own tree"},
    "member_heads_on_main": {
        "checked_at": "2026-10-01T16:37Z-16:44Z (git ls-remote refs/pull/<n>/head + gh api, read-only)",
        "heads_unchanged": {"54575": "e28d7c772d", "125376": "5f3f5896a4", "126502": "6d4fbff950", "93717": "3c4c81f706", "111127": "5444b1a2a8", "128138": "83401c2591"},
        "state": "all six OPEN, none merged",
        "merge_tree_on_44a1ce9724": {
            "c54575 (e28d7c772d)": {"clean": False, "conflicts": ["tests/tools/test_file_tools_live.py", "tests/tools/test_fuzzy_match.py"],
                                    "tools/fuzzy_match.py": "merges clean; sha256 fc55b3d0563cee1e..., the same file c54575-rebased-on-main.diff gives",
                                    "why": "main deleted class TestStrategyNameSurfaced (test_fuzzy_match.py) and class TestTerminalOutputCleanliness (test_file_tools_live.py; its section comment is still there) next to the PR's additions; both classes exist at the PR's merge base fa75692211"},
            "c125376 full head (5f3f5896a4, includes bot_relay commit 1c890ae8d0)": {"clean": False, "conflicts": ["tui_gateway/methods_bot_relay.py"]},
            "c126502 (6d4fbff950)": {"clean": True},
            "c93717 (3c4c81f706)": {"clean": False, "conflicts": ["tools/fuzzy_match.py"]},
            "c111127 (5444b1a2a8)": {"clean": True},
            "c128138 (83401c2591)": {"clean": True},
        },
        "c125376_fix_commit_cherry_pick": {"command": "git merge-tree --write-tree --merge-base 5f3f5896a4^ 44a1ce9724 5f3f5896a4",
                                           "clean": True, "tree": "79e982be4d378e2de4b3e2e249f533ca6a4d197f",
                                           "tools/fuzzy_match.py_blob": "e01522910cf9ab15766dbdb780a2453345ab9fbd (same blob as on every earlier main)"},
        "c54575_rebase_diff": {"file": "c54575-rebased-on-main.diff", "sha256": "e8da44106d152e99ea6c6d4905c4c3db6897f1f7bf0ea236dff3a700635b4c5d",
                               "applies_clean_on": "44a1ce9724 (git apply --check; also with trailing whitespace stripped)",
                               "numstat": {"tools/fuzzy_match.py": [30, 0], "tests/tools/test_fuzzy_match.py": [58, 0], "tests/tools/test_file_tools_live.py": [69, 0]},
                               "tests_added": "5 def test_ lines (3 in test_fuzzy_match.py, 2 live)",
                               "inlined_in": "body.md section 3, byte for byte (round-trip of the posted text gives the same sha256)"},
        "foldin_diff": {"file": "foldin-125376-stripped-guard.diff", "sha256": "c0846607c44d3207c14accf3f38a4b38f38aa41558591eb2a44d1bf7f1759fee",
                        "applies_to": "5f3f5896a4:tools/fuzzy_match.py (offset -1)",
                        "origin": "word for word the fix proposed by Enough1122 in the 2026-09-29 review comment on #125376"},
        "related_new": {"NousResearch/hermes-agent#129645 (29789718ff, Froraut, opened 2026-09-30)": "found by the round-4 dedupe re-search; line endings / @@ hint validation, not a wrong-region fix; merge-tree clean on 44a1ce9724; the c54575 diff and 5f3f5896a4's fuzzy_match.py hunk both still apply on main + #129645"},
    },
    "env": {"host": "<local-workstation> (name withheld)",
            "python_interpreter": "<venv-python> (interpreter only; HOME/HERMES_HOME isolated)",
            "HOME": "$S/testhome-sf3-edit-fuzzy-wrong-region", "HERMES_HOME": "$HOME/.hermes",
            "network": "no provider, no model, direct tool calls; git ls-remote, git fetch of refs/pull/129645/head and gh api read-only for head, state and dedupe checks",
            "sandbox": "process isolation via run_tests.sh clean env; bwrap NOT used (xf executor not built)"},
    "evidence_class": {"local": True, "ci": "none", "simulation": False, "runtime": False, "kind": "mechanism"},
    "not_tested": ["model behaviour after a refusal (E02, deferred)", "#125376 full head and #93717 (CONFLICTING, not run)",
                   "F14 standing guard set", "bwrap sandbox / blind verifier", "#129645 as an arm (related, not evaluated)"],
    "verdict": "KEEP",
    "resource_usage": {"api_cost_usd": 0.0, "gpu_s": 0, "test_runs": len(b["runs"]) + len(b["fresh"]), "coverage_runs": 2, "e01_m01_arms": 5, "probe_scripts": 4},
    "scripts": b["scripts"],
    "ai_assistance": "Claude Code (Opus 5.5) rebased the commit, re-ran every proof and wrote this receipt",
    "privacy": "public-aggregate (synthetic fixtures only; absolute local paths replaced by $S, $WT, <venv-python> and <pytest-tmp>; no host name, no email addresses)",
}
out = D / "receipts" / "F01-r20261001-04.json"
out.write_text(json.dumps(receipt, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(out.name, len(out.read_text()))
