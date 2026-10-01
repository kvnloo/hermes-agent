+++
xf_staging = 1
id = "compaction-hook-salvage"
version = 4               # round-3 rebuild after the round-2 re-verifier (6 problems on 111f361fb0); local branch forced to the new commit as instructed, nothing was ever pushed
title = "One observer compaction hook: A/B the open carriers per the #64231 SALVAGE verdict"
branch = "staging/compaction-hook-salvage"
branch_physical = "local ref staging/compaction-hook-salvage in the scratch mirror h.git, not pushed. It publishes to kvnloo/hermes-agent as staged/compaction-hook-salvage: the fork's legacy refs/heads/staging blocks staging/*, so OD-0 is resolved by this rename (ls-remote 2026-10-01T17:14:55Z: no refs/heads/staged/compaction-hook-salvage on the fork; five other staged/* branches and the legacy refs/heads/staging exist)"
branch_sha = "1ab964166a125b64ea4d5c05e7f5813bffd7bb2d"
status = "EVIDENCED"      # round-3 fixes done and re-proved; P5 PENDING (F14 not run; E12 INFRA under strict S16); push (owner), receipt freeze (P8) and blind re-verify (P10) pending
route = "salvage-row"
promotion_form = "salvage-support"   # unchanged: seven external PRs own a compaction hook; our part is a Co-authored-by fold-in
feature = "compaction-lifecycle-hooks"
invariant = "A plugin subscribed to the local compaction observer is told exactly once per committed local compaction, after the compacted transcript is durable (and, for a manual /compress, after its host commits), and only after the attempt has released its commit fence and the session's compression lease (so a slow plugin cannot make an interrupt wait behind it: the #118120 hazard). It is never told about an attempt that did not commit (a failed summary that aborts under compression.abort_on_summary_failure=true, the commit site's would-grow refusal, a SessionDB write failure, a discarded manual compress), and it can neither break nor change the compaction. Not a contract case, probe only: a failed summary under the default abort_on_summary_failure=false commits the deterministic fallback, and that commit is announced."

[base]
repo = "NousResearch/hermes-agent"
sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
fetched_at = "2026-10-01T16:10:39Z (main commit time 15:56:40Z)"
previous_base = "a3b56cac95488242856b6fb1f121842a38c3e391 (round-2 staging commit 111f361fb0; 17 commits before 44a1ce9724, none touching an invalidate_on path)"
selection_base = "e496ccc7d7"
first_built_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (round-0 staging commit b3b8d73999)"
invalidate_on = ["agent/conversation_compression.py", "agent/context_compressor.py", "hermes_cli/plugins.py", "hermes_cli/plugins_dispatch.py", "hermes_cli/lifecycle.py", "agent/conversation_compression_manual.py", "hermes_state_messages.py", "hermes_state_compression.py", "hermes_cli/hooks.py", "website/docs/user-guide/features/hooks.md", "agent/agent_init.py", "agent/compression_facade.py"]
drift_note = "None of the invalidate_on paths changed from e496ccc7d7 or a3b56cac95 to 44a1ce9724. agent/compression_facade.py joins invalidate_on in round 3 because the test now passes an explicit CompressionCommitFence through AIAgent._compress_context."
freshness_recheck = { main = "07ab19b0a399f33bd760852e0b0588d07efe8c22", checked_at = "2026-10-01T17:15:12Z", commits_since_base = 7, invalidate_on_changed = false, merge_tree_clean = true, merge_tree = "0866f21271", foldin_merge_tree_clean = true }

[upstream]
issues = ["NousResearch/hermes-agent#64231", "NousResearch/hermes-agent#118382", "NousResearch/hermes-agent#8643", "NousResearch/hermes-agent#93389", "NousResearch/hermes-agent#125384", "NousResearch/hermes-agent#119317", "NousResearch/hermes-agent#118120"]
eval_prs = []
carrier = { pr = 53806, author = "ledfoot631", head = "6067388d0c", compression_commit = "e560abd758", form = "start-side hook ported + Co-authored-by fold-in. The port deviates from e560abd758 in four disclosed ways: (1) its agent/agent_init.py and hermes_cli/hooks.py hunks and test hunk are left out (and the 6067388d0c resume-hook commit); (2) the pre_context_compression call sits in _run_summary_phase, because main moved the summarizer call out of compress_context, still after the memory providers' pre-compress step and right before the summarizer; (3) task_id is passed into _run_summary_phase so that call's payload keys are e560abd758's; (4) the call lives in the new sibling agent/conversation_compression_observer.py and dispatches through hermes_cli.lifecycle.invoke_hook (first-party observers, then plugins) instead of e560abd758's hermes_cli.plugins.invoke_hook. The fold-in replaces the carrier's post-commit on_session_start(boundary_reason='compression') call with on_compression_complete." }
competitors = [
  { pr = 93391, author = "clomp42", head = "9da3734b8e", result = "0 of 7 pass under its own hook name: pre_compression fires before the summarizer on every attempt (start-side seam, same as #53806's pre hook)" },
  { pr = 118847, author = "Baophan00", head = "222e3e26c3", result = "1 of 7 pass: post_compaction fires inside ContextCompressor.compress() before the commit, so it also fires for the would-grow refusal, failed SessionDB writes and a discarded manual compress; silent only when the summary aborts; session_id is the pre-rotation id" },
  { pr = 119347, author = "fangliquanflq", head = "4a527fc35d", result = "not materialized: transform (transform_compaction_input), 3 semantic conflict hunks at the #61932 pruned-copy seam; excluded from the observer slot (#120582 risk)" },
  { pr = 125881, author = "pstarkgit", head = "d3fdffcf82", result = "1 of 7 pass: pre_compression_commit is a fail-closed admission gate (a non-allow subscriber blocks the compaction), a different control-point contract; merges clean" },
  { pr = 4123, author = "GratefulDave", head = "16c60cd623", result = "not run: pre_compact before compressor.compress and post_compact at the end of compress_context, payload session_id + project_dir; 37,736 commits behind main 44a1ce9724, conflicts in agent/conversation_compression.py, hermes_cli/plugins.py, run_agent.py" },
  { pr = 7150, author = "Tauriqbarron", head = "f823aebeb2", result = "not run: adds pre_compress/post_compress to VALID_HOOKS with no call site in its diff; its main change is a pre_tool_call redirect (get_pre_tool_call_intercept); 42,445 commits behind" },
]
overlapping_open = [
  { pr = 127058, author = "Finn763", head = "f306319fe7", for_issue = 118120, note = "OPEN, MERGEABLE: delivers memory on_session_switch after finish_commit(), outside the commit fence. Edits _finish_compaction_boundary's signature/return and compress_context's boundary call and finally. Merge with the r5 fold-in: 1 conflict region (both append a post-fence delivery after commit_fence.finish_commit()), resolved by keeping both; the resolved tree passes the contract test and #127058's own test (MRG/mrg-r5). The staging commit (test only) merges clean with it" },
]
also_seen = [
  { pr = 59758, author = "gulivan", note = "CLOSED by teknium1 2026-07-22: hooks land with a real, named consumer" },
]
close_after = [93391, 118847, 4123]
stay_open = [125881, 119347, 7150]
stay_open_note = "#7150: keep open for its pre_tool_call redirect; its pre_compress/post_compress names have no call site and could be dropped from it once the carrier merges"
demand = { score = 5.24, source = "selection.json combined_score (maintainer-fit 6, evidence 6, impact 4)" }
maintainer_signal = "teknium1, #64231 verdict table (2026-08-13): SALVAGE #53806, rename to observer form on_compression_start (or keep pre_ only as a fail-closed control point); #8643 FOLD into the #53806 family. teknium1 closed #59758 for lacking a named consumer."

[[donors]]
sha = "e560abd758"
author = "Ádám Somorjai <ledfoot631@users.noreply.github.com>"
role = "carrier (compression commit of #53806): its pre_context_compression call and VALID_HOOKS entry are ported with the four disclosed deviations above; its post-commit on_session_start call is replaced by on_compression_complete. Also credited on the staging commit: the test pins the post-commit boundary call shape (session_id, old_session_id after the durable commit) that #53806 introduced"
trailer = "Co-authored-by: Ádám Somorjai <ledfoot631@users.noreply.github.com>"

[[donors]]
sha = "222e3e26c3"
author = "Baophan00 <109447498+Baophan00@users.noreply.github.com>"
role = "design reuse, no code: #118847 (written for #118382) is a post-compaction plugin observer carrying before/after token counts; the fold-in's tokens_before/tokens_after payload and the test's 0 < tokens_after < tokens_before assertion take that design. Credited on the fold-in and on the staging commit"
trailer = "Co-authored-by: Baophan00 <109447498+Baophan00@users.noreply.github.com>"

[[donors]]
sha = "9da3734b8e"
author = "clomp <277387657+clomp42@users.noreply.github.com>"
role = "design reuse, no code: #93391's pre_compression payload carries an in_place flag; the fold-in's in_place field and the test's in_place assertion take it. Credited on the fold-in and on the staging commit (GitHub noreply address of clomp42; the PR commit's author name is 'clomp')"
trailer = "Co-authored-by: clomp <277387657+clomp42@users.noreply.github.com>"

[[donors]]
sha = "f306319fe7"
author = "finn763 <165816600+finn763@users.noreply.github.com>"
role = "design reuse, no code: #127058 (for #118120) captures the boundary hook inside the commit and delivers it in compress_context's finally after finish_commit(); the fold-in delivers on_compression_complete at that point, and the test's fence/lease assertion pins it. Credited on the fold-in and on the staging commit (the #127058 commit's own author identity)"
trailer = "Co-authored-by: finn763 <165816600+finn763@users.noreply.github.com>"

[[donors]]
sha = "1ab964166a125b64ea4d5c05e7f5813bffd7bb2d"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "behaviour-contract test (staging commit, author) + fold-in: sibling module, post-fence delivery, payload, timeout bound, hooks-catalog row and hooks-CLI test payload; offered as patches/arm-foldin.patch (one production diff on main)"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[credit]
staging_commit_trailers = ["Co-authored-by: Ádám Somorjai <ledfoot631@users.noreply.github.com>", "Co-authored-by: Baophan00 <109447498+Baophan00@users.noreply.github.com>", "Co-authored-by: clomp <277387657+clomp42@users.noreply.github.com>", "Co-authored-by: finn763 <165816600+finn763@users.noreply.github.com>", "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"]
foldin_offer = "commit author Ádám Somorjai (#53806, carrier); Co-authored-by Kevin Rajan, Baophan00, clomp, finn763 (body.md lists the four trailers)"
thanked_not_trailered = [
  { who = "carlosrenatoy", why = "#118382 (the named consumer); no code or design reused" },
  { who = "nirvana6", why = "#118120 (the fence hazard trace); the report, not code or a design, so thanked in body.md rather than trailered" },
]
not_credited = [
  { pr = 125881, author = "pstarkgit", why = "nothing reused: its pre_compression_commit is a fail-closed admission gate with a state{counts} payload; neither the fail-closed semantics nor that payload is taken" },
  { pr = 119347, author = "fangliquanflq", why = "nothing reused: a summarizer-input transform; not materialized" },
  { pr = 4123, author = "GratefulDave", why = "pre_compact/post_compact names, placement and payload not used; not run" },
  { pr = 7150, author = "Tauriqbarron", why = "not used; not run" },
]
rule = "credit every contributor whose idea or code is used. close_after names #93391 and #118847, whose designs the fold-in reuses, so both are credited rather than closed uncredited; #4123 is closed as superseded and nothing of it is used"

