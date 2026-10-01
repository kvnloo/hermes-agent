+++
xf_staging = 1
id = "compressor-media-extraction"
title = "Split context_compressor.py along <stem>_<topic>: image/media slice -> agent/context_compressor_media.py"
version = 1
branch = "staging/compressor-media-extraction"
branch_fork = "kvnloo/hermes-agent:staged/compressor-media-extraction (not pushed)"
branch_physical = "local-only in scratch h.git. OD-0 is resolved by the rename: the fork keeps a legacy refs/heads/staging (28790e597c) that blocks refs/heads/staging/*, so this branch goes to the fork as staged/compressor-media-extraction (ls-remote 2026-10-01 06:15 and 08:43 CDT: no refs/heads/staged*; re-checked 11:51 CDT in fix round 3: refs/heads/staged/ now holds five other items' branches, none named staged/compressor-media-extraction, and refs/heads/staging is still 28790e597c)"
branch_sha = "c5e8be14b43bf75bcc2e4e8d95f2d4810a7e2779"
branch_version_deviation = "FACTORY §10 says a rebuild goes to staging/<id>-v2. Fix round 1 instead moved the local staging/compressor-media-extraction from d2bff3a59e to the rebuild c5e8be14b4. Recorded, not renamed: neither commit was ever pushed; v1 is kept at refs/xf/superseded/compressor-media-extraction-v1 (re-checked fix round 3: d2bff3a59edd1a9be5a90f5d84bbded1fbe04e8b), so nothing is lost; and the push plan maps the local name to staged/compressor-media-extraction. phase3_results.json builds[id].branch_sha still says d2bff3a59e; the current head is c5e8be14b4. If the orchestrator wants the -v2 name, rename before the first push"
status = "STAGED"          # one commit + evidence; blocked from PROMOTION_READY by the pre-ask (P2), P5 (flaky = false not recorded; F14 is EQUAL), P8, P10, P12
route = "support-note"     # selection said core-pr; adjusted after the ownership check (#80636 and the four PRs stacked on it own this slice)
promotion_form_selected = "core-pr"
promotion_form_effective = "salvage-support (support-note on #80636; salvage PR only if that thread agrees)"
feature = "compression-god-file-decomposition"
invariant = "Moving the image/media cluster out of agent/context_compressor.py changes no behaviour: identical source/AST for every moved statement, identical AST for every other facade statement, identical outputs, identical test pass/fail sets, and zero references to a moved name through the old path anywhere in the tree (old_path_zero = 0). The facade itself imports the six moved names it still calls (_is_image_part, _retire_stale_tool_result_images, _rewritten, _strip_historical_media, _strip_images_from_tool_msg, _summary_part_text), so those six stay importable from agent.context_compressor; the other ten do not."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
fetched_at = "2026-10-01T05:56-05:00 (commit time of main tip at fetch, fix round 1)"
selection_pin = "e496ccc7d7 (selection/catalog); first build d2bff3a59e on 572e4f4fad (superseded); rebuilt on aea969677c"
freshness = "Not re-based. Polish round 5 (2026-10-01 13:30-13:40 CDT, receipt recheck/r20261001-05): main 34f8ec3b40 (committed 2026-10-01T17:29:37Z) is 38 commits past this base (base is an ancestor) and 9 past 44a1ce9724. 0 diff lines in the invalidate_on paths (agent/context_compressor*.py, agent/turn_request_assembly.py, agent/chat_completion_helpers.py, agent/image_eviction_policy.py); all 10 touched files plus test_compressor_zero_user_guard.py, native_compaction.py, turn_context.py, conversation_compression.py and AGENTS.md keep the base's blob ids. The round-4 advisory's aaa863f7ff is an intermediate main, superseded by this check"

[upstream]
issues = ["NousResearch/hermes-agent#78645 (andrexibiza, OPEN, needs-decision: shard agent/context_compressor.py)",
          "NousResearch/hermes-agent#78647 (andrexibiza, OPEN, needs-decision: repo-wide god-file epic)"]
owner_pr = { pr = 80636, author = "andrexibiza", head = "5aa1746a288f6401b6b2b28ae3607e99d9b72e74", state = "OPEN (maintainer HOLD)", note = "LB4 media slice; 4 stacked commits; re-export seam; conflicts with main. Its LB4 commit 5aa1746a28 is also carried, unchanged, by the four PRs listed under competitors" }
competitors = [
  { pr = 80645, author = "andrexibiza", head = "2ace2a70c00ac818d0759fec406f3735a6f6d8f5", result = "conflicts with main; add/add on the media module vs this branch", note = "LB5a, stacked on #80636; carries 5aa1746a28 unchanged (same agent/context_compressor_media.py blob ffd4d23465 and seam test)" },
  { pr = 80644, author = "andrexibiza", head = "c871197b77b4fbe6cf0059a74161322b5dc02ad2", result = "conflicts with main; add/add on the media module vs this branch", note = "LB7, stacked on #80636 plus LB5a; carries 5aa1746a28 unchanged; updated 2026-08-31" },
  { pr = 81074, author = "andrexibiza", head = "4effdf33967f49f19069c00c5b5348fd8c10539b", result = "conflicts with main; add/add on the media module vs this branch", note = "LB6; carries 5aa1746a28 unchanged; teknium1 names it as #80636's claimed superseder (the HOLD reason, #113887 comment 5727991843)" },
  { pr = 81181, author = "andrexibiza", head = "e40f2db1402cb629dedcff57e656dee439bb51c3", result = "conflicts with main; add/add on the media module vs this branch", note = "stack tip (summary kernel), updated 2026-08-31; carries 5aa1746a28 unchanged" },
]
related = ["NousResearch/hermes-agent#80628 (LB2, closed stale by teknium1 2026-09-02)",
           "NousResearch/hermes-agent#113887 (refactor triage wave, CLOSED 2026-09-19; teknium1 HOLD list: #80626/#80636/#80645 -> #81074)",
           "NousResearch/hermes-agent#102117 (teknium1, MERGED 2026-09-04: whole-codebase simplification; carries 4a64d42f9b, micro-compaction -> agent/micro_compaction.py)",
           "NousResearch/hermes-agent#104920 (teknium1, MERGED 2026-09-07; carries 77086b1439, which added agent/context_compressor_summary.py)",
           "NousResearch/hermes-agent#80626, #80634, #81243 (andrexibiza text-utils, budget, message-marker slices; none adds the media module)",
           "NousResearch/hermes-agent#125186 and NousResearch/hermes-agent#127838 (auxiliary_client.py; deliberately not touched)",
           "a5bd246865 (compat layer removed; AGENTS.md: no re-export shims for internal moves)"]
close_after = []
demand = { score = 0, source = "AGENTS.md 'Refactor god-files into clean modules ... wanted work'; no user demand" }
maintainer_signal = "teknium1 has been splitting agent/context_compressor.py himself. (a) 4a64d42f9b 'refactor(agent): extract micro-compaction into agent/micro_compaction.py' (authored 2026-09-02, -580/+2 lines in the facade) is one of his 2026-09-02 commits that reached main on 2026-09-04 through the merge of his own #102117 ('whole-codebase simplification — -34% source LOC, every god file decomposed, zero behavior change'; opened 2026-09-03, 24 reviews: 21 COMMENTED, 1 APPROVED, 1 CHANGES_REQUESTED, 1 DISMISSED (re-read 2026-10-01 18:38Z, receipt recheck/r20261001-05; earlier rounds said '24 COMMENTED'), merged by teknium1). The same series rewrote the media helpers in place (806d2c3274 'dedupe image-part stripping', d3b93c45c9 'flatten historical-media strip') but did not move them. #102117 took the facade from 9,246 to 4,918 lines; it is 5,753 on 44a1ce9724 and on 34f8ec3b40 (same blob 6da13625b3). He closed sibling slice #80628 as stale on 2026-09-02 (comment 5507897412), the same day he wrote 4a64d42f9b. (b) 77086b1439 'refactor: isolate compression summary dispatch' (2026-09-07) added agent/context_compressor_summary.py, the same <stem>_<topic> naming this branch uses; it landed through his own salvage PR #104920 (rebase-merged by teknium1 2026-09-07). The round-2 verifier called both 'direct commits to main'. Re-checked in fix round 3: both arrived through PRs teknium1 opened and merged himself. 4a64d42f9b is reachable only through #102117's merge commit d3630f8532; 77086b1439 sits on main's first-parent line because #104920 was rebase-merged, and GitHub links it to #104920. teknium1's own comment uses the same 'direct-commit' wording for the 2026-09-02 splits. (c) His 2026-09-18 comment 5727991843 on #113887 (that wave issue is now CLOSED, 2026-09-19) says the 57 PRs it closes as superseded were superseded 'mostly [by] the 2026-09-02 direct-commit god-file splits'. It keeps 48 PRs open because the wave's superseded claim does not hold (for example, the code they move 'still sits inline on main'). It holds #80626/#80636/#80645 because their claimed replacement #81074 is still open. Reading: the maintainer splits this file himself in bulk and has already partly answered the pre-ask's question; he has not closed outside slices whose code is still inline, but none of andrexibiza's nine compressor slices has merged (#80628 closed, the other eight open). The support note now says this and asks first whether the media helpers are already on his list. Owner stance: kvnloo's #78647 comment 5610610089 is about the apps/desktop/electron/main.ts extract map, not the compressor; its heading says 'comment-first — no mega-PR' and its body says 'no competing mega-PR from me'. It is read here only as the owner's general stance on god-file splits."

[[donors]]
sha = "5aa1746a288f6401b6b2b28ae3607e99d9b72e74"
author = "Andrex Ibiza, MBA <84248988+andrexibiza@users.noreply.github.com>"
role = "original slice (module name + topic cut); not cherry-picked (conflicts, stale members, re-export seam)"
trailer = "Co-authored-by: Andrex Ibiza, MBA <84248988+andrexibiza@users.noreply.github.com>"

