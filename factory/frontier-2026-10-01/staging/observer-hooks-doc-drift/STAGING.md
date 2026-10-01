+++
xf_staging = 1
id = "observer-hooks-doc-drift"
title = "Document post_api_request's first_chunk_at, context_length and moa_references"
version = 2               # round-1 rebuild after the phase-3 verifier (CHANGES_REQUIRED on f47410f2ac); local branch forced to the new commit as instructed, nothing was ever pushed. Round 2 (2026-10-01T12:20Z) changed only this manifest and added receipt DOCS-CHECKS/r20261001-04; the commit, patch and PR body are unchanged. Polish round (2026-10-01T18:36Z) changed PR_BODY.md (line references pinned to main 34f8ec3b40; AI disclosure names the docs change and the description) and this manifest, and added receipt DOCS-CHECKS/r20261001-05; the commit, patch and local branch are unchanged, no -v2
branch = "staging/observer-hooks-doc-drift"
branch_physical = "local ref staging/observer-hooks-doc-drift in scratch h.git, not pushed. It publishes to kvnloo/hermes-agent as staged/observer-hooks-doc-drift: the fork's legacy refs/heads/staging @28790e597c blocks staging/*, so OD-0 is resolved by the staged/ rename. staged/observer-hooks-doc-drift is free on the fork (ls-remote ~2026-10-01T11:18Z, no staged/* refs yet)."
branch_sha = "9225807160327a648a21bd493e9ed943f8ce5baa"
status = "STAGED"        # commit + complete docs evidence; round-1 fixes and round-2 manifest fixes done; blind re-verify (P10), freeze (P8) and queue (P12) pending
route = "docs-leaf"      # promotion_form = "docs"; rides the kvnloo/hermes-agent#404 docs-bundle queue, no slot of its own
feature = "observer-hooks-doc-drift"
invariant = "Every kwarg the post_api_request emitter passes (agent/turn_response_intake.py:68-98) appears in the observer-hooks.md post_api_request field list, described as the source produces it."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
fetched_at = "2026-10-01T11:0xZ (start of round 1; exact minute not recorded)"
previous_base = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (round-0 head f47410f2ac; 47 commits before aea969677c, none touching a cited file)"
invalidate_on = ["website/docs/developer-guide/observer-hooks.md", "agent/turn_response_intake.py", "agent/turn_api_request.py", "agent/chat_completion_helpers.py", "agent/codex_runtime.py", "agent/conversation_loop.py", "agent/turn_response_check.py", "agent/moa_trace.py", "agent/moa_loop.py", "agent/turn_usage.py", "hermes_cli/plugins.py", "any new post_api_request emitter or kwarg (re-run F13)"]
freshness_recheck = { main = "34f8ec3b407e50bad3ae27e4cd79d65212061356", checked_at = "2026-10-01T18:35:56Z", commits_since_base = 38, invalidate_on_changed = false, new_emitter_or_kwarg = false, page_blob_unchanged = true, merge_tree_clean = true, tree = "ac1a4ea154", receipt = "DOCS-CHECKS/r20261001-05", note = "0 of the 11 invalidate_on files changed; 0 diff lines name post_api_request and 0 added lines call invoke_hook; all 14 cited spans in PR_BODY.md re-read on this main and match (blobs identical to base); tree equals the F14 arm be5c73d230", previous = "040b6df2c4 at 12:16:17Z, 8 commits, tree 36e87a74ee; before that e8c97320ac at 11:16:21Z, 6 commits, tree d049544da9" }
beyond_pinned_main = "Informational, not a gate input: upstream main was 363e9d5f0a (committed 2026-10-01T18:25:54Z, 23 commits after 34f8ec3b40) at the polish round. Read with gh only (compare + contents); it is not in the local mirror, so no merge-tree was run on it. Of the invalidate_on files only agent/codex_runtime.py changed (+35/-10, 4 hunks in app-server session code at :534-:693, 0 +/- lines name first_chunk_at, post_api_request, moa_references, context_length or invoke_hook). It moves the cited codex_runtime.py:1090-1096 to :1115-1121; the PR body pins its line references to 34f8ec3b40, so they stay correct (DOCS-CHECKS/r20261001-05)"

