+++
xf_staging = 1
id = "compaction-hook-salvage"
version = 3               # round-2 rebuild after the round-1 re-verifier (7 problems on de819a7d06); local branch forced to the new commit as instructed, nothing was ever pushed
title = "One observer compaction hook: A/B five competing carriers per the #64231 SALVAGE verdict"
branch = "staging/compaction-hook-salvage"
branch_physical = "local ref staging/compaction-hook-salvage in the scratch mirror h.git, not pushed. It publishes to kvnloo/hermes-agent as staged/compaction-hook-salvage: the fork's legacy refs/heads/staging @28790e597c blocks staging/*, so OD-0 is resolved by this rename (ls-remote 2026-10-01T13:39:40Z: no refs/heads/staged/* on the fork)"
branch_sha = "111f361fb0003405e4724b4c6523f6ce5d118c22"
status = "EVIDENCED"      # round-2 fixes done and re-proved; P5 waits on the owner's S16 decision; push (owner), receipt freeze (P8) and blind re-verify (P10) pending
route = "salvage-row"
promotion_form = "salvage-support"   # unchanged: five external PRs own the hook; our part is a Co-authored-by fold-in
feature = "compaction-lifecycle-hooks"
invariant = "A plugin subscribed to the local compaction observer is told exactly once per committed local compaction, after the compacted transcript is durable (and, for a manual /compress, after its host commits), never for an attempt that did not commit (a failed summary that aborts under compression.abort_on_summary_failure=true, the commit site's would-grow refusal, a SessionDB write failure, a discarded manual compress), and can neither break nor change the compaction. Not a contract case, probe only: a failed summary under the default abort_on_summary_failure=false commits the deterministic fallback, and that commit is announced."

[base]
repo = "NousResearch/hermes-agent"
sha = "a3b56cac95488242856b6fb1f121842a38c3e391"
fetched_at = "2026-10-01, between 12:37Z (the commit time, 18:07:32+05:30) and 12:53Z (first r4 cell)"
previous_base = "aea969677c60a1bb72fe227fdfb98f196a2092cc (round-1 staging commit de819a7d06; 12 commits before a3b56cac95, none touching an invalidate_on path or agent/agent_init.py)"
selection_base = "e496ccc7d7"
first_built_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (round-0 staging commit b3b8d73999)"
invalidate_on = ["agent/conversation_compression.py", "agent/context_compressor.py", "hermes_cli/plugins.py", "hermes_cli/plugins_dispatch.py", "hermes_cli/lifecycle.py", "agent/conversation_compression_manual.py", "hermes_state_messages.py", "hermes_state_compression.py", "hermes_cli/hooks.py", "website/docs/user-guide/features/hooks.md", "agent/agent_init.py"]
drift_note = "None of the invalidate_on paths changed from aea969677c to a3b56cac95. agent/agent_init.py joins invalidate_on in round 2 because the test now stubs its fetch_model_metadata import."
freshness_recheck = { main = "666b9f04c4229341c9188b096eb64d2a5e807347", checked_at = "2026-10-01T13:39:38Z", commits_since_base = 4, invalidate_on_changed = false, merge_tree_clean = true }

[upstream]
issues = ["NousResearch/hermes-agent#64231", "NousResearch/hermes-agent#118382", "NousResearch/hermes-agent#8643", "NousResearch/hermes-agent#93389", "NousResearch/hermes-agent#125384", "NousResearch/hermes-agent#119317"]
eval_prs = []
carrier = { pr = 53806, author = "ledfoot631", head = "6067388d0c", compression_commit = "e560abd758", form = "hand-port of the compression commit + Co-authored-by fold-in. The hand-port deviates from e560abd758 in three disclosed ways: its agent/agent_init.py and hermes_cli/hooks.py hunks and test hunk are left out (and the 6067388d0c resume-hook commit); the pre_context_compression call sits in _run_summary_phase, because main moved the summarizer call out of compress_context, still after the memory providers' pre-compress step and right before the summarizer; task_id is passed into _run_summary_phase so that call's payload keys are e560abd758's. The fold-in does not touch that start-side call." }
competitors = [
  { pr = 93391, author = "clomp42", head = "9da3734b8e", result = "0/7 under its own hook name: pre_compression fires before the summarizer on every attempt (start-side seam, same as #53806's pre hook)" },
  { pr = 118847, author = "Baophan00", head = "222e3e26c3", result = "1/7: post_compaction fires inside ContextCompressor.compress() before the commit, so it also fires for the would-grow refusal, failed SessionDB writes and a discarded manual compress; silent only when the summary aborts; session_id is the pre-rotation id" },
  { pr = 119347, author = "fangliquanflq", head = "4a527fc35d", result = "not materialized: transform (transform_compaction_input), 3 semantic conflict hunks at the #61932 pruned-copy seam; excluded from the observer slot (#120582 risk)" },
  { pr = 125881, author = "pstarkgit", head = "d3fdffcf82", result = "1/7: pre_compression_commit is a fail-closed admission gate (a non-allow subscriber blocks the compaction), a different control-point contract; merges clean" },
]
also_seen = [
  { pr = 4123, author = "GratefulDave", head = "16c60cd623", note = "pre_compact/post_compact; 37.7k behind; conflicts in agent/conversation_compression.py, hermes_cli/plugins.py, run_agent.py; not an arm" },
  { pr = 7150, author = "Tauriqbarron", head = "f823aebeb2", note = "pre/post_compress bundled with a pre_tool_call redirect; 42.4k behind; not an arm" },
  { pr = 59758, author = "gulivan", note = "CLOSED by teknium1 2026-07-22: hooks land with a real, named consumer" },
]
close_after = [93391, 118847]
stay_open = [125881, 119347]
demand = { score = 5.24, source = "selection.json combined_score (maintainer-fit 6, evidence 6, impact 4)" }
maintainer_signal = "teknium1, #64231 verdict table (2026-08-13): SALVAGE #53806, rename to observer form on_compression_start (or keep pre_ only as a fail-closed control point); #8643 FOLD into the #53806 family. teknium1 closed #59758 for lacking a named consumer."

[[donors]]
sha = "e560abd758"
author = "Ádám Somorjai <ledfoot631@users.noreply.github.com>"
role = "carrier (compression commit of #53806, hand-ported: its agent/conversation_compression.py and hermes_cli/plugins.py hunks, with the two disclosed adaptations above; its hermes_cli/hooks.py, agent/agent_init.py and test hunks and the 6067388d0c resume-hook commit are left out). Also credited on the staging commit: the test pins the post-commit boundary call shape (session_id, old_session_id after the durable commit) that #53806 introduced"
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
sha = "111f361fb0003405e4724b4c6523f6ce5d118c22"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "behaviour-contract test (staging commit, author) + fold-in: post-commit placement, payload, hooks-catalog row and hooks-CLI test payload; offered as patches/arm-c53806-foldin.patch (carrier hand-port + fold-in as one production diff on main)"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[credit]
staging_commit_trailers = ["Co-authored-by: Ádám Somorjai <ledfoot631@users.noreply.github.com>", "Co-authored-by: Baophan00 <109447498+Baophan00@users.noreply.github.com>", "Co-authored-by: clomp <277387657+clomp42@users.noreply.github.com>", "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"]
foldin_offer = "commit author Ádám Somorjai (#53806, carrier); Co-authored-by Kevin Rajan, Baophan00, clomp (body.md lists the three trailers)"
not_credited = [
  { pr = 125881, author = "pstarkgit", why = "nothing reused: its pre_compression_commit is a fail-closed admission gate with a state{counts} payload; neither the fail-closed semantics nor that payload is taken" },
  { pr = 119347, author = "fangliquanflq", why = "nothing reused: a summarizer-input transform; not materialized" },
  { pr = 4123, author = "GratefulDave", why = "pre_compact/post_compact names and placement not used; not an arm" },
  { pr = 7150, author = "Tauriqbarron", why = "not used; not an arm" },
]
rule = "credit every contributor whose idea or code is used. close_after names #93391 and #118847, whose designs the fold-in reuses, so both are credited rather than closed uncredited"