[[donors]]
sha = "c5e8be14b43bf75bcc2e4e8d95f2d4810a7e2779"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "salvage rebuild on current main (one commit, generated by regen/extract_media.py, message regen/COMMIT_MSG.txt). Replaces the unpushed d2bff3a59e: same patch-id 2c92e56f, corrected commit message"

[ownership]
searched_at = "2026-10-01T06:15-05:00 (fix round 1; first search 03:5x). Fix round 2: full open-PR file census 08:28-08:59 CDT, GitHub mergeable states 10:14 CDT. Fix round 3: open-PR listing 11:15-11:45 CDT, census refresh against 44a1ce9724, states and mergeable 11:47 CDT, andrexibiza compressor PRs re-searched (8 open + #80628 closed), maintainer commits on the facade since 2026-08-01"
queries = ["gh search prs context_compressor (open)", "context_compressor_media", "split/extract/decompose", "#80636 timeline", "#78645", "#78647", "#113887",
           "gh api pulls/<n>/files for every open andrexibiza context_compressor PR: 80626, 80634, 80636, 80644, 80645, 81074, 81181, 81243"]
open_external = [80636, 80645, 80644, 81074, 81181]
stack = "#80645, #80644, #81074 and #81181 (andrexibiza, all OPEN) stack on #80636 and carry its LB4 commit 5aa1746a28 unchanged: the same agent/context_compressor_media.py blob (ffd4d23465) and tests/agent/test_context_compressor_media_seam.py, with no later commit touching the module. A salvage of LB4 obsoletes that commit in all five PRs. Against this branch each one gains an add/add conflict on agent/context_compressor_media.py, on top of the agent/context_compressor.py conflict it already has with main. #80626, #80634 and #81243 do not add the module."
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
overlap_census_refresh = "fix round 3 (receipt recheck/r20261001-04), against main 44a1ce9724 (facade blob unchanged since bd394e2a4b): 411 of 33,677 open PRs touch agent/context_compressor.py (GraphQL listing 11:15-11:45 CDT; 226 of them are among the 706 open area/compression PRs). None of round 2's 404 has closed. 396 were reused unchanged (same head, or not updated since 08:28 CDT); 15 were re-analysed (8 updated since, 7 new; a 16th candidate, #122509, does not touch the facade). Result: 26 edit a moved statement (5 = #80636's stack; 16 = stale-base diffs of 619-3,000 files, 13 CONFLICTING with main at 11:47 CDT; 4 focused: #90910, #106867, #107589, #110103; plus new #130634, a 63-file mixed feature PR opened 2026-10-01 15:52Z). 5 add a facade use of a moved name the facade does not import (#82129, #85481, #90771, #104914, #130634). 10 add an old-path reference elsewhere (5 stack seam tests; #104914, #107589 and #130634 would fail to import; #110103 and #120403 still resolve). Outside the stack and the stale-base diffs, 8 PRs are flagged: 7 need a port or import fix (#85481, #90910, #104914, #106867, #107589, #110103, #130634), and #120403 keeps working. GitHub reports 4 of the 8 MERGEABLE at 11:47 CDT (#106867, #107589, #120403, #130634). Ownership unchanged."
overlap_census = "fix round 2 (receipt overlap/r20261001-03): 404 of 33,537 open PRs touch agent/context_compressor.py (listed 08:28-08:59 CDT; 223 of them are among the 694 open area/compression PRs). Statement-level census of the 403 analysable PRs against main bd394e2a4b: 25 edit a moved statement (5 = #80636's stack; 16 = stale-base diffs of 619-3,000 files, 13 already CONFLICTING with main; 4 focused: #90910, #106867, #107589, #110103). 4 add a facade use of a moved name the facade does not import (#82129, #85481, #90771, #104914). 9 add an old-path reference elsewhere (5 stack seam tests, #104914, #107589, #110103, #120403). Focused PRs outside the stack that need a port or import fix: 6 (#85481, #90910, #104914, #106867, #107589, #110103); a 7th flagged focused PR, #120403, keeps working (round 2 counted it among 7 'needing a fix', which overstated it). GitHub reported 3 of the 7 MERGEABLE with main at 10:14 CDT (#106867, #107589, #120403). Ownership unchanged. Superseded for counts by overlap_census_refresh."
verdict = "EXTERNAL (one author, five open PRs carrying LB4) -> salvage-support (support-note on #80636)"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "E14-parity/r20261001-02", path = "receipts/E14-test-parity-r20261001-02.json", sha256 = "65bb4bdc22309d486710d49311b6d9de84ffedd5d37c7516606d3f0ee47f3e3e" },
  { id = "static-gates/r20261001-02", path = "receipts/proof-static-gates-r20261001-02.json", sha256 = "ca47e4ff2a3c5eccca711f12ce4b6b472e59a303d7d2d84f17eb332109f89f7b" },
  { id = "redgreen/r20261001-02", path = "receipts/proof-redgreen-r20261001-02.json", sha256 = "a1db440c5ed9da6e65bce626b8ac7cbc3b57d780961a7ee784bea088c719ea75" },
  { id = "sabotage/r20261001-02", path = "receipts/proof-sabotage-perhunk-r20261001-02.json", sha256 = "98490ba8925424de79cf48c48e8aa0b6505f4b2d7a23a0428360394ef96db153" },
  { id = "golden/r20261001-02", path = "receipts/T1-golden-parity-r20261001-02.json", sha256 = "1e3b4823502965e6a8f3b422573d06e66d8da7074c67f57456a970a063d641c5" },
  { id = "regen/r20261001-02", path = "receipts/regen-reproducibility-r20261001-02.json", sha256 = "387f07b2425621f397bfc58737a1d353f2ebbff185508b8de74db284c9c7f9ae" },
  { id = "overlap/r20261001-03", path = "receipts/overlap-merge-check-r20261001-03.json", sha256 = "54ec900fb64184a2267a7c8636a3101d0f06c4b51dbb787bae2337fe7dbd63a4" },
  { id = "push-trigger/r20261001-03", path = "receipts/push-trigger-check-r20261001-03.json", sha256 = "330bf6216a6f65f5c21fbaf15cefca8a15695c6954c5b4e99e72222bd882bedd" },
  { id = "recheck/r20261001-04", path = "receipts/recheck-r20261001-04.json", sha256 = "da7efab26c5d62e90a712510cd886b38a0ba7b00bb1bb40ca1d512cd5355e25c" },
  { id = "E14-static/r20261001-02", path = "receipts/E14-static-metrics-r20261001-02.json", sha256 = "3180577e449c0acba392e4352d79331c2825cd58a8f2ea8dc310ca94c048a51b" },
  { id = "E14-bench/r20261001-02", path = "receipts/E14-bench-r20261001-02.json", sha256 = "ff28718165c653079cb3424034fa405cc895cb8a6c3f191f6653eb816f791dca" },
  { id = "E14-lookup/r20261001-02", path = "receipts/E14-lookup-sim-r20261001-02.json", sha256 = "2fb14208a6286ef5fc0c2ed37664a9f51d88552a0f1955d8169feabaf0408aa2" },
  { id = "F14/r20261001-01", path = "receipts/F14-r20261001-01.json", sha256 = "f34da3e5836992579bc37958b309d5e8b18dee63c00dec696969868ef6de271f" },
  { id = "recheck/r20261001-05", path = "receipts/recheck-r20261001-05.json", sha256 = "2fb6470d0be396ae722ac32e7fb4d87914ae3146cf85ac6d275a4253dde37182" },
]
superseded = [               # overlap/r20261001-02: superseded in fix round 2 by overlap/r20261001-03. The rest: first build (d2bff3a59e on 572e4f4fad); paths scrubbed in fix round 1. Fix round 3 replaced env.host with "<local-host>" in all 21 receipts (active and superseded); every hash here and above is of the scrubbed file
  { id = "overlap/r20261001-02", path = "receipts/overlap-merge-check-r20261001-02.json", sha256 = "5b1cbb5152d1375e620f42ff398830c0ed24cf486177e75f94af495c217ef2e2" },
  { id = "E14-parity/r20261001-01", path = "receipts/E14-test-parity-r20261001-01.json", sha256 = "790306c5beb30d73a5c1940d848727d10b27119af2d56b98b862bd36f23f3ac0" },
  { id = "static-gates/r20261001-01", path = "receipts/proof-static-gates-r20261001-01.json", sha256 = "a664238c0611345ee95e01456cc6a68065419e25cefa20009e9b78c6d087f3c7" },
  { id = "redgreen/r20261001-01", path = "receipts/proof-redgreen-r20261001-01.json", sha256 = "99aab731bafb75316a997ecfd49e288ed508ab516f0ef956332e347adaeae6b0" },
  { id = "golden/r20261001-01", path = "receipts/T1-golden-parity-r20261001-01.json", sha256 = "504d8dceb78abf77639c0fd39e14bd2ab251c451c15bf75fc6ccf79d884f04f3" },
  { id = "regen/r20261001-01", path = "receipts/regen-reproducibility-r20261001-01.json", sha256 = "5293731661ab2d3669d538682a05eeb172228a4d3b90b1c58b83c6d2192e8786" },
  { id = "overlap/r20261001-01", path = "receipts/overlap-merge-check-r20261001-01.json", sha256 = "d3434c9c8f75531fbba6bb2a2ae3af064ec4ff2b04f57278b4bed2e1a548c597" },
  { id = "E14-static/r20261001-01", path = "receipts/E14-static-metrics-r20261001-01.json", sha256 = "27a165a1a572d74d6c5f092395a20b55110af30b35c518b978b0b1eab8a9df25" },
  { id = "E14-bench/r20261001-01", path = "receipts/E14-bench-r20261001-01.json", sha256 = "4729134e3eb392e419f27cf6760e69dd2043bfd03728a66685fab2d878edd881" },
  { id = "E14-lookup/r20261001-01", path = "receipts/E14-lookup-sim-r20261001-01.json", sha256 = "70d5e63209ed3f1cf05fa6af38ee22d80167a96dbe7caa617283488c91c19f60" },
]
red = { test = "head's 5 changed test files on base", main = "aea969677c", marker = "ModuleNotFoundError: No module named 'agent.context_compressor_media'", receipt = "redgreen/r20261001-02" }
green = { reps = "3/3 (57 passed each)", receipt = "redgreen/r20261001-02" }
negative_control = { mutation = "per-hunk: each of the 16 -U0 hunks outside the new file reversed alone, plus all 3 facade deletion hunks together; the facade sibling import split per name (6); the new file sabotaged per moved statement (16); one re-export control", result = "30 of 40 rows re-RED under tests (narrow set, then the 365-file wide set for behaviour-changing rows that stayed green); 8 more are caught only by a verify_media gate; 2 are unpinned", unpinned = ["hunk:agent/context_compressor.py#1 (re-adding the unused outbound_image_retire_count import; behaviour-neutral; ruff F401 would flag it)", "facade-import:_rewritten (its only facade call site, _demote_stale_tail_tools, is untested on main and head; ruff F821 would flag it)"], receipt = "sabotage/r20261001-02" }
adjacent = { identical = true, receipt = "E14-parity/r20261001-02", pre_existing = [
  "tests/agent/lsp/test_workspace.py",
  "tests/agent/test_relay_atof_cwd.py",
  "tests/agent/test_relay_runtime_plugins.py",
  "tests/agent/test_relay_tools.py",
  "tests/agent/test_shell_hooks_tree_kill.py (300 s timeout in both concurrent full runs; passes 6/6 alone on both trees)",
  "tests/tools/test_browser_use_harness.py",
  "tests/tools/test_fal_sdk.py (collection error)",
  "tests/tools/test_local_env_blocklist.py",
  "tests/tools/test_microsoft_graph_auth.py",
  "tests/tools/test_modal_sandbox_fixes.py",
  "tests/tools/test_plugin_guard.py (7 errors)",
  "tests/tools/test_tts_deepinfra.py",
  "tests/tools/test_tts_mistral.py",
  "tests/tools/test_web_keyless_fallback.py",
] }
guards = { F14 = "EQUAL", receipt = "F14/r20261001-01", arm = "639aa4c211e7437b6c0d6e3473fd1bfc9c18c0dc (c5e8be14b4 cherry-picked clean onto main 34f8ec3b40; same patch-id 2c92e56f; tree 7f7e21c2cc = merge-tree of main and the branch)", set_sha256 = "aba79fe8f09dabc62950aacd0a53c2fdc30bc58746f405f9aa050bf474d739b9", note = "2 runs; each equals the main baseline on all 40 verdict ids (verdict, marker, fingerprint; 36 PASS, 4 FAIL shared with main); flaky list empty" }
quantitative = []                  # no value claim in the body
cache_read_ratio = { status = "N_A", note = "no wire change: golden parity identical over 63,998 calls" }
route_scope = "local-compressor and send path; native compaction untouched"
not_tested = ["hermes CLI end to end (runtime_bench needs OD-2)", "Windows/macOS", "real transcripts (golden corpus is synthetic)", "independent blind read", "flakiness beyond GREEN 3/3"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "", commit = "" }