[ownership]
searched_at = "2026-10-01T08:50Z-09:20Z; re-checked 11:20Z, 13:41Z and 16:19Z (carrier and competitor heads unchanged, all OPEN; #127058 OPEN at f306319fe7; #118382 and #118120 last comments 2026-09-22 by Sahilvishnaliya)"
queries = ["compression hook (open)", "compaction hook (open)", "on_compression", "118382", "compaction (open, sorted by update)", "compression hook (merged)", "compaction hook (closed)", "on_compression_complete OR on_compression_start OR post_compaction OR pre_compaction", "author:Sahilvishnaliya hook", "compaction hook created:>=2026-10-01", "compression hook created:>=2026-10-01", "commit fence hook (open)", "118120"]
open_external = [53806, 93391, 118847, 119347, 125881, 4123, 7150]
overlapping_open = [127058]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
issue_claims = "Sahilvishnaliya commented 'I'm working on this — planning a PR' on both #118382 and #118120 (2026-09-22); no PR from them found. #127058 (Finn763) says 'Closes #118120'"
verdict = "EXTERNAL -> salvage-support; our part is a Co-authored-by fold-in. #127058 is a different defect on the same code region (not a competitor); the fold-in composes with it"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "F05/f05-r5", path = "receipts/F05-f05-r5.json", sha256 = "835d89112f7fea4f717b94c59a915cae713e68b14624d2415d9779a21379f1e2" },
  { id = "E12/e12-r5", path = "receipts/E12-e12-r5.json", sha256 = "e1af3d5878af4c6c24342f687faf8eef7ec5a316bccb41522bbe1dd88466313a" },
  { id = "MRG/mrg-r5", path = "receipts/MRG-mrg-r5.json", sha256 = "8d4bc5a83284c22a70318d408160a060c9169335562e385f048a487ca5123505" },
  { id = "PROOF/r5", path = "receipts/PROOF-r5.json", sha256 = "32c6e58a51598a79287cdc2cec45cbf201cbd1d8427df87f3c37e9ce699874ec" },
  { id = "OWN/own-r5", path = "receipts/OWN-own-r5.json", sha256 = "37530d14d7325f0e6276e202a1f6cf1df4352de7b4d5b303c7c89b63a1113b63" },
  { id = "SANDBOX/guard-canary-r4", path = "receipts/SANDBOX-guard-canary-r4.json", sha256 = "6332c96ab8060d0868d63655416d34027c8402d33c8ddbdfbb59e6310f20de08", note = "still current: the r5 runs use the same guard file; env.host redacted in round 3" }
]
superseded = [
  { id = "F05/f05-r4", path = "receipts/F05-f05-r4.json", sha256 = "5dcb5ce32bda57504ea388cc338c17242646ccd01eb930ba23de39ed30a29306", verdict = "KEEP as issued; superseded by F05/f05-r5 (round-3 test adds the fence/lease clause; the r4 fold-in placement fails it); env.host redacted in round 3" },
  { id = "E12/e12-r4", path = "receipts/E12-e12-r4.json", sha256 = "6e525ab11d74e13502d5d3484d54829e6b3589c9c8124f90a1d6212a8ac19b07", verdict = "INFRA (strict S16); superseded by E12/e12-r5; env.host redacted in round 3" },
  { id = "OWN/own-r4", path = "receipts/OWN-own-r4.json", sha256 = "b5a1c7bfc635c639aedb15313154950b52494f61bf6825f880052de687c545c0", verdict = "n/a (fairness), validity INFRA; superseded by OWN/own-r5; env.host redacted in round 3" },
  { id = "PROOF/r4", path = "receipts/PROOF-r4.json", sha256 = "0aa04fec2ef67f34d092ce6b8cc0a2feec09b98350ab6bc4982fa1a3b735725e", verdict = "INFRA; superseded by PROOF/r5; env.host redacted in round 3" },
  { id = "F05/f05-r3", path = "receipts/F05-f05-r3.json", sha256 = "c05c048ddee2c5027d85c0438dbb45c7f6d0d32cd3e9a7f4d6a7ea8fa56e3519", verdict = "INFRA (strict S16 after the round-2 re-label); env.host redacted in round 3" },
  { id = "E12/e12-r3", path = "receipts/E12-e12-r3.json", sha256 = "e12b85630543cf849759aed34a8221732eb350bbc4c9c7add38fe1103522a023", verdict = "INFRA (strict S16; exception never accepted, one premise false); env.host redacted in round 3" },
  { id = "OWN/own-r3", path = "receipts/OWN-own-r3.json", sha256 = "7c119d0035ddb3b62b509c7b6007c2e0bb2ad22899d9d3201bc74a6f75f9aee9", verdict = "n/a (fairness); validity INFRA under strict S16; env.host redacted in round 3" },
  { id = "PROOF/r3", path = "receipts/PROOF-r3.json", sha256 = "28b613c322a58117d3e168d9ef86d86ccaa6eeafd801b6cd941bd8c31aed12fb", verdict = "INFRA; env.host redacted in round 3" },
  { id = "SANDBOX/guard-canary-r3", path = "receipts/SANDBOX-guard-canary-r3.json", sha256 = "7452a25f3e7f4f1b61a1f4b7be720cf9ebd88436a79cf21e5dfd9d953e546361", verdict = "PASS for its 5 cases; its prewarm suppression is retired; env.host redacted in round 3" },
  { id = "F05/f05-r1", path = "receipts/F05-f05-r1.json", sha256 = "85625ea19f2c27ebefaebef16d0f4249d0dcf4736c39c55ce3ae1adceb6adb06", verdict = "INFRA (S16)" },
  { id = "F05/f05-r2", path = "receipts/F05-f05-r2.json", sha256 = "f7044149577e55ff6d9cff55fa26b2306c68bf3b3bfbbdbd20f48a4f1d4b951b", verdict = "INFRA (S16)" },
  { id = "E12/e12-r2", path = "receipts/E12-e12-r2.json", sha256 = "9752f0f59ab600a36caded81b5a05d9254d1ce78188691f83bc49589d6226d3a", verdict = "INFRA (S16, unattributable)" },
  { id = "PROOF/r2", path = "receipts/PROOF-r2.json", sha256 = "b0aee1db3a713f6546d5d06e674f69c487e9b11024a32405205f549c60f4de0a", verdict = "INFRA" },
  { id = "OWN/own-r1", path = "receipts/OWN-own-r1.json", sha256 = "984100f78f4a693daf397867202447dd51efbbeb53ead7717f2028d33aad72de", verdict = "INFRA (S16, unattributable)" },
  { id = "SANDBOX/guard-canary", path = "receipts/SANDBOX-guard-canary.json", sha256 = "509e5bca29510c40c68ed7d9b571115e8026746bc880311b3d1b0c0c1f33f65c", verdict = "PASS (connect() only; DNS not guarded)" }
]
red = { test = "tests/agent/test_compaction_observer_hook_contract.py::test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred]", main = "44a1ce9724", marker = "AssertionError: on_compression_complete fired 0 times", reps = "3/3 (4 passed / 3 failed each)", receipt = "F05/f05-r5" }
green = { arm = "foldin-r5 6a2f717e4c", reps = "3/3 (7 passed / 0 failed each)", also = "foldin-ref-r5 3/3, foldin-x127058-r5 3/3", receipt = "F05/f05-r5" }
negative_control = { mutation = "observer dispatched just before _commit_compaction", result = "RED: 6 of 7 fail, 3/3 reps", also = "in-fence (staged call run right after staging, inside the fence with the lease held): 2 of 7 fail; round-2 offer re-applied (r4-offer-r5): 2 of 7 fail; manual deferral bypassed: 2 of 7 fail. Per-hunk sabotage: staging call removed 3 of 7 fail, finally call removed 2 of 7 fail, tokens_before dropped 3 of 7 fail, tokens_after dropped 3 of 7 fail, deferred chain removed 1 of 7 fail. Unpinned (0 of 7 fail): VALID_HOOKS entry, timeout bound, hooks-CLI payload + docs row, start-side call", receipt = "F05/f05-r5" }
adjacent = { files = 20, base = "354 passed / 3 failed (only the new contract test's 3 fires-once cases) / 2 skipped", arm = "357 / 0 / 2 skipped on foldin and on foldin-x127058", identical_outside_new_test = true, s16 = "348 blocked DNS lookups per arm in this cell (340 on MainThread from 8 sibling test files, 8 on openrouter-prewarm), identical per file on base and both arms: INFRA under strict S16", receipt = "E12/e12-r5" }
guards = { replay_gates = "11/11 PASS on base, foldin and foldin-x127058; verdict maps equal; 0 blocked attempts", ab_checkpoint_preflight = "local compress-call counts equal to base (capture 0/0 cli and gateway, restore 0, over_threshold 0 then 1); 0 blocked attempts", test_region_scoping = "ALL PASS on all three (2 blocked DNS lookups per arm from the eval's own agent init: INFRA under strict S16)", f14 = "NOT RUN: these are 3 of F14's harnesses, so P5's F14-equal requirement is not met", receipt = "E12/e12-r5" }
merge_127058 = { cells = 6, foldin_x127058 = "contract 7 passed / 0 failed; #127058's own test 1/0; its 4 named neighbour files 92/0", s5x127058 = "contract 4/3 (no hook, as expected); #127058's own test 1/0; neighbours 92/0", merge_tree = "foldin-r5 + #127058 head: 1 conflict region (both append after commit_fence.finish_commit()); staging commit + #127058: clean", s16 = "4 of 6 cells INFRA under strict S16 (#127058's test: 4, the neighbours: 230 blocked DNS lookups per arm, identical); the contract cells: 0", receipt = "MRG/mrg-r5" }
egress = { F05 = "91 cells: 0 connect, 0 dns from any thread, 0 INFRA", E12 = "12 cells: 0 connect; replay_gates and ab_checkpoint_preflight 0 dns; adjacent 348 and test_region_scoping 2 blocked DNS lookups per arm, identical on base and arms, all in upstream code: 6 of 12 cells INFRA under strict S16 (experiment INFRA); PASS only under the recorded, not accepted S16 exception", OWN = "10 cells: 8 INFRA under strict S16 (rotation_state and #53806's ported tests, which do not pin the window); #118847 and #125881 cells 0", MRG = "6 cells: 4 INFRA under strict S16 (upstream tests); the two contract cells 0", guard = "the r4 guard file, unchanged (sha256 3a808849b4...); SANDBOX/guard-canary-r4 remains its proof", receipts = "F05/f05-r5, E12/e12-r5, OWN/own-r5, MRG/mrg-r5" }
own = { c93391 = "test_compression_rotation_state.py 43/0 (base 40/0)", c118847 = "test_post_compaction_hook.py 7/0 (mocks the seam)", c125881 = "test_context_governance.py 9/0", counts = "passed/failed", c53806 = "3 tests ported from e560abd758: verbatim 0/3 on base, hand-port and fold-in; drift-adapted (2 tests) 2/0 on the hand-port, 1/1 on the fold-in (boundary test fails by design), 0/2 on base", receipt = "OWN/own-r5" }
quantitative = []
cache_read_ratio = { status = "N_A", why = "the observer fires after the sanctioned compaction cache break; compacted messages + system prompt asserted byte-identical with and without subscribers" }
route_scope = "local-compressor"
not_tested = ["native and codex_app_server compaction (structural only)", "session_db=None agents", "micro-compaction / proactive prune", "real summarizer", "per-host manual /compress handlers", "shell hooks (hooks-CLI payload added, no shell hook run)", "hung subscriber (the hook_callback_timeout bound is unpinned: sab-h6 stays green)", "an actual interrupt issued while the observer runs (the test asserts the fence state hard_interrupt waits on)", "fallback-summary commit as a contract case (probe only)", "#53806's start-side pre_context_compression (no contract case; no docs row or hooks-CLI payload; rename left to the author/maintainers)", "#53806's own tests pass only with two drift edits on current main, and its agent-init test needs the left-out agent_init hunk (OWN/own-r5)", "F14 standing set (only 3 of its harnesses ran)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-compaction-hook-salvage", commit = "" }