[ownership]
searched_at = "2026-10-01T08:50Z-09:20Z; re-checked 11:20Z and 2026-10-01T13:41Z (carrier and competitor heads unchanged, all OPEN; #118382 last comment 2026-09-22 by Sahilvishnaliya; no new compaction/compression hook PR)"
queries = ["compression hook (open)", "compaction hook (open)", "on_compression", "118382", "compaction (open, sorted by update)", "compression hook (merged)", "compaction hook (closed)", "on_compression_complete OR on_compression_start OR post_compaction OR pre_compaction", "author:Sahilvishnaliya hook", "compaction hook created:>=2026-10-01", "compression hook created:>=2026-10-01"]
open_external = [53806, 93391, 118847, 119347, 125881, 4123, 7150]
merged_overlap = []
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
issue_claim = "NousResearch/hermes-agent#118382: Sahilvishnaliya commented 'I'm working on this — planning a PR' (2026-09-22); no PR found"
verdict = "EXTERNAL -> salvage-support; our part is a Co-authored-by fold-in"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "F05/f05-r4", path = "receipts/F05-f05-r4.json", sha256 = "fa765a48ef10f9741997f7239973052a28e6c40ed4b6edbe6a6f03583593f14b" },
  { id = "E12/e12-r4", path = "receipts/E12-e12-r4.json", sha256 = "46dcf42d507c23a2ea14e8304011a61701cc96aa3fc2d32ccad81385496a3f69" },
  { id = "PROOF/r4", path = "receipts/PROOF-r4.json", sha256 = "6497f43f6511a28ffa5d017483245e01daff7432276eee9e5256d473a8fab84b" },
  { id = "OWN/own-r4", path = "receipts/OWN-own-r4.json", sha256 = "1ef62c45e21e3e87bd1f495d3a4608e1075495a92b7dbdc5e05831d91fd8e9a8" },
  { id = "SANDBOX/guard-canary-r4", path = "receipts/SANDBOX-guard-canary-r4.json", sha256 = "1561afc9f6374455055108c68eca3fb70d85cb4cac2fb2bde22dec178100afbe" }
]
superseded = [
  { id = "F05/f05-r3", path = "receipts/F05-f05-r3.json", sha256 = "4052db4f8205c69d83a6d5c780e41e760926cd06fba27059fbf36c2c106d3a20", verdict = "INFRA (strict S16 after the round-2 re-label: every cell had a suppressed prewarm attempt)" },
  { id = "E12/e12-r3", path = "receipts/E12-e12-r3.json", sha256 = "130c228c787a90fdef5985fe66166d8b36a40fddfaae4f80987a8fdcbcecc666", verdict = "INFRA (strict S16; exception never accepted, one premise false)" },
  { id = "OWN/own-r3", path = "receipts/OWN-own-r3.json", sha256 = "0b730965e9ac0885eec49fd7683efcd726d37011dac531ee86a31a5dd7702714", verdict = "n/a (fairness); validity INFRA under strict S16" },
  { id = "PROOF/r3", path = "receipts/PROOF-r3.json", sha256 = "77fbb6561e9ba3c445e7cf227747835bbdcfd149783bb83927585137591bf300", verdict = "INFRA" },
  { id = "SANDBOX/guard-canary-r3", path = "receipts/SANDBOX-guard-canary-r3.json", sha256 = "55eb52eb86921ade47f7bda22ab6cb39761b8eaaa2f2eea2bd35d66c574b2e17", verdict = "PASS for its 5 cases; its prewarm suppression is retired" },
  { id = "F05/f05-r1", path = "receipts/F05-f05-r1.json", sha256 = "85625ea19f2c27ebefaebef16d0f4249d0dcf4736c39c55ce3ae1adceb6adb06", verdict = "INFRA (S16)" },
  { id = "F05/f05-r2", path = "receipts/F05-f05-r2.json", sha256 = "f7044149577e55ff6d9cff55fa26b2306c68bf3b3bfbbdbd20f48a4f1d4b951b", verdict = "INFRA (S16)" },
  { id = "E12/e12-r2", path = "receipts/E12-e12-r2.json", sha256 = "9752f0f59ab600a36caded81b5a05d9254d1ce78188691f83bc49589d6226d3a", verdict = "INFRA (S16, unattributable)" },
  { id = "PROOF/r2", path = "receipts/PROOF-r2.json", sha256 = "b0aee1db3a713f6546d5d06e674f69c487e9b11024a32405205f549c60f4de0a", verdict = "INFRA" },
  { id = "OWN/own-r1", path = "receipts/OWN-own-r1.json", sha256 = "984100f78f4a693daf397867202447dd51efbbeb53ead7717f2028d33aad72de", verdict = "INFRA (S16, unattributable)" },
  { id = "SANDBOX/guard-canary", path = "receipts/SANDBOX-guard-canary.json", sha256 = "509e5bca29510c40c68ed7d9b571115e8026746bc880311b3d1b0c0c1f33f65c", verdict = "PASS (connect() only; DNS not guarded)" }
]
red = { test = "tests/agent/test_compaction_observer_hook_contract.py::test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred]", main = "a3b56cac95", marker = "AssertionError: on_compression_complete fired 0 times", reps = "3/3 (4 passed / 3 failed each)", receipt = "F05/f05-r4" }
green = { arm = "c53806-foldin-r4 c915bb4f1a", reps = "3/3 (7 passed / 0 failed each)", also = "foldin-ref-r4 3/3, foldin-bounded-r4 3/3", receipt = "F05/f05-r4" }
negative_control = { mutation = "hook call moved from the post-commit notify to just before _commit_compaction", result = "RED 6 of 7 failed, 3/3 reps", also = "manual deferral bypassed: RED 2/7; per-hunk sabotage: observer call removed RED 3/7, queue payload RED 1/7, tokens_before RED 3/7, tokens_after RED 3/7; VALID_HOOKS entry, keeping the carrier's on_session_start post-commit call, and the hooks-CLI payload + docs row stay GREEN (unpinned)", receipt = "F05/f05-r4" }
adjacent = { files = 17, base = "302 passed / 3 failed (only the new contract test's 3 fires-once cases) / 2 skipped", arm = "305 / 0 / 2 skipped on c53806-foldin and on foldin-bounded", identical_outside_new_test = true, s16 = "231 blocked DNS lookups per arm in this cell, identical on base and arms: INFRA under strict S16", receipt = "E12/e12-r4" }
guards = { replay_gates = "11/11 PASS on base, c53806-foldin and foldin-bounded; verdict maps equal; 0 blocked attempts", ab_checkpoint_preflight = "local compress-call counts equal to base (capture 0/0 cli and gateway, restore 0, over_threshold 0 then 1); 0 blocked attempts", test_region_scoping = "ALL PASS on all three (2 blocked DNS lookups per arm from the eval's own agent init: INFRA under strict S16)", receipt = "E12/e12-r4" }
egress = { F05 = "78 cells: 0 connect, 0 dns from any thread, 0 INFRA; r4 guard suppresses nothing", prewarm_check = "round-1 test file alone on main: 2 blocked getaddrinfo('openrouter.ai'), all on thread openrouter-prewarm, per -j 2 run; round-2 file: 0", E12 = "12 cells: 0 connect; replay_gates and ab_checkpoint_preflight 0 dns; adjacent 231 and test_region_scoping 2 blocked DNS lookups per arm, identical on base and arms, all in upstream code: 6 of 12 cells INFRA under strict S16 (experiment INFRA); PASS only under the recorded, not accepted S16 exception", OWN = "10 cells: 8 INFRA under strict S16 (rotation_state and #53806's ported tests, which do not pin the window); #118847 and #125881 cells 0", canary = "5/5; guard log connect 1, dns 2 (1 on openrouter-prewarm); nothing suppressed", receipts = "F05/f05-r4, E12/e12-r4, OWN/own-r4, SANDBOX/guard-canary-r4" }
own = { c93391 = "test_compression_rotation_state.py 43/0 (base 40/0)", c118847 = "test_post_compaction_hook.py 7/0 (mocks the seam)", c125881 = "test_context_governance.py 9/0", counts = "passed/failed", c53806 = "3 tests ported from e560abd758: verbatim 0/3 on base, hand-port and fold-in; drift-adapted (2 tests) 2/0 on the hand-port, 1/1 on the fold-in (boundary test fails by design), 0/2 on base", receipt = "OWN/own-r4" }
quantitative = []
cache_read_ratio = { status = "N_A", why = "the observer fires after the sanctioned compaction cache break; compacted messages + system prompt asserted byte-identical with and without subscribers" }
route_scope = "local-compressor"
not_tested = ["native and codex_app_server compaction (structural only)", "session_db=None agents", "micro-compaction / proactive prune", "real summarizer", "per-host manual /compress handlers", "shell hooks (hooks-CLI payload added, no shell hook run)", "hung subscriber", "fallback-summary commit as a contract case (probe only)", "#53806's start-side pre_context_compression (no contract case; no docs row or hooks-CLI payload; rename left to the author/maintainers)", "#53806's own tests pass only with two drift edits on current main, and its agent-init test needs the left-out agent_init hunk (OWN/own-r4)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-compaction-hook-salvage", commit = "" }