[gates]
P1 = "PASS"       # need: facade 5,753 lines on aea969677c, 44a1ce9724 and 34f8ec3b40 (same blob 6da13625b3) vs the ~2,000-line rule; recheck at promotion (24 h)
P2 = "PENDING"    # external owner #80636 (+ 4 stacked PRs carrying LB4) -> route adjusted; pre-ask on #80636 not yet posted (owner action)
P3 = "PASS"       # one invariant, pure move, no env/config, no hook, no shim, sibling 243 lines
P4 = "PASS"       # sabotage shows compress(), iteration-summary and per-turn send paths run the sibling
P5 = "PENDING"    # RED, GREEN 3/3, per-hunk sabotage with unpinned rows listed, ADJACENT identical, F14 EQUAL (F14/r20261001-01) are recorded; missing: flaky = false (not measured beyond GREEN 3/3, no receipt records it), so not PASS
P6 = "N_A"        # no value claim; navigability numbers are MODELED and not relied on
P7 = "PASS"       # one commit on main aea969677c, author ok, merge-tree clean on 34f8ec3b40 (38 commits newer, no invalidate_on change, regenerated tree identical; see [merge_check]), 0 of 52 workflows push-match staged/<id>; recheck at promotion
P8 = "PENDING"    # receipts local + sha256; not frozen to z0evals
P9 = "PASS"       # template body, NOT_TESTED, AI disclosed for code and text in both body.md and PR_BODY.md, no @mentions, no factory jargon, privacy scan clean (host names scrubbed in fix round 3; re-scanned in polish round 5, stale regen/__pycache__ moved out); self-checked only
P10 = "PENDING"   # blind exact-head verifier
P11 = "RECORDED"  # AGENTS.md wanted work; maintainer HOLD on #80636; maintainer splits this file himself (4a64d42f9b via #102117, 77086b1439 via #104920), see maintainer_signal
P12 = "PENDING"   # owner queue / staging cap

[verification]
verifier = ""
provenance = "independent"
exact_head = "c5e8be14b43bf75bcc2e4e8d95f2d4810a7e2779"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
checked_at = "2026-10-01T13:32-05:00 (polish round 5; main tip committed 2026-10-01T17:29:37Z, the pinned upstream main for this round)"
clean = true
note = "38 commits past base aea969677c (base is an ancestor), none touching invalidate_on (git diff over agent/context_compressor*.py, turn_request_assembly, chat_completion_helpers, image_eviction_policy: 0 lines). All 10 touched files plus test_compressor_zero_user_guard.py, native_compaction.py, turn_context.py, conversation_compression.py and AGENTS.md have the base's blob ids. merge-tree clean (tree 7f7e21c2cc, also the F14 arm's tree). extract_media.py on a fresh 34f8ec3b40 worktree, run in the xf bwrap sandbox, regenerates exactly that tree (10 files, +264/-243), and verify_media.py gives 6/6 PASS on it with output identical to round 4's (receipt recheck/r20261001-05)"
previous = "44a1ce9724 at 11:12 CDT (fix round 3): merge-tree clean (tree 7e2368a3b9), regenerated tree identical, verify_media 6/6 (recheck/r20261001-04). a3b56cac95 at 07:46 CDT: merge-tree clean (tree 6a8a815796), regenerated tree identical (regen/r20261001-02)"
recheck = "git -C h.git merge-tree --write-tree main staging/compressor-media-extraction"
api_recheck = "fix round 2, 2026-10-01T08:30-05:00, GitHub API only (h.git could not fetch: /tmp full). Main bd394e2a4bdf55fa2f14b0f6963d343049787f90 is 15 commits past base aea969677c (compare: ahead 15, behind 0). All 10 files the commit touches, plus tests/agent/test_compressor_zero_user_guard.py and agent/native_compaction.py, have the same blob ids as on the base, and agent/context_compressor_media.py does not exist there. So the commit still applies to that main without a three-way conflict, and the facade is still 5,753 lines. This is not a merge-tree run."

[push]
fork_branch = "staged/compressor-media-extraction"
collision_check = "git ls-remote kvnloo/hermes-agent 2026-10-01T06:15-05:00, re-checked 08:43-05:00 in fix round 2: no refs/heads/staged or staged/*; refs/heads/staging 28790e597c is the legacy branch (OD-0, resolved by the staged/ rename). Fix round 3, 11:51-05:00: staged/cu-capture-mode-projection, staged/cu-repeat-input-dedup, staged/observer-hooks-doc-drift, staged/postmortem-logcalls-zero-hit and staged/prefix-parity-journeys exist; staged/compressor-media-extraction does not, so no collision"
no_follow_tags = true
workflow_push_matches = 0          # 52 workflows parsed on the exact tree (receipt push-trigger/r20261001-03). 11 have a push trigger: branches main (8), wine2e/** (1), wine2e-install/** (1), and tags v* (live-providers.yml, 1). A branch push matches none; the tag trigger is why no_follow_tags is required. Fix round 3: .github/workflows has 0 diff lines from aea969677c to 44a1ce9724 (still 52 files). Polish round 5: 0 diff lines to 34f8ec3b40, still 52 files (recheck/r20261001-05)
pushed_at = ""

[body]
path = "body.md"
kind = "support-note"
salvage_pr_body = { path = "PR_BODY.md", kind = "pr-body", use = "only if the #80636 thread agrees to a salvage PR" }
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "self-checked (no lane/envelope/E##/F## in body.md or PR_BODY.md); polish round 5 re-checked both files: no P1-P12, OD-n, xf, receipt paths or fork-only refs; upstream items are cited as #N"
privacy_scan = "re-run in fix rounds 1, 2 and 3: no home paths, scratch paths, session ids or emails beyond noreply trailers in body.md, PR_BODY.md, STAGING.md, regen/ or receipts/ (round 2 scanned every text file; .gz logs unchanged since round 1). Fix round 3: every receipt's env.host carried the local host name; all 21 now say '<local-host>' (new hashes under [evidence]; the pre-scrub hashes are deliberately not published, because with the rest of each file known they would let anyone confirm a guessed host name). A host-name grep over every file here, .gz logs included, finds none. Polish round 5 re-scanned all 106 files here (.gz logs decompressed) for home, data-disk, scratch and workspace paths, GitHub/OpenAI/AWS/Slack tokens, bearer strings, private keys, emails other than noreply, the host name and bytecode: the only hit is the '<run>/home/.hermes' placeholder in the F14 receipt. The stale regen/__pycache__ (fix round 3) was moved to a private run directory, so no bytecode is left"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/compressor-media-extraction