[upstream]
issues = ["NousResearch/hermes-agent#64231 (teknium1 hook catalog; DOCS_ONLY class: #63339, #60735)", "NousResearch/hermes-agent#16106 (yepyhun, provider timing trace / TTFB)"]
eval_prs = []
carrier = { pr = 0, author = "", head = "" }   # own docs leaf, no carrier
competitors = []
adjacent_open_prs = [   # editors of observer-hooks.md first (all 7 found by a sweep of every open PR's file list, DOCS-CHECKS/r20261001-04), then PRs that change the payload but not the page
  { pr = 53007, author = "OutThisLife", head = "7fde663972", touches = "observer-hooks.md (+20 appended after the page's last line, main :334)", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (offset 15); reverse order (main + #53007, then this branch) also clean. Documents none of the three fields. Its code (hermes_cli/observability/relay_traces.py) reads first_chunk_at from post_api_request as a consumer, which agrees with this page; it adds no emitter or kwarg (DOCS-CHECKS/r20261001-04)" },
  { pr = 108924, author = "Finn763", head = "d69414122a", touches = "observer-hooks.md (+10/-2: an on_turn_interrupted row in the turn-scoped table after main :117, and the :127-128 paragraph rewritten to name it); code: agent/turn_finalizer.py +22, hermes_cli/plugins.py +8, hermes_cli/hooks.py, hermes_cli/plugins_dispatch.py, a test; other docs: user-guide hooks.md +51/-1, plugins.md, plugins/index.md; cli-config.yaml.example", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (no offset); reverse order clean (this branch's hunk lands at offset 8). Documents none of the three fields; its only +/- lines naming post_api_request are a hook-name list in user-guide/features/plugins.md. It conflicts with #113174 (both edit :127-130) on plain main as well, so that is between those two PRs, not with this branch (DOCS-CHECKS/r20261001-04)" },
  { pr = 113174, author = "fangliquanflq", head = "e528319005", touches = "observer-hooks.md (+30/-0: a '### Prompt-Builtin Completion' section inserted at main :130, just above '### Request-Scoped API Hooks'); code: 21 other files incl. hermes_cli/plugins.py +1/-1 (adds post_prompt_builtin_run to VALID_HOOKS)", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (no offset); reverse order clean (this branch's hunk lands at offset 30). Documents none of the three fields and no +/- line names post_api_request (DOCS-CHECKS/r20261001-04)" },
  { pr = 119347, author = "fangliquanflq", head = "4a527fc35d", touches = "observer-hooks.md (+1/-0: a transform_compaction_input row in the return-behaviour table after main :64); code: agent/compaction_hooks.py +188, agent/context_compressor.py +113/-14, hermes_cli/plugins.py +1 (VALID_HOOKS) and 6 more files", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (no offset); reverse order clean (this branch's hunk lands at offset 1). Documents none of the three fields; its +/- lines naming context_length are test fixtures (ContextCompressor(config_context_length=...)), not the attribute or the emitter. It conflicts with #121005 (it inserts inside #121005's :63 context) on plain main as well, so that is between those two PRs (DOCS-CHECKS/r20261001-04)" },
  { pr = 121005, author = "fabiomotta0311", head = "b29e6193b1", touches = "observer-hooks.md (+1/-1: rewrites the pre_tool_call return-behaviour table row at main :63); code: hermes_cli/plugins.py +75/-3, model_tools.py, agent/agent_runtime_helpers.py (pre_tool_call approval args)", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (no offset); reverse order clean. Documents none of the three fields and no +/- line names post_api_request (DOCS-CHECKS/r20261001-04)" },
  { pr = 124310, author = "marcxxv", head = "b6d9c4cd80", touches = "observer-hooks.md (+8/-0: an on_session_end fallback paragraph after main :109, above '### Turn-Scoped LLM Hooks'); code: agent/conversation_loop.py +3/-1 (wraps run_conversation in observe_turn_completion; api_start_time at :1650 untouched), agent/turn_observer_lifecycle.py +67, agent/turn_context.py, agent/turn_finalizer.py and a test file", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (no offset); reverse order clean (this branch's hunk lands at offset 8). Documents none of the three fields and no +/- line names post_api_request, api_start_time or first_chunk_at (DOCS-CHECKS/r20261001-04)" },
  { pr = 125192, author = "brucezyc", head = "52b505e68a", touches = "observer-hooks.md (+2/-1: the first subagent_stop sentence at main :231 gains child_subagent_id); code: 45 other files incl. hermes_cli/plugins.py (delegation milestone windows)", result = "same file, no hunk conflict: applies cleanly on top of 9225807160 (offset 15); reverse order clean. Documents none of the three fields and no +/- line names post_api_request (DOCS-CHECKS/r20261001-04)" },
  { pr = 123978, author = "nekwo", head = "09c927c745", touches = "11 files (+194/-8). Relevant here: agent/turn_response_intake.py +3 adds a cost= kwarg to this exact emitter, between context_length and assistant_message; agent/codex_runtime.py +49/-5 adds a second post_api_request emitter (Codex app-server) that sends api_request_id/api_duration/started_at/ended_at/first_chunk_at/moa_references as None; user-guide/features/hooks.md +3/-1 adds cost to the post_api_request row and section", result = "no file overlap, both merge orders clean. Semantic dependency, measured on main+#123978: F13 RED becomes [context_length, cost, first_chunk_at, moa_references], GREEN on top of this branch is [cost], 2 emitter sites (codex_runtime.py:159, turn_response_intake.py:68), cited range shifts to :83-100. If #123978 lands first: rebase, add a cost bullet and the Codex app-server None case to the first_chunk_at bullet and the moa_references line, re-run F13. The PR body says so." },
  { pr = 101688, author = "Bacaa14", head = "86a079b3ed", touches = "agent/conversation_loop.py (adds a rate_limit kwarg to post_api_request, written against the emitter's old home before it moved to turn_response_intake.py)", result = "same class as #123978; stale layout, no file overlap. Re-run F13 if it lands" },
  { pr = 70690, author = "AlexeyZelenin", head = "b52dc53c66", touches = "agent/codex_runtime.py (a Codex app-server post_api_request emitter, overlapping #123978)", result = "same class as #123978; no file overlap. Re-run F13 if it lands" },
]
listed_not_page_edits = [   # GitHub's file list names the page, but neither PR edits it relative to current main (DOCS-CHECKS/r20261001-04)
  { pr = 121502, author = "Sonnenwerk", head = "2b1f674eb4", why = "1519 files against its stored base a5bd246865 only because the branch merged main, which brought in main's own ab8a99c730 (fix(relay)). Against current main it changes 3 files, not the page; merge-tree with 9225807160 is clean" },
  { pr = 120375, author = "ssxi341-alt", head = "b81354460a", why = "a 14,123-file 'chore(sync)' snapshot commit on a merge-base 35,959 commits behind main, which adds a whole older copy of the page (blob 6a7d1389fb, 0 mentions of the three fields). That is an add/add conflict with main's page already, and this branch does not change it" },
]
field_origin = ["first_chunk_at: NousResearch/hermes-agent#100425 (salvage of #98555, 2026-09-01), Codex extension #115819", "context_length / moa_references: origin PR not identified (blobless history)"]
close_after = []
demand = { score = 20, source = "catalog.json (impact 1, evidence strong)" }
maintainer_signal = "teknium1's #64231 verdict table accepts a DOCS_ONLY class"
prs_recheck = "2026-10-01T18:36Z (DOCS-CHECKS/r20261001-05): every PR above and in listed_not_page_edits is still OPEN with the recorded head; #100425 and #115819 are MERGED and touch no website/ file; #16106 and #64231 are open issues. Top-up of PRs created 12:16:34Z-18:32:49Z: 288 (267 open), 6 truncated file lists re-read over REST, 0 touch observer-hooks.md, turn_response_intake.py, hermes_cli/hooks.py or user-guide features/hooks.md"
wave_issues = "kvnloo/hermes-agent#402 is closed and was posted upstream as NousResearch/hermes-agent#130139 (salvage wave); kvnloo#403 became NousResearch/hermes-agent#130140 (close wave). Neither mentions this item (gh read 2026-10-01)."

[ownership]
searched_at = "2026-10-01T08:55Z; re-run ~2026-10-01T11:17Z; round 2: file lists of all open PRs 11:41-12:13Z, top-up 12:16:30Z"
queries = ["first_chunk_at", "moa_references", "observer-hooks.md", "observer hooks docs", "post_api_request context_length", "post_api_request docs", "first_chunk_at docs (all states)", "issues: first_chunk_at", "re-run: open PRs first_chunk_at / moa_references / observer-hooks.md / post_api_request", "round 2: file list of every open PR (33,478 enumerated + 21 opened since), not a text search (DOCS-CHECKS/r20261001-04)"]
open_external = []            # no open PR documents these three fields. The open PRs that mention them change code (#105326, #113523, #96225, #112405) or add kwargs/emitters (#123978, #101688, #70690); none of those edits observer-hooks.md. The 7 open PRs that do edit observer-hooks.md (#53007, #108924, #113174, #119347, #121005, #124310, #125192) document other hooks and are recorded under adjacent_open_prs; #120375 and #121502 are listed by GitHub but are not real edits (listed_not_page_edits)
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD work, no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "PLAN section 9 wants docs fixes consolidated and owned by the Hermes lane; handled by riding the #404 docs-bundle queue (not checked against PLAN.txt itself, which lives under ~/.hermes and is off limits)"
verdict = "OURS (no external owner)"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]   # not touched

[evidence]   # local durable paths; claude/ledger:factory/xf/... copies pending
receipts = [
  { id = "F13/r20261001-03", path = "receipts/F13-r20261001-03.json", sha256 = "7e0a6d0a66d6736b5d6936fa358be6134e78fe39aa421de5c9a09ba3fa5391ff" },
  { id = "DOCS-CHECKS/r20261001-03", path = "receipts/DOCS-CHECKS-r20261001-03.json", sha256 = "c0ea273063130fcf1444c47c4f6c3cb6fa6c7744c2e125e5bc980f4044449960" },
  { id = "DOCS-CHECKS/r20261001-04", path = "receipts/DOCS-CHECKS-r20261001-04.json", sha256 = "fc82032ebf821b37a556a0a76b1b7f61f8142f78ddf12308fdadbaab58c3101d", note = "round 2, supplements -03: sweep of every open PR's file list, plus apply-checks in both orders for the 7 that edit observer-hooks.md; freshness on main 040b6df2c4" },
  { id = "F14/r20261001-01", path = "receipts/F14-r20261001-01.json", sha256 = "ea3f200d9c545c5df052e3e67526be97a3b6a7c3397548e8cab7c2ce7994739f", note = "Wave 0 F14 guard set (rev 1, set sha256 aba79fe8f09d...) on 9225807160 cherry-picked onto main 34f8ec3b40 (arm be5c73d230, ref refs/xf/w0/observer-hooks-doc-drift); 2 runs, both EQUAL to the baseline on all 40 verdict ids" },
  { id = "DOCS-CHECKS/r20261001-05", path = "receipts/DOCS-CHECKS-r20261001-05.json", sha256 = "19bbef44704bcc52c97347a379ca346903332d5888f5d2a0eb561d1131aa40ff", note = "polish round, supplements -04: freshness on main 34f8ec3b40 (merge-tree clean, tree ac1a4ea154, 0 invalidate_on changes, 14/14 cited spans match), referenced-PR states, open-PR top-up (288, 0 hits), informational look at newer main 363e9d5f0a" },
]
superseded_receipts = [
  { id = "F13/r20261001-02", path = "receipts/F13-r20261001-02.json", sha256 = "67c26e8b5b5c16358f6ef9db417baa81bd437f2f73e02d3ae85f4372277f4faa", sha256_before_redaction = "8e3146fb21308f3c1a2da8c7ebd129e849f70d0a95e900f295ed5fbf781dce83", why = "head f47410f2ac on base 572e4f4fad; rebuilt in round 1" },
  { id = "DOCS-CHECKS/r20261001-02", path = "receipts/DOCS-CHECKS-r20261001-02.json", sha256 = "3b84da29055e4919183667b6fc9f18c60966a88400df134c8c789e4796f80053", sha256_before_redaction = "20bb9a9901c0ca05856c185d1fd35342320a20577f61aad1897f68754c68b87d", why = "same rebuild" },
  { id = "F13/r20261001-01", path = "receipts/F13-r20261001-01.json", sha256 = "f595bde17ece762f68f371a897e74e26aa6c3c84c352489d2051566f6c5285f0", sha256_before_redaction = "d0fa02765db0b2af0139e52a0d3cb3066bc85fbfe6ee35618a40a51153956ddc", why = "head d663ec667d, amended before publication (first_chunk_at bullet gained the failed-stream case)" },
  { id = "DOCS-CHECKS/r20261001-01", path = "receipts/DOCS-CHECKS-r20261001-01.json", sha256 = "9a06f3f35d3efe2bad2ee81c0cd0cde0bbe040400278c3604c32517d4741d6cc", sha256_before_redaction = "72d59f6ac64bd37028e7e907fab7e2008af9f8b45ed3113d69f2a4834a4061e4", why = "same amend" },
]
redaction_note = "Round 1 replaced the absolute local paths in the four superseded receipts' command strings (scratch repo, receipt output path, venv python) with <scratch>/h.git, a relative path and $HERMES_PYTHON. Nothing else changed; files re-frozen a-w. The -03 receipts carry no absolute local paths (the F13 checker now writes portable command strings)."
checker = { f13 = "tools/f13_hook_doc_diff.py sha256 e2e5c04bbc52f289266a99df1dda4ef1ee3667e70e42dc283a1edff67d70c784 (round 1 added --reps and portable command strings; the gate logic is unchanged)", probe = "tools/test_probe_ttfb_retry.py sha256 8bec0bf29c45125265819767ea6df7a9edc0d7de0cf559e24352c37d350ded40 (evidence only, not in the commit)", open_pr_sweep = "tools/open_pr_sweep/*.py (round 2; per-file sha256 in DOCS-CHECKS/r20261001-04 tools_sha256; gh read-only)" }
red = { test = "F13 static key diff (post_api_request emitter kwargs minus observer-hooks.md list)", main = "aea969677c", marker = "undocumented = [context_length, first_chunk_at, moa_references]", receipt = "F13/r20261001-03" }
green = { reps = "3/3 (deterministic static check; --reps 3, all three passes identical)", observed = "undocumented = []", receipt = "F13/r20261001-03" }
negative_control = { mutation = "drop each new bullet (3 cases) + inject a synthetic kwarg into the emitter (1 case); retry probe: reset started_at per try", result = "4/4 re-RED with exactly the mutated key; retry probe RED at the started_at equality", receipt = "F13/r20261001-03, DOCS-CHECKS/r20261001-03" }
retry_caveat = { stale = "f47410f2ac observer-hooks.md:157 'Time to first byte is `first_chunk_at - started_at`.'", sources = "conversation_loop.py:1650 (one api_start_time per API call, before the retry loop), :1501-1530 (build_api_request per try), turn_api_request.py:106-107 (first_chunk_at reset per try), turn_response_check.py:119 (api_duration spans every try), chat_completion_helpers.py:3571-3590 (stream reconnect backoff)", probe = "2 passed x3 runs; main-loop retry: difference 0.640 s vs 0.005 s for the answering try; stream reconnect: 0.307 s vs 0.000 s", receipt = "DOCS-CHECKS/r20261001-03" }
adjacent = { identical = true, observed = "tests/agent/test_first_chunk_at_hook.py + tests/agent/test_moa_observability_bridge.py: 17 passed, 0 failed on 9225807160 (code identical to base)", pre_existing = [] }
guards = { F14 = "EQUAL", receipt = "F14/r20261001-01", observed = "arm be5c73d230 (9225807160 cherry-picked clean onto main 34f8ec3b40, patch-id identical): r1 and r2 each 36 PASS / 4 FAIL over 40 verdict ids, identical (verdict, marker, fingerprint) to baseline-34f8ec3b40 on every id; the 4 FAILs are the baseline's own; flaky list empty", previous = "N_A (docs-only, no code path changes), before the Wave 0 F14 set existed" }
quantitative = []
cache_read_ratio = { status = "N_A" }
route_scope = "n/a"
not_tested = ["Docusaurus build:fast", "ascii-guard lint:diagrams", "runtime payload values on bedrock_converse (static evidence only)", "Codex Responses physical stream retry after events on the failed stream (static only; the page says 'can also include')"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "", commit = "" }

[gates]
P1 = "PASS"
P2 = "PASS"
P3 = "PASS"
P4 = "N_A"
P5 = "PASS"   # re-checked in the F14 round: F14 EQUAL (F14/r20261001-01) plus RED, GREEN 3/3, sabotage, ADJACENT and flaky=false already recorded with receipts
P6 = "N_A"
P7 = "PASS"
P8 = "PENDING"
P9 = "PASS"
P10 = "PENDING"
P11 = "RECORDED"
P12 = "PENDING"

[verification]
verifier = ""
provenance = "independent"
exact_head = "9225807160327a648a21bd493e9ed943f8ce5baa"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""      # never set by the author worker
prior = "phase-3 verifier on f47410f2ac: accept=false (CHANGES_REQUIRED), 5 problems, all fixed in round 1. Round-1 re-verifier on 9225807160: 2 minor manifest problems (3 unrecorded editors of observer-hooks.md; 'no file overlap' wording for #53007), commit and PR body need no change; both fixed in round 2. See History"

[merge_check]
main_sha = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
checked_at = "2026-10-01T18:35:56Z"
clean = true
tree = "ac1a4ea15479ae2239f244365078fac89a1cf816"   # same tree as the F14 arm be5c73d230 (DOCS-CHECKS/r20261001-05)
previous = "040b6df2c4 at 12:16:17Z, clean, tree 36e87a74ee"
recheck = "git merge-tree --write-tree main staging/observer-hooks-doc-drift"

[push]
target = "kvnloo/hermes-agent refs/heads/staged/observer-hooks-doc-drift"
no_follow_tags = true
workflow_push_matches = 0     # .github/workflows on aea969677c: 11 push workflows, no push filter matches staged/observer-hooks-doc-drift; only tag trigger is v* (live-providers). 0 workflow files changed between aea969677c and 34f8ec3b40 (DOCS-CHECKS/r20261001-05), so the scan still holds there
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }   # self-assessed; P10 re-checks
jargon_lint = "PASS"          # grep for envelope/lane/E##/F##/P1-P12/OD-n/xf/factory/staging/receipt/probe/@mention/home paths/kvnloo: 0 hits (re-run in the polish round on the edited body)
privacy_scan = "PASS"         # re-run 2026-10-01T18:38Z over STAGING.md, PR_BODY.md, the patch, receipts/ and tools/: no absolute local paths, host name, secrets or bytecode
sha256 = "34441a20ecdb2aa9b21683fc1c7196ddc5b8d9ed208c738ab9b7b7d39fc8feab"   # PR_BODY.md after the polish round

[queue]
board = "kvnloo/hermes-agent#404"
position = "after the 39 existing rows; folded into the next docs bundle"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# observer-hooks-doc-drift: Document post_api_request's first_chunk_at, context_length and moa_references

**Promotion form:** docs (route `docs-leaf`), unchanged by rounds 1 and 2. Round 2 found no external owner, so the form stays docs; salvage-support and HOLD don't apply. It rides the docs-bundle queue on kvnloo/hermes-agent#404 and takes no slot of its own.
**RFC / issue links:** NousResearch/hermes-agent#64231 (hook catalog, DOCS_ONLY class) and NousResearch/hermes-agent#16106 (provider timing trace). Fork board: kvnloo/hermes-agent#404 (39 rows). The old wave boards kvnloo#402 and kvnloo#403 are closed; they became NousResearch/hermes-agent#130139 and #130140, and neither mentions this item.
**Branch:** local `staging/observer-hooks-doc-drift` @ `9225807160327a648a21bd493e9ed943f8ce5baa` in scratch `h.git`. On the fork it will be `staged/observer-hooks-doc-drift`, because the fork's legacy `staging` branch blocks `staging/*`. That rename resolves OD-0. It is one commit on upstream main `aea969677c`, and merge-tree is clean on the newer `34f8ec3b40` (18:36Z, 38 commits later, tree `ac1a4ea154`; DOCS-CHECKS/r20261001-05). The commit was not rebased.
**Artifacts in this directory:** `PR_BODY.md`, `observer-hooks-doc-drift.patch` (sha256 `5e44f54fbaa6bdae761770d3900b14dcd1a9fda44b8513d38f7614f51327a741`, byte-identical to `git format-patch -1 --stdout 9225807160`), `receipts/`, and `tools/` (the F13 checker, the markdown structure check, the retry probe and, from round 2, `tools/open_pr_sweep/` for the open-PR file-list sweep and apply-checks, so others can reproduce the results).

## Invariant

Every kwarg the `post_api_request` emitter passes (`agent/turn_response_intake.py:68-98`) appears in the `post_api_request` field list of `website/docs/developer-guide/observer-hooks.md`, described the way the source produces it.

Proof path: a static AST scan of all 2,089 non-test Python files at base `aea969677c`. It finds exactly one `post_api_request` emitter, at `agent/turn_response_intake.py:68`, which passes 24 kwargs. Those are diffed against three things: the page's list, the page's Correlation IDs table, and the inherited `pre_api_request` identity/runtime bullets. The descriptions themselves were checked by reading the source. A runtime probe outside the commit backs the one timing claim (the retry caveat).

## Route and carrier choice

This is our own docs leaf. No open upstream PR documents these fields; the searches are listed in the front matter and were re-run in rounds 1 and 2.

**Open PRs that edit `observer-hooks.md` itself.** Round 1 recorded only #53007. The round-1 re-verifier found three more in a 140-PR sample, so round 2 read the file list of every open upstream PR instead of searching text (DOCS-CHECKS/r20261001-04). It enumerated 33,478 open PRs at 11:45-11:49Z and covered all of them. It used GraphQL lists, re-read 159 truncated lists over REST, and diffed 18 PRs too large for the API locally, against their merge-base with main. #126874 is the one exception: GitHub reports 0 changed files and its head repository is deleted. A top-up at 12:16Z checked the 21 PRs opened since; none touches the page.

Seven open PRs edit the page. Each one documents a different hook, none mentions `first_chunk_at`, `context_length` or `moa_references`, and none touches the `post_api_request` field list (`:151-158`). Each one is in the same file as this commit with no hunk conflict:

- its hunk applies cleanly on top of this commit (`git apply --check`, rc=0);
- the reverse order is also clean (main plus that PR's hunk, then this commit's diff).

Line numbers are on main `040b6df2c4`. Its copy of the page is the same blob as on base `aea969677c` (`3d9c636706`), and every hunk applies there at its stated position.

- #53007 (OutThisLife, head `7fde663972`) appends a NeMo Relay trace section after the page's last line (`:334`). It applies cleanly on top, at a 15-line offset.
- #108924 (Finn763, head `d69414122a`) adds an `on_turn_interrupted` row to the turn-scoped table after `:117` and rewrites the paragraph at `:127-128`. It applies cleanly on top with no offset.
- #113174 (fangliquanflq, head `e528319005`) adds a `### Prompt-Builtin Completion` section at `:130`, just above `### Request-Scoped API Hooks`. It applies cleanly on top with no offset.
- #119347 (fangliquanflq, head `4a527fc35d`) adds a `transform_compaction_input` row to the return-behaviour table after `:64`. It applies cleanly on top with no offset.
- #121005 (fabiomotta0311, head `b29e6193b1`) rewrites the `pre_tool_call` row of the return-behaviour table at `:63`. It applies cleanly on top with no offset.
- #124310 (marcxxv, head `b6d9c4cd80`) adds an `on_session_end` fallback paragraph after `:109`. It applies cleanly on top with no offset.
- #125192 (brucezyc, head `52b505e68a`) rewrites the first sentence of the `subagent_stop` paragraph at `:231` to name `child_subagent_id`. It applies cleanly on top, at a 15-line offset.

"No offset" means the edit sits above this commit's insertion. When all seven are stacked on this commit, two pairs collide: #108924 with #113174 (around `:127-130`), and #119347 with #121005 (around `:63-64`). Both pairs fail the same way on plain main, so they conflict with each other, not with this commit. Every other pair applies on both trees.

Six of the seven also change code under `invalidate_on`: `hermes_cli/plugins.py` (#108924, #113174, #119347, #121005, #125192) and `agent/conversation_loop.py` (#124310). None changes the emitter or the documented semantics:

- in #108924, #113174, #121005, #124310 and #125192, no added or removed line names `post_api_request`, `api_start_time`, `first_chunk_at`, `context_length` or `moa_references`, except a hook-name list in #108924's `user-guide/features/plugins.md`;
- #119347's only matches are test fixtures building a `ContextCompressor`;
- #53007's relay-trace observer reads `first_chunk_at` from `post_api_request` as a consumer, which agrees with this page;
- #124310's `conversation_loop.py` change wraps `run_conversation` in an observer context and leaves the `api_start_time` assignment at `:1650` alone.

So unlike #123978 below, none of them changes what this page documents. If one lands first, the only step is the usual merge-tree re-check.

GitHub's file lists also name the page for two more PRs that don't really edit it:

- #121502 (Sonnenwerk): its 1,519-file list is computed against a stale stored base. It reaches the page only through main's own `ab8a99c730`, which the branch merged. Against current main it changes 3 files, and merge-tree with this commit is clean.
- #120375 (ssxi341-alt): a 14,123-file `chore(sync)` snapshot on a base 35,959 commits behind main. It adds a whole older copy of the page, with no mention of the three fields. That copy already conflicts add/add with main's page, and this commit doesn't change that.

**Open PRs that change the same payload but not this file:**

- #123978 (nekwo) touches 11 files. Three matter here:
  - `user-guide/features/hooks.md`: it edits the `post_api_request` row and section to add `cost`. That table also omits the three fields, but this commit leaves `hooks.md` alone so it doesn't conflict with an external contributor's open PR.
  - `agent/turn_response_intake.py` (+3): it adds a `cost=` kwarg to this exact emitter, between `context_length` and `assistant_message`.
  - `agent/codex_runtime.py` (+49/-5): it adds a second `post_api_request` emitter, for the Codex app-server runtime. That emitter sends `started_at`, `first_chunk_at`, `api_duration` and `moa_references` as `None`.

  The two PRs share no file, and both merge orders are clean. The dependency is semantic, and it was measured on main + #123978 (DOCS-CHECKS/r20261001-03). F13 RED there is `[context_length, cost, first_chunk_at, moa_references]`. With this branch on top, GREEN is `[cost]`, there are 2 emitter sites, and the cited range moves to `:83-100`. So if #123978 lands first, this branch needs a rebase: add a `cost` bullet and the app-server `None` case, then re-run F13. If this branch lands first, the `cost` line goes on top. The PR body explains this interaction.
- #101688 (rate-limit state kwarg, written against the emitter's old home in `conversation_loop.py`) and #70690 (another Codex app-server emitter) are older open PRs of the same kind. Neither shares a file. The rule is the same: re-run F13 if either lands.

The fork branch `perf/first-visible-clocks` @ `6653c99cfd` is reference only. Its 3 lines in `observer-hooks.md` sit under `api_request_error` and name `first_reasoning_at` and `first_text_at`, which don't exist on main. Nothing was copied, so there is no Co-authored-by.

**Doc text (D2 rule).** Stale text, quoted from `observer-hooks.md:151-158` at `aea969677c` (the same blob `3d9c636706` as at `572e4f4fad`): "`post_api_request` includes the same identity/runtime fields plus: `api_duration`, `started_at`, `ended_at` / `finish_reason`, `message_count`, `response_model` / `usage` / `assistant_content_chars`, `assistant_tool_call_count` / sanitized response payload: `response` / compatibility object: `assistant_message`". The page has 0 occurrences of the three fields. The contradicting source is `agent/turn_response_intake.py:83-97` (blob `eebd9d12de`). How each field is described comes from:

- `first_chunk_at`:
  - reset before every attempt: `turn_api_request.py:107`;
  - set from the first counted chunk in `_StreamingCall`, which covers chat completions and Anthropic: `chat_completion_helpers.py:3005-3012`, `:4063-4065`;
  - set on the first parsed event in the Codex Responses runner: `codex_runtime.py:1090-1096`;
  - not set by `bedrock_converse` (`_BedrockStream`). These are the only two setters repo-wide;
  - not set on a partial-stream stub, which returns at `:4057-4059`, before the copy.
  - **Retry caveat (round 1).** The round-0 text said "Time to first byte is `first_chunk_at - started_at`" with no qualification. That formula came from the source comment at `turn_response_intake.py:84`, and it is wrong for a retried call. `started_at` has one assignment, at `conversation_loop.py:1650`, made once per API call before `_run_api_retry_loop`. The loop runs `build_api_request` again for each try (`:1513`), which resets `first_chunk_at` (`turn_api_request.py:106-107`) but never `started_at`. `api_duration` is `now - api_start_time` (`turn_response_check.py:119`). Reconnecting a dropped stream inside one try also keeps `started_at` (`chat_completion_helpers.py:3571-3590`). The page now says that the difference is time to first byte when nothing was retried, and that after a retry it can also include the failed tries and the backoff. It says "can" because the Codex runner keeps an earlier physical stream's first event (`codex_runtime.py:1095-1096`). It speaks of retries, not restarts: compression, redirect and fallback restarts start a new outer iteration with a fresh `started_at`. A probe outside the commit, `tools/test_probe_ttfb_retry.py`, confirms both retry shapes on the real loop with a mocked provider (details in Evidence), and its negative control goes RED.
- `context_length`: `agent.context_compressor.context_length`. That is the built-in compressor or a context-engine plugin (`agent_init.py:1979`, `:2003`).
- `moa_references`: `conversation_loop.py:307-318`, then `MoAClient.last_reference_metrics()`, then `slot_metrics()` at `moa_trace.py:64-72`. The keys are `label`, `model`, `provider`, `temperature`, `usage`, `cost_usd`, `cost_status`, `cost_source` and `output`. `output` is privacy-redacted only when `moa.privacy_filter` is set (`moa_loop.py:1293-1307`). The hook's `usage` is the aggregator's only (`turn_usage.py:48-58`).

All 14 cited blobs are byte-identical on `572e4f4fad` and `aea969677c`, so every line citation is valid on the new base.

## Member branches

| Ref | SHA | Role | Rebase status |
|---|---|---|---|
| `staging/observer-hooks-doc-drift` (local, scratch h.git; fork name `staged/observer-hooks-doc-drift`) | `9225807160` | The staged docs commit (author Kevin Rajan, `docs(observer-hooks):`, +15/-0) | On main `aea969677c`. merge-tree clean on `34f8ec3b40` (+38 commits, no invalidating path changed; tree `ac1a4ea154`, the same tree as the F14 arm). |
| `refs/fork/perf/first-visible-clocks` | `6653c99cfd` | Reference only. Its 3 `observer-hooks.md` lines document fork-only fields and are not copied. | merge-tree with `9225807160` is clean |

## First slice

**Committed.** One commit, `9225807160`: `docs(observer-hooks): list first_chunk_at, context_length and moa_references`. One file, `website/docs/developer-guide/observer-hooks.md`, +15/-0. There's no zh-Hans mirror of this page.

Commit history, all local and never published:

- `d663ec667d`: first build.
- `f47410f2ac` (round 0): added "the stream failed after sending output" to the `first_chunk_at` bullet, which `test_partial_stream_stub_leaves_timestamp_none` pins.
- `9225807160` (round 1): rebuilt on main `aea969677c`. The `first_chunk_at` bullet's last sentence became the retry caveat (+4 lines), and the commit message says the same.

The local branch was forced from `f47410f2ac` to `9225807160` as the fix instructions required. Nothing had been pushed.

## Evidence

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| F13 code-vs-docs key diff (T0, static, $0) | `receipts/F13-r20261001-03.json` (sha256 `7e0a6d0a…`) | KEEP | OBSERVED | 1 run of 3 deterministic reps (all identical), 2,089 files, wall 35.79 s | RED on `aea969677c`: 3 undocumented (`context_length`, `first_chunk_at`, `moa_references`). GREEN on `9225807160`: 0, reps 3/3. Negatives: 4/4 re-RED. Coverage: 21 of 41 VALID_HOOKS have a detected `*invoke_hook` site. |
| Docs checks + retry probe (T0, $0) | `receipts/DOCS-CHECKS-r20261001-03.json` (sha256 `c0ea2730…`) | KEEP | OBSERVED | probe 2 tests x 3 runs | See below |
| Open-PR editors of the page (T0, $0, round 2; supplements `-03`) | `receipts/DOCS-CHECKS-r20261001-04.json` (sha256 `fc82032e…`) | KEEP | OBSERVED | 33,478 open PRs (+21 top-up); 7 editors x 2 merge orders; 21 pairs x 2 trees | 7 real editors, all clean on top and in reverse order; 0 document the three fields; 0 change the emitter. 2 GitHub-listed non-edits (#120375, #121502). Freshness on `040b6df2c4`: merge-tree clean, 0 `invalidate_on` changes. |
| Polish-round freshness and open-PR top-up (T0, $0; supplements `-04`) | `receipts/DOCS-CHECKS-r20261001-05.json` (sha256 `19bbef44…`) | KEEP | OBSERVED | 1 merge-tree, 14 cited spans, 14 PRs + 2 issues, 288 new PRs (6 re-read over REST) | merge-tree clean on `34f8ec3b40` (tree `ac1a4ea154`); 0 of 11 `invalidate_on` files changed; 14 of 14 cited spans match; every referenced PR in its recorded state; 0 of 288 new PRs touch the page or the emitter. Informational: newer main `363e9d5f0a` moves the cited `codex_runtime.py:1090-1096` to `:1115-1121`. |
| F14 standing-regression guards (Wave 0 set rev 1, T0, $0, sandboxed) | `receipts/F14-r20261001-01.json` (sha256 `ea3f200d…`) | KEEP | OBSERVED | 2 runs x 19 cells (40 verdict ids) vs the 2-run baseline on main `34f8ec3b40` | **EQUAL.** `9225807160` cherry-picks cleanly onto `34f8ec3b40` (arm `be5c73d230`, same patch-id, ref `refs/xf/w0/observer-hooks-doc-drift`). r1 and r2: 36 PASS / 4 FAIL each, identical verdict, marker and fingerprint to the baseline on all 40 ids, and r1 = r2. The 4 FAILs are the baseline's own; none added. 0 blocked execs. |

The docs checks, all OBSERVED on `9225807160`:

- Retry caveat probe (`tools/test_probe_ttfb_retry.py`, copied into the worktree for the run and removed afterwards; not part of the commit). 2 passed, 0 failed, in 3 runs.
  - Main-loop retry: the 1st try fails after 0.2 s, then a 0.3 s backoff. Both `pre_api_request` events and the `post_api_request` carry the same `started_at`. `first_chunk_at - started_at` = 0.640 s, against 0.005 s for the try that answered; `api_duration` = 0.642 s.
  - Stream reconnect inside one try: `first_chunk_at - started_at` = 0.307 s, against 0.000 s from the reopened stream.
  - Negative control: resetting `started_at` before every try turns the main-loop case RED at the `started_at` equality.
- `check_doc_links.py`: OK.
- Skill-docs generator freshness: `extract-skills.py` and `generate-skill-docs.py` both rc=0, with 0 changed paths under `website/docs`, `sidebars.ts` and `i18n`. All of this ran under `unshare -rn`, and a connect probe confirmed egress was blocked.
- CommonMark+GFM structure: the list goes from 6 items to 9, and each new item is one paragraph. The diff adds 15 lines with 0 MDX-hazard characters outside code spans. The negative control (an injected `{x}`/`<x>` line) is flagged.
- Adjacent emitter tests: 17 passed, 0 failed.
- merge-tree: clean against main (freshness check on `e8c97320ac`), against all 18 `ready/docs*` bundles, and against the fork reference branch. Round 2 re-ran the main check on `040b6df2c4` (clean, tree `36e87a74ee`; in `-04`). It also re-ran the 18 bundle merges locally (18/18 clean; manifest-only, not in a receipt).
- Overlap sweep: 0 of 67 other `ready/*`, `staging/*`, `staged/*` and `promote/*` heads touch `observer-hooks.md`. The round-2 local re-count at 12:20Z found 0 of 71 (manifest-only).
- Open upstream PRs that edit `observer-hooks.md` (round 2, `-04`): 7 real editors. Each is in the same file with no hunk conflict; each applies cleanly on top of this commit and in the reverse order. #53007 and #125192 land at offset 15; the others, which sit above the insertion, need no offset. None documents the three fields. Details are in Route and carrier choice. `-03` had apply-checked #53007 alone.
- #123978 interaction measured (see Route and carrier choice).

The F13 receipt's `informational_matrix` is not gated. It also flags other drift on the same page, which still needs a source read before anyone writes it up:

- `pre_api_request`: `retry_count`, `middleware_trace`, `system_prompt`, and the legacy `user_message`/`conversation_history`/`request_messages` (partly covered by Payload Safety);
- `post_tool_call`: `middleware_trace`;
- `subagent_stop`: `child_role`/`child_status` (the prose says "role/status fields");
- `hooks.md` table: `post_api_request` lacks the same 3 fields, `pre_api_request` lacks `system_prompt`, `transform_terminal_output` lacks `tool_call_id`.

These are follow-up candidates for a later bundle, not part of this commit.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| D2 docs rule: quote the stale text and cite the contradicting source (`turn_response_intake.py:83-97`) | met | Section above; `DOCS-CHECKS-r20261001-03.json` `d2_docs_rule` and `retry_qualification` |
| Website link and generator checks are clean | met (link + generator); Docusaurus build and ascii-guard NOT_TESTED | `DOCS-CHECKS-r20261001-03.json` |
| Folded into the next docs bundle in #404 order (no separate slot) | pending (owner action) | merge-tree clean with all 18 `ready/docs*` bundles |

## Gate checklist (P1-P12)

- **P1 Need: PASS.** RED on `aea969677c` (F13/r20261001-03). Re-check at 18:36Z on `34f8ec3b40` (38 commits later): 0 of 11 `invalidate_on` files changed, no new emitter or kwarg (0 diff lines name `post_api_request`), page blob unchanged (DOCS-CHECKS/r20261001-05). The earlier 12:16Z re-check on `040b6df2c4` is in DOCS-CHECKS/r20261001-04. The RED was reproduced on 2026-10-01 (round 1, ~11:20Z). If the row is queued more than 24 h after that, the promotion-day F13 re-run in Experiments must refresh it first.
- **P2 Ownership: PASS.** No open or merged PR documents these fields. That was re-searched in rounds 1 and 2; round 2 read the file list of every open PR. Seven open PRs edit `observer-hooks.md`: #53007, #108924, #113174, #119347, #121005, #124310 and #125192. Each is in the same file with no hunk conflict, and each applies cleanly on top of this commit in both merge orders (#53007 and #125192 at offset 15, the others with no offset). None documents the three fields (DOCS-CHECKS/r20261001-04). #120375 and #121502 are listed by GitHub but are not real edits. #123978 has no file overlap. Its semantic dependency is recorded above, with the rebase rule. The claimant lanes are TUI work. No Hermes-lane item is known, but PLAN.txt was not read (it's under `~/.hermes`).
- **P3 Shape: PASS.** One file, +15/-0, no env vars, no hooks, no code.
- **P4 Real path: N_A.** It's docs-only. Three things stand in for it: the D2 source quote, the exhaustive setter grep, and the retry probe through the real conversation loop. The adjacent tests pin the other described semantics.
- **P5 Proof: PASS.** F13 RED with the marker matched (`[context_length, first_chunk_at, moa_references]`), GREEN 3/3 (`--reps 3`, identical), 4/4 negative controls (F13/r20261001-03). The commit is one hunk (`@@ -151,9 +151,24 @@`), and its 15 added lines are exactly the three bullets the sabotage cases drop, so no hunk is unpinned. Adjacent tests 17/17, identical to base (DOCS-CHECKS/r20261001-03). The retry probe passes 2/2 in 3 runs, and its negative control goes RED. `flaky = false` (deterministic). F14 guards: EQUAL (F14/r20261001-01). The docs change can't move any F14 probe; the run shows that the cherry-pick onto main `34f8ec3b40` leaves the 40-id guard set unchanged.
- **P6 Numbers: N_A.** The body makes no value claim. The probe timings illustrate the caveat and are not a performance claim.
- **P7 Package: PASS (local).** One commit on main `aea969677c`, correct author and subject. merge-tree is clean on current main `34f8ec3b40` (tree `ac1a4ea154`, DOCS-CHECKS/r20261001-05). The workflow push-trigger scan for `staged/observer-hooks-doc-drift` found 0 matches, and no workflow file changed between base and `34f8ec3b40`. `--no-follow-tags` is required. Not pushed.
- **P8 Freeze: PENDING.** Receipt sha256 hashes are recorded and the files are `chmod a-w`. They are not yet copied to `claude/ledger:factory/xf/receipts/`, and no z0evals study exists. Copy only the cited receipts as evidence: both `-03` receipts, DOCS-CHECKS `-04` and `-05`, and F14 `-01`.
- **P9 Text: PASS (self-assessed).** The template sections are filled (the "For New Skills" section is deleted, as the template asks for non-skill PRs) and NOT_TESTED is honest. AI assistance is disclosed for both the docs change and the description, and there are no @mentions. The jargon and privacy grep found 0 hits (re-run in the polish round). The body carries the retry caveat, the #123978 interaction and the Correlation IDs pointer, and pins its line references to `main` at `34f8ec3b40`.
- **P10 Independent read: PENDING.** A different worker needs to re-verify exact head `9225807160` after the round-1 and round-2 fixes. Round 2 changed only this manifest and added a receipt; the head is unchanged.
- **P11 Demand: RECORDED.** Impact is 1 and evidence is 9. This is a real docs fix, not test infra.
- **P12 Queue: PENDING.** Owner decision. The Wave 0 global precondition (F15, F14, E48, F11) was not met when this gate was last assessed. F14 has since run for this item (EQUAL); F15, E48 and F11 were not re-checked here. The staging cap applies. The row goes behind the 39 existing #404 rows.

## Experiments

**Run ($0):**
- F13: `python3 tools/f13_hook_doc_diff.py --repo <scratch>/h.git --base aea969677c60a1bb72fe227fdfb98f196a2092cc --head 9225807160327a648a21bd493e9ed943f8ce5baa --out receipts/F13-r20261001-03.json --run-id F13/r20261001-03 --supersedes ... --reps 3` (run from this directory under `unshare -rn`). Result: KEEP, 3 to 0 undocumented, GREEN 3/3, 4/4 negatives.
- Docs checks and the retry probe: the commands are recorded per check in `receipts/DOCS-CHECKS-r20261001-03.json`, with `$TH`, `$HERMES_PYTHON` and `<scratch>` placeholders. Result: KEEP.
- #123978 interaction (informational): F13 with `--base` = main + #123978 and `--head` = that + this branch. Both are unreferenced probe commits, and no ref was created. Result: as recorded above.
- F14 guards (Wave 0): a worktree detached at main `34f8ec3b40`, then `git cherry-pick 9225807160` with the author kept. Then `f14_run.py run <worktree> maps/observer-hooks-doc-drift-r{1,2}.json --label observer-hooks-doc-drift-r{1,2}` and `f14_run.py compare baseline-34f8ec3b40.json <map>`, all from the factory's `f14/` directory, with one sandboxed cell per probe. The full command list is in `receipts/F14-r20261001-01.json`. Result: EQUAL in both runs.
- Open-PR editor sweep (round 2, gh read-only), run from a scratch copy of `tools/open_pr_sweep/`:
  - `enum_numbers.py` lists every open PR number;
  - `sweep.py`/`sweep_asc.py` and `fetch_by_number.py <numbers> <out>` read the file lists;
  - `rest_files.py <N...>` re-reads lists that GraphQL truncated;
  - `analyse.py` lists the editors;
  - `gh pr diff <N>` for each editor, then `apply_checks.py <scratch>/h.git 9225807160 <main> aea969677c <N...>`.

  Too-large PRs were diffed locally after `git fetch --filter=blob:none --no-write-fetch-head <upstream> refs/pull/<N>/head`, which creates no ref. Result: KEEP (DOCS-CHECKS/r20261001-04).

**Queued:**
- T2 (local GPU) and T3 (paid): **none**. The selection lists no experiments beyond F13, and the change makes no value claim (P6 N_A).
- Optional T1, not needed for promotion: a runtime check that a streamed `bedrock_converse` attempt emits `first_chunk_at = None`. It would drive `_BedrockStream` with a fake `converse_stream` client and a recording `post_api_request` hook, from a test file outside the commit: `HOME=<scratch>/testhome-st-observer-hooks-doc-drift HERMES_HOME=$HOME/.hermes HERMES_PYTHON=<venv python> bash scripts/run_tests.sh -j 2 <probe file> -q`. The static evidence is exhaustive (two setters repo-wide), so this is a nice-to-have.
- Polish round (gh read-only + local git, $0): the merge-tree, `invalidate_on` diff, cited-span re-read, referenced-PR state and open-PR top-up commands are recorded in `receipts/DOCS-CHECKS-r20261001-05.json`, with a `<scratch>` placeholder. Result: KEEP.
- On promotion day, the freshness re-run: the F13 command above with `--base main --head staging/observer-hooks-doc-drift --run-id F13/r<date>-01 --supersedes F13/r20261001-03 --reps 3`, plus `git merge-tree --write-tree main staging/observer-hooks-doc-drift`. The PR body pins its line references to `main` at `34f8ec3b40`, so they stay correct as main moves. If the commit is rebased (for example after #123978), re-check every cited line and re-pin the body to the new base. Check #123978, #101688 and #70690 first: if any has merged, rebase and extend the list before re-running. If any of the seven page editors (#53007, #108924, #113174, #119347, #121005, #124310, #125192) has merged, the merge-tree run covers it; all seven apply cleanly with this commit in both orders today. Re-run `apply_checks.py` for the ones still open if their heads moved.

## NOT_TESTED

- **Docusaurus `npm run build:fast`.** There's no `website/node_modules` in the sandbox, and `npm ci` plus `prebuild.mjs` need the network. The mitigation is the static MDX-hazard scan (0 hazards) and the CommonMark+GFM parse. Docusaurus 3 defaults to the MDX format, and full MDX parsing was not available.
- **`npm run lint:diagrams` (ascii-guard 2.3.0).** It isn't installed. The added lines contain no box-drawing or `+--` patterns.
- **Runtime payload values.** Apart from the retry probe, the descriptions come from reading the source plus the existing tests. `bedrock_converse` = `None` is static evidence only, and so are the `context_length` values for third-party context engines.
- **Codex Responses physical stream retry** when the failed stream had already sent events. `first_chunk_at` then keeps the earlier stream's first event (`codex_runtime.py:1095-1096`). This is static only, and it's why the page says the difference "can" include failed tries.
- **`moa_references` repeats on a fan-out cache HIT** (`_last_reference_metrics` is set only on the cache-miss path). This is observed statically and untested. The doc uses the accessor's own wording, "most recent fan-out", and does not document the repeat as contract. The PR body raises it for maintainers.
- **Hermes-lane PLAN.txt** (§9 docs consolidation) was not read, because it lives under `~/.hermes`.

## Next steps

1. Push `staging/observer-hooks-doc-drift` to the fork as `staged/observer-hooks-doc-drift`. OD-0 is resolved by that rename. Use `--no-follow-tags`, quote the refspec, and run an `ls-remote` collision check first. Owner action; not run here.
2. A blind exact-head verifier, a different worker, re-reads `9225807160` with the raw diff, the repo and the D2 oracle, and sets the QA class. This is P10.
3. Copy `STAGING.md`, `PR_BODY.md` (as `body.md`), the patch, both `-03` receipts, DOCS-CHECKS `-04` and `-05`, and F14 `-01` to `claude/ledger:factory/xf/staging/observer-hooks-doc-drift/` and `factory/xf/receipts/`, then freeze the cited receipts. This is P8.
4. Fold into the next docs bundle in kvnloo/hermes-agent#404 order, behind the 39 existing rows, with no separate slot.
5. Rebase triggers: #123978 (or #101688 / #70690) merging. Add `cost` (or `rate_limit`) and the Codex app-server `None` case to the list, then re-run F13. A merge of one of the seven page editors is not a rebase trigger: they apply cleanly in both orders. Just re-run merge-tree.
6. Optionally, after #123978 lands or closes, add the same three fields to the `hooks.md` plugin-hook table row as a follow-up, plus the informational-matrix items after a source read of each.

## Origin action (owner only)

`gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/observer-hooks-doc-drift --base main --title "docs(observer-hooks): list first_chunk_at, context_length and moa_references" --body-file PR_BODY.md`. This was NOT run. Or fold the commit into the next docs bundle PR per #404.

## History

- 2026-10-01T08:50Z | CANDIDATE | builder (Claude Code, Opus 5.5) | Selection entry read. Premise re-checked on `572e4f4fad`: 0 doc hits, emitter at `:83-97`, no competing PR.
- 2026-10-01T08:58Z | EVIDENCED | builder | F13/r20261001-01 KEEP and DOCS-CHECKS/r20261001-01 KEEP on `d663ec667d`.
- 2026-10-01T09:05Z | EVIDENCED | builder | `first_chunk_at` bullet corrected for the partial-stream stub case and the commit amended before publication to `f47410f2ac`. Superseding `-02` receipts: KEEP.
- 2026-10-01T09:09Z | STAGED | builder | Local branch created. Freshness re-check on `234badf401` clean. Worktree removed.
- phase 3 | VERIFYING -> CHANGES_REQUIRED | phase-3 verifier | accept=false on `f47410f2ac`, 5 problems:
  - the TTFB sentence is wrong after a retry;
  - the Evidence table quoted 7.95 s from the superseded `-01` receipt (`-02` records 12.52 s);
  - the #123978 entry was incomplete (it changes this emitter and adds a Codex app-server emitter);
  - How-to-Test step 1 missed the Correlation IDs table;
  - P5 recorded GREEN 1/1 where FACTORY §11.1 requires 3/3.
- 2026-10-01T11:20Z | STAGED | stfix round 1 (Claude Code, Opus 5.5) | All 5 fixed:
  1. Rebuilt on main `aea969677c` as `9225807160`. The `first_chunk_at` bullet now carries the retry caveat, and the commit message says the same. The caveat is proved by source citations and by a runtime probe with a negative control (DOCS-CHECKS/r20261001-03). The PR body explains it.
  2. The Evidence table now quotes the new receipt's own numbers (F13/r20261001-03: 3 reps, 2,089 files, 35.79 s).
  3. #123978 is recorded in full (11 files, `cost=` on this emitter, the Codex app-server emitter, a measured F13 interaction, the rebase rule), plus #101688 and #70690 as the same class. The PR body says how the two PRs interact.
  4. PR body step 1 now names the Correlation IDs table (`api_call_count`).
  5. P5 GREEN is 3/3 via the checker's new `--reps 3`.

  Also: the F13 checker writes portable command strings, and the four superseded receipts had their local paths redacted (hashes before and after are recorded). The fork branch name is now `staged/observer-hooks-doc-drift` (OD-0 resolved by the rename). Main re-checked on `e8c97320ac`: clean. Local branch forced `f47410f2ac` -> `9225807160`. Worktree and test home removed; no stash, no push, no GitHub writes.
- round-1 re-verify | STAGED (manifest fix requested) | round-1 re-verifier | Commit and PR body need no change. 2 minor manifest problems:
  - MANIFEST INCOMPLETE: #113174, #121005 and #124310 also edit `observer-hooks.md` and weren't recorded (its sweep covered 140 open PRs from 6 searches). All apply cleanly on top of `9225807160`, and none documents the three fields.
  - WORDING: P2 said "#53007 and #123978 are adjacent with no file overlap". #53007 edits the same file; only #123978 has no file overlap.
- 2026-10-01T12:25Z | STAGED | stfix round 2 (Claude Code, Opus 5.5) | Both fixed, manifest only. Commit `9225807160`, patch and PR body unchanged; local branch not moved.
  1. Instead of extending the sample, read the file list of every open upstream PR (33,478 at 11:45Z, plus a 21-PR top-up at 12:16Z). It found 7 real editors of the page. That's the verifier's three plus #53007, and three nobody had recorded: #108924, #119347 and #125192. It also found 2 GitHub-listed non-edits (#120375 snapshot, #121502 stale base). Each real editor's hunk applies cleanly on top of this commit and in the reverse order. None documents the three fields, and none changes the emitter. The one pair conflict each (#108924/#113174, #119347/#121005) is between other PRs and fails on plain main too. All recorded in `[upstream].adjacent_open_prs`, `listed_not_page_edits`, the Route section and new receipt DOCS-CHECKS/r20261001-04 (frozen, sha256 `fc82032e…`).
  2. P2 now reads "same file, no hunk conflict" for the page editors (#53007 at offset 15), with "no file overlap" kept only for #123978.

  Also re-measured: main `040b6df2c4` (8 commits after base, no `invalidate_on` path changed, page blob unchanged, merge-tree clean, tree `36e87a74ee`); 18/18 docs bundles clean; 0 of 71 local heads touch the page. Promotion form unchanged (docs): no external owner. OD-0 stays resolved by the `staged/` rename. Sweep tools are in `tools/open_pr_sweep/`. No worktree was needed (temporary index files only); PR heads were fetched into scratch `h.git` with no ref created; no stash, no push, no GitHub writes.
- 2026-10-01T18:29Z | STAGED | Wave 0 F14 guard run (Claude Code, Opus 5.5) | **F14 EQUAL** (F14/r20261001-01, frozen, sha256 `ea3f200d…`). `9225807160` cherry-picked cleanly onto upstream main `34f8ec3b40`, with the original author kept and Kevin Rajan as committer. The result is arm `be5c73d230`: same patch-id, tree `ac1a4ea154`, the same tree `git merge-tree` gives. New ref `refs/xf/w0/observer-hooks-doc-drift`. Two runs of the 40-id F14 set (rev 1, set sha256 `aba79fe8f09d…`): each 36 PASS / 4 FAIL, identical verdict, marker and fingerprint to `baseline-34f8ec3b40` on every id. r1 = r2, flaky list empty, 0 blocked execs. The 4 FAILs are the baseline's own (cache_estimator, notice_delivery, context_cap, readtool lying_extension). `guards.F14` changed from N_A to EQUAL. P5 stays PASS: RED with marker, GREEN 3/3, sabotage (1 hunk, no unpinned lines), ADJACENT identical and flaky=false were already recorded with receipts. Side observation (OBSERVED, not gated; P1 not changed): 0 `invalidate_on` files changed and 0 diff lines name `post_api_request` between `aea969677c` and `34f8ec3b40` (38 commits). That is a text check, not the F13 freshness re-run. Commit, patch, PR body and the local branch are unchanged. Worktree removed and pruned. `refs/heads/main` unchanged; no stash, no push, no GitHub writes.
- 2026-10-01T18:38Z | STAGED | polish round (Claude Code, Opus 5.5) | Round-4 advisories for this item: none (empty list). Upstream-facing text re-read against the source on main `34f8ec3b40`:
  1. `PR_BODY.md`: every cited span (14) still matches and every referenced PR and issue is in the stated state. #100425 and #115819 touched no `website/` file, so "the guide's list wasn't updated either time" holds. Two edits: line references are now pinned to `main` at `34f8ec3b40` (upstream main had already moved to `363e9d5f0a`, where the cited `codex_runtime.py:1090-1096` sits at `:1115-1121`), and the AI-assistance line now names both the docs change and the description. No owner-review claim. Template check: "For New Skills" is correctly deleted.
  2. Commit message: accurate, no fork jargon, AI co-author trailer present. Unchanged, so no `-v2` ref was created; the branch stays `9225807160`.
  3. Freshness (DOCS-CHECKS/r20261001-05, frozen, sha256 `19bbef44…`): merge-tree clean on `34f8ec3b40` (tree `ac1a4ea154`, same as the F14 arm); 38 commits since base, 0 of 11 `invalidate_on` files changed, no new emitter or kwarg, page blob unchanged, 0 workflow files changed. `[base].freshness_recheck`, `[merge_check]`, the Branch line, the member-branches row and P1/P7 now cite `34f8ec3b40`. Open-PR top-up: 288 PRs created since 12:16Z (267 open), 6 truncated lists re-read over REST, 0 touch the page or the emitter; the 10 recorded open PRs keep their heads.
  4. Privacy scan of STAGING.md, PR_BODY.md, the patch, receipts/ and tools/: clean (only the `<run>/home` placeholder and a fake test key in the probe). No bytecode. Patch still byte-identical to `git format-patch -1 9225807160`. TOML front matter parses.

  Gates unchanged: P8, P10 and P12 stay PENDING, so status stays STAGED. No worktree was needed (read-only git and gh); no ref created or moved, no stash, no push, no GitHub writes.