[gates]
P1 = "PASS"
P2 = "PASS"
P3 = "PENDING"   # AGENTS.md facade rule: new behaviour is appended to agent/conversation_compression.py (4,579 -> 4,617 lines); surfaced as maintainer decision (d)
P4 = "PASS"
P5 = "PENDING"   # RED/GREEN/NEG/sabotage are clean (F05 r4, 0 INFRA), but E12's adjacent and region-scoping cells are INFRA under strict S16 (upstream DNS lookups); PASS only if the owner accepts the recorded S16 exception
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
round1 = "re-verifier on de819a7d06: 7 problems (commit message/body wording for manual_discarded, false network claim, undisclosed hand-port deviation and untested carrier tests, unsettled credit, on-request offer vs self_service, P5 scored PASS on an unaccepted S16 exception, fallback-commit claim + private-only figure); see 'Round-2 fixes'"

[merge_check]
main_sha = "a3b56cac95488242856b6fb1f121842a38c3e391"
checked_at = "on a3b56cac95 when the branch was forced (round 2); re-checked 2026-10-01T13:39Z on main 666b9f04c4 (4 commits later, no invalidate_on path touched): clean"
clean = true
tree = "c3e9452f8b on a3b56cac95 (equals the staging commit's tree); 240424fa9c on 666b9f04c4"
recheck = "git merge-tree --write-tree main staging/compaction-hook-salvage"
foldin_applies = "2026-10-01T13:39Z (tools/chs_final_checks_r4.sh): patches/staging-compaction-hook-salvage.patch passes git apply --check on a3b56cac95; the diff inlined in body.md is byte-identical to patches/arm-c53806-foldin.patch, applies with git apply on 111f361fb0, and leaves no difference against c53806-foldin-r4"

[push]
fork_branch = "staged/compaction-hook-salvage"
no_follow_tags = true
workflow_push_matches = 0   # 52 workflow files on 111f361fb0: 41 without a push trigger, 10 whose push branches do not match staged/compaction-hook-salvage, 1 tags-only
pushed_at = ""

[body]
path = "body.md"
kind = "wave-row"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
self_service_basis = "body.md links the test commit on kvnloo/hermes-agent staged/compaction-hook-salvage (valid once the owner pushes it, before posting) and carries the combined production diff inline in a collapsed block; nothing is offered 'on request'. If OD-4 later pushes the fold-in to the fork, the block can become a compare link"
jargon_lint = "PASS (self-check: no envelope/lane/E##/F##/arm names in body.md)"
privacy_scan = "PASS (synthetic fixtures only; no session ids, home paths or message text; contributor addresses are GitHub noreply forms)"

[queue]
board = "none. kvnloo/hermes-agent#402 (fork salvage board) was closed COMPLETED 2026-10-01T07:32Z: its 9 rows were posted upstream as NousResearch/hermes-agent#130139, and none of them is about compaction. This item is not a kvnloo/hermes-agent#404 row either: that queue lists 39 staged PR branches, and this item opens no PR"
position = "owner picks one: (a) one comment carrying body.md on the carrier thread NousResearch/hermes-agent#53806 (preferred: one concrete delta per thread), or (b) one delta-row comment on NousResearch/hermes-agent#130139. Never a new wave issue"
spray_check = "re-checked 2026-10-01T13:41Z: kvnloo opened 5 upstream issues since 2026-09-30T13:00Z (#129760, #129761, #129963, #130139, #130140; 4 are wave tables, 2 of them posted 07:32Z today) and 4 PRs on 2026-10-01 (#129918, #129928, #130203, #130205); #130139 still has 0 comments. Another wave-style table the same day is high spray risk: post (a) or (b) on a later day, not today"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# One observer compaction hook: A/B five competing carriers per the #64231 SALVAGE verdict

**Promotion form:** salvage-support (route `salvage-row`, body kind `wave-row`). Unchanged in round 2: five external PRs own the hook, and our part is a `Co-authored-by` fold-in. No finding pointed to a different form: the carrier and competitors are still open with unchanged heads, and nothing here is blocked on a design hold.

**Status:** EVIDENCED, version 3. Round 2 fixed the seven problems the round-1 re-verifier listed (see "Round-2 fixes"). The staging commit was rebuilt on main `a3b56cac95` as `111f361fb0` (new message; the test now also stubs the OpenRouter metadata prewarm), and the local branch was forced to it. RED, GREEN, negative controls, sabotage, guards, adjacent files and the carriers' own tests were re-run on that base under an egress guard that suppresses nothing. P5 is PENDING: it needs the owner to accept or reject the recorded S16 exception for upstream DNS lookups in E12/OWN. Nothing is pushed. The fork branch name is `staged/compaction-hook-salvage` (OD-0 resolved by the rename). The receipt freeze (P8) and the blind exact-head verification (P10) have not happened.

## Links

- **Upstream verdict / RFC:** NousResearch/hermes-agent#64231. teknium1's batch-disposition table (2026-08-13) says of PR #53806: "SALVAGE … rename to observer form `on_compression_start` (or keep `pre_` only if it becomes a genuine control point with fail-closed semantics)". The same table folds #8643 into the #53806 family.
- **Named consumer:** NousResearch/hermes-agent#118382 (carlosrenatoy). There is no plugin signal at compaction, so providers infer it from a turn-count drop. A scoping correction in that thread says MemoryProvider already has `on_pre_compress` + `prefetch`, so the remaining gap is plain plugins.
- **Related asks:**
  - NousResearch/hermes-agent#93389 (the issue behind #93391)
  - NousResearch/hermes-agent#125384 (compaction hook for preference auto-execution)
  - NousResearch/hermes-agent#119317 (the task-aware keep/drop issue behind #119347)
  - NousResearch/hermes-agent#8643 (`on_context_window_update`)