**Title:** Split `agent/context_compressor.py` along `<stem>_<topic>`, starting with image/media handling.
**Promotion form:** selected `core-pr`. Effective form is **salvage-support**: a support note on NousResearch/hermes-agent#80636 (`body.md`), plus a salvage PR (`PR_BODY.md`) only if that thread agrees.
**Branch:** `staging/compressor-media-extraction` @ `c5e8be14b43bf75bcc2e4e8d95f2d4810a7e2779`. It is one commit on main `aea969677c` and exists only in the local scratch `h.git`. It goes to the fork as `staged/compressor-media-extraction`: the fork's legacy `refs/heads/staging` blocks every `staging/*` name, and this rename resolves OD-0. Nothing has been pushed.

## Invariant

Moving the image/media cluster out of `agent/context_compressor.py` changes no behaviour.

What the old-path half of the invariant means: no file in the tree refers to a moved name through `agent.context_compressor` (`old_path_zero` = 0). It does not mean the old path is closed. The facade imports the six moved names it still calls (`_is_image_part`, `_retire_stale_tool_result_images`, `_rewritten`, `_strip_historical_media`, `_strip_images_from_tool_msg`, `_summary_part_text`), so `from agent.context_compressor import _rewritten` still works, as do the other five. The remaining ten moved names are not importable from the old path. This is why the old-path test imports added by #110103 and #120403 (`_summary_part_text`, `_rewritten`) would keep working, while those added by #104914, #107589 and #130634 would not.

The real call paths now run the sibling's code:

- `ContextCompressor.compress()` → `_strip_historical_media`
- `_prune_old_tool_results` → `_retire_stale_tool_result_images`
- `chat_completion_helpers._iteration_summary_api_messages` → `evict_stale_outbound_tool_images`
- `conversation_loop` → `turn_request_assembly.assemble_api_request:155` → `evict_stale_outbound_tool_images`

## Premise re-check (2026-10-01)