[gates]
P1 = "PASS"
P2 = "PASS"
P3 = "PASS"      # round 3: new behaviour in a sibling (agent/conversation_compression_observer.py, 82 lines); the facade gets +16/-1 call plumbing (4,579 -> 4,594 lines)
P4 = "PASS"
P5 = "PENDING"   # RED/GREEN/NEG/sabotage clean in F05 r5; F14 was not run (FACTORY: P5 needs F14 guards equal), and E12 r5 is INFRA under strict S16 (upstream DNS lookups)
P6 = "N_A"
P7 = "PENDING"
P8 = "PENDING"
P9 = "PENDING"
P10 = "PENDING"
P11 = "RECORDED"
P12 = "PENDING"

[verification]
verifier = ""
provenance = "self"
exact_head = ""
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
round0 = "phase-3 verifier on 8c834af1e4: accept=false, manifest_accurate=false (9 problems; see 'Round-1 fixes')"
round1 = "re-verifier on de819a7d06: 7 problems; see 'Round-2 fixes'"
round2 = "re-verifier on 111f361fb0: accept=false, 6 problems (missed #118120/#127058 overlap, five-vs-seven undercount and no disposition for #4123/#7150, P3 sibling not built, undisclosed plugins-vs-lifecycle dispatcher drift, P5 pending, TITLE line); see 'Round-3 fixes'"

[merge_check]
main_sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
checked_at = "on 44a1ce9724 when the branch was forced (round 3, 2026-10-01T17:15:12Z); re-checked the same minute on main 07ab19b0a3 (7 commits later, no invalidate_on path touched): clean"
clean = true
tree = "29740a06f7 (the staging commit's own tree, on 44a1ce9724); 0866f21271 merged with 07ab19b0a3"
recheck = "git merge-tree --write-tree main staging/compaction-hook-salvage"
foldin_applies = "2026-10-01T17:14Z (tools/chs_final_checks_r5.sh, raw/final-checks-r5.txt): patches/staging-compaction-hook-salvage.patch passes git apply --check on 44a1ce9724; the diff inlined in body.md is byte-identical to patches/arm-foldin.patch, applies with git apply on 1ab964166a, and leaves no difference against foldin-r5; foldin-r5 merges clean with main 07ab19b0a3 (tree 4df2fdc3df)"
with_127058 = "staging commit + #127058 head f306319fe7: merge-tree clean. foldin-r5 + #127058: 1 conflict region in agent/conversation_compression.py (both append after commit_fence.finish_commit()); resolution in patches/foldin-x127058-delta.patch; tests in MRG/mrg-r5"

[push]
fork_branch = "staged/compaction-hook-salvage"
no_follow_tags = true
workflow_push_matches = 0   # tools/chs_workflow_scan_r5.py on 1ab964166a: 52 workflow files, 41 without a push trigger, 10 whose push branches do not match staged/compaction-hook-salvage, 1 tags-only (raw/workflow-scan-r5.json)
pushed_at = ""

[body]
path = "body.md"
kind = "wave-row"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
self_service_basis = "body.md links the test commit on kvnloo/hermes-agent staged/compaction-hook-salvage (valid once the owner pushes it, before posting) and carries the combined production diff inline in a collapsed block, with its trailers; nothing is offered 'on request'"
jargon_lint = "PASS (self-check: no envelope/lane/E##/F##/arm/round names in body.md)"
privacy_scan = "PASS (synthetic fixtures only; no session ids, home paths, host names or message text; contributor addresses are GitHub noreply forms)"
no_title_line = "body.md has no TITLE line: the origin action is a comment, which has no title"

[queue]
board = "none. kvnloo/hermes-agent#402 (fork salvage board) was closed COMPLETED 2026-10-01T07:32Z: its 9 rows were posted upstream as NousResearch/hermes-agent#130139, and none of them is about compaction. This item is not a kvnloo/hermes-agent#404 row either: that queue lists 39 staged PR branches, and this item opens no PR. The staged-branch tracking issues kvnloo/hermes-agent#407-#411 (all OPEN) are for other items"
position = "owner picks one: (a) one comment carrying body.md on the carrier thread NousResearch/hermes-agent#53806 (preferred: one concrete delta per thread), or (b) one delta-row comment on NousResearch/hermes-agent#130139. Never a new wave issue"
spray_check = "re-checked 2026-10-01T16:20Z: kvnloo opened 5 upstream issues since 2026-09-30T13:00Z (#129760, #129761, #129963, #130139, #130140; 4 are wave tables, 2 of them posted 07:32Z today) and 4 PRs on 2026-10-01 (#129918, #129928, #130203, #130205); #130139 has 1 comment (kvnloo, 14:28Z, a parked-work audit update, not about compaction). Another wave-style post the same day is high spray risk: post (a) or (b) on a later day, not today"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# One observer compaction hook: A/B the open carriers per the #64231 SALVAGE verdict