- **Speculative-hook precedent:** NousResearch/hermes-agent#59758 was closed by teknium1 on 2026-07-22: "hooks land with a real consumer, not ahead of one".
- **Fork boards:** kvnloo/hermes-agent#402 (salvage board) is closed. Its rows went upstream today as NousResearch/hermes-agent#130139 (9 rows, none about compaction; 0 comments at 2026-10-01T13:41Z). kvnloo/hermes-agent#403 became NousResearch/hermes-agent#130140 (close wave). kvnloo/hermes-agent#404 is the staged-PR queue (39 rows); this item is not a PR, so it gets no row there. No kvnloo/hermes-agent issue or PR exists for this item, and no campaign thread has been created (OD-9).
- **Fork branch (after the owner's push):** https://github.com/kvnloo/hermes-agent/tree/staged/compaction-hook-salvage, one commit, https://github.com/kvnloo/hermes-agent/commit/111f361fb0003405e4724b4c6523f6ce5d118c22. body.md links both.

## Invariant

A plugin subscribed to the local compaction observer is told about a local compaction exactly once. The call comes after the compacted transcript is durable in state.db and, for a manual `/compress`, after its host commits. The plugin is never told about an attempt that did not commit, and it can neither break nor change the compaction.

"Did not commit" means four distinct paths, each a case in the test:

- a failed summary that aborts under `compression.abort_on_summary_failure: true`;
- the commit site's would-grow refusal (the fallback summary would grow the transcript);
- a SessionDB write failure;
- a manual compress the host discards. Here the compacted rows *are* written to state.db; only the host's discard means the compaction did not commit for the host, and the case asserts both.

With the default `abort_on_summary_failure: false`, a failed summary does **not** abort: the compressor inserts its deterministic fallback summary and, on a realistic window, commits it. That is a committed compaction, and the observer correctly fires once. This is **probe-only, not a case in the committed test**: probe scenario `fallback_committed`, 61 messages in, payload tokens 75,000 → 30,598 on `c53806-foldin-r4` (public in `receipts/F05-f05-r4.json` → `fallback_commit_probe`).

**Real call path exercised:**

1. `AIAgent._compress_context`
2. `agent.conversation_compression.compress_context`
3. `_run_summary_phase`: the real `ContextCompressor.compress`, with only `_generate_summary` replaced
4. `_commit_compaction`: the real `SessionDB.archive_and_compact` / `publish_compression_child`, with the anti-growth guard
5. `_finish_compaction_boundary`
6. `_notify_context_engine_compression_complete`, either directly or deferred until `finalize_context_engine_compression_notification`

Dispatch is the real `PluginManager.invoke_hook` on a fresh manager. The seam is never mocked. Agent init's model-metadata lookups are stubbed at their network boundary: `patch("agent.context_compressor.get_model_context_length", return_value=256_000)` pins the window (the idiom the sibling compression tests use; 256,000 is the value the unpinned lookup fell back to), and `patch("agent.agent_init.fetch_model_metadata", return_value={})` makes the once-per-process `openrouter-prewarm` thread that `AIAgent` init starts for an OpenRouter base URL run a stub. Round 1 had only the first patch, so the prewarm thread still made one DNS lookup per pytest worker; the r3 guard hid it by not starting that thread. Measured under the r4 guard, which suppresses nothing: the round-1 test file made 2 blocked `getaddrinfo('openrouter.ai')` per `-j 2` run, all on thread `openrouter-prewarm`; the round-2 file makes 0 (`receipts/SANDBOX-guard-canary-r4.json` → `contract_test_prewarm_check`).

## Member branches

All refs live in the scratch mirror `h.git`. PR heads were fetched read-only to `refs/xf/pr/<n>`. Round-2 arms are pinned at `refs/xf/arms/compaction-hook-salvage/<arm>-r4`, all on the staging commit `111f361fb0`. Their diffs against the staging commit are in `patches/arm-<arm>.patch`. Round-1 patches moved to `patches/r3/`, round-0 patches are in `patches/r2/`, and older refs are kept unchanged.

| ref | sha | role | status vs main `a3b56cac95` |
|---|---|---|---|
| `refs/heads/staging/compaction-hook-salvage` | `111f361fb0` | **staging commit**: contract test only (blob `6e8fca00bb`, +152), author Kevin Rajan, trailers for ledfoot631, Baophan00, clomp | 1 commit on main; merge-tree clean (also on 666b9f04c4); push-trigger scan of the 52 workflow files on this tree: 0 match `staged/compaction-hook-salvage` |
| NousResearch/hermes-agent#53806 (`refs/xf/pr/53806`) | `6067388d0c` (compression commit `e560abd758`) | **carrier** (ledfoot631), named in the SALVAGE verdict | CONFLICTING in 11 files (agent/agent_init.py, agent/conversation_compression.py, agent/shell_hooks.py, gateway/slash_commands.py, hermes_cli/cli_commands_mixin.py, hermes_cli/hooks.py, hermes_cli/plugins.py + 4 test files); 33.6k behind. Hand-ported as `c53806-handport-r4` `58d12e4a86`: the compression commit's conversation_compression.py + plugins.py hunks, with the start-side call in `_run_summary_phase` and `task_id` passed in (+3/-1 over the round-1 hand-port) |
| `c53806-foldin-r4` | `c915bb4f1a` | **carrier + fold-in**, the proposed final shape | vs staging commit: +65/-12 in agent/conversation_compression.py, hermes_cli/plugins.py, hermes_cli/hooks.py, website/docs/user-guide/features/hooks.md (`patches/arm-c53806-foldin.patch`) |
| NousResearch/hermes-agent#93391 (`refs/xf/pr/93391`) | `9da3734b8e` | competitor (clomp42, `pre_compression`) | conflicts in 3 website docs files only; code + tests re-applied 3-way clean (`c93391-code-r4` `7ed14fd149`, same patch-id as rounds 0 and 1) |
| NousResearch/hermes-agent#118847 (`refs/xf/pr/118847`) | `222e3e26c3` | competitor (Baophan00, `post_compaction` for #118382) | CONFLICTING, 1 hunk in agent/context_compressor.py; hand-port re-applied (`c118847-handport-r4` `3f435c525f`, same patch-id) |
| NousResearch/hermes-agent#119347 (`refs/xf/pr/119347`) | `4a527fc35d` | directive/transform variant (fangliquanflq); excluded from the observer slot (#120582 risk) | CONFLICTING, 3 semantic hunks at the #61932 pruned-copy seam; no safe port, not materialized |
| NousResearch/hermes-agent#125881 (`refs/xf/pr/125881`) | `d3fdffcf82` | fail-closed policy-hook carrier (pstarkgit) | merge-tree clean; `c125881-merge-r4` `8a33b22c18` (same patch-id) |
| NousResearch/hermes-agent#122522 (`refs/pr/122522`) | `f596584b01` | not a member (adjacent summary_source=original work) | n/a |

- **Fold-in variants:** `foldin-ref-r4` `4aa5577d5b` (fold-in without the carrier's start-side hook or its `task_id` pass-through; same patch-id as `foldin-ref-r3`), `foldin-bounded-r4` `c113f73be5` (+ `on_compression_complete` in `_HOOK_TIMEOUT_BOUNDED_HOOKS`)
- **Negative controls:** `neg-prefire-r4` `15f7cf5516` (call moved before `_commit_compaction`), `neg-nodefer-r4` `2ecc4bc579` (deferral bypassed)
- **Per-hunk sabotage of the fold-in:** `sab-h1-observer-call` `457eb2db2d`, `sab-h2-queue-payload` `6b8861e2ba`, `sab-h3-tokens-before` `bcc2a59d4b`, `sab-h4-tokens-after` `a5ad7eefdb`, `sab-h5-valid-hooks` `775847aaba`, `sab-h6-keep-carrier-post-commit` `ba87f0a882`, `sab-h7-payload-and-docs` `69e6e95452` (all `-r4`)

`c53806-handport-r4` applies the round-1 hand-port patch to the staging commit and adds the `task_id` pass-through by hand. `c53806-foldin-r4` is that commit plus `patches/r3/foldin-on-c53806-handport.patch` (applies unchanged); the fold-in alone is `patches/foldin-on-c53806-handport.patch`. Every other r4 arm is built by `tools/chs_build_arms_r4.py`: either one textual mutation of `c53806-foldin-r4`, or a competitor's round-0 diff re-applied onto the new staging commit with `git apply -3`.

## First-slice status

**Committed.** One commit, `111f361fb0003405e4724b4c6523f6ce5d118c22`, on main `a3b56cac95`:

- Subject: `test(compression): pin the plugin observer contract at the local compaction boundary`
- Author: `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`; trailers `Co-authored-by` ledfoot631, Baophan00, clomp (see [credit]) and the Claude Code attribution line.
- Diff: 1 file, +152. It is exported as `patches/staging-compaction-hook-salvage.patch` (`git format-patch -1`).
- The local branch `staging/compaction-hook-salvage` was forced from round 1's `de819a7d06` to this commit. The round-1 patch is kept at `patches/r3/`.
- Message corrections in round 2: the three failure cases (aborted summary, would-grow refusal, write failure) check the unchanged session id and state.db rows, and the first two also the compressor's flag; the manual-discard case is described separately, because there the compacted rows *are* written and the case asserts that; the network sentence now says the metadata lookups are stubbed (window pinned, prewarm stubbed); the fallback-commit sentence is gone, because no case covers it.

`tests/agent/test_compaction_observer_hook_contract.py` holds 2 behaviour-contract tests with 7 parametrized cases:

- **`test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred]`**
  - The observer fires exactly once.
  - When it runs, the session id it is handed already holds the compacted transcript in state.db.
  - The payload carries `session_id` (current), `old_session_id`, `in_place`, and `0 < tokens_after < tokens_before`.
  - A manual compress fires only after `finalize(committed=True)`.
  - With a raising subscriber and a subscriber returning `{"action": "block"}` both registered, the compacted messages and the rebuilt system prompt match a no-subscriber run byte for byte. This covers fail-open, observer-only and unchanged outbound bytes.
- **`test_observer_is_silent_when_nothing_commits[summary_aborted|would_grow_refused|commit_failed|manual_discarded]`**
  - `summary_aborted`: `abort_on_summary_failure = True` and the summary returns None. Precondition: the compressor reports `_last_compress_aborted`.
  - `would_grow_refused`: the default config and the summary returns None. The fallback summary would grow this small window, so the commit site refuses it. Precondition: `_last_compress_refused_would_grow`.
  - `commit_failed`: `archive_and_compact` raises.
  - Precondition for these three: the session id is unchanged and state.db's rows for it equal the rows before the attempt.
  - `manual_discarded`: the host finalizes `committed=False`, and a later `finalize(committed=True)` cannot revive the call. The unchanged-rows check is skipped here on purpose; instead the case asserts `_durable_summary(db, agent.session_id)`: the compacted rows were written, and only the host discarded the compaction.

The hook name is the single constant `HOOK = "on_compression_complete"`. The production change is **not** on the staging branch. It is offered to the carrier as one production diff on main: `patches/arm-c53806-foldin.patch`. That diff is the carrier hand-port plus the fold-in, byte-identical to `git diff 111f361fb0 c53806-foldin-r4`, and it applies to main once the staging commit (test only) is in; body.md carries it inline in a collapsed block. `patches/foldin-on-c53806-handport.patch` is only a reading aid: it is relative to our hand-port, not to #53806's head. The minimal reference without the carrier's start-side hook is `patches/foldin-ref-on_compression_complete.patch`. The optional bounded variant is `patches/arm-foldin-bounded.patch`.

The selection's contract lists `new_session_id` separately. Here `session_id` is the post-commit id, which is what `session_id` means in every shipped hook. `new_session_id` is not duplicated.

## Route and carrier choice

**Route: salvage-row.** Five open external PRs carry a compression hook (P2 → salvage). Our part is a `Co-authored-by` fold-in: the contract test, plus the post-commit placement, payload, docs row and hooks-CLI payload.

**Carrier: #53806 (ledfoot631) + fold-in.** It is the only candidate whose hook fires at the right moment: its post-commit plugin `on_session_start(boundary_reason="compression")` runs after the durable commit and stays silent on uncommitted attempts. The verdict also names it.

It misses three things:

- It ignores the manual-host deferral: it fires before the host commits, and after a discard.
- It carries no `in_place` or token fields.
- Reusing `on_session_start` delivers compaction events to every existing session-start subscriber.

The fold-in fixes all three:

- It moves the call into `_notify_context_engine_compression_complete`. That function is the fence the context engine already uses, so the observer inherits the deferral.
- It names the hook `on_compression_complete` and adds the payload. The payload takes `tokens_before`/`tokens_after` from #118847's post-compaction design and `in_place` from #93391, so both authors are credited (see [credit]).
- It adds the hook to `VALID_HOOKS` with a comment, to the "Shipped plugin-hook catalog" table in `website/docs/user-guide/features/hooks.md`, and to `hermes_cli/hooks.py` `_DEFAULT_PAYLOADS`. `VALID_HOOKS` doubles as the shell-hook allow-list, so `hermes hooks test on_compression_complete` gets the runtime payload shape.

**How the hand-port differs from #53806's compression commit (round-2 disclosure).** Round 1 said the fold-in "leaves that hook exactly as #53806 wrote it". That was not true of the hand-port it sits on, and it is now disclosed in body.md too:

- *Location.* #53806 calls `pre_context_compression` inside `compress_context`, right after the memory providers' `on_pre_compress` and right before `compressor.compress(...)`. Current main moved both of those into `_run_summary_phase`, so the hand-port puts the call there, after `_pre_compress_memory_context` and right before the summarizer dispatch. Same relative order, different function.
- *Payload.* `task_id` is not in `_run_summary_phase`'s scope on main. Round 1 dropped the kwarg. Round 2 passes `task_id` into `_run_summary_phase` (signature + call site, +2 lines), so the payload keys are #53806's: `session_id, task_id, conversation_history, approx_tokens, focus_topic, force, model, platform, conversation_id`.
- *Left out.* The commit's `agent/agent_init.py` hunk (plugin `on_session_start` at agent init), its `hermes_cli/hooks.py` hunk (a `pre_context_compression` test payload) and its test hunk, plus the separate resume-hook commit `6067388d0c`.

**#53806's own tests (round-2 fairness check, OWN r4).** Its compression commit adds three tests to `tests/run_agent/test_compression_boundary_hook.py`. Main moved that file to `tests/agent/`, where the hunk no longer applies, so they were ported verbatim into a factory-only file (`tools/chs_c53806_own_tests.py`) and run on base, the hand-port and the fold-in; a second port (`tools/chs_c53806_own_tests_adapted.py`) makes two marked drift edits.

| #53806 test (from e560abd758) | base (verbatim / adapted) | hand-port (verbatim / adapted) | fold-in (verbatim / adapted) | why |
|---|---|---|---|---|
| `test_plugin_on_session_start_called_on_agent_init` | FAIL / not run | FAIL / not run | FAIL / not run | needs the left-out `agent/agent_init.py` hunk; not adapted |
| `test_pre_context_compression_plugin_hook_fires_before_compress` | FAIL / FAIL | FAIL / PASS | FAIL / PASS | verbatim: main hands the hook the transcript with the store's row metadata (`_db_persisted`, `_row_id`, `message_uid`, `timestamp`, `_db_row_snapshot`), so `conversation_history == messages` fails while `session_id`, `task_id` and `approx_tokens` match (same result with the call placed in `compress_context`, tried while building). Adapted: compares role/content |
| `test_plugin_on_session_start_called_with_compression_boundary` | FAIL / FAIL | FAIL / PASS | FAIL / FAIL | verbatim: a one-message compaction no longer commits on main, so there is no post-commit call. Adapted: 10 messages, as main's own boundary test uses. Fold-in: fails by design (the call is replaced) |

Totals (passed/failed): verbatim base 0/3, hand-port 0/3, fold-in 0/3; adapted base 0/2, hand-port 2/0, fold-in 1/1. These cells are INFRA under strict S16: like most upstream tests, the carrier's tests do not pin the context window, so they make blocked DNS lookups (20, 20, 20, 14, 7, 14).

The fold-in deliberately fails the boundary test: it replaces that `on_session_start(boundary_reason="compression")` call with `on_compression_complete`. The `pre_context_compression` test passes on both arms once the drift edit is applied, which shows the `task_id` pass-through keeps the carrier's payload.

**What the fold-in does not do.** It does not touch the start-side `pre_context_compression`. No contract case covers it, and #118382 needs only the post-commit signal. Its name (#64231 asks for `on_compression_start`), its payload, its missing docs row and hooks-CLI payload, and whether it stays at all are maintainer decision (a). `foldin-ref-r4` shows the fold-in passes 7/7 without the start-side hook (and without the `task_id` pass-through).

The table below is OBSERVED in **F05 r4** (main `a3b56cac95`, staging commit `111f361fb0`): every arm ran in the same run under the r4 egress guard, with 0 blocked connect or DNS attempts from any thread in its 78 cells. The clause probe (`tools/chs_clause_probe_r4.py`, 9 scenarios per arm) supplies the timing and fire columns. "Own name" means the contract test with `HOOK` set to the carrier's hook name, 3 reps. The `#53806 pre` row describes our hand-port of that call (see the disclosure above), not #53806's head, which does not apply to main.

| carrier | merge | hook (own name) | fires relative to summary / commit | 4 committing scenarios (rotated, in-place, manual, fallback commit) | 5 non-committing scenarios (aborted summary, would-grow refusal, in-place write fail, rotation write fail, manual discard) | manual-host deferral | payload keys | contract, own name |
|---|---|---|---|---|---|---|---|---|
| main | n/a | none | never | 0/4 fire | silent (trivially) | n/a | n/a | 4/7 pass (RED) |
| #53806 post | hand-port | `on_session_start` + `boundary_reason="compression"` | after durable commit | fires once, 4/4 | 4/5 silent; fires on manual discard | ignored (fires before finalize) | session_id, old_session_id, boundary_reason, platform, model, context_length, conversation_id | 3/7 |
| #53806 pre (our hand-port) | hand-port, call in `_run_summary_phase`, `task_id` passed in | `pre_context_compression` | before summary | fires once, 4/4 | 0/5 silent | ignored | session_id, task_id, conversation_history, approx_tokens, focus_topic, force, model, platform, conversation_id | 0/7 (start-side by design) |
| #93391 | docs-only conflicts | `pre_compression` | before summary | fires once, 4/4 | 0/5 silent | ignored | session_id, messages, platform, compression_count, in_place | 0/7 (start-side) |
| #118847 | 1-hunk hand-port | `post_compaction` | after summary, **before** commit | fires once, 4/4, transcript not yet durable | 1/5 silent (aborted summary only); fires on the would-grow refusal (after_tokens 3,365 > before_tokens 1,672), both write failures and the manual discard | ignored | session_id (pre-rotation id), before_tokens, after_tokens, messages_removed, reason | 1/7 |
| #125881 | clean | `pre_compression_commit` (policy) | after summary, before commit | fires, but a non-`allow` subscriber **blocks** the compaction (state.db rows 13 → 0 vs baseline, output changed) in 4/4 | 1/5 silent (aborted summary only) | ignored | session_id, state{counts} | 1/7 (fail-closed control point by design) |
| #119347 | 3 semantic conflicts | `transform_compaction_input` | before summary (transform) | not run | not run | n/a | n/a | not run |
| **#53806 + fold-in** | built | `on_compression_complete` | after durable commit; after host finalize | fires once, 4/4 | 5/5 silent | honoured | session_id, old_session_id, in_place, tokens_before, tokens_after, platform | **7/7, 3/3 reps** |

Payload keys exclude `telemetry_schema_version`, which the dispatcher adds to every hook call; the #118847 token figures come from its own-name contract run (assertion text in the F05 r4 receipt).

Each other carrier's own tests still pass on its arm. This is a fairness check: each carrier proves its own, different contract (OWN r4).

- #93391: `test_compression_rotation_state.py`, 43/0 (base 40/0). Both cells INFRA under strict S16 (119 and 113 blocked DNS lookups from that upstream file).
- #118847: `test_post_compaction_hook.py`, 7/0, 0 lookups. These tests mock `hermes_cli.lifecycle.invoke_hook`, which is the seam itself.
- #125881: `test_context_governance.py`, 9/0, 0 lookups.

**WAVE row:** proposed text in `body.md`. Carrier #53806 + fold-in. Close #93391 and #118847 after it merges; both are credited on the fold-in, because their designs are reused. Keep #125881 and #119347 open: they are different contracts and compose with the observer.

## Evidence

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| F05 r4: carrier A/B, 9 arms with the clause probe + 9 negative/sabotage arms, main a3b56cac95 | `receipts/F05-f05-r4.json` | KEEP | OBSERVED | 3 reps × 7 cases per arm (+3 own-name reps per carrier), 9 probe scenarios per probed arm; 78 cells, 0 INFRA (0 connect, 0 dns from any thread) | see the carrier table. base 4/7 (RED); c53806-foldin, foldin-ref, foldin-bounded 7/7; neg-prefire 1/7; neg-nodefer 5/7; sabotage h1 4/7, h2 6/7, h3 4/7, h4 4/7, h5/h6/h7 7/7 (unpinned). All reps agree. Fallback-commit probe: fires once, tokens 75,000 → 30,598 |
| E12 r4: guards + 17 adjacent files on base, c53806-foldin and foldin-bounded | `receipts/E12-e12-r4.json` | **INFRA** (strict S16); PASS only if the owner accepts the recorded exception | OBSERVED (+ one structural note) | 1 run per arm per harness; 12 cells, 6 INFRA | replay_gates 11/11 PASS on all three, equal verdict maps, 0 lookups. ab_checkpoint_preflight local compress calls identical (capture 0/0 cli and gateway, restore 0, over_threshold 0 then 1), 0 lookups. test_region_scoping ALL PASS (2 lookups per arm). Adjacent 17 files: base 302 / 3 / 2 skipped (the 3 are the new test) → 305 / 0 / 2 on both fold-in arms; 231 blocked DNS lookups per arm (224 from 7 sibling test files on the main thread, 7 on the openrouter-prewarm thread); the per-file attribution is identical on base and both fold-in arms. Observer fires are 0 in replay_gates and the preflight by construction (no SessionDB in their real-compression scenarios; the preflight stubs `_compress_context`), so 0 is not a native-route measurement |
| PROOF r4: gate columns | `receipts/PROOF-r4.json` | **INFRA** (strict S16); PASS if the exception is accepted | OBSERVED | aggregation of F05 r4 + E12 r4 | RED marker matched; GREEN 3/3; NEG RED; unpinned hunks listed |
| OWN r4: carriers' own tests on their arms, incl. #53806's ported tests | `receipts/OWN-own-r4.json` | n/a (fairness) | OBSERVED | 10 cells, 8 INFRA under strict S16 | 43/0 (#93391), 7/0 (#118847), 9/0 (#125881); base rotation_state 40/0; #53806 verbatim 0/3 on every arm, adapted 2/0 on the hand-port and 1/1 on the fold-in (see the #53806 table) |
| Guard canary r4 + prewarm check | `receipts/SANDBOX-guard-canary-r4.json` | PASS | OBSERVED | 5 cases + 2 prewarm runs | 5/5: connect to 1.1.1.1:443 refused, getaddrinfo('example.com') refused, loopback connect and localhost DNS still work, a thread named openrouter-prewarm starts and its lookup is refused and logged with its name; guard log exactly connect 1, dns 2 (1 on openrouter-prewarm). Prewarm check: round-1 test file 2 lookups (all openrouter-prewarm), round-2 file 0 |

Superseded (kept as history, re-labelled): the r3 receipts (F05, E12, OWN, PROOF, canary) were issued under the r3 guard, which refused to start the `openrouter-prewarm` thread. That hid the contract test's own lookup, so F05 r3's "0 dns" and the S16-exception bullet "the new contract test itself makes 0 lookups" were not true measurements. `tools/chs_supersede_r3.py` re-labels F05 r3 INFRA (all 78 cells logged `prewarm_suppressed`), E12 r3 and PROOF r3 INFRA, annotates the false bullet in E12/OWN r3, and points each at its r4 successor; measured values are kept. F05 r1, F05 r2, E12 r2, OWN r1 and PROOF r2 stay **INFRA** under FACTORY S16, as re-labelled in round 1 (`tools/chs_supersede_r1r2.py`): their guard refused connects but not DNS lookups, and E12 r2/OWN r1 logged blocked connects per run, not per cell. The r1 canary is PASS for connect() only.

## Experiments run ($0 only)

- **Chain.** `bash tools/chs_run_all_r4.sh $WORKTREE $TESTHOME $PY` ran every step below strictly in sequence (one isolated test HOME, one guard log). Stdout: `raw/run-all-r4.stdout` (private).
- **F05 r4 (carrier A/B).** `python3 tools/chs_ab_runner_r4.py --worktree $WORKTREE --run-id f05-r4 --arms "$(cat raw/f05-r4.arms)" --reps 3 --testhome $TESTHOME --python $PY`, then `--run-id f05-r4s --arms "$(cat raw/f05-r4s.arms)" --skip-probe` for the negative and sabotage arms. Arms were built by `python3 tools/chs_build_arms_r4.py $WORKTREE 111f361fb0 c915bb4f1a`. The probe is `tools/chs_clause_probe_r4.py`: the r3 probe plus the same prewarm stub as the test. Raw logs are in `raw/f05-r4/` and `raw/f05-r4s/` (private).
- **E12 r4 (guards + adjacent).** `bash tools/chs_guards_r4.sh <arm> <commit> e12-r4 $WORKTREE $TESTHOME $PY` runs `evals/token_accounting/replay_gates.py` and `evals/native_compaction/ab_checkpoint_preflight.py` through `tools/chs_guard_wrap_r4.py` (egress guard, observer counter), then `evals/compaction/test_region_scoping.py`, then the same 17 adjacent test files as r3. Arms: base `111f361fb0`, `c53806-foldin-r4`, `foldin-bounded-r4`. Each harness's guard log and stack dump are kept per cell; `tools/chs_dns_attribution_r4.py` attributes each lookup to thread, test file and upstream source.
- **OWN r4.** `bash tools/chs_own_r4.sh $WORKTREE $TESTHOME $PY`: each competitor's own test file on its r4 arm, base for rotation_state, and #53806's ported tests (verbatim and drift-adapted) on base, `c53806-handport-r4` and `c53806-foldin-r4`.
- **Guard canary r4.** `tools/chs_guard_canary_r4.py` copied into the worktree and run through `scripts/run_tests.sh`.
- **Disk-full re-run.** The shared `/tmp` tmpfs that holds the isolated test HOME filled up at 13:20:44Z, during the last OWN cell (`c53806-foldin-own-adapted`: a guard log write failed with ENOSPC) and before the canary (its worktree checkout failed). `tools/chs_rerun_r4_tail.sh` re-ran both at 13:39Z on the right commits with no ENOSPC; both results match the first attempts, which are kept privately under `raw/own-r4/enospc-1/` and `raw/guard-canary-r4-enospc-1/`. No earlier cell logged ENOSPC (grep of every r4 log), and the receipts record the re-run.
- **Prewarm check.** The round-1 and round-2 test files, each alone on main `a3b56cac95` under the r4 guard (`raw/prewarm-r4/`, private; summarised in the canary receipt).
- **Isolation for every run:**
  - HOME = `$S/testhome-sf-compaction-hook-salvage`; HERMES_HOME = `$HOME/.hermes`.
  - `HERMES_PYTHON` points at the live venv's interpreter, used read-only as an interpreter only. `run_tests.sh` uses `env -i` and `-j 2`.
  - The r4 egress guard `tools/chs_egress_guard_r4.py` is loaded through the isolated HOME's `pytest_live_guard.py` shim. It refuses non-loopback `connect`/`connect_ex` and non-loopback `getaddrinfo`/`gethostbyname*`, logs each refusal with its thread name, and suppresses nothing (r3's guard also refused to start the `openrouter-prewarm` thread). A cell with any `connect` or `dns` line is INFRA (S16).
  - Result: F05 r4 had 0 `connect`, 0 `dns` and 0 INFRA cells in 78 cells, with nothing suppressed. E12 r4 had 0 `connect`; replay_gates and ab_checkpoint_preflight had 0 `dns`. The adjacent cell made 231 blocked DNS lookups per arm and test_region_scoping made 2; OWN r4 had 8 of 10 cells with lookups. All come from upstream code this item does not touch (or the carrier's own tests): the model-metadata GET at `AIAgent` init in tests that do not pin the window, the `openrouter-prewarm` thread, and the OpenRouter video-catalog GET while tool definitions are built. Per-cell attribution (`receipts/E12-e12-r4.json` → `egress.dns_attribution`, from `tools/chs_dns_attribution_r4.py`) is identical on base and the fold-in arms. Under strict S16 those cells are INFRA, so E12 r4 is INFRA (6 of 12 cells); see the next section.
  - There is no bwrap or netns: FACTORY §6 layer 1 was not used. This is the in-process layer only, recorded in each receipt's `env.sandbox`.
- **Cost:** $0, T1, cpu lane, 0 GPU-s.

## Recorded S16 exception (owner decision; not accepted)

FACTORY S16 says every blocked exec or connect fails the cell as INFRA, and defines no exception. The E12 adjacent and region-scoping cells and some OWN cells contain DNS lookups that the guard refused, all from upstream code this item does not change (or, for the #53806 port, from the carrier's own tests, which do not pin the window): the model-metadata GET at `AIAgent` init, the `openrouter-prewarm` thread (now visible, 1 per pytest worker process), and the OpenRouter video-catalog GET while tool definitions are built. The counts are identical on base and the fold-in arms, every path falls back, there are 0 connects, and the new contract test itself makes 0 lookups under the r4 guard. The exception text is in `receipts/E12-e12-r4.json` → `egress.s16_exception`. **Strictly, E12 r4 is INFRA (6 of 12 cells) and so is PROOF r4.** If the owner accepts the exception, both read PASS (`verdict_if_s16_exception_accepted`) and P5 can move to PASS; if the owner rejects it, the adjacent set needs a run where those upstream lookups cannot happen (a netns, or a session-wide metadata stub), and P5 stays PENDING.

## Experiments queued (not run)

None of this item's gates needs a T2 or T3 experiment, because the contract does not depend on the model. Queued for completeness:

1. **T1 ($0, recommended before posting): consumer end-to-end for #118382.**
   - Setup: a minimal out-of-tree plugin subscribes to `on_compression_complete`, flags the session, and re-injects a context block through `pre_llm_call` on the next turn. It is driven through the real turn loop against the loopback fake provider from `evals/token_accounting/replay_gates.py`, with `session_db` set so the commit is durable.
   - Command, after writing `tools/chs_consumer_e2e.py`: `env -i PATH=/usr/bin:/bin HOME=$TESTHOME HERMES_HOME=$TESTHOME/.hermes $PY tools/chs_guard_wrap_r4.py <worktree at c53806-foldin-r4> tools/chs_consumer_e2e.py raw/consumer/counts.json --out raw/consumer/result.json`
   - Pass: exactly one re-injection after each committed compaction, none after a refused one.
2. **T1 ($0, only if the owner rejects the S16 exception): adjacent set without upstream lookups.** Re-run the 17 adjacent files with a session-wide conftest stub for `agent.model_metadata.fetch_model_metadata` and the video catalog, or inside a network namespace, on base and `c53806-foldin-r4`.
3. **T2 (local GPU, strictly serial, gated on OD-1 because `MINIMUM_CONTEXT_LENGTH = 64_000` exceeds the 8K router presets): real-summarizer smoke.**
   - Setup: the same probe with `_generate_summary` left real, and `auxiliary.compression` pointed at a ≥64K local preset in the arm's own `$HERMES_HOME/config.yaml` (not an env var).
   - Command: `flock <gpu lock> env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes-t2 HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 1 tests/agent/test_zz_chs_clause_probe.py -q`, with sidecar `{"hook": "on_compression_complete", "out": "raw/t2/probe.jsonl", "real_summary": true}`. The `real_summary` switch still has to be added to `tools/chs_clause_probe_r4.py`.
   - Expected: identical clause verdicts.
4. **T3:** none.

## Acceptance gates (selection)

| gate | status | evidence |
|---|---|---|
| Contract test is RED on main (no hook) and GREEN on the chosen carrier, or carrier plus fold-in | **met** | RED 3 of 7 failed × 3 reps on a3b56cac95. GREEN 7/7 × 3 reps on #53806 + fold-in (`c53806-foldin-r4`). F05 r4, PROOF r4 |
| Negative control: moving the fire before the commit makes the test fail | **met** | `neg-prefire-r4`: 6 of 7 failed × 3 reps |
| replay_gates PASS is unchanged | **met** | E12 r4 (replay_gates cells: 0 blocked attempts) |
| ab_checkpoint_preflight verdicts are unchanged | **met** | E12 r4 (preflight cells: 0 blocked attempts) |
| Observer-only (return ignored), unless the winner is the fail-closed pre_ variant | **met** | the winner is the observer; a `{"action": "block"}` return and a raising subscriber leave output byte-identical (contract case). #125881's fail-closed variant is recorded as a separate control point |
| The named consumer is cited (#118382) | **met** | body.md, this manifest |
| The disposition table is posted once (WAVE row) on #118382 or #53806 | **not met (owner action)** | text prepared in `body.md`. Posting is a GitHub write the factory does not perform; see [queue] for the target and the spray check |

## Gate checklist (FACTORY P1-P12)

| gate | status | basis |
|---|---|---|
| P1 Need | PASS | RED on a3b56cac95 (≤24 h); invalidate_on paths unchanged since e496ccc7d7; freshness re-check in [base] |
| P2 Ownership | PASS | external carriers → salvage-support; no claimant-lane, hold or Hermes-lane overlap; #118382's verbal claim has no PR; heads re-checked 2026-10-01T13:41Z |
| P3 Shape | **PENDING** | One invariant, a fire site and a named consumer (#118382). No new env var or config key, no shim. But AGENTS.md says "New behaviour goes in a new or topical sibling — never appended to a facade", and the fold-in appends the observer dispatch to `agent/conversation_compression.py`, which is already 4,579 lines on main (4,617 with the combined diff: +50/-12 there, including the carrier's `task_id` pass-through). It sits there because it must run inside the existing notify fence. A maintainer may want the dispatch in a `conversation_compression_*` sibling. That is surfaced as maintainer decision (d), and no sibling variant was built. `hermes_cli/plugins.py` is 2,331 → 2,341 (comment + entries). The staging commit adds only a new 152-line test |
| P4 Real path | PASS | real AIAgent/SessionDB/ContextCompressor/PluginManager; only the summary LLM call, the two init-time model-metadata lookups (window pin, prewarm stub) and, for one failure case, the SessionDB write are faked; seam not mocked |
| P5 Proof | **PENDING** | RED marker matched; GREEN 3/3; NEG RED; sabotage per hunk (h1-h4 re-RED; h5 VALID_HOOKS entry, h6 the carrier's on_session_start post-commit call kept, h7 hooks-CLI payload + docs row: unpinned and listed); guards equal; flaky=false (all reps agree); F05 r4 0 INFRA cells under a guard that suppresses nothing. Adjacent: 17 files identical to base apart from the new test, but those cells (and region scoping) carry upstream DNS lookups, so under strict S16 E12 r4 is INFRA. PASS only if the owner accepts the recorded S16 exception (round 1 scored PASS on that unaccepted exception; corrected) |
| P6 Numbers | N_A | no value claim |
| P7 Package | PENDING | one clean commit on fresh main with correct author/subject and trailers, merge-tree clean, 0 workflow matches. Push as `staged/compaction-hook-salvage` is an owner action (OD-0 resolved by the rename; OD-4 still decides whether the fold-in is pushed or stays a ledger patch / inline block) |
| P8 Freeze | PENDING | r4 receipts written with sha256 (front matter) in full xf.receipt.v1 form, repo-relative paths only; not frozen to z0evals |
| P9 Text | PENDING | body.md rewritten (template-free wave row, AI assistance disclosed, no @mentions, no bare fork links, branch linked, diff inline); needs an independent tone/jargon read |
| P10 Independent read | PENDING | round-0 verifier: accept=false; round-1 re-verifier: 7 problems; no blind re-verification of `111f361fb0` yet |
| P11 Demand | RECORDED | combined score 5.24; maintainer SALVAGE verdict; consumer #118382 |
| P12 Queue | PENDING | no fork board applies (see [queue]); owner posts once on #53806 or as a delta row on #130139, on a later day than today's waves |

## NOT_TESTED

- **Native and Codex app-server compaction.** Native means OpenAI Responses server-side compaction on gpt-5.6/Astra. Neither route has a client commit. `_route_codex_compaction` returns before `_commit_compaction`, and native checkpoint turns never call `_compress_context`: ab_checkpoint_preflight counts 0 calls on capture and restore. The observer therefore cannot fire on these routes by construction. That is a structural argument; no hook fire count was taken on a real native turn. Scope: local compressor only.
- **Agents without a SessionDB.** With `session_db=None` there is no durable commit, so neither the context engine nor the observer is notified. This is the same guard the context engine already has. It is not exercised; worth a maintainer note.
- **Micro-compaction and proactive-prune rewrites.** These are not compaction boundaries and are not exercised.
- **Real summarizer.** The summary is fixed text, or None for the failure scenarios. The payload does not depend on summary content.
- **Fallback-summary commit as a contract case.** It is observed only in the probe (`fallback_committed`: fires once on every fold-in arm; payload tokens in the F05 r4 receipt). It is not a case in the committed test, and the commit message no longer claims it is.
- **Host surfaces.** The manual deferral is exercised through `compress_context(defer_context_engine_notification=True)` + `finalize_context_engine_compression_notification`. It was not driven through `agent/conversation_compression_manual.py:compress_now`, `gateway/slash_commands_session.py`, `acp_adapter/commands.py` or TUI/Desktop.
- **Shell hooks.** VALID_HOOKS doubles as the shell-hook allow-list, so a `hooks:` config entry for `on_compression_complete` becomes valid, and `hermes hooks test` now has its payload. `tests/hermes_cli/test_hooks_cli.py` passes, but no shell hook was run against a real compaction.
- **The carrier's start-side hook.** `pre_context_compression` is hand-ported with #53806's payload (including `task_id`) but in `_run_summary_phase`, not `compress_context` (see the disclosure). It has no contract case, no docs-catalog row and no `_DEFAULT_PAYLOADS` entry (the carrier's own hooks.py hunk was left out of the hand-port). Its rename to `on_compression_start` is maintainer decision (a).
- **#53806's own tests.** Run, not ported into any commit: verbatim they fail on current main (agent-init hunk left out; store-row metadata in the transcript; a one-message compaction no longer commits). Only the drift-adapted port passes, and on the fold-in its boundary test fails by design (OWN r4). The agent-init behaviour (plugin `on_session_start` when an agent binds to a session) is not in the hand-port and is not tested.
- **Docs pages other than the hook catalog.** `website/docs/user-guide/features/plugins.md` keeps its own category list and a stale "27 lifecycle events" count on main. It points to the hooks.md catalog as canonical and was not edited.
- **Slow or hung subscriber.** In the fold-in, the observer runs synchronously while the compaction lease is still held, like today's context-engine callback, memory `on_session_switch` and `session:compress`. `foldin-bounded-r4` puts it in `_HOOK_TIMEOUT_BOUNDED_HOOKS` (worker thread, `plugins.hook_callback_timeout`, fail-open), and the contract still passes 7/7 × 3 reps there. An actual hang was not simulated.
- **Kernel-level sandbox.** There is no bwrap/netns (FACTORY §6 layer 1). The in-process guard cannot stop a native extension or a subprocess from reaching the network. None of the selected tests spawns one.
- **Credential, device, TTY and browser boundaries:** N/A.
- **Pre-guard exploratory runs (round 0).** The first exploratory RED/GREEN runs on 572e4f4fad (about 03:55-04:05 -0500) ran without any guard. The isolated home held no credentials; the key is the literal `test-key`. No round-2 receipt depends on them.
- **Static observation, unverified by test:** `session:compress` (`event_callback`) in `_finish_compaction_boundary` has no `session_commit_succeeded` guard, so it may fire for a failed split. Out of scope here.

## Origin action (owner only, not run)

1. Push `staging/compaction-hook-salvage` to the fork as `staged/compaction-hook-salvage` (`--no-follow-tags`) **before** posting, so body.md's branch and commit links resolve.
2. Post `body.md` once, as **one comment on NousResearch/hermes-agent#53806** (the SALVAGE carrier; preferred). The alternative is one delta-row comment on NousResearch/hermes-agent#130139, using the table row alone (keep the collapsed diff). Do not open a new wave issue. kvnloo opened four wave tables upstream in the last 24 h, two of them today, so post on a later day (see [queue].spray_check).

The fold-in is offered as one production diff on current main, inline in body.md: `patches/arm-c53806-foldin.patch` (#53806's compression commit hand-ported, plus the fold-in), applied on top of the test commit, with the trailers in [credit]. #53806's own head conflicts in 11 files and is 33.6k commits behind, so a diff relative to it, or to our hand-port alone, would not apply. No new PR and no slot.

## Next steps

1. **Owner:** decide the recorded S16 exception (accept → P5 PASS; reject → run queued experiment 2). Push as `staged/compaction-hook-salvage` (OD-0 resolved by the rename). Decide OD-4: push the fold-in on the carrier head, or keep the inline block.
2. **Blind exact-head verification (P10)** of `111f361fb0` by a different worker. Inputs: `patches/staging-compaction-hook-salvage.patch`, `patches/arm-c53806-foldin.patch`, and the oracle: RED on main with marker `on_compression_complete fired 0 times`; GREEN 7/7 on carrier + fold-in; prefire negative control RED; the contract test alone logs 0 lookups under a guard that suppresses nothing.
3. **Maintainer decisions to surface in the comment** (all four are in body.md):
   - (a) the start-side hook: keep #53806's `pre_context_compression`, rename it `on_compression_start` per #64231 (then add a contract case, a hooks.md catalog row and a `_DEFAULT_PAYLOADS` entry), or drop it from the PR (the `task_id` pass-through goes with it)
   - (b) manual-discard semantics (wait for the host, as the context engine does)
   - (c) whether to bound the hook under `plugins.hook_callback_timeout` (foldin-bounded)
   - (d) whether the observer dispatch should live in a `conversation_compression_*` sibling (AGENTS.md facade rule; resolves P3)
4. **Run the queued T1 consumer end-to-end** before posting. It answers the speculative-hook rule (#59758) with a working consumer.
5. **Freeze the cited r4 receipts (P8)**, and re-check freshness within 24 h of posting: `git merge-tree --write-tree main staging/compaction-hook-salvage`, then the RED cell.

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