- **Still needed.** The facade is 5,753 lines on `aea969677c`, the same count as on `572e4f4fad` and the critic's `e496ccc7d7`. It is still the same blob (`6da13625b3`) on `bd394e2a4b` (fix round 2), on `44a1ce9724` (fix round 3) and on `34f8ec3b40` (polish round 5). AGENTS.md calls god-file extraction wanted work and says to split at about 2,000 lines, in its own commit.
- **The maintainer splits this file himself (fix round 3).** This is the most direct evidence on the pre-ask's question.
  - On 2026-09-02, teknium1 wrote a series of refactor commits on `agent/context_compressor.py`. They reached main on 2026-09-04 through the merge of his own #102117 ("whole-codebase simplification — −34% source LOC, every god file decomposed, zero behavior change"). One of them, `4a64d42f9b`, moved about 580 lines into `agent/micro_compaction.py`. Two others reworked the media helpers in place without moving them (`806d2c3274` "dedupe image-part stripping", `d3b93c45c9` "flatten historical-media strip"). #102117 took the facade from 9,246 to 4,918 lines. It has grown back to 5,753.
  - He closed the sibling slice #80628 as stale on 2026-09-02, the same day he wrote `4a64d42f9b`.
  - `77086b1439` (2026-09-07, his own salvage PR #104920) added `agent/context_compressor_summary.py`. That is the same `<stem>_<topic>` naming this branch uses.
  - His #113887 comment 5727991843 (2026-09-18) says the PRs it closes as superseded were superseded "mostly [by] the 2026-09-02 direct-commit god-file splits". He kept open the PRs whose code still sits inline on main, and put #80636 on HOLD rather than closing it.
  - The round-2 verifier described `4a64d42f9b` and `77086b1439` as direct commits to main. Both actually came through PRs that teknium1 opened and merged himself. teknium1 uses the same "direct-commit" wording for the 2026-09-02 splits.
  - So the pre-ask's question (is an outside split wanted now?) is already partly answered: the maintainer does these splits himself, in bulk. He has not closed outside slices whose code is still inline, but none of andrexibiza's nine compressor slices has merged (#80628 closed, the other eight open). The support note now says this and asks first whether the media helpers are already on his list.
- **Already owned upstream.** NousResearch/hermes-agent#80636 (andrexibiza, OPEN, labels `type/refactor`, `area/compression`, `P3`) is this exact slice: "extract content/media strip helpers (LB4)" into `agent/context_compressor_media.py`. It belongs to andrexibiza's shard campaign: lock issue #78645 and epic #78647, both `needs-decision`.
  - teknium1's 2026-09-18 triage on #113887 (that issue is now CLOSED) keeps #80636 open on HOLD, because its claimed superseder #81074 is still open. The code it moves is still inline on main.
  - The sibling slice #80628 (LB2) was closed by teknium1 on 2026-09-02 as stale ("no longer applies cleanly ... seam tests fail on main").
- **Four more open PRs carry the same commit.** #80645 (LB5a), #80644 (LB7), #81074 (LB6) and #81181 (summary kernel, the stack tip, updated 2026-08-31) are all andrexibiza's, all OPEN, and all stack on #80636. Each contains the LB4 commit `5aa1746a28` unchanged, so each also adds `agent/context_compressor_media.py` (blob `ffd4d23465`) and `tests/agent/test_context_compressor_media_seam.py`. #81074 is the PR teknium1 names as #80636's superseder. A salvage of LB4 therefore obsoletes that commit in five open PRs, not one. Against this branch, each of the five gains an add/add conflict on the media module, on top of the `agent/context_compressor.py` conflict it already has with main. The pre-ask below says so.
- **The file is busy (fix round 2, refreshed in fix round 3).** At 11:15–11:45 CDT, 411 of 33,677 open PRs touched `agent/context_compressor.py` (404 of 33,537 at 08:28–08:59). Outside #80636's stack and the stale-base diffs, eight PRs are flagged:
  - Five change moved code, so the change would have to move to the new module: #90910, #106867, #107589, #110103, and #130634 (a 63-file mixed feature PR opened on 2026-10-01).
  - #85481 and #104914 (and #130634 again) add facade calls to moved helpers that the facade would no longer import. That would be a NameError after a textually clean merge.
  - #104914, #107589 and #130634 add old-path test imports that would fail.
  - #120403 only adds an old-path import of `_rewritten`. That still resolves, because the facade imports the name back. Only `old_path_zero` flags it.
  - So seven need a port or an import fix, and one keeps working. Round 2's "seven would need a follow-up" counted #120403 among them and missed #130634, which did not exist yet. GitHub reports #106867, #107589, #120403 and #130634 MERGEABLE (11:47 CDT).
  - Sixteen stale-base diffs of 619–3,000 files also touch moved statements, and 13 of those conflict with main.
  - This does not change who owns the slice. It does make the pre-ask's question concrete, so the pre-ask quotes the counts. Receipts: overlap/r20261001-03 (full census), recheck/r20261001-04 (refresh).
- **#80636 cannot be cherry-picked.**
  - It is 25,973 commits behind main (`aea969677c`) and stacks four commits (text utils, skill prune, budget, media).
  - `git merge-tree` conflicts in `agent/context_compressor.py`, both for the whole PR and for the media commit alone.
  - Its media module holds August versions of the functions. For example, `_strip_historical_media` has no `spared=`, and the module lacks the tool-image retirement and outbound eviction code.
  - It keeps an `is`-identical re-export seam, which AGENTS.md (after a5bd246865) rules out.
- **Route.** Do not open a parallel PR. Offer the rebuilt, shim-free slice on #80636 and credit andrexibiza as co-author. This matches PROTOCOL's EXTERNAL-OWNED rule. It also fits the owner's general stance on god-file splits: his #78647 comment 5610610089 is about the desktop `main.ts` extract map, not the compressor, but says "comment-first — no mega-PR" and "no competing mega-PR from me". The route stays salvage-support: the stack has one author and one maintainer decision point (#80636 / #81074), so it does not change who owns the slice. The maintainer's own splits (above) narrow the ask but do not change the route. Before its question, the note now says "If the media helpers are already planned that way, please ignore this.", so the owner does not ask something the maintainer has partly answered. A parallel PR would be even less appropriate now.
- `auxiliary_client.py` stays out of scope (#125186, #127838), as the selection said.

## Member branches

| Ref | SHA | Role | Rebase status |
|---|---|---|---|
| `staging/compressor-media-extraction` (local; fork name `staged/compressor-media-extraction`) | `c5e8be14b43bf75bcc2e4e8d95f2d4810a7e2779` | The salvage rebuild: one commit made by `regen/extract_media.py`, message from `regen/COMMIT_MSG.txt` | On main `aea969677c` (0 behind at build). Regenerates to an identical tree (`0cb7ba9d0c`), which is also exactly the tree `merge-tree` gives for the superseded `d2bff3a59e` on that main. merge-tree is clean on main `a3b56cac95` (12 commits newer, none touching `invalidate_on`), and regenerating on it gives exactly the merged tree (`6a8a815796`). The same holds on `44a1ce9724` (`7e2368a3b9`) and on `34f8ec3b40` (38 commits newer, `7f7e21c2cc`, polish round 5). |
| superseded first build | `d2bff3a59edd1a9be5a90f5d84bbded1fbe04e8b` | Same patch (patch-id `2c92e56f`) on `572e4f4fad`; its message said "five test modules" (four is right). Never pushed. Kept at `refs/xf/superseded/compressor-media-extraction-v1` in the scratch repo | Replaced, not deleted. Deviation from FACTORY §10: the rebuild moved the local branch name instead of creating `staging/compressor-media-extraction-v2` (see `branch_version_deviation`). `phase3_results.json` still records `d2bff3a59e` as the build SHA. |
| NousResearch/hermes-agent#80636 head (`refs/xf/pr/80636`) | `5aa1746a288f6401b6b2b28ae3607e99d9b72e74` | Original slice, credited (`Co-authored-by`) and not reused as code | 25,973 behind `aea969677c`; CONFLICT in `agent/context_compressor.py` |
| #80645 / #80644 / #81074 / #81181 heads (`refs/xf/pr/<n>`) | `2ace2a70c0` / `c871197b77` / `4effdf3396` / `e40f2db140` | Stacked descendants carrying `5aa1746a28` unchanged | 25,973 behind `aea969677c`; CONFLICT in `agent/context_compressor.py` (1 / 3 / 5 / 9 hunks vs main) |
| fork `claude/ledger` | not written | Intended home of `regen/` and `receipts/` (owner or ledger worker) | n/a |

The selection listed no member branches. No fork branch carries this work.

## First slice: status

**Committed** (local). `c5e8be14b4` "refactor(compression): move image/media helpers into agent/context_compressor_media.py":

- Author: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>.
- Trailers: `Co-authored-by: Andrex Ibiza, MBA <84248988+andrexibiza@users.noreply.github.com>` and Claude.
- Size: 10 files, +264/−243.
- The message is kept in `regen/COMMIT_MSG.txt`. It says four test modules import from the sibling and two docstrings are repointed, which matches the diff. The first build's message said "five test modules"; `tests/agent/test_image_eviction_policy.py` only has a docstring change.

What moved. 16 top-level statements, byte-for-byte, with their comments:

- `_MAX_KEEP_TOOL_IMAGES`, `_replace_image_parts`, `_tool_result_parts`, `_tool_content_has_images`, `_strip_images_from_tool_msg`, `_rewritten`
- `_retire_stale_tool_result_images`, `_image_payload`, `evict_stale_outbound_tool_images`
- `_IMAGE_PART_TYPES`, `_is_image_part`, `_content_has_images`, `_strip_images_from_content`, `_strip_historical_media`, `_summary_part_text`, `_image_part_label`

Wiring:

- The facade imports only the six names it calls: `_is_image_part`, `_retire_stale_tool_result_images`, `_rewritten`, `_strip_historical_media`, `_strip_images_from_tool_msg`, `_summary_part_text`.
- The facade drops `outbound_image_retire_count`, which only moved code used.
- The two send-path callers and four test modules import from the sibling.
- Two docstrings are repointed (`agent/image_eviction_policy.py`, `tests/agent/test_image_eviction_policy.py`).
- Facade: 5,753 → 5,531 lines. Sibling: 243 lines.

Deviation from the selection's first_slice, on purpose:

- The five content-text helpers (`_part_text`, `_with_part_text`, `_content_text_for_contains`, `_is_text_only_content`, `_append_text_to_content`; lines 1382-1423) stay in the facade. They are text utilities, not media. `conversation_compression.py` imports `_append_text_to_content` from the facade, and andrexibiza's #80626 covers text utils separately.
- `_MAX_KEEP_TOOL_IMAGES` (lines 1170-1176) moves. It is the default argument of `_retire_stale_tool_result_images`, and the sibling must not import the facade.

The regeneration recipe is kept outside the commit, in `regen/`:

- `extract_media.py`: AST-based, stdlib only. It refuses rather than guesses when the tree drifts.
- `COMMIT_MSG.txt`: the commit message, so a regeneration does not copy it from an old commit.
- `verify_media.py`: the 6 static gates.
- `golden_parity.py`: differential outputs. `golden_coverage.py`: replays the same corpus and writes `golden-coverage.json` (how often each rewrite path fired). It reproduces the first build's `receipts/raw/golden-coverage.json` byte for byte.
- `sabotage_perhunk.py`: per-hunk sabotage (below).
- `parity_compare.py`: test-log comparison.
- `moved_symbol_lookup.py`: targeted lookup_sim.

## Experiments run ($0 only)

All rows are on base `aea969677c` and head `c5e8be14b4` (receipt round `r20261001-02`), except where the row says otherwise.

| Experiment | Tier | Receipt | Result | Label |
|---|---|---|---|---|
| E14 test parity: `tests/agent/` + `tests/tools/`, base vs head | T1 | `receipts/E14-test-parity-r20261001-02.json` | **Identical.** 1,683 files, 20,111 passed, 16 failed, 131 skipped on both trees. Same 14 failing files and the same 16 failures + 8 errors (23 distinct parsed ids). 13 of those files fail the same way on `572e4f4fad` and are unrelated to compression (relay plugins, LSP, TTS/web keyless, plugin_guard, fal_sdk collection). The 14th, `test_shell_hooks_tree_kill.py`, hit the 300 s limit in both runs because the two runs were concurrent; alone it passes 6/6 on both trees. Per-file counts identical. | OBSERVED |
| Static gates (`verify_media.py`) + controls | T0 | `receipts/proof-static-gates-r20261001-02.json` | 6/6 PASS on head: verbatim 16/16, facade_rest 194 statements identical, no_shim, old_path_zero (0 references), native_coupling, imports. A re-export added → no_shim FAIL. | OBSERVED |
| RED / GREEN / call-path sabotage | T1 | `receipts/proof-redgreen-r20261001-02.json` | RED: 4/5 changed test files fail on base with `ModuleNotFoundError: agent.context_compressor_media`; the other two of the six files pass (18). GREEN 57/57 ×3. `_strip_historical_media` raising → 26 failures, 8 of them in `compress()` test classes. `evict_stale_outbound_tool_images` raising → 25 failures: 12 outbound-vision, 5 iteration-summary, 8 conversation-loop through `turn_request_assembly.py:155`. | OBSERVED |
| Per-hunk sabotage (`regen/sabotage_perhunk.py`) | T1 | `receipts/proof-sabotage-perhunk-r20261001-02.json` | 40 rows: 16 single-hunk reverts, the 3 facade deletion hunks together, 6 per-name drops from the facade import, 16 per-statement sabotages of the new file, 1 re-export control. 30 re-RED under tests (the 11-file narrow set; the 365-file wide set for behaviour-changing rows that stayed green, with pre-existing failures excluded). 8 more are caught only by a `verify_media` gate (old-path docstring/import reverts, re-added facade copies, the re-export). **Unpinned (2):** re-adding the unused `outbound_image_retire_count` import (behaviour-neutral), and dropping `_rewritten` from the facade import (its one facade call site, `_demote_stale_tail_tools`, has no test on main either). `ruff check --select F` flags both (F401, F821); the repo's ruff selection does not. | OBSERVED |
| Golden output parity (14 functions, seeded synthetic corpus, loopback guard) | T1 | `receipts/T1-golden-parity-r20261001-02.json` | 63,998 calls with identical digests (`983b2307…` on both trees at n=400). Coverage from `regen/golden_coverage.py`, identical on both trees: 367/400 conversations carry images; `_strip_historical_media` changed 258, retirement rewrote in 162, send-path eviction fired in 59 (1,069 messages rewritten). The negative control flips exactly 3 digests. | OBSERVED |
| Regeneration reproducibility | T0 | `receipts/regen-reproducibility-r20261001-02.json` | Regenerated tree == commit tree (`0cb7ba9d0c`) == merge-tree of the first build on `aea969677c`; patch-id `2c92e56f` for both commits. Rehearsal on `a3b56cac95`: regenerated tree == merged tree (`6a8a815796`). `--color-moved` marks 230/243 deleted and 235/264 added lines as moved. ruff (repo config) and `check-windows-footguns.py` clean on the 10 touched files. | OBSERVED |
| Overlap and conflict surface | T0 | `receipts/overlap-merge-check-r20261001-03.json` (supersedes `-02`) | **404 of 33,537 open PRs touch the facade.** The listing ran 08:28–08:59 CDT through GraphQL, with REST for file lists that were truncated or null. 223 of those PRs carry `area/compression`; the round-1 re-verifier counted 221 of 692 in that label. **Merge-tree sample** (from `-02`, main `aea969677c`), 3 PRs outside the stack: #129147 clean on both trees; #118847 1→1 and #119347 3→3 conflict hunks, so the branch adds none. #80636 and its four stacked PRs already conflict with main (1, 1, 3, 5, 9 hunks) and also get the add/add conflict on the media module. **Statement-level census** of the 403 analysable PRs against main `bd394e2a4b`. Each PR's own pre-image comes from reverse-applying its patch, or from the merge-base blob for 14 PRs. 25 PRs edit a moved statement: 5 are the stack; 16 are stale-base diffs of 619–3,000 files (13 already CONFLICTING); 4 are focused (#90910, #106867, #107589, #110103). 4 PRs add a facade use of a moved name the facade does not import (#82129, #85481, #90771, #104914). 9 PRs add an old-path reference elsewhere: #104914 and #107589 would fail to import, while #110103 and #120403 still resolve and only `old_path_zero` flags them. That leaves 7 flagged focused PRs outside the stack. Six need a port or an import fix; #120403 keeps working. Fix round 3 corrects round 2's "7 need a fix", and the refresh adds #130634. GitHub reports #106867, #107589 and #120403 MERGEABLE (10:14 CDT). Not analysable: #107532, whose head facade is a 90 KB single line of mojibake, and #42793, whose REST file list is empty. The other-file scan was skipped on 17 mega-diffs. | OBSERVED |
| Fix-round-3 re-measure on main `44a1ce9724` | T0 | `receipts/recheck-r20261001-04.json` | **Merge and regeneration:** `44a1ce9724` is 29 commits past the base, with 0 diff lines in the `invalidate_on` paths. All 10 touched files keep the base's blob ids. merge-tree is clean (tree `7e2368a3b9`), `extract_media.py` on a fresh worktree gives exactly that tree, and `verify_media.py` gives 6/6 PASS on it. **States:** every cited PR and issue was re-read at 11:47 CDT. All are as stated; #113887 is CLOSED (2026-09-19). Every flagged PR has the same head as in round 2. **Maintainer splits:** see the premise and `maintainer_signal`. **Overlap refresh** (`regen/overlap_delta.py`): 411 of 33,677 open PRs touch the facade. 396 rows were reused, 15 re-analysed. One new flagged PR, #130634. | OBSERVED |
| E14 `static_metrics.py` | T0 | `receipts/E14-static-metrics-r20261001-02.json` | Files +1, lines +21. The facade moves from 6th to 7th largest file. files_gt_2000 50→50 and files_gt_5000 7→7 (the facade is still 5,531). Largest import cycle 1,131→1,132 (via `agent.turn_context`). cc/mi unchanged. | OBSERVED (static) |
| E14 `bench.py` (naive locate-X) | T0 | `receipts/E14-bench-r20261001-02.json` | 13 test-import tasks leave a >2k-line file (5,634 → 5,621). Whole-file read cost −1,996,801 tokens over 24,707 tasks (−0.42%). | MODELED |
| E14 `lookup_sim.py` stock (4,000 sampled, seed 7) + targeted census | T0 | `receipts/E14-lookup-sim-r20261001-02.json` | Stock: no moved name drawn this time; +10 tokens in total (one facade function, `_collect_protected_skill_names`). Targeted, 14 moved functions: 33,428 → 23,195 simulated tokens (−30.6%), same 28 calls. The facade's remaining defs read +0.1% here but −2.1% in the first build for the same file, so that census is noise. | MODELED |
| F14 standing guard set (Wave 0; 19 probes, 40 verdict ids, set `aba79fe8f09d`), main baseline vs this commit cherry-picked onto main `34f8ec3b40`. Not on `aea969677c`/`c5e8be14b4`: the arm is `639aa4c211` (clean cherry-pick, same patch-id `2c92e56f`, tree `7f7e21c2cc` = merge-tree of that main and the branch) | T1 | `receipts/F14-r20261001-01.json` | **EQUAL.** Two serial runs in the xf bwrap sandbox, one cell per probe with its own HOME/HERMES_HOME, loopback only. Each run equals the main baseline on all 40 ids (verdict, marker and fingerprint): 36 PASS, 4 FAIL. The 4 FAILs (`cache_estimator_probe`, `notice_delivery_probe`, `context_cap_probe`, readtool `lying_extension`) are main's own, with identical markers. r1 vs r2 is also EQUAL; the set's flaky list is empty. Runner `2323a591…`, sandbox `c9586195…`, readtool helper `0df21aee…`, the same as for the baseline. 12 of the 19 probes reference the compressor or send path (grep); runtime coverage of the moved statements under F14 was not measured. | OBSERVED |
| Polish-round-5 re-measure on main `34f8ec3b40` | T0 | `receipts/recheck-r20261001-05.json` | **Merge and regeneration:** `34f8ec3b40` is 38 commits past the base, with 0 diff lines in the `invalidate_on` paths; all 10 touched files and 5 coupled files keep the base's blob ids. merge-tree is clean (tree `7f7e21c2cc`). `extract_media.py` on a fresh worktree, in the xf bwrap sandbox, gives exactly that tree, and `verify_media.py` gives 6/6 PASS with output identical to round 4's. **States:** all 29 cited PRs and issues are as stated (18:38Z). All 13 stack and flagged PR heads are unchanged since round 4, so the census rows carry over. GitHub's mergeable flag read UNKNOWN (recomputing after the main move) and was not re-read. #102117 had 24 reviews (21 COMMENTED, 1 APPROVED, 1 CHANGES_REQUESTED, 1 DISMISSED). **Topic cut:** #80636's media module (blob `ffd4d23465`) holds 9 names; this branch keeps `_append_text_to_content` in the facade, and `_strip_image_parts_from_parts` and `_truncate_tool_call_args_json` no longer exist on main. The overlap census itself was not re-run. | OBSERVED |

Environment:

- Tests ran through `scripts/run_tests.sh -j 2` with HOME and HERMES_HOME at scratch test homes and `HERMES_PYTHON` set to the installed venv's interpreter (Python 3.11.14, pytest 9.1.1).
- The navigability scripts ran in a separate uv venv (py 3.14.7, tiktoken 0.14.0, radon 6.0.1). The `o200k_base` cache file sha256 is `446a9538…1a2d`. Downloading it was the only network step, and it happened during the first build's venv build.
- No bwrap was used. `runtime_bench.py` was not run.
- Receipts carry no absolute local paths: worktrees appear as `$W/<tree>`, the scratch dir as `$S`, the interpreter as `$HERMES_PYTHON`. The first build's receipts and raw logs were scrubbed the same way; each raw entry keeps `source_sha256` of the pre-scrub file.

## Experiments queued

No T2 (local GPU) or T3 (paid) experiment applies. A byte-verbatim move has no model-facing behaviour, and golden parity already shows identical outputs. Queued $0 and owner-gated items:

1. **Promotion-time regeneration (T0/T1, $0, D8).** Run on the exact main of the day. `$S` is the scratch dir holding `h.git`, `$R` this directory's `regen/`, `$W` a fresh worktree root on `/mnt` (not tmpfs):
   ```
   git -C $S/h.git -c credential.helper= fetch -q --filter=blob:none https://github.com/NousResearch/hermes-agent.git "+refs/heads/main:refs/heads/main"
   git -C $S/h.git worktree add --detach $W/base main && git -C $S/h.git worktree add --detach $W/head main
   python3 $R/extract_media.py $W/head            # exit 2 = recipe mismatch: re-read the drift, do not force
   python3 $R/verify_media.py $W/base $W/head --python $HERMES_PYTHON --json verify.json
   (cd $W/head && git add -A agent tests && git -c user.name="Kevin Rajan" -c user.email="7121943+kvnloo@users.noreply.github.com" commit -F $R/COMMIT_MSG.txt)
   for t in base head; do mkdir -p $S/testhome-cme-$t/.hermes; (cd $W/$t && HOME=$S/testhome-cme-$t HERMES_HOME=$S/testhome-cme-$t/.hermes HERMES_PYTHON=$HERMES_PYTHON bash scripts/run_tests.sh -j 2 tests/agent/ tests/tools/ -q -rfE > $t.log 2>&1); done
   python3 $R/parity_compare.py base.log head.log --json parity.json
   for t in base head; do T=$(mktemp -d -p $S); mkdir -p $T/.hermes; (cd $W/$t && env -i PATH=/usr/bin:/bin HOME=$T HERMES_HOME=$T/.hermes PYTHONPATH=$W/$t PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 $HERMES_PYTHON $R/golden_parity.py --n 400 --out golden-$t.json && env -i PATH=/usr/bin:/bin HOME=$T HERMES_HOME=$T/.hermes PYTHONPATH=$W/$t PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 $HERMES_PYTHON $R/golden_coverage.py --n 400 --out golden-coverage-$t.json); done
   git -C $S/h.git worktree add --detach $W/sab "$(git -C $W/head rev-parse HEAD)" && python3 $R/sabotage_perhunk.py $W/sab $W/base --python $HERMES_PYTHON --home $S/testhome-cme-sab --json sabotage.json --wide-files-from wide.txt --known-failures known.txt   # wide.txt: test files naming context_compressor|turn_request_assembly|chat_completion_helpers|image_eviction|conversation_loop; known.txt: failing ids of head.log
   F=$(git -C $W/head diff --name-only HEAD~1 HEAD); for t in base head; do (cd $W/$t && ruff check --no-cache --select F --statistics $F); done   # must match; covers the 2 rows no test pins (F401, F821)
   python3 $R/overlap_scan.py ASC 400 open.jsonl && OVERLAP_MAIN=$(git -C $S/h.git rev-parse main) python3 $R/overlap_census.py $R census.json open.jsonl && python3 $R/overlap_summary.py census.json   # GitHub API reads only (several thousand REST calls on a shared token); re-counts open PRs touching the facade and which of them edit moved code
   ```
   Do not `cat-file`, `merge-tree` or fetch every overlapping PR head in the shared blobless scratch `h.git`. Each missing PR head sets off a promisor fetch. On 2026-10-01, about 150 of them added about 8.4 GiB of packs and filled the 12 GB `/tmp` tmpfs (see "Environment alert" below). Merge-test only the PRs the census flags, and do it in a repo on `/mnt`.
   Update `regen/COMMIT_MSG.txt` first if a count in it changed (facade line count, number of importers).
2. **runtime_bench (local CPU, $0; needs OD-2 because it runs the `hermes` CLI and pytest collection).** Run inside bwrap with a disposable venv from `python -m pm.build_env --source <tree> --out <fresh> --group dev --group test`:
   `NAV_OUT=out $VENV/bin/python evals/codebase_navigability/runtime_bench.py $W/base base 9` and then the same command for `$W/head head 9`. Expect import time to rise slightly; the README predicts it.
3. **F14 standing guard set (T1, $0).** Done on main `34f8ec3b40`: EQUAL (receipt F14/r20261001-01). Re-run at promotion if the day's main changes any `invalidate_on` path: `agent/context_compressor*.py`, `agent/turn_request_assembly.py`, `agent/chat_completion_helpers.py` and `agent/image_eviction_policy.py`.
4. **Blind exact-head read (P10).** A different worker gets only `c5e8be14b4`, the repo and the oracle (the invariant above plus `verify_media.py`).

## Acceptance gates (from the selection)

| Gate | Status | Evidence |
|---|---|---|
| Identical pass/fail sets on `tests/agent/` and `tests/tools/` before and after. Failures that also occur on main are recorded, not chased. | met | E14-parity/r20261001-02 |
| Zero references to moved symbols through the old path, including tests, plugins, website, getattr and monkeypatch strings (D2) | met | `old_path_zero` 0 references. In the per-hunk run, reverting any of the 3 production import/docstring hunks or any of the 8 test hunks that hold an import or docstring flips it. Five of those reverts pass pytest (3 old-path imports, 2 docstrings), so only this gate catches them. |
| No shim module | met | `no_shim`: the facade imports 6 names, all read. No `__all__`. The sibling never imports the facade. The N2a control (a re-export added) flips it. |
| The native_compaction → is_compaction_summary_message coupling is untouched | met | `agent/native_compaction.py` is byte-identical. The definition stays in the facade. The import probe passes. |
| Regenerated and merge-checked on the exact main at promotion time (D8) | pending (recipe ready) | Regenerated on `aea969677c` (fix round 1): the tree equals the commit tree and the merge-tree result for the first build. Rehearsed on `a3b56cac95` (round 2), on `44a1ce9724` (fix round 3) and on `34f8ec3b40` (polish round 5): each time the regenerated tree equals the merged tree (`6a8a815796`, `7e2368a3b9`, `7f7e21c2cc`), and on `44a1ce9724` and `34f8ec3b40` `verify_media.py` gives 6/6 PASS. Must be redone on the day's main. |
| One pre-ask comment on whether outside splits of compression files are wanted now | pending (owner action) | `body.md`; post on #80636. Fix round 3: the note now says the maintainer has already split micro-compaction and summary dispatch out himself, and asks first whether the media helpers are already on his list. |

FACTORY P1-P12 are in the front matter. P5 is PENDING, not PASS. F14 guards are now EQUAL (F14/r20261001-01). The per-hunk sabotage it also requires is done, and the two rows no test pins are listed above and in `[evidence].negative_control`. What P5 still lacks is a recorded `flaky = false`: flakiness was not measured beyond GREEN 3/3, and no receipt records it. The class reachable today is **STAGED**. PROMOTION_READY needs these first:

- the #80636 thread answers;
- a recorded `flaky = false` (P5);
- receipts frozen to z0evals (P8);
- the P10 blind read;
- P12 queue.

OD-0 no longer blocks: the fork branch name is `staged/compressor-media-extraction`.

## Environment alert (not a branch defect; owner decision)

The round-1 re-verifier's overlap sizing ran `git cat-file -e <PR head>` over its list of 221 PRs in the shared blobless scratch `h.git`. Each missing PR head set off a promisor lazy fetch. Re-measured read-only in fix round 2 (about 08:40 CDT):

- `h.git/objects/pack` is 8.9 GiB. 310 `.pack` files (7.55 GiB) are dated 2026-10-01 between 08:03 and 08:21 CDT. Only 4 packs (0.46 GiB) are older, and none is newer.
- The 12 GB `/tmp` tmpfs is at 100% (7.8 MiB free). Any worker writing to `/tmp` can fail with ENOSPC. Here it broke the harness's own output capture until outputs were redirected to `/mnt`.
- No refs were written. The branch is unchanged: `staging/compressor-media-extraction` = `c5e8be14b4`.

Update, fix round 3 (about 11:10 CDT, read-only): the scratch `h.git` path is now a symlink to a copy on the large data disk, and its pack directory there is 9.1 GiB. `/tmp` is at 23% (9.1 GiB free). This round did not do the move and does not know who did. The promisor packs are still present. This round's merge-tree and regeneration ran against that repo, and its worktrees were on the data disk.

Nothing was deleted in fix round 2. The re-verifier's targeted cleanup was denied by the auto-mode classifier. That cleanup would delete only packs dated at or after 08:03 whose `.promisor` names only its PR-head SHAs, and skip any pack that holds a ref, a worktree tip or a multi-pack-index entry. Whether to run it is the owner's decision. Do not run `git gc --prune=now` or a repack on the full tmpfs as a substitute, because both need free space first. This round's overlap census used only GitHub API reads and touched no local object store.

## NOT_TESTED

- `hermes` CLI end to end, runtime import time and RSS (`runtime_bench.py`, OD-2).
- Windows and macOS. The change has no platform code, and `scripts/check-windows-footguns.py` is clean on the 10 touched files.
- Real transcripts. Golden parity used a seeded synthetic corpus. Behaviour identity rests on AST identity plus that corpus.
- An independent blind read.
- Flakiness beyond GREEN 3/3 (P5's `flaky = false` is not recorded). The F14 guard set ran on this commit cherry-picked onto main `34f8ec3b40`, not on `c5e8be14b4` itself (same patch-id), and does not measure which moved statements it reaches.
- `tests/` outside `tests/agent/` and `tests/tools/`. The full suite was not run. No other test directory imports a moved name; `old_path_zero` scans the whole tree.
- Native compaction routes. The code is untouched, and the server-side summaries cannot be inspected.

## Origin action (owner only)

The single smallest ask is one comment on NousResearch/hermes-agent#80636, text in `body.md`. No @mentions. Attach `compressor-media-extraction.patch`, or link `kvnloo/hermes-agent:staged/compressor-media-extraction` once it is pushed. The comment says that the same media commit sits in #80645, #80644, #81074 and #81181, and that landing a rebuilt slice obsoletes it in all five. It also says the maintainer has already split micro-compaction and summary dispatch out himself, and asks first whether the media helpers are already on his list (fix round 3). The PR numbers it cites were re-checked OPEN/MERGED/CLOSED as stated at 11:47 CDT and again at 13:38 CDT in polish round 5 (recheck/r20261001-05); re-check again before posting:

> This slice no longer applies to main. The media code has grown since August (tool-image retirement inside the protected tail, the send-path `evict_stale_outbound_tool_images`, the `_multimodal` envelope). `merge-tree` now conflicts in `agent/context_compressor.py`, and AGENTS.md now rules out re-export seams for internal moves.
>
> I rebuilt just the media slice on current main without the seam. It keeps this PR's module name and media topic, and callers and tests import from `agent/context_compressor_media.py`. One difference: the text helper `_append_text_to_content`, which this PR also moves, stays in the facade, because `conversation_compression.py` imports it from there. No behaviour change: tests/agent and tests/tools give the same pass/fail set before and after, and all 16 moved statements are byte- and AST-identical. Patch attached.
>
> One knock-on to flag: the same media commit (5aa1746a28) also sits, unchanged, in #80645, #80644, #81074 and #81181, which stack on this PR. If a rebuilt media slice lands, that commit is obsolete in all five, and each would need to drop it when rebased, because it adds the same new file.
>
> Since this PR was opened, the file has also been split from the maintainer side: micro-compaction moved to `agent/micro_compaction.py` (4a64d42f9b, in #102117) and summary dispatch to `agent/context_compressor_summary.py` (77086b1439, in #104920). If the media helpers are already planned that way, please ignore this.
>
> If not: is an outside split of the media helpers wanted now, given how often this file changes? On 2026-10-01, 411 of the 33,677 open PRs touched it. Not counting this stack and 16 stale-base diffs of 600+ files, seven of them would need a small follow-up if this lands: five change the moved code (#90910, #106867, #107589, #110103, #130634), and #85481 and #104914 add facade calls to moved helpers that the facade would no longer import. An eighth, #120403, only adds an old-path import of `_rewritten`, which keeps working because the facade still imports that name. If yes, happy for it to be folded into this PR, or to go in as a salvage with Andrex as co-author, whichever the maintainers prefer.
>
> AI assistance: prepared with Claude Code (Claude Opus 5.5). It made the move with a small AST-based script, ran the checks and drafted this comment.

Only if that thread says yes to a salvage PR: regenerate on the day's main (queued item 1), then run `gh pr create -R NousResearch/hermes-agent --base main --head kvnloo:staged/compressor-media-extraction --title "refactor(compression): move image/media helpers into agent/context_compressor_media.py" --body-file PR_BODY.md` (NOT run here).

## Next steps

1. Owner: post the pre-ask comment (`body.md`) on #80636, with `compressor-media-extraction.patch` (in this directory). Then wait for the thread.
2. Ledger worker: commit `regen/`, `receipts/`, this STAGING.md, `body.md` and `PR_BODY.md` to `claude/ledger:factory/xf/staging/compressor-media-extraction/`. The receipt hashes are listed in the front matter.
3. Another worker: blind exact-head read of `c5e8be14b4` (P10).
4. At promotion: run queued items 1 and 3 on the exact main. Update the numbers in PR_BODY.md and `body.md`, including the merge-check line in PR_BODY.md (`34f8ec3b407e` at polish round 5), the overlap census counts (411 of 33,677 at fix round 3; the flagged heads were re-read unchanged in polish round 5) and the eight flagged PRs outside the stack (seven needing a fix, plus #120403). `regen/overlap_delta.py` refreshes the census cheaply when main's facade blob is unchanged. If `extract_media.py` exits 2, the recipe needs a human look; do not force it.
5. Owner decision (environment, not this branch): whether to remove the promisor packs that filled `/tmp` on 2026-10-01 (see "Environment alert"; the repo has since been moved to the data disk and `/tmp` is no longer full). Fix rounds 2 and 3 deleted nothing.
6. Orchestrator: either accept the recorded §10 deviation (local name kept, v1 at `refs/xf/superseded/compressor-media-extraction-v1`) or rename to `staging/compressor-media-extraction-v2` before the first push, and update `phase3_results.json` builds[id].branch_sha (still `d2bff3a59e`, re-read in polish round 5) to `c5e8be14b4`. Polish round 5 found the commit message accurate, so it made no message-only `-v2`; the rename stays the orchestrator's choice.
7. Later slices, only if the thread wants outside splits now and the maintainer is not doing them himself: text utils (#80626), budget (#80634) and tool-result summarizers (#80645). Each would be a salvage of andrexibiza's slice, with the same recipe and no shim.

## History

- 2026-10-01 | CANDIDATE → STAGED | builder (Claude Code, Opus 5.5) | one commit on main `572e4f4fad`, 9 receipts, route adjusted core-pr → salvage-support after finding #80636
- 2026-10-01 | STAGED (fix round 1) | fixer (Claude Code, Opus 5.5) | phase-3 verifier findings. Rebuilt on main `aea969677c` with the corrected commit message (four test modules, not five): `c5e8be14b4`, same patch-id; the local branch was moved to it (never pushed). Recorded the #80636 stack (#80645, #80644, #81074, #81181) in ownership, competitors, PR_BODY.md and the pre-ask. P5 PASS → PENDING (F14 not run); added per-hunk sabotage with the unpinned rows listed. Added `regen/golden_coverage.py`, `regen/sabotage_perhunk.py`, `regen/COMMIT_MSG.txt`. Scrubbed absolute paths from STAGING.md and receipts. Fork branch name `staged/compressor-media-extraction` (OD-0 resolved). `body.kind` set to the enum value `support-note` (`body.md`); `adjacent.pre_existing` is a list. All evidence re-run as round `r20261001-02`.
- 2026-10-01 | STAGED (fix round 2) | fixer (Claude Code, Opus 5.5) | round-1 re-verifier findings. Text and evidence only; the branch is unchanged (`c5e8be14b4`, local, not pushed) and the promotion form stays salvage-support.
  - (1) The overlap text named only a 3-PR merge-tree sample. A full GitHub-API census found 404 of 33,537 open PRs touching the facade. 25 edit a moved statement; 7 focused PRs outside the stack would need a port or an import fix. New receipt overlap/r20261001-03 supersedes `-02`; the census scripts are in `regen/overlap_*.py`. PR_BODY.md, `body.md`, the ownership record, the premise and the experiments row were updated.
  - (2) The `[push]` comment now names the `tags: v*` trigger in live-providers.yml (new receipt push-trigger/r20261001-03; 11 push-triggered workflows of 52, 0 match a branch push).
  - (3) `maintainer_signal` and the Route bullet now quote kvnloo's #78647 comment exactly ("comment-first — no mega-PR", "no competing mega-PR from me") and say that the comment is about the desktop `main.ts` extract map.
  - (4) The environment alert (promisor packs filling `/tmp`) is recorded for an owner decision. Nothing was deleted.
  - Also: an API blob-identity recheck on main `bd394e2a4b` (`[merge_check].api_recheck`). Queued item 1 now uses the API census instead of per-PR `merge-tree` in `h.git`.
- 2026-10-01 | STAGED (fix round 3) | fixer (Claude Code, Opus 5.5) | round-2 re-verifier findings. Text, receipts and evidence only. The branch is unchanged (`c5e8be14b4`, local, never pushed), no code or test changed, and the promotion form stays salvage-support.
  - (1) Maintainer signal. teknium1 has been splitting the facade himself: `4a64d42f9b` (micro-compaction → `agent/micro_compaction.py`, written 2026-09-02, reached main through his own #102117 on 2026-09-04) and `77086b1439` (`agent/context_compressor_summary.py`, his own #104920, 2026-09-07). He closed #80628 on 2026-09-02. His #113887 comment calls the superseding work "mostly the 2026-09-02 direct-commit god-file splits". All of this is now in `maintainer_signal`, the premise and the route. `body.md` now acknowledges it and asks first whether the media helpers are already on his list. Correction to the finding: neither commit was pushed straight to main without a PR; both came through PRs teknium1 opened and merged himself.
  - (2) The invariant said "no name reachable through the old path". It now says what was shown: zero old-path references in the tree (`old_path_zero` = 0). The six names the facade imports back stay importable from the old path.
  - (3) `body.md` said seven focused PRs "edit the moved code or import it by the old path". That was wrong for #85481 (a facade call to a moved name, which would be a NameError) and for #120403 (an old-path import that keeps working). It now names each category, using the refreshed census. The refresh found 411 of 33,677 open PRs touching the facade, plus one new flagged PR, #130634. So seven need a follow-up and #120403 does not. The round-2 manifest's "7 need a fix" is corrected the same way. The AI-assistance line now also says Claude drafted the comment.
  - (4) The FACTORY §10 `-v2` deviation is recorded (`branch_version_deviation`, the member-branches table, next step 6). The branch was not renamed, because the push plan maps the local name to `staged/compressor-media-extraction`.
  - (5) The host name in every receipt's `env.host` was replaced by `<local-host>` (21 receipts, hashes updated).
  - Re-measured on main `44a1ce9724`: merge-tree clean (tree `7e2368a3b9`), regeneration identical, `verify_media` 6/6 PASS, and the PR merge-tree sample unchanged. Every cited PR and issue was re-read (#113887 is now noted as CLOSED). New receipt recheck/r20261001-04; new script `regen/overlap_delta.py`. `regen/overlap_scan_segment.py` gained resume and a secondary-rate-limit backoff.
  - Not done: F14 guards (P5 stays PENDING), the z0evals freeze (P8), the blind read (P10), queue (P12). The environment's promisor packs were not touched.
- 2026-10-01 | STAGED (F14 guard run) | Wave 0 F14 worker (Claude Code, Opus 5.5) | F14 standing guard set run on this item. The staging branch is unchanged (`c5e8be14b4`, local, never pushed).
  - Arm: `c5e8be14b4` cherry-picked onto main `34f8ec3b40` (38 commits past its parent `aea969677c`). Clean, author kept, same patch-id `2c92e56f`; arm `639aa4c211`, tree `7f7e21c2cc` = `merge-tree` of that main and the branch. New local ref `refs/xf/w0/compressor-media-extraction` in the scratch `h.git`.
  - Two runs (`compressor-media-extraction-r1`, `-r2`), each compared with the main baseline (`baseline-34f8ec3b40.json`, set `aba79fe8f09d`): **EQUAL** on all 40 verdict ids (36 PASS, 4 FAIL shared with main, same markers and fingerprints). r1 vs r2 is EQUAL as well. New receipt F14/r20261001-01, with both maps under `receipts/raw/F14-r20261001-01/`.
  - `guards.F14` NOT_RUN → EQUAL. P5 stays PENDING: RED, GREEN 3/3, per-hunk sabotage (unpinned rows listed), ADJACENT identical and F14 are now recorded with receipts, but `flaky = false` is not (flakiness was not measured beyond GREEN 3/3). No other gate changed.
  - Not done: the round-4 advisories (wording in body.md and PR_BODY.md, the #102117 review count, freshness on aaa863f7ff, the -v2 rename) are outside this run; nothing was pushed.
- 2026-10-01 | STAGED (polish round 5) | polish worker (Claude Code, Opus 5.5) | round-4 advisories, each re-checked against git, gh (read-only) and the files. Text, manifest and one new receipt only. The branch is unchanged (`c5e8be14b4`, local, never pushed), no code or test changed, no `-v2` was made, and the promotion form stays salvage-support.
  - (1) Topic cut, fixed. #80636's media module (blob `ffd4d23465`) holds 9 names, including `_append_text_to_content`, which this branch leaves in the facade (and two helpers that no longer exist on main). `body.md` now says "keeps this PR's module name and media topic" and names that one difference. PR_BODY.md says the same, lists all five text helpers that stay, and says where the cut differs from #80636.
  - (2) #102117 review count, fixed. `maintainer_signal` said "24 COMMENTED reviews". GitHub shows 24 reviews: 21 COMMENTED, 1 APPROVED, 1 CHANGES_REQUESTED, 1 DISMISSED.
  - (3) Freshness, fixed. Re-measured on the pinned main `34f8ec3b40` (newer than the advisory's `aaa863f7ff`): 38 commits past base, 0 `invalidate_on` diff lines, every touched and coupled file at the base's blob id, merge-tree clean (`7f7e21c2cc`), sandboxed regeneration gives exactly that tree, and `verify_media` gives 6/6 PASS. `[base].freshness`, `[merge_check]`, P1, P7, the experiments table, the acceptance-gates row and PR_BODY.md's merge line now say `34f8ec3b40`. All 29 cited items have the stated state, and all 13 stack and flagged PR heads are unchanged since round 4. New receipt recheck/r20261001-05, raw files under `receipts/raw/r05/`.
  - (4) The `-v2` rename and `phase3_results.json`: not acted on, by design. The commit message was re-checked claim by claim (5,753 lines, the AGENTS.md split rule, the six facade imports, the four test modules, the two docstrings, the AST identity, the parity sets) and is accurate. "It does not re-export the others" already covers old-path importability, and "the media slice of #80636" does not claim the same cut. So no message-only `-v2` was needed. `phase3_results.json` is the orchestrator's file and still says `d2bff3a59e` (next step 6).
  - (5) Old-path importability, fixed in PR_BODY.md. A new paragraph says the six names the facade still calls stay importable from `agent.context_compressor`, while the other ten, including `evict_stale_outbound_tool_images`, now come only from the sibling. It notes that no file in the tree uses the old path and that AGENTS.md rules out shims.
  - (6) Policy fit: by design. The route stays support-note first, and `body.md` still offers folding the slice into #80636 before a separate salvage.
  - (7) Status: STAGED is still right. P2, P5 (F14 is EQUAL, but `flaky = false` is not recorded), P8, P10 and P12 are PENDING.
  - Also: `body.md` now writes the census count as "411 of the 33,677 open PRs". The Origin-action quote was regenerated from `body.md` and matches it exactly. The stale `regen/__pycache__` (CPython 3.14 bytecode from fix round 3) was moved out of the publishable set into a private run directory, not deleted. The privacy scan was re-run (see `[body].privacy_scan`).