**Promotion form:** salvage-support (route `salvage-row`, body kind `wave-row`). Unchanged in round 3: seven external PRs own a compaction hook (round 2 said five; #4123 and #7150 were listed in `open_external` but left out of the count and the disposition), and our part is a `Co-authored-by` fold-in. #127058 is an open PR on the same code region for a different defect (#118120); it is not a competitor, and the fold-in now composes with it. Nothing here is blocked on a design hold, so the item is neither HOLD nor a different form.

**Status:** EVIDENCED, version 4. Round 3 fixed the six problems the round-2 re-verifier listed (see "Round-3 fixes"). The staging commit was rebuilt on main `44a1ce9724` as `1ab964166a` (the fires-once case now also asserts that the observer runs after the commit fence and the session's compression lease are released; new message and a fourth trailer), and the local branch was forced to it. The offered fold-in was rebuilt: both dispatches moved into a sibling module, `on_compression_complete` is delivered after the fence is released (as #127058 does for the memory hook) and is timeout-bounded, and #53806's start-side call goes through `hermes_cli.lifecycle`. RED, GREEN, negative controls, sabotage, the three guards, 20 adjacent files, the carriers' own tests and the #127058 merge were re-run on that base. P5 is PENDING: F14 was not run (only 3 of its harnesses), and E12's adjacent and region-scoping cells carry upstream DNS lookups (INFRA under strict S16). Nothing is pushed. The receipt freeze (P8) and the blind exact-head verification (P10) have not happened.

## Links

- **Upstream verdict / RFC:** NousResearch/hermes-agent#64231. teknium1's batch-disposition table (2026-08-13) says of PR #53806: "SALVAGE … rename to observer form `on_compression_start` (or keep `pre_` only if it becomes a genuine control point with fail-closed semantics)". The same table folds #8643 into the #53806 family.
- **Named consumer:** NousResearch/hermes-agent#118382 (carlosrenatoy). There is no plugin signal at compaction, so providers infer it from a turn-count drop. A scoping correction in that thread says MemoryProvider already has `on_pre_compress` + `prefetch`, so the remaining gap is plain plugins.
- **Hazard on the same seam:** NousResearch/hermes-agent#118120 (nirvana6, OPEN, 2026-09-21): a memory-provider hook that blocks inside the compaction commit fence makes the session uninterruptible (the interrupt path waits on the fence lock; kill -9 required). NousResearch/hermes-agent#127058 (Finn763, OPEN, MERGEABLE, head `f306319fe7`, "Closes #118120") delivers memory `on_session_switch` after `finish_commit()`. It edits `_finish_compaction_boundary`'s signature and return, the `compress_context` boundary call and its `finally`.
- **Related asks:**
  - NousResearch/hermes-agent#93389 (the issue behind #93391; a named consumer for a start-side hook)
  - NousResearch/hermes-agent#125384 (compaction hook for preference auto-execution)
  - NousResearch/hermes-agent#119317 (the task-aware keep/drop issue behind #119347)
  - NousResearch/hermes-agent#8643 (`on_context_window_update`)
- **Speculative-hook precedent:** NousResearch/hermes-agent#59758 was closed by teknium1 on 2026-07-22: "hooks land with a real consumer, not ahead of one".
- **Fork boards:** kvnloo/hermes-agent#402 (salvage board) is closed. Its rows went upstream as NousResearch/hermes-agent#130139 (9 rows, none about compaction; 1 comment at 16:20Z, kvnloo's parked-work audit update, not about compaction). kvnloo/hermes-agent#403 became NousResearch/hermes-agent#130140 (close wave). kvnloo/hermes-agent#404 is the staged-PR queue (39 rows); this item is not a PR, so it gets no row there. The accepted staged branches' tracking issues are kvnloo/hermes-agent#407-#411 (all OPEN, other items). No kvnloo/hermes-agent issue or PR exists for this item, and no campaign thread has been created (OD-9).
- **Fork branch (after the owner's push):** https://github.com/kvnloo/hermes-agent/tree/staged/compaction-hook-salvage, one commit, https://github.com/kvnloo/hermes-agent/commit/1ab964166a125b64ea4d5c05e7f5813bffd7bb2d. body.md links both.

## Invariant

A plugin subscribed to the local compaction observer is told about a local compaction exactly once. The call comes after the compacted transcript is durable in state.db and, for a manual `/compress`, after its host commits. By then the attempt has released its commit fence and the session's durable compression lease, so a slow plugin cannot make an interrupt wait on the fence lock (#118120) or hold up the session's next compaction. The plugin is never told about an attempt that did not commit, and it can neither break nor change the compaction.

"Did not commit" means four distinct paths, each a case in the test:

- a failed summary that aborts under `compression.abort_on_summary_failure: true`;
- the commit site's would-grow refusal (the fallback summary would grow the transcript);
- a SessionDB write failure;
- a manual compress the host discards. Here the compacted rows *are* written to state.db; only the host's discard means the compaction did not commit for the host, and the case asserts both.

With the default `abort_on_summary_failure: false`, a failed summary does **not** abort: the compressor inserts its deterministic fallback summary and, on a realistic window, commits it. That is a committed compaction, and the observer correctly fires once. This is **probe-only, not a case in the committed test**: probe scenario `fallback_committed`, 61 messages in, payload tokens 75,000 → 30,580 on `foldin-r5` (public in `receipts/F05-f05-r5.json` → `fallback_commit_probe`).

**Real call path exercised:**

1. `AIAgent._compress_context` with an explicit `CompressionCommitFence` (direct path, as gateway hygiene calls it)
2. `agent.conversation_compression.compress_context`
3. `_run_summary_phase`: the real `ContextCompressor.compress`, with only `_generate_summary` replaced
4. `_commit_compaction`: the real `SessionDB.archive_and_compact` / `publish_compression_child`, with the anti-growth guard, inside `begin_commit()`
5. `_finish_compaction_boundary`
6. in the fold-in: `stage_compression_complete` right after the boundary, and the staged call in `compress_context`'s `finally`, after `lease.release()` and `finish_commit()`; for a manual compress, chained onto the pending context-engine notification and run by `finalize_context_engine_compression_notification`

Dispatch is the real `hermes_cli.lifecycle` → `PluginManager.invoke_hook` on a fresh manager. The seam is never mocked. In the fires-once case each fired event records `fence.commit_in_flight` (what `hard_interrupt` checks before it waits on the fence lock) and `db.get_compression_lock_holder(old_session_id)` (the durable lease the next compaction waits on); both must be clear. Agent init's model-metadata lookups are stubbed at their network boundary, as in round 2: `patch("agent.context_compressor.get_model_context_length", return_value=256_000)` pins the window, and `patch("agent.agent_init.fetch_model_metadata", return_value={})` makes the once-per-process `openrouter-prewarm` thread run a stub.

## Member branches

All refs live in the scratch mirror `h.git`. PR heads were fetched read-only to `refs/xf/pr/<n>` (round 3 added `refs/xf/pr/127058`). Round-3 arms are pinned at `refs/xf/arms/compaction-hook-salvage/<arm>-r5`, built by `tools/chs_build_arms_r5.py` on the staging commit `1ab964166a` (`raw/build-arms-r5.txt`). Their diffs against the staging commit are in `patches/arm-<arm>.patch`. Round-2 patches moved to `patches/r4/`, round-1 patches are in `patches/r3/`, round-0 patches in `patches/r2/`; older refs are kept unchanged.

| ref | sha | role | status vs main `44a1ce9724` |
|---|---|---|---|
| `refs/heads/staging/compaction-hook-salvage` | `1ab964166a` | **staging commit**: contract test only (+169), author Kevin Rajan, trailers for ledfoot631, Baophan00, clomp, finn763 | 1 commit on main; merge-tree clean; push-trigger scan of the 52 workflow files on this tree: 0 match `staged/compaction-hook-salvage` |
| `foldin-r5` | `6a2f717e4c` | **carrier start-side hook + fold-in**, the proposed final shape | vs staging commit: +115/-1 in agent/conversation_compression.py (+16/-1), agent/conversation_compression_observer.py (new, 82), hermes_cli/plugins.py (+11), hermes_cli/plugins_dispatch.py (+1), hermes_cli/hooks.py (+4), website/docs/user-guide/features/hooks.md (+1) (`patches/arm-foldin.patch`, inlined in body.md) |
| NousResearch/hermes-agent#53806 (`refs/xf/pr/53806`) | `6067388d0c` (compression commit `e560abd758`) | **carrier** (ledfoot631), named in the SALVAGE verdict | CONFLICTING in 11 files (agent/agent_init.py, agent/conversation_compression.py, agent/shell_hooks.py, gateway/slash_commands.py, hermes_cli/cli_commands_mixin.py, hermes_cli/hooks.py, hermes_cli/plugins.py + 4 test files); 33,698 commits behind. Hand-port arm `c53806-handport-r5` `809dcbbb49` (the r4 hand-port re-applied 3-way, same patch-id), used for the carrier's own-name rows and its own tests |
| NousResearch/hermes-agent#93391 | `9da3734b8e` | competitor (clomp42, `pre_compression`) | conflicts in 3 website docs files only; code + tests re-applied 3-way clean (`c93391-code-r5` `bc2e3a1ee8`, same patch-id as rounds 0-2) |
| NousResearch/hermes-agent#118847 | `222e3e26c3` | competitor (Baophan00, `post_compaction` for #118382) | CONFLICTING, 1 hunk in agent/context_compressor.py; hand-port re-applied (`c118847-handport-r5` `e5b6d4cfcf`, same patch-id) |
| NousResearch/hermes-agent#119347 | `4a527fc35d` | directive/transform variant (fangliquanflq); excluded from the observer slot (#120582 risk) | CONFLICTING, 3 semantic hunks at the #61932 pruned-copy seam; no safe port, not materialized |
| NousResearch/hermes-agent#125881 | `d3fdffcf82` | fail-closed policy-hook carrier (pstarkgit) | merge-tree clean; `c125881-merge-r5` `d2130c1220` (same patch-id) |
| NousResearch/hermes-agent#4123 | `16c60cd623` | competitor (GratefulDave, `pre_compact`/`post_compact`) | 37,736 commits behind; conflicts in agent/conversation_compression.py, hermes_cli/plugins.py, run_agent.py; not materialized, not run |
| NousResearch/hermes-agent#7150 | `f823aebeb2` | competitor in name only (Tauriqbarron, `pre_compress`/`post_compress` added to VALID_HOOKS with no call site; main change: a pre_tool_call redirect) | 42,445 commits behind; not materialized, not run |
| NousResearch/hermes-agent#127058 (`refs/xf/pr/127058`) | `f306319fe7` | overlapping open PR (Finn763, #118120): memory on_session_switch after the fence | MERGEABLE; 172 commits behind; staging commit + #127058: merge-tree clean; `foldin-x127058-r5` `3b474fe613` = foldin-r5 merged with it (1 conflict region, both deliveries kept; `patches/foldin-x127058-delta.patch`); `s5x127058-r5` = staging commit merged with it (baseline) |
| NousResearch/hermes-agent#122522 (`refs/pr/122522`) | `f596584b01` | not a member (adjacent summary_source=original work) | n/a |

- **Fold-in variants:** `foldin-ref-r5` `65f00040e7` (without the carrier's start-side hook, its VALID_HOOKS entry and the `task_id` plumbing), `r4-offer-r5` `cab44f0017` (round 2's combined diff, observer inside the commit fence, re-applied 3-way clean, same patch-id: the real-world in-fence control)
- **Negative controls:** `neg-prefire-r5` `a64815d629` (observer dispatched just before `_commit_compaction`), `neg-infence-r5` `bc6272c1c5` (the staged call run right after staging, inside the fence with the lease held), `neg-nodefer-r5` `4970204cde` (deferral bypassed: a manual compress fires in `compress_context`'s finally)
- **Per-hunk sabotage of the fold-in:** `sab-h1-stage-call` `80a8d96f11`, `sab-h2-finally-call` `c9439470ec`, `sab-h3-tokens-before` `de3483efbb`, `sab-h4-tokens-after` `50f142ab86`, `sab-h5-valid-hooks` `94492cfa5d`, `sab-h6-bounded` `9951799992`, `sab-h7-payload-and-docs` `38bf5828f0`, `sab-h8-start-call` `cc9303be63`, `sab-h9-deferred-chain` `e126a77a4b` (all `-r5`)

## First-slice status

**Committed.** One commit, `1ab964166a125b64ea4d5c05e7f5813bffd7bb2d`, on main `44a1ce9724`:

- Subject: `test(compression): pin the plugin observer contract at the local compaction boundary`
- Author: `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`; trailers `Co-authored-by` ledfoot631, Baophan00, clomp, finn763 (see [credit]) and the Claude Code attribution line.
- Diff: 1 file, +169. It is exported as `patches/staging-compaction-hook-salvage.patch` (`git format-patch -1`).
- The local branch `staging/compaction-hook-salvage` was forced from round 2's `111f361fb0` to this commit. The round-2 patch is kept at `patches/r4/`.
- Message changes in round 3: "Seven open PRs" (was "Several"); a new bullet for the fence/lease clause citing #118120 and #127058; "CompressionCommitFence" in the real-components sentence; #127058's delivery point in the design-credit sentence; the finn763 trailer.

`tests/agent/test_compaction_observer_hook_contract.py` holds 2 behaviour-contract tests with 7 parametrized cases:

- **`test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred]`** (runs with an explicit `CompressionCommitFence`, baseline and observed alike)
  - The observer fires exactly once.
  - When it runs, the session id it is handed already holds the compacted transcript in state.db.
  - When it runs, `fence.commit_in_flight` is false and `db.get_compression_lock_holder(old_session_id)` is `None` (new in round 3).
  - The payload carries `session_id` (current), `old_session_id`, `in_place`, and `0 < tokens_after < tokens_before`.
  - A manual compress fires only after `finalize(committed=True)`.
  - With a raising subscriber and a subscriber returning `{"action": "block"}` both registered, the compacted messages and the rebuilt system prompt match a no-subscriber run byte for byte.
- **`test_observer_is_silent_when_nothing_commits[summary_aborted|would_grow_refused|commit_failed|manual_discarded]`** (unchanged from round 2)
  - `summary_aborted`: `abort_on_summary_failure = True` and the summary returns None. Precondition: `_last_compress_aborted`.
  - `would_grow_refused`: the default config and the summary returns None. Precondition: `_last_compress_refused_would_grow`.
  - `commit_failed`: `archive_and_compact` raises.
  - Precondition for these three: the session id is unchanged and state.db's rows for it equal the rows before the attempt.
  - `manual_discarded`: the host finalizes `committed=False`, and a later `finalize(committed=True)` cannot revive the call. The case asserts `_durable_summary(db, agent.session_id)` instead of unchanged rows.

The hook name is the single constant `HOOK = "on_compression_complete"`. The production change is **not** on the staging branch. It is offered to the carrier as one production diff on main, `patches/arm-foldin.patch` (byte-identical to `git diff 1ab964166a foldin-r5`), which applies once the staging commit is in; body.md carries it inline in a collapsed block with its trailers. The minimal variant without the carrier's start-side hook is `patches/arm-foldin-ref.patch`.

The selection's contract lists `new_session_id` separately. Here `session_id` is the post-commit id, which is what `session_id` means in every shipped hook. `new_session_id` is not duplicated.

## Route and carrier choice

**Route: salvage-row.** Seven open external PRs add a plugin hook around context compaction: #53806, #93391, #118847, #119347, #125881, #4123 and #7150 (P2 → salvage). Our part is a `Co-authored-by` fold-in: the contract test, plus the sibling module, the post-fence delivery, the payload, the timeout bound, the docs row and the hooks-CLI payload.

**Carrier: #53806 (ledfoot631) + fold-in.** It is the only candidate whose post-commit hook fires at the right moment: its plugin `on_session_start(boundary_reason="compression")` runs after the durable commit and stays silent on uncommitted attempts. The verdict also names it.

It misses four things:

- It ignores the manual-host deferral: it fires before the host commits, and after a discard.
- It carries no `in_place` or token fields.
- Reusing `on_session_start` delivers compaction events to every existing session-start subscriber.
- It runs inside the commit fence with the session's compression lease held (the #118120 hazard; measured in round 3: the probe's fired events on `c53806-handport-r5` record `commit_fence_in_flight_at_fire = true`).

The fold-in fixes all four:

- `on_compression_complete` is staged in `compress_context` right after `_finish_compaction_boundary` (same condition as the context-engine notification) and run in `compress_context`'s `finally`, after `lease.release()` and `commit_fence.finish_commit()`: the delivery point #127058 uses for the memory hook. A manual compress chains the call onto the pending context-engine notification, so the host's `finalize(committed=True)` fires both and a discard fires neither.
- It names the hook `on_compression_complete` and adds the payload. The payload takes `tokens_before`/`tokens_after` from #118847's post-compaction design and `in_place` from #93391; the delivery point is #127058's. All three authors are credited (see [credit]).
- `on_compression_complete` joins `_HOOK_TIMEOUT_BOUNDED_HOOKS` (`plugins.hook_callback_timeout`, default 30s, fail-open), as `on_session_start`, the carrier's own post-commit hook, already is. With the post-fence delivery that means an interrupt never waits on a plugin, and the compaction worker waits at most the timeout per callback.
- It adds the hook to `VALID_HOOKS` with a comment, to the "Shipped plugin-hook catalog" table in `website/docs/user-guide/features/hooks.md`, and to `hermes_cli/hooks.py` `_DEFAULT_PAYLOADS`. `VALID_HOOKS` doubles as the shell-hook allow-list, so `hermes hooks test on_compression_complete` gets the runtime payload shape.

**Where the code lives (P3, round 3).** Both dispatches live in a new sibling, `agent/conversation_compression_observer.py` (82 lines): `notify_compression_start` (#53806's start-side call), `stage_compression_complete` and the private `_invoke_compression_complete`. The facade `agent/conversation_compression.py` (4,579 lines on main) gets +16/-1: two lazy imports and calls into the sibling, the `_compression_complete` local and its two-line delivery in the `finally`, and the `task_id` parameter of `_run_summary_phase` plus its call-site keyword. That follows AGENTS.md's facade rule ("New behaviour goes in a new or topical sibling — never appended to a facade"; "Siblings may import each other and late-import the facade inside functions") and the existing `conversation_compression_reply_anchor` call pattern in `compress_context`. Round 2's diff added +50/-12 to the facade.

**How the start-side port differs from #53806's compression commit (disclosed in body.md).**

- *Location.* #53806 calls `pre_context_compression` inside `compress_context`, right after the memory providers' `on_pre_compress` and right before `compressor.compress(...)`. Current main moved both of those into `_run_summary_phase`, so the call sits there, after `_pre_compress_memory_context` and right before the summarizer dispatch. Same relative order, different function.
- *Payload.* `task_id` is passed into `_run_summary_phase` (signature + call site), so the payload keys are #53806's: `session_id, task_id, conversation_history, approx_tokens, focus_topic, force, model, platform, conversation_id`.
- *Dispatcher (round 3, was undisclosed in round 2).* #53806 calls `hermes_cli.plugins.invoke_hook` directly. The port calls `hermes_cli.lifecycle.invoke_hook` from the sibling, which notifies first-party observers (`hermes_cli.observability`) and then plugins. On main `44a1ce9724`, 12 of the 13 files under `agent/` and `gateway/` that dispatch hooks import `hermes_cli.lifecycle`; the one exception is `gateway/run_agent_cache.py`. `hermes_cli.observability` handles neither compression hook today (`handles_hook` is false), so no first-party observer receives the transcript. The call stays unconditional, as #53806 wrote it (no `has_hook` guard), so #53806's own test, which patches `hermes_cli.plugins.invoke_hook`, still reads the call.
- *Left out.* The commit's `agent/agent_init.py` hunk (plugin `on_session_start` at agent init), its `hermes_cli/hooks.py` hunk (a `pre_context_compression` test payload) and its test hunk, plus the separate resume-hook commit `6067388d0c`.

**#53806's own tests (OWN r5).** Its compression commit adds three tests to `tests/run_agent/test_compression_boundary_hook.py`. Main moved that file to `tests/agent/`, where the hunk no longer applies, so they are ported verbatim into a factory-only file (`tools/chs_c53806_own_tests.py`) and with two marked drift edits (`tools/chs_c53806_own_tests_adapted.py`), and run on base, the hand-port and the fold-in.

| #53806 test (from e560abd758) | base (verbatim / adapted) | hand-port (verbatim / adapted) | fold-in (verbatim / adapted) | why |
|---|---|---|---|---|
| `test_plugin_on_session_start_called_on_agent_init` | FAIL / not run | FAIL / not run | FAIL / not run | needs the left-out `agent/agent_init.py` hunk; not adapted |
| `test_pre_context_compression_plugin_hook_fires_before_compress` | FAIL / FAIL | FAIL / PASS | FAIL / PASS | verbatim: main hands the hook the transcript with the store's row metadata (`_db_persisted`, `_row_id`, `message_uid`, `timestamp`, `_db_row_snapshot`), so `conversation_history == messages` fails while `session_id`, `task_id` and `approx_tokens` match. Adapted: compares role/content. On the fold-in the call goes through `hermes_cli.lifecycle`, which still calls the `hermes_cli.plugins.invoke_hook` the test patches |
| `test_plugin_on_session_start_called_with_compression_boundary` | FAIL / FAIL | FAIL / PASS | FAIL / FAIL | verbatim: a one-message compaction no longer commits on main, so there is no post-commit call. Adapted: 10 messages, as main's own boundary test uses. Fold-in: fails by design (the call is replaced by `on_compression_complete`) |

Totals (passed/failed): verbatim base 0/3, hand-port 0/3, fold-in 0/3; adapted base 0/2, hand-port 2/0, fold-in 1/1. These cells are INFRA under strict S16: like most upstream tests, the carrier's tests do not pin the context window, so they make blocked DNS lookups (20, 20, 20, 14, 7, 14). The `pre_context_compression` test passes on the hand-port and on the fold-in once the drift edit is applied, which shows the `task_id` plumbing and the lifecycle dispatch keep the carrier's payload.

**What the fold-in does not do.** It does not rename or test the start-side `pre_context_compression`. #118382 needs only the post-commit signal. Its name (#64231 asks for `on_compression_start`), its payload, its missing docs row and hooks-CLI payload, and whether it stays at all are maintainer decision (a). `foldin-ref-r5` shows the fold-in passes 7 of 7 without the start-side hook (and without the `task_id` plumbing).

**Disposition (body.md row).** Carrier #53806 + fold-in. Close #93391, #118847 and #4123 after it merges: #93391 and #118847 are credited on the fold-in because their designs are reused; #4123 adds `pre_compact`/`post_compact` on the same two seams and nothing of it is used. Keep #125881 and #119347 open: they are different contracts and compose with the observer. Keep #7150 open for its `pre_tool_call` redirect; its `pre_compress`/`post_compress` names have no call site and could be dropped from it. #127058 is not part of the row: it fixes #118120 and composes with the fold-in (MRG r5).

The table below is OBSERVED in **F05 r5** (main `44a1ce9724`, staging commit `1ab964166a`): every arm ran in the same run under the r4 egress guard, which suppresses nothing. The clause probe (`tools/chs_clause_probe_r5.py`, 9 scenarios per arm, explicit commit fence) supplies the timing, fire and fence/lease columns. "Own name" means the contract test with `HOOK` set to the carrier's hook name, 3 reps; every count reads "N of 7 cases pass". The `#53806 pre` row describes our port of that call (see the disclosure above), not #53806's head, which does not apply to main.

| carrier | merge | hook (own name) | fires relative to summary / commit | 4 committing scenarios (rotated, in-place, manual, fallback commit) | 5 non-committing scenarios (aborted summary, would-grow refusal, in-place write fail, rotation write fail, manual discard) | manual-host deferral | at fire: commit fence in flight / lease held | payload keys | contract, own name |
|---|---|---|---|---|---|---|---|---|---|
| main | n/a | none | never | 0/4 fire | silent (trivially) | n/a | n/a | n/a | 4 of 7 pass (RED) |
| #53806 post | hand-port | `on_session_start` + `boundary_reason="compression"` | after durable commit, inside the fence | fires once, 4/4 | 4/5 silent; fires on manual discard | ignored (fires before finalize) | yes / yes | session_id, old_session_id, boundary_reason, platform, model, context_length, conversation_id | 3 of 7 pass |
| #53806 pre (our port) | hand-port, call in `_run_summary_phase`, `task_id` passed in | `pre_context_compression` | before summary | fires once, 4/4 | 0/5 silent | ignored | no / yes | session_id, task_id, conversation_history, approx_tokens, focus_topic, force, model, platform, conversation_id | 0 of 7 pass (start-side by design) |
| #93391 | docs-only conflicts | `pre_compression` | before summary | fires once, 4/4 | 0/5 silent | ignored | no / yes | session_id, messages, platform, compression_count, in_place | 0 of 7 pass (start-side) |
| #118847 | 1-hunk hand-port | `post_compaction` | after summary, **before** commit | fires once, 4/4, transcript not yet durable | 1/5 silent (aborted summary only); fires on the would-grow refusal (after_tokens 3,365 > before_tokens 1,672), both write failures and the manual discard | ignored | no / yes | session_id (pre-rotation id), before_tokens, after_tokens, messages_removed, reason | 1 of 7 pass |
| #125881 | clean | `pre_compression_commit` (policy) | after summary, before commit | fires, but a non-`allow` subscriber **blocks** the compaction (state.db rows 0 while the no-subscriber baseline commits; output changed) in 4/4 | 1/5 silent (aborted summary only) | ignored | no / yes | session_id, state{counts} | 1 of 7 pass (fail-closed control point by design) |
| #119347 | 3 semantic conflicts | `transform_compaction_input` | before summary (transform) | not run | not run | n/a | n/a | n/a | not run |
| #4123 | conflicts in 3 files, 37,736 behind | `pre_compact` / `post_compact` | before summary / end of `compress_context` (diff read) | not run | not run | n/a | n/a | session_id, project_dir (diff read) | not run |
| #7150 | 42,445 behind | `pre_compress` / `post_compress` | no call site in its diff | not run | not run | n/a | n/a | n/a | not run |
| round-2 offer (`r4-offer`) | re-applied | `on_compression_complete` | after durable commit, inside the fence | fires once, 4/4 | 5/5 silent | honoured | yes / yes (manual: no / no) | session_id, old_session_id, in_place, tokens_before, tokens_after, platform | 5 of 7 pass (rotated, in-place fail the fence assertion) |
| **#53806 + fold-in** | built | `on_compression_complete` | after durable commit, after fence and lease release; after host finalize | fires once, 4/4 | 5/5 silent | honoured | no / no | session_id, old_session_id, in_place, tokens_before, tokens_after, platform | **7 of 7 pass, 3 of 3 reps** |

Payload keys exclude `telemetry_schema_version`, which the dispatcher adds to every hook call; the probe also omits `conversation_history`, `messages` and `state` from its key list, and the table restores them from the carriers' diffs. The #118847 token figures come from its own-name contract run (assertion text in `raw/f05-r5/c118847-handport-adapted-rep1.log`, summarised in the F05 r5 receipt).

Each other carrier's own tests still pass on its arm (OWN r5, fairness):

- #93391: `test_compression_rotation_state.py`, 43/0 (base 40/0). Both cells INFRA under strict S16 (119 and 113 blocked DNS lookups from that upstream file).
- #118847: `test_post_compaction_hook.py`, 7/0, 0 lookups. These tests mock `hermes_cli.lifecycle.invoke_hook`, which is the seam itself.
- #125881: `test_context_governance.py`, 9/0, 0 lookups.


## Evidence

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| F05 r5: carrier A/B, 10 arms with the clause probe + 12 negative/sabotage arms, main 44a1ce9724 | `receipts/F05-f05-r5.json` | KEEP | OBSERVED | 3 reps × 7 cases per arm (+3 own-name reps per carrier), 9 probe scenarios per probed arm; 91 cells, 0 INFRA (0 connect, 0 dns from any thread) | see the carrier table. base 4 of 7 pass (RED); foldin, foldin-ref, foldin-x127058 7 of 7; r4-offer 5 of 7; neg-prefire 1 of 7; neg-infence 5 of 7; neg-nodefer 5 of 7; sabotage h1 4 of 7, h2 5 of 7, h3 4 of 7, h4 4 of 7, h9 6 of 7; h5/h6/h7/h8 7 of 7 (unpinned). All reps agree. Fallback-commit probe: fires once, tokens 75,000 → 30,580 |
| E12 r5: guards + 20 adjacent files on base, foldin and foldin-x127058 | `receipts/E12-e12-r5.json` | **INFRA** (strict S16); PASS only if the owner accepts the recorded exception | OBSERVED (+ one structural note) | 1 run per arm per harness; 12 cells, 6 INFRA | replay_gates 11/11 PASS on all three, equal verdict maps, 0 lookups. ab_checkpoint_preflight local compress calls identical (capture 0/0 cli and gateway, restore 0, over_threshold 0 then 1), 0 lookups. test_region_scoping ALL PASS (2 lookups per arm). Adjacent 20 files: base 354 / 3 / 2 skipped (the 3 are the new test) → 357 / 0 / 2 on both arms; 348 blocked DNS lookups per arm (340 from 8 sibling test files on the main thread, 8 on the openrouter-prewarm thread), the per-file attribution identical on all three. Observer fires are 0 in replay_gates and the preflight by construction (no SessionDB in their real-compression scenarios; the preflight stubs `_compress_context`), so 0 is not a native-route measurement |
| MRG r5: composition with #127058 | `receipts/MRG-mrg-r5.json` | **INFRA** (strict S16, upstream tests); PASS if the exception is accepted | OBSERVED | 6 cells | foldin + #127058 (one conflict region, both post-fence deliveries kept): contract 7/0, #127058's own test 1/0, its 4 neighbour files 92/0. Staging commit + #127058 (clean merge): contract 4/3 (no hook), #127058's test 1/0, neighbours 92/0. Contract cells 0 lookups; #127058's test 4 and the neighbours 230 per arm, identical |
| OWN r5: carriers' own tests on their arms, incl. #53806's ported tests | `receipts/OWN-own-r5.json` | n/a (fairness) | OBSERVED | 10 cells, 8 INFRA under strict S16 | 43/0 (#93391), 7/0 (#118847), 9/0 (#125881); base rotation_state 40/0; #53806 verbatim 0/3 on every arm, adapted 2/0 on the hand-port and 1/1 on the fold-in (see the #53806 table) |
| PROOF r5: gate columns | `receipts/PROOF-r5.json` | **INFRA** (strict S16); PASS if the exception is accepted; F14 not run | OBSERVED | aggregation of F05 r5 + E12 r5 + MRG r5 | RED marker matched; GREEN 3/3; NEG RED; unpinned hunks listed; F14 not run |
| Guard canary r4 (still current) | `receipts/SANDBOX-guard-canary-r4.json` | PASS | OBSERVED | 5 cases + 2 prewarm runs | the r5 runs use the same guard file (`tools/chs_egress_guard_r4.py`, sha256 `3a808849b4…` in every r5 receipt's `runner_revision`), so its canary stands |

Superseded (kept as history): the r4 receipts (F05, E12, OWN, PROOF) now carry `superseded_by` r5 (`tools/chs_supersede_r4.py`), because round 3 changed the test (fence/lease clause) and the offered fold-in; the round-2 offer, re-applied as `r4-offer-r5`, fails the new clause (5 of 7 pass). Their verdicts and measurements are unchanged. The r3 receipts stay INFRA as re-labelled in round 2 (`tools/chs_supersede_r3.py`), and F05 r1, F05 r2, E12 r2, OWN r1 and PROOF r2 stay INFRA as re-labelled in round 1 (`tools/chs_supersede_r1r2.py`). Round 3 also replaced the host name in the r3 and r4 receipts' `env.host` with "withheld" (no other change), so their sha256 values below are new.

## Experiments run ($0 only)

- **Chain.** `bash tools/chs_run_all_r5.sh $WORKTREE $TESTHOME $PY` ran every step below strictly in sequence (one isolated test HOME, one guard log). Stdout: `raw/run-all-r5.stdout` (private).
- **Arms.** `python3 tools/chs_build_arms_r5.py $WORKTREE 1ab964166a 6a2f717e4c` (`raw/build-arms-r5.txt`): one textual mutation of `foldin-r5` per negative/sabotage arm, the r4 carrier diffs and round 2's offer re-applied with `git apply -3` (patch-ids equal to r4), and `foldin-x127058-r5` (merge with #127058's head, conflict resolved by keeping both deliveries).
- **F05 r5 (carrier A/B).** `python3 tools/chs_ab_runner_r5.py --worktree $WORKTREE --run-id f05-r5 --arms "$(cat raw/f05-r5.arms)" --reps 3 --testhome $TESTHOME --python $PY`, then `--run-id f05-r5s --arms "$(cat raw/f05-r5s.arms)" --skip-probe` for the negative and sabotage arms. The probe is `tools/chs_clause_probe_r5.py`: the r4 probe with an explicit commit fence, recording fence and lease state per fire. Raw logs: `raw/f05-r5/`, `raw/f05-r5s/` (private).
- **E12 r5 (guards + adjacent).** `bash tools/chs_guards_r5.sh <arm> <commit> e12-r5 $WORKTREE $TESTHOME $PY` runs `evals/token_accounting/replay_gates.py` and `evals/native_compaction/ab_checkpoint_preflight.py` through `tools/chs_guard_wrap_r4.py` (egress guard, observer counter), then `evals/compaction/test_region_scoping.py`, then 20 adjacent test files (r4's 17 plus `test_memory_session_switch.py`, `test_memory_boundary_commit.py`, `test_compression_concurrent_fork.py`, the neighbours #127058 names for the `finally` both diffs edit). Arms: base `1ab964166a`, `foldin-r5`, `foldin-x127058-r5`. `tools/chs_dns_attribution_r4.py` attributes each lookup.
- **OWN r5.** `bash tools/chs_own_r5.sh $WORKTREE $TESTHOME $PY`.
- **MRG r5.** `bash tools/chs_merge127058_r5.sh $WORKTREE $TESTHOME $PY`: on `foldin-x127058-r5` and on `s5x127058-r5`, the contract test, #127058's own `tests/agent/test_compression_fence_memory_hook_118120.py`, and its four named neighbours.
- **Workflow scan.** `python3 tools/chs_workflow_scan_r5.py <h.git> 1ab964166a staged/compaction-hook-salvage` → `raw/workflow-scan-r5.json`.
- **Closing checks.** `bash tools/chs_final_checks_r5.sh <h.git> $WORKTREE` → `raw/final-checks-r5.txt`.
- **Isolation for every run:** HOME = `$S/testhome-sf3-compaction-hook-salvage`; HERMES_HOME = `$HOME/.hermes`; `HERMES_PYTHON` points at the live venv's interpreter, used read-only as an interpreter only; `run_tests.sh` uses `env -i` and `-j 2`. The r4 egress guard is loaded through the isolated HOME's `pytest_live_guard.py` shim; it refuses non-loopback `connect`/`connect_ex` and `getaddrinfo`/`gethostbyname*`, logs each refusal with its thread name, and suppresses nothing. A cell with any `connect` or `dns` line is INFRA (S16). There is no bwrap or netns (FACTORY §6 layer 1 not used).
- **Cost:** $0, T1, cpu lane, 0 GPU-s.

## Recorded S16 exception (owner decision; not accepted)

FACTORY S16 says every blocked exec or connect fails the cell as INFRA, and defines no exception. The E12 adjacent and region-scoping cells, the MRG cells that run #127058's test and its neighbours, and 8 OWN cells contain DNS lookups that the guard refused, all from upstream code this item does not change (or, for the #53806 port, from the carrier's own tests, which do not pin the window): the model-metadata GET at `AIAgent` init, the `openrouter-prewarm` thread (1 per pytest worker process), and the OpenRouter video-catalog GET while tool definitions are built. The counts are identical on base and the fold-in arms, every path falls back, there are 0 connects, and the contract test itself makes 0 lookups (F05 r5: 91 cells, 0 dns). **Strictly, E12 r5 is INFRA (6 of 12 cells), MRG r5 is INFRA (4 of 6) and so is PROOF r5.** The exception text is in `receipts/E12-e12-r5.json` → `egress.s16_exception`. If the owner accepts it, E12 r5 reads `verdict_if_s16_exception_accepted`; if the owner rejects it, the adjacent set needs a run where those upstream lookups cannot happen (queued experiment 2). Either way P5 stays PENDING until F14 runs.

## Experiments queued (not run)

None of this item's gates needs a T2 or T3 experiment, because the contract does not depend on the model. Queued:

1. **T1 ($0, recommended before posting): consumer end-to-end for #118382.** A minimal out-of-tree plugin subscribes to `on_compression_complete`, flags the session, and re-injects a context block through `pre_llm_call` on the next turn, driven through the real turn loop against the loopback fake provider from `evals/token_accounting/replay_gates.py`, with `session_db` set. Command, after writing `tools/chs_consumer_e2e.py`: `env -i PATH=/usr/bin:/bin HOME=$TESTHOME HERMES_HOME=$TESTHOME/.hermes $PY tools/chs_guard_wrap_r4.py <worktree at foldin-r5> tools/chs_consumer_e2e.py raw/consumer/counts.json --out raw/consumer/result.json`. Pass: exactly one re-injection after each committed compaction, none after a refused one.
2. **T1 ($0, only if the owner rejects the S16 exception): adjacent set without upstream lookups.** Re-run the 20 adjacent files with a session-wide conftest stub for `agent.model_metadata.fetch_model_metadata` and the video catalog, or inside a network namespace, on base and `foldin-r5`.
3. **T1 ($0, needed for P5): F14 standing set** on base and `foldin-r5` (FACTORY §13 row 2), or the owner's statement of which F14 subset is the guard for this item.
4. **T1 ($0, optional): hung-subscriber and live-interrupt probe.** A subscriber that blocks on an Event; assert that `agent.hard_interrupt()` returns within 1s while it blocks, and that the compaction worker returns within `plugins.hook_callback_timeout` (set to 2s in the arm's `$HERMES_HOME/config.yaml`). This would pin the bound (sab-h6 is unpinned today).
5. **T2 (local GPU, strictly serial, gated on OD-1): real-summarizer smoke**, as in round 2 (`real_summary` switch still to be added to `tools/chs_clause_probe_r5.py`). Expected: identical clause verdicts.
6. **T3:** none.

## Acceptance gates (selection)

| gate | status | evidence |
|---|---|---|
| Contract test is RED on main (no hook) and GREEN on the chosen carrier, or carrier plus fold-in | **met** | RED 3 of 7 fail × 3 reps on 44a1ce9724. GREEN 7 of 7 pass × 3 reps on #53806 + fold-in (`foldin-r5`). F05 r5, PROOF r5 |
| Negative control: moving the fire before the commit makes the test fail | **met** | `neg-prefire-r5`: 6 of 7 fail × 3 reps |
| replay_gates PASS is unchanged | **met** | E12 r5 (replay_gates cells: 0 blocked attempts) |
| ab_checkpoint_preflight verdicts are unchanged | **met** | E12 r5 (preflight cells: 0 blocked attempts) |
| Observer-only (return ignored), unless the winner is the fail-closed pre_ variant | **met** | the winner is the observer; a `{"action": "block"}` return and a raising subscriber leave output byte-identical (contract case). #125881's fail-closed variant is recorded as a separate control point |
| The named consumer is cited (#118382) | **met** | body.md, this manifest |
| The disposition table is posted once (WAVE row) on #118382 or #53806 | **not met (owner action)** | text prepared in `body.md`. Posting is a GitHub write the factory does not perform; see [queue] for the target and the spray check |

## Gate checklist (FACTORY P1-P12)

| gate | status | basis |
|---|---|---|
| P1 Need | PASS | RED on 44a1ce9724 (≤24 h); invalidate_on paths unchanged since e496ccc7d7 and a3b56cac95; freshness re-check in [base] |
| P2 Ownership | PASS | seven external carriers → salvage-support; #127058 is a different defect on the same region and composes (MRG r5); no claimant-lane, hold or Hermes-lane overlap; Sahilvishnaliya's verbal claims on #118382 and #118120 have no PR; heads re-checked 2026-10-01T16:19Z |
| P3 Shape | PASS | One invariant, a fire site and a named consumer (#118382; #93389 for the start-side hook). No new env var or config key, no shim. New behaviour sits in the sibling `agent/conversation_compression_observer.py` (82 lines); the facade gets +16/-1 call plumbing (4,579 → 4,594), the AGENTS.md sibling pattern. `hermes_cli/plugins.py` 2,331 → 2,342, `hermes_cli/plugins_dispatch.py` 602 → 603. The carrier's untested start-side hook rides along as #53806's own code, pending maintainer decision (a); `foldin-ref` is the smallest surface if it is dropped. The staging commit adds only a new 169-line test |
| P4 Real path | PASS | real AIAgent/SessionDB/ContextCompressor/CompressionCommitFence/PluginManager; only the summary LLM call, the two init-time model-metadata lookups (window pin, prewarm stub) and, for one failure case, the SessionDB write are faked; seam not mocked |
| P5 Proof | **PENDING** | RED marker matched; GREEN 3/3; NEG RED (prefire, in-fence, no-defer); sabotage per hunk (h1 stage call, h2 finally call, h3 tokens_before, h4 tokens_after, h9 deferred chain re-RED; h5 VALID_HOOKS entry, h6 timeout bound, h7 hooks-CLI payload + docs row, h8 start-side call: unpinned and listed); flaky=false (all reps agree); F05 r5 0 INFRA cells. Not PASS: **F14 was not run** (E12 ran 3 of its harnesses; FACTORY P5 requires F14 guards equal), and E12 r5's adjacent and region-scoping cells carry upstream DNS lookups (INFRA under strict S16; the recorded exception is not accepted) |
| P6 Numbers | N_A | no value claim |
| P7 Package | PENDING | one clean commit on fresh main with correct author/subject and trailers, merge-tree clean, 0 workflow matches. Push as `staged/compaction-hook-salvage` is an owner action (OD-4 still decides whether the fold-in is pushed or stays an inline block) |
| P8 Freeze | PENDING | r5 receipts written with sha256 (front matter), repo-relative paths only, no host names; not frozen to z0evals |
| P9 Text | PENDING | body.md rewritten (no TITLE line, seven PRs with a disposition each, #118120/#127058 cited, behaviour changes listed, "N of 7 pass" throughout, AI assistance covers the test, fold-in, port and text, trailers for every reused design); needs an independent tone/jargon read |
| P10 Independent read | PENDING | round-2 re-verifier: accept=false (6 problems); no blind re-verification of `1ab964166a` yet |
| P11 Demand | RECORDED | combined score 5.24; maintainer SALVAGE verdict; consumer #118382 |
| P12 Queue | PENDING | no fork board applies (see [queue]); owner posts once on #53806 or as a delta row on #130139, on a later day than today's waves |

## NOT_TESTED

- **Native and Codex app-server compaction.** Neither route has a client commit (`_route_codex_compaction` returns before `_commit_compaction`; native checkpoint turns never call `_compress_context`), so the observer cannot fire there by construction. Structural argument only. Scope: local compressor.
- **Agents without a SessionDB.** With `session_db=None` there is no durable commit, so neither the context engine nor the observer is notified. Not exercised.
- **Micro-compaction and proactive-prune rewrites.** Not compaction boundaries; not exercised.
- **Real summarizer.** The summary is fixed text, or None for the failure scenarios.
- **Fallback-summary commit as a contract case.** Probe only (`fallback_committed`).
- **Host surfaces.** The manual deferral is exercised through `compress_context(defer_context_engine_notification=True)` + `finalize_context_engine_compression_notification`, not through `compress_now`, `gateway/slash_commands_session.py`, `acp_adapter/commands.py` or TUI/Desktop.
- **The progress-timeout path.** The contract test passes an explicit fence, which takes the facade's direct path (as gateway hygiene does). The default turn-loop path runs `compress_context` in a pool worker under `run_compress_context_with_progress_timeout`; there the observer runs in the worker after `finish_commit()`. A slow subscriber still delays the turn: by code reading, if the host's wait budget runs out meanwhile, it finds the commit already admitted and keeps waiting for the worker. Bounded by `plugins.hook_callback_timeout` per callback; not exercised.
- **Shell hooks.** `VALID_HOOKS` doubles as the shell-hook allow-list; `tests/hermes_cli/test_hooks_cli.py` passes, but no shell hook was run against a real compaction.
- **Slow or hung subscriber, live interrupt.** The fold-in bounds `on_compression_complete` (`_HOOK_TIMEOUT_BOUNDED_HOOKS`), but no hang was simulated, and `sab-h6-bounded` stays green: the bound is not pinned. The test asserts the fence state `hard_interrupt` checks, not an actual interrupt (queued experiment 4).
- **The carrier's start-side hook.** `pre_context_compression` is ported with #53806's payload but has no contract case, no docs-catalog row and no `_DEFAULT_PAYLOADS` entry. It runs before the commit fence is entered but with the session's compression lease held, it is not timeout-bounded (as in #53806), and it receives the full transcript (probe: `c53806-handport-pre` events record `lease_held_at_fire = true`, `commit_fence_in_flight_at_fire = false`). Its rename to `on_compression_start` is maintainer decision (a).
- **#53806's own tests.** Verbatim they fail on current main (agent-init hunk left out; store-row metadata in the transcript; a one-message compaction no longer commits). Only the drift-adapted port passes, and on the fold-in its boundary test fails by design (OWN r5).
- **#4123 and #7150.** Not materialized or run (37,736 and 42,445 commits behind; #7150's compress hooks have no call site). Their dispositions rest on a diff read.
- **F14.** Not run.
- **Docs pages other than the hook catalog.** `website/docs/user-guide/features/plugins.md` keeps its own category list and a stale "27 lifecycle events" count on main; not edited.
- **Kernel-level sandbox.** No bwrap/netns. The in-process guard cannot stop a native extension or a subprocess; none of the selected tests spawns one.
- **Credential, device, TTY and browser boundaries:** N/A.
- **Static observation, unverified by test:** `session:compress` (`event_callback`) in `_finish_compaction_boundary` has no `session_commit_succeeded` guard, so it may fire for a failed split. Out of scope here.

## Origin action (owner only, not run)

1. Push `staging/compaction-hook-salvage` to the fork as `staged/compaction-hook-salvage` (`--no-follow-tags`) **before** posting, so body.md's branch and commit links resolve.
2. Post `body.md` once, as **one comment on NousResearch/hermes-agent#53806** (the SALVAGE carrier; preferred). The alternative is one delta-row comment on NousResearch/hermes-agent#130139, using the disposition row (keep the collapsed diff). Do not open a new wave issue. Post on a later day (see [queue].spray_check).

The fold-in is offered as one production diff on current main, inline in body.md (`patches/arm-foldin.patch`), applied on top of the test commit, with the trailers in [credit]. #53806's own head conflicts in 11 files and is 33,698 commits behind, so a diff relative to it would not apply. No new PR and no slot.

## Next steps

1. **Owner:** decide the recorded S16 exception (accept → E12 reads PASS; reject → queued experiment 2); run or scope F14 (queued experiment 3); push as `staged/compaction-hook-salvage`; decide OD-4.
2. **Blind exact-head verification (P10)** of `1ab964166a` by a different worker. Inputs: `patches/staging-compaction-hook-salvage.patch`, `patches/arm-foldin.patch`, and the oracle: RED on main with marker `on_compression_complete fired 0 times`; GREEN 7 of 7 on carrier + fold-in; prefire and in-fence negative controls RED; the contract test alone logs 0 lookups under a guard that suppresses nothing.
3. **Maintainer decisions to surface in the comment** (all three are in body.md): (a) the start-side hook (keep, rename to `on_compression_start` with a contract case, docs row and `_DEFAULT_PAYLOADS` entry, or drop it with the `task_id` plumbing); (b) manual-discard semantics; (c) the timeout bound (on by default; one line to remove). Round 2's decision (d), the facade sibling, is resolved by the fold-in.
4. **Watch #127058.** If it merges first, rebase the fold-in: the only conflict is the shared post-fence block (`patches/foldin-x127058-delta.patch` shows the resolution).
5. **Run the queued T1 consumer end-to-end** before posting.
6. **Freeze the cited r5 receipts (P8)**, and re-check freshness within 24 h of posting: `git merge-tree --write-tree main staging/compaction-hook-salvage`, then the RED cell.

## Round-3 fixes (round-2 re-verifier, problems[0..5])

| # | re-verifier finding | fix | where |
|---|---|---|---|
| 0 | #118120 (fence hazard) and #127058 (its open fix, same `_finish_compaction_boundary` / `compress_context` region) were not cited; the fold-in added an unbounded third-party observer inside the commit fence; NOT_TESTED likened it to the very call #127058 moves out | Both cited (Links, [upstream].overlapping_open, [ownership], body.md). The fold-in now stages `on_compression_complete` after the boundary and runs it in `compress_context`'s `finally` after `lease.release()` and `finish_commit()` (#127058's delivery point), and bounds it under `plugins.hook_callback_timeout`. The test's fires-once case asserts the fence has no commit in flight and the lease is free when the observer runs; RED on the round-2 placement (`r4-offer-r5`, `neg-infence-r5`). Merge checked against #127058's head: 1 conflict region, resolved by keeping both deliveries; with both, the contract test and #127058's own test pass (MRG r5). finn763 credited for the design | staging commit `1ab964166a`; `foldin-r5`; `patches/foldin-x127058-delta.patch`; F05 r5; MRG r5; body.md |
| 1 | "Five open PRs" undercount; no disposition for #4123 and #7150 | "Seven" in body.md, the commit message and this manifest. #4123: close after the carrier merges (same two seams, nothing reused). #7150: keep open for its `pre_tool_call` redirect; its compress hook names have no call site and could be dropped. Both read from their diffs (not run; 37,736 and 42,445 commits behind) | body.md row and results table; [upstream] close_after / stay_open / competitors |
| 2 | P3: the observer and the 20-line start-side block were appended to the 4,579-line facade; the sibling variant was not built | Built: `agent/conversation_compression_observer.py` (82 lines) holds both dispatches; the facade gets +16/-1 call plumbing. P3 → PASS; round 2's maintainer decision (d) is gone | `foldin-r5`; Route and carrier choice; P3 row |
| 3 | The start-side call kept #53806's `hermes_cli.plugins.invoke_hook`, unlike main's `hermes_cli.lifecycle` dispatch, and this was not among the disclosed deviations | Ported to `hermes_cli.lifecycle.invoke_hook` (in the sibling) and disclosed as the fourth deviation, with the re-measured count (12 of the 13 hook-dispatching files under agent/ and gateway/ use lifecycle on 44a1ce9724). #53806's adapted own test still passes on the fold-in (OWN r5) | sibling; [upstream].carrier; body.md; OWN r5 |
| 4 | P5 PENDING (E12 INFRA under strict S16; P8, P10 pending) | Still PENDING, now with a second reason stated: F14 was not run (FACTORY: P5 needs F14 guards equal). E12 r5 re-run on the new base with 20 adjacent files; the S16 exception stays recorded, not accepted. F14 queued as experiment 3 | P5 row; E12 r5; Experiments queued |
| 5 | body.md started with a `TITLE:` line | Dropped | body.md; [body].no_title_line |
| - | (found while fixing) the r3/r4 receipts named the host in `env.host` | Replaced with "withheld" in every receipt; r5 receipts name no host; superseded hashes updated | `receipts/*.json`; [evidence].superseded |

## Round-2 fixes (round-1 re-verifier, problems[0..6])

| # | re-verifier finding | fix | where |
|---|---|---|---|
| 0 | commit message ("Each of these cases first checks why nothing committed and that state.db is unchanged") and body.md ("Four attempts that commit nothing stay silent ... Each first checks that state.db is unchanged") misdescribe `manual_discarded`, which skips the unchanged-rows check and asserts `_durable_summary` instead | New staging commit `111f361fb0` on fresh main with a corrected message: three cases check unchanged session id and rows (the first two also the compressor's flag), and the manual-discard case is described separately (compacted rows written and asserted; only the host's discard keeps the observer silent). body.md and this manifest say the same. RED re-proved (3/3 reps) | staging commit; body.md; First-slice status; Invariant |
| 1 | "no model-metadata lookup over the network" was false: the `openrouter-prewarm` thread still ran; F05 r3's "0 dns" held only because the harness skipped the thread; same for the S16-exception bullet | The test now also patches `agent.agent_init.fetch_model_metadata` during init, so the prewarm thread runs a stub; comment, docstring and commit message say "stubbed ... no network request". A new r4 guard suppresses nothing and logs thread names. Measured: round-1 file 2 lookups on `openrouter-prewarm` per `-j 2` run, round-2 file 0; F05 r4 78 cells, 0 dns, 0 connect from any thread. The r3 receipts are re-labelled (F05 r3 INFRA) and the false bullet is annotated; the r4 exception text uses the r4 measurement | `tools/chs_egress_guard_r4.py`, `receipts/*-r4.json`, `tools/chs_supersede_r3.py` |
| 2 | the hand-port silently dropped `task_id` and moved the call out of `compress_context`; "leaves that hook exactly as #53806 wrote it" was false; #53806's own tests were not run | `task_id` is now passed into `_run_summary_phase`, so the payload keys are #53806's. The location change (forced by main moving the summarizer call) and the left-out hunks are disclosed in body.md, the carrier field, Route and carrier choice and NOT_TESTED. #53806's three tests were ported (verbatim + drift-adapted) and run on base, hand-port and fold-in (OWN r4; results above) | arms `c53806-handport-r4`, `c53806-foldin-r4`; `tools/chs_c53806_own_tests*.py`; `receipts/OWN-own-r4.json` |
| 3 | credit not settled: the fold-in reuses #118847's before/after-token observer design and #93391's `in_place`, but only Kevin Rajan's trailer was offered | Co-authored-by for Baophan00 and clomp42 (noreply forms) on the fold-in offer and on the staging commit, plus ledfoot631 on the staging commit; [credit] records who is and is not credited and why | staging commit; [[donors]], [credit]; body.md |
| 4 | "available on request" contradicts self_service/no_labor | body.md links the fork branch and commit with qualified kvnloo/hermes-agent URLs and carries the combined diff inline in a collapsed block; the origin action pushes before posting | body.md; [body].self_service_basis; Origin action |
| 5 | P5 scored PASS on an S16 exception the owner never accepted, with a false premise | P5 = PENDING. E12 r4 and PROOF r4 report `verdict = INFRA` under strict S16, with `verdict_if_s16_exception_accepted = PASS` alongside; the exception is a separate section marked "not accepted" | [gates], P5 row, Recorded S16 exception, receipts |
| 6 | the commit message claimed the fallback-commit announcement is pinned; the 75,000 → 30,622 figure was private-only | The sentence is gone from the commit message and the test docstring; the invariant marks it probe-only; the r4 figure (75,000 → 30,598) is public in `receipts/F05-f05-r4.json` → `fallback_commit_probe` | staging commit; Invariant; F05 r4 |

## Round-1 fixes (phase-3 verifier, problems[0..8])

| # | verifier finding | fix | where |
|---|---|---|---|
| 0 | `summary_failed` actually tested the would-grow refusal; `not _durable_summary(...)` was vacuous; "stays silent when the summary fails" was false in general; body.md called the same scenario a "refused fallback summary" | The case was split into `summary_aborted` (`abort_on_summary_failure=True`, precondition `_last_compress_aborted`) and `would_grow_refused` (default config, precondition `_last_compress_refused_would_grow`). The non-commit precondition became "session id and state.db rows unchanged". The probe gained `fallback_committed` | staging commit `de819a7d06` (superseded by `111f361fb0`); F05 r3 (superseded) |
| 1 | queue target was stale: #402 closed 07:32Z, posted upstream as #130139 | [queue] now has no fork board, an owner choice between one #53806 comment and a delta row on #130139, and a recorded spray check (post on a later day) | [queue], Origin action, Links |
| 2 | the fold-in's `on_compression_start` rename had no test and was not disclosed | The fold-in no longer touches the start-side hook; disclosed in body.md as maintainer decision (a). `foldin-ref` passes 7/7 without it | arms; body.md |
| 3 | no hooks.md catalog row and no `_DEFAULT_PAYLOADS` entry | The fold-in adds both for `on_compression_complete`, and `tests/hermes_cli/test_hooks_cli.py` + `test_plugins.py` joined the adjacent set | `patches/arm-c53806-foldin.patch`; E12 |
| 4 | receipts lacked §9.2 fields; S16 blocked connects not classified; DNS leaked; "loopback-only" overstated | Full §9.2 receipts; DNS guarded and logged per cell; r1/r2 receipts re-labelled INFRA. (Round 2 found that the r3 guard's thread suppression hid one lookup; see Round-2 fix 1) | `receipts/` |
| 5 | the carrier table was attributed to F05 r1, which had no `c53806-foldin` arm | The table comes from the run where every arm ran together (now F05 r4) | Route and carrier choice |
| 6 | the origin action offered a diff relative to our unpublished hand-port | It offers `patches/arm-c53806-foldin.patch`, the combined production diff on main, plus the staging patch | First-slice status, Origin action |
| 7 | receipts embedded local paths | All receipts use repo-relative paths and placeholders; the builders assert it | `receipts/` |
| 8 | AGENTS.md sibling rule; P3 scored PASS | P3 is PENDING, surfaced as maintainer decision (d) | [gates], P3 row, body.md |

## History

| when (UTC) | status | worker | reason |
|---|---|---|---|
| 2026-10-01T08:50Z | CANDIDATE | builder (Claude Code, Opus 5.5) | selection read; premise re-checked on 572e4f4fad: VALID_HOOKS has no compression hook, fire site unchanged at conversation_compression.py:2564, no newer carrier found |
| 2026-10-01T09:03Z | CANDIDATE | builder | contract test committed on 572e4f4fad (`b3b8d73999`); RED 3/6 |
| 2026-10-01T09:12-09:30Z | EVIDENCED | builder | F05 r1 (12 arms) under the r1 connect-only guard |
| 2026-10-01T09:51-10:05Z | EVIDENCED | builder | staging commit cherry-picked onto bafb42b431 (`8c834af1e4`); F05 r2 + E12 r2 + OWN r1; local branch `staging/compaction-hook-salvage` created; worktree removed |
| 2026-10-01T10:10Z | EVIDENCED | phase-3 verifier | accept=false, manifest_accurate=false; 9 problems |
| 2026-10-01T11:04-12:15Z | EVIDENCED (v2) | round-1 fixer (Claude Code, Opus 5.5) | test case split + real non-commit preconditions + pinned context window; staging commit rebuilt on aea969677c (`de819a7d06`), local branch forced; fold-in reshaped; r3 egress guard; F05 r3 + E12 r3 + OWN r3 + canary r3; worktree removed |
| 2026-10-01 (after 12:15Z) | EVIDENCED (v2) | round-1 re-verifier | 7 problems (see Round-2 fixes) |
| 2026-10-01T12:40-13:45Z | EVIDENCED (v3) | round-2 fixer (Claude Code, Opus 5.5) | prewarm stubbed in the test + corrected commit message; staging commit rebuilt on a3b56cac95 (`111f361fb0`), local branch forced; hand-port passes `task_id`; trailers for ledfoot631, Baophan00, clomp; r4 guard (no suppression); F05 r4 + E12 r4 + OWN r4 (incl. #53806's own tests) + canary r4 + prewarm check; r3 receipts re-labelled and superseded; P5 → PENDING; body.md links the branch and inlines the diff; worktree removed |
| 2026-10-01T16:00-17:20Z | EVIDENCED (v4) | round-3 fixer (Claude Code, Opus 5.5) | #118120/#127058 cited; fence/lease clause added to the test; staging commit rebuilt on 44a1ce9724 (`1ab964166a`), local branch forced; fold-in rebuilt (sibling module, post-fence delivery, timeout bound, lifecycle dispatch for the start-side call); seven PRs with a disposition each; r5 arms, F05 r5 + E12 r5 + OWN r5 + MRG r5; r4 receipts superseded; host name redacted from all receipts; P3 → PASS; P5 stays PENDING (F14 not run); body.md without TITLE line; worktree removed |
