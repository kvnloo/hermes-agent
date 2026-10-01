+++
xf_staging = 1
id = "compaction-hook-salvage"
version = 2               # round-1 rebuild after the phase-3 verifier (accept=false on 8c834af1e4); local branch forced to the new commit as instructed, nothing was ever pushed
title = "One observer compaction hook: A/B five competing carriers per the #64231 SALVAGE verdict"
branch = "staging/compaction-hook-salvage"
branch_physical = "local ref staging/compaction-hook-salvage in the scratch mirror h.git, not pushed. It publishes to kvnloo/hermes-agent as staged/compaction-hook-salvage: the fork's legacy refs/heads/staging @28790e597c blocks staging/*, so OD-0 is resolved by this rename (ls-remote 2026-10-01T11:19Z: no refs/heads/staged/* on the fork)"
branch_sha = "de819a7d0660be8fd560c35bbc4c56676bc8408b"
status = "EVIDENCED"      # round-1 fixes done and re-proved; push (owner), receipt freeze (P8) and blind re-verify (P10) pending
route = "salvage-row"
promotion_form = "salvage-support"   # unchanged: five external PRs own the hook; our part is a Co-authored-by fold-in
feature = "compaction-lifecycle-hooks"
invariant = "A plugin subscribed to the local compaction observer is told exactly once per committed local compaction, after the compacted transcript is durable (and, for a manual /compress, after its host commits), never for an attempt that did not commit (a failed summary that aborts under compression.abort_on_summary_failure=true, the commit site's would-grow refusal, a SessionDB write failure, a discarded manual compress), and can neither break nor change the compaction. A failed summary under the default abort_on_summary_failure=false commits the deterministic fallback, and that commit is announced."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
fetched_at = "2026-10-01T11:04Z (main committed 2026-10-01T05:56:05-05:00)"
previous_base = "bafb42b431fca313471958fdf77f9c30e455f86b (round-0 staging commit 8c834af1e4; 31 commits before aea969677c, none touching an invalidate_on path)"
selection_base = "e496ccc7d7"
first_built_on = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (round-0 staging commit b3b8d73999)"
invalidate_on = ["agent/conversation_compression.py", "agent/context_compressor.py", "hermes_cli/plugins.py", "hermes_cli/plugins_dispatch.py", "hermes_cli/lifecycle.py", "agent/conversation_compression_manual.py", "hermes_state_messages.py", "hermes_state_compression.py", "hermes_cli/hooks.py", "website/docs/user-guide/features/hooks.md"]
drift_note = "None of the invalidate_on paths changed from bafb42b431 to aea969677c."
freshness_recheck = { main = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5", checked_at = "2026-10-01T12:13Z", commits_since_base = 8, invalidate_on_changed = false, merge_tree_clean = true }

[upstream]
issues = ["NousResearch/hermes-agent#64231", "NousResearch/hermes-agent#118382", "NousResearch/hermes-agent#8643", "NousResearch/hermes-agent#93389", "NousResearch/hermes-agent#125384", "NousResearch/hermes-agent#119317"]
eval_prs = []
carrier = { pr = 53806, author = "ledfoot631", head = "6067388d0c", compression_commit = "e560abd758", form = "hand-port of the compression commit + Co-authored-by fold-in; the fold-in leaves the carrier's start-side pre_context_compression as written" }
competitors = [
  { pr = 93391, author = "clomp42", head = "9da3734b8e", result = "0/7 under its own hook name: pre_compression fires before the summarizer on every attempt (start-side seam, same as #53806's pre hook)" },
  { pr = 118847, author = "Baophan00", head = "222e3e26c3", result = "1/7: post_compaction fires inside ContextCompressor.compress() before the commit, so it also fires for the would-grow refusal (after_tokens > before_tokens), failed SessionDB writes and a discarded manual compress; silent only when the summary aborts; session_id is the pre-rotation id" },
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
role = "carrier (compression commit of #53806, hand-ported: its agent/conversation_compression.py and hermes_cli/plugins.py hunks; its hermes_cli/hooks.py and agent/agent_init.py hunks and the 6067388d0c resume-hook commit are left out)"

[[donors]]
sha = "de819a7d0660be8fd560c35bbc4c56676bc8408b"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "fold-in: behaviour-contract test (staging commit) + post-commit placement, payload, hooks-catalog row and hooks-CLI test payload; offered as patches/arm-c53806-foldin.patch (carrier hand-port + fold-in as one production diff on main)"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[ownership]
searched_at = "2026-10-01T08:50Z-09:20Z; re-checked 2026-10-01T11:20Z (carrier and competitor heads unchanged, still OPEN; #118382 last comment 2026-09-22; no new compaction/compression hook PR created 2026-10-01)"
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
  { id = "F05/f05-r3", path = "receipts/F05-f05-r3.json", sha256 = "6859073f016f4b4d73476fbe0b22c576123f20bb42f5a29f9fef499f71ddcd97" },
  { id = "E12/e12-r3", path = "receipts/E12-e12-r3.json", sha256 = "beed843535649759952661f17d406cd86b42c224179c0d3399767a754b8da995" },
  { id = "PROOF/r3", path = "receipts/PROOF-r3.json", sha256 = "9b363d17240a807c67771d250c0d09fdfc5beff3268e6b24b2dae640409dcd68" },
  { id = "OWN/own-r3", path = "receipts/OWN-own-r3.json", sha256 = "4a93b603d66da7d54d55ddd5ee50ca0e65cf2b90c09a3cedb99ae4e6f06c364d" },
  { id = "SANDBOX/guard-canary-r3", path = "receipts/SANDBOX-guard-canary-r3.json", sha256 = "9f51b75a7cfc051e16c23193a7fb4c62afc73c84a97dfcafef20423940794d4c" },
]
superseded = [
  { id = "F05/f05-r1", path = "receipts/F05-f05-r1.json", sha256 = "85625ea19f2c27ebefaebef16d0f4249d0dcf4736c39c55ce3ae1adceb6adb06", verdict = "INFRA (S16)" },
  { id = "F05/f05-r2", path = "receipts/F05-f05-r2.json", sha256 = "f7044149577e55ff6d9cff55fa26b2306c68bf3b3bfbbdbd20f48a4f1d4b951b", verdict = "INFRA (S16)" },
  { id = "E12/e12-r2", path = "receipts/E12-e12-r2.json", sha256 = "9752f0f59ab600a36caded81b5a05d9254d1ce78188691f83bc49589d6226d3a", verdict = "INFRA (S16, unattributable)" },
  { id = "PROOF/r2", path = "receipts/PROOF-r2.json", sha256 = "b0aee1db3a713f6546d5d06e674f69c487e9b11024a32405205f549c60f4de0a", verdict = "INFRA" },
  { id = "OWN/own-r1", path = "receipts/OWN-own-r1.json", sha256 = "984100f78f4a693daf397867202447dd51efbbeb53ead7717f2028d33aad72de", verdict = "INFRA (S16, unattributable)" },
  { id = "SANDBOX/guard-canary", path = "receipts/SANDBOX-guard-canary.json", sha256 = "509e5bca29510c40c68ed7d9b571115e8026746bc880311b3d1b0c0c1f33f65c", verdict = "PASS (connect() only; DNS not guarded)" },
]
red = { test = "tests/agent/test_compaction_observer_hook_contract.py::test_observer_fires_once_after_the_durable_commit[rotated|in_place|manual_deferred]", main = "aea969677c", marker = "AssertionError: on_compression_complete fired 0 times", reps = "3/3 (4 passed / 3 failed each)", receipt = "F05/f05-r3" }
green = { arm = "c53806-foldin-r3 77bbc5f9a4", reps = "3/3 (7 passed / 0 failed each)", also = "foldin-ref-r3 3/3, foldin-bounded-r3 3/3", receipt = "F05/f05-r3" }
negative_control = { mutation = "hook call moved from the post-commit notify to just before _commit_compaction", result = "RED 6 of 7 failed, 3/3 reps", also = "manual deferral bypassed: RED 2/7; per-hunk sabotage: observer call removed RED 3/7, queue payload RED 1/7, tokens_before RED 3/7, tokens_after RED 3/7; VALID_HOOKS entry, keeping the carrier's on_session_start post-commit call, and the hooks-CLI payload + docs row stay GREEN (unpinned)", receipt = "F05/f05-r3" }
adjacent = { files = 17, base = "302 passed / 3 failed (only the new contract test's 3 fires-once cases) / 2 skipped", arm = "305 / 0 / 2 skipped on c53806-foldin and on foldin-bounded", identical_outside_new_test = true, receipt = "E12/e12-r3" }
guards = { replay_gates = "11/11 PASS on base, c53806-foldin and foldin-bounded; verdict maps equal", ab_checkpoint_preflight = "local compress-call counts equal to base (capture 0/0 cli and gateway, restore 0, over_threshold 0 then 1)", test_region_scoping = "ALL PASS on all three", receipt = "E12/e12-r3" }
egress = { F05 = "78 cells: 0 connect, 0 dns, 0 INFRA", E12 = "12 cells: 0 connect; replay_gates and ab_checkpoint_preflight 0 dns; the adjacent and test_region_scoping cells had 224 and 2 blocked DNS lookups per arm, all from upstream code (sibling tests' model-metadata and video-catalog GETs), identical on base and arms: 6 of 12 cells INFRA under a strict S16 reading, kept under a recorded S16 exception", OWN = "4 cells: the two test_compression_rotation_state cells had 112 and 118 blocked DNS lookups from that upstream file (same exception)", canary = "connect 1, dns 1, prewarm_suppressed 1, as designed", note = "the r3 guard blocks connect AND DNS and logs per cell; the contract test pins the context window (no model-metadata lookup at agent init); the harness does not start the openrouter-prewarm thread (prewarm_suppressed, at most one per pytest worker process). r1/r2 receipts are INFRA under S16 and superseded", receipts = "F05/f05-r3, E12/e12-r3, OWN/own-r3, SANDBOX/guard-canary-r3" }
quantitative = []
cache_read_ratio = { status = "N_A", why = "the observer fires after the sanctioned compaction cache break; compacted messages + system prompt asserted byte-identical with and without subscribers" }
route_scope = "local-compressor"
not_tested = ["native and codex_app_server compaction (structural only)", "session_db=None agents", "micro-compaction / proactive prune", "real summarizer", "per-host manual /compress handlers", "shell hooks (hooks-CLI payload added, no shell hook run)", "hung subscriber", "#53806's start-side pre_context_compression (no contract case; no docs row or hooks-CLI payload; rename left to the author/maintainers)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-compaction-hook-salvage", commit = "" }

[gates]
P1 = "PASS"
P2 = "PASS"
P3 = "PENDING"   # AGENTS.md facade rule: new behaviour is appended to agent/conversation_compression.py (4,579 -> 4,615 lines); surfaced as maintainer decision (d)
P4 = "PASS"
P5 = "PASS"
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

[merge_check]
main_sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
checked_at = "2026-10-01T11:10Z (re-checked 2026-10-01T12:13Z on main 040b6df2c4: clean)"
clean = true
tree = "98fd26c2f4 on aea969677c (equals the staging commit's tree); dd6813d7ac on 040b6df2c4"
recheck = "git merge-tree --write-tree main staging/compaction-hook-salvage"

[push]
fork_branch = "staged/compaction-hook-salvage"
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "body.md"
kind = "wave-row"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PASS (self-check: no envelope/lane/E##/F##/arm names in body.md)"
privacy_scan = "PASS (synthetic fixtures only; no session ids, home paths or message text)"

[queue]
board = "none. kvnloo/hermes-agent#402 (fork salvage board) was closed COMPLETED 2026-10-01T07:32Z: its 9 rows were posted upstream as NousResearch/hermes-agent#130139, and none of them is about compaction. This item is not a kvnloo/hermes-agent#404 row either: that queue lists 39 staged PR branches, and this item opens no PR"
position = "owner picks one: (a) one comment carrying body.md on the carrier thread NousResearch/hermes-agent#53806 (preferred: one concrete delta per thread), or (b) one delta-row comment on NousResearch/hermes-agent#130139. Never a new wave issue"
spray_check = "2026-10-01T11:20Z: kvnloo opened 5 upstream issues in the previous 24 h (#129760, #129761, #129963, #130139, #130140; 4 are wave tables, 2 of them posted 07:32Z today) and 4 PRs on 2026-10-01 (#129918, #129928, #130203, #130205). Another wave-style table the same day is high spray risk: post (a) or (b) on a later day, not today"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# One observer compaction hook: A/B five competing carriers per the #64231 SALVAGE verdict

**Promotion form:** salvage-support (route `salvage-row`, body kind `wave-row`). Unchanged in round 1: five external PRs own the hook, and our part is a `Co-authored-by` fold-in.

**Status:** EVIDENCED, version 2. Round 1 fixed every problem the phase-3 verifier listed (see "Round-1 fixes"). The staging commit was rebuilt on main `aea969677c` (`de819a7d06`), and the local branch was forced to it. RED, GREEN, negative controls, sabotage, guards and adjacent files were re-proved on that base. Nothing is pushed. The fork branch name is `staged/compaction-hook-salvage` (OD-0 resolved by the rename). The receipt freeze (P8) and the blind exact-head verification (P10) have not happened.

## Links

- **Upstream verdict / RFC:** NousResearch/hermes-agent#64231. teknium1's batch-disposition table (2026-08-13) says of PR #53806: "SALVAGE … rename to observer form `on_compression_start` (or keep `pre_` only if it becomes a genuine control point with fail-closed semantics)". The same table folds #8643 into the #53806 family.
- **Named consumer:** NousResearch/hermes-agent#118382 (carlosrenatoy). There is no plugin signal at compaction, so providers infer it from a turn-count drop. A scoping correction in that thread says MemoryProvider already has `on_pre_compress` + `prefetch`, so the remaining gap is plain plugins.
- **Related asks:**
  - NousResearch/hermes-agent#93389 (the issue behind #93391)
  - NousResearch/hermes-agent#125384 (compaction hook for preference auto-execution)
  - NousResearch/hermes-agent#119317 (the task-aware keep/drop issue behind #119347)
  - NousResearch/hermes-agent#8643 (`on_context_window_update`)
- **Speculative-hook precedent:** NousResearch/hermes-agent#59758 was closed by teknium1 on 2026-07-22: "hooks land with a real consumer, not ahead of one".
- **Fork boards:** kvnloo/hermes-agent#402 (salvage board) is closed. Its rows went upstream today as NousResearch/hermes-agent#130139 (9 rows, none about compaction; 0 comments at 11:20Z). kvnloo/hermes-agent#403 became NousResearch/hermes-agent#130140 (close wave). kvnloo/hermes-agent#404 is the staged-PR queue (39 rows); this item is not a PR, so it gets no row there. No kvnloo/hermes-agent issue or PR exists for this item, and no campaign thread has been created (OD-9).

## Invariant

A plugin subscribed to the local compaction observer is told about a local compaction exactly once. The call comes after the compacted transcript is durable in state.db and, for a manual `/compress`, after its host commits. The plugin is never told about an attempt that did not commit, and it can neither break nor change the compaction.

"Did not commit" means four distinct paths, each a case in the test:

- a failed summary that aborts under `compression.abort_on_summary_failure: true`;
- the commit site's would-grow refusal (the fallback summary would grow the transcript);
- a SessionDB write failure;
- a manual compress the host discards.

With the default `abort_on_summary_failure: false`, a failed summary does **not** abort: the compressor inserts its deterministic fallback summary and, on a realistic window, commits it. That is a committed compaction, and the observer correctly fires once (probe scenario `fallback_committed`, 61 messages in: tokens 75,000 → 30,622 on `c53806-foldin-r3`). The round-0 text said the observer "stays silent when the summary fails". That was false in general, and it is corrected everywhere.

**Real call path exercised:**

1. `AIAgent._compress_context`
2. `agent.conversation_compression.compress_context`
3. `_run_summary_phase`: the real `ContextCompressor.compress`, with only `_generate_summary` replaced
4. `_commit_compaction`: the real `SessionDB.archive_and_compact` / `publish_compression_child`, with the anti-growth guard
5. `_finish_compaction_boundary`
6. `_notify_context_engine_compression_complete`, either directly or deferred until `finalize_context_engine_compression_notification`

Dispatch is the real `PluginManager.invoke_hook` on a fresh manager. The seam is never mocked. The test pins the context window with `patch("agent.context_compressor.get_model_context_length", return_value=256_000)`, the idiom the sibling compression tests use, so agent init makes no model-metadata request over the network. 256,000 is the value the unpinned lookup fell back to, so behaviour is unchanged.

## Member branches

All refs live in the scratch mirror `h.git`. PR heads were fetched read-only to `refs/xf/pr/<n>`. Round-1 arms are pinned at `refs/xf/arms/compaction-hook-salvage/<arm>-r3`, all on the staging commit `de819a7d06`. Their diffs against the staging commit are in `patches/arm-<arm>.patch`. Round-0 refs are kept unchanged, and round-0 patches moved to `patches/r2/`.

| ref | sha | role | status vs main `aea969677c` |
|---|---|---|---|
| `refs/heads/staging/compaction-hook-salvage` | `de819a7d06` | **staging commit**: contract test only (blob `95d731de93`, +152), author Kevin Rajan | 1 commit on main; merge-tree clean (also on 040b6df2c4); push-trigger scan of the 52 workflow files on this tree: 0 match `staged/compaction-hook-salvage` (all push triggers are `main` or tags) |
| NousResearch/hermes-agent#53806 (`refs/xf/pr/53806`) | `6067388d0c` (compression commit `e560abd758`) | **carrier** (ledfoot631), named in the SALVAGE verdict | CONFLICTING in 11 files (agent/agent_init.py, agent/conversation_compression.py, agent/shell_hooks.py, gateway/slash_commands.py, hermes_cli/cli_commands_mixin.py, hermes_cli/hooks.py, hermes_cli/plugins.py + 4 test files); 33.6k behind. Hand-ported (`c53806-handport-r3` `96bd5a54e4`): the compression commit's conversation_compression.py + plugins.py hunks, identical patch-id to the round-0 hand-port |
| `c53806-foldin-r3` | `77bbc5f9a4` | **carrier + fold-in**, the proposed final shape | vs staging commit: +62/-11 in agent/conversation_compression.py, hermes_cli/plugins.py, hermes_cli/hooks.py, website/docs/user-guide/features/hooks.md (`patches/arm-c53806-foldin.patch`) |
| NousResearch/hermes-agent#93391 (`refs/xf/pr/93391`) | `9da3734b8e` | competitor (clomp42, `pre_compression`) | conflicts in 3 website docs files only; code + tests re-applied 3-way clean (`c93391-code-r3` `57997c2607`, same patch-id as round 0) |
| NousResearch/hermes-agent#118847 (`refs/xf/pr/118847`) | `222e3e26c3` | competitor (Baophan00, `post_compaction` for #118382) | CONFLICTING, 1 hunk in agent/context_compressor.py; hand-port re-applied (`c118847-handport-r3` `12ebf32dc2`, same patch-id) |
| NousResearch/hermes-agent#119347 (`refs/xf/pr/119347`) | `4a527fc35d` | directive/transform variant (fangliquanflq); excluded from the observer slot (#120582 risk) | CONFLICTING, 3 semantic hunks at the #61932 pruned-copy seam; no safe port, not materialized |
| NousResearch/hermes-agent#125881 (`refs/xf/pr/125881`) | `d3fdffcf82` | fail-closed policy-hook carrier (pstarkgit) | merge-tree clean; `c125881-merge-r3` `f7b42fa597` (same patch-id) |
| NousResearch/hermes-agent#122522 (`refs/pr/122522`) | `f596584b01` | not a member (adjacent summary_source=original work) | n/a |

- **Fold-in variants:** `foldin-ref-r3` `584ed12b31` (fold-in without the carrier's start-side hook), `foldin-bounded-r3` `b459478759` (+ `on_compression_complete` in `_HOOK_TIMEOUT_BOUNDED_HOOKS`)
- **Negative controls:** `neg-prefire-r3` `872a518d7e` (call moved before `_commit_compaction`), `neg-nodefer-r3` `861fa0738e` (deferral bypassed)
- **Per-hunk sabotage of the fold-in:** `sab-h1-observer-call` `e64de5a2fc`, `sab-h2-queue-payload` `d3d7aa96f1`, `sab-h3-tokens-before` `c7b903c2d6`, `sab-h4-tokens-after` `6415fedad0`, `sab-h5-valid-hooks` `7c22d89da4`, `sab-h6-keep-carrier-post-commit` `eb788bbae1`, `sab-h7-payload-and-docs` `8c73a4675a` (all `-r3`)

`c53806-handport-r3` re-applies the round-0 hand-port patch onto the staging commit. `c53806-foldin-r3` is that commit plus the fold-in, built by hand; the fold-in alone is `patches/foldin-on-c53806-handport.patch`. Every other r3 arm is built by `tools/chs_build_arms_r3.py`: either one textual mutation of `c53806-foldin-r3`, or a competitor's round-0 diff re-applied onto the new staging commit with `git apply -3`.

## First-slice status

**Committed.** One commit, `de819a7d0660be8fd560c35bbc4c56676bc8408b`, on main `aea969677c`:

- Subject: `test(compression): pin the plugin observer contract at the local compaction boundary`
- Author: `Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`
- Diff: 1 file, +152. It is exported as `patches/staging-compaction-hook-salvage.patch` (`git format-patch -1`).
- The local branch `staging/compaction-hook-salvage` was forced from round 0's `8c834af1e4` to this commit. The round-0 patch is kept at `patches/r2/`.

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
  - `manual_discarded`: the host finalizes `committed=False`, and a later `finalize(committed=True)` cannot revive the call.
  - Precondition for the first three: the session id is unchanged and state.db's rows for it equal the rows before the attempt. A commit would have written the compacted transcript. This replaces round 0's sentinel check, which was vacuous because the sentinel cannot appear when the summary is None.

The hook name is the single constant `HOOK = "on_compression_complete"`. The production change is **not** on the staging branch. It is offered to the carrier as one production diff on main: `patches/arm-c53806-foldin.patch`. That diff is the carrier hand-port plus the fold-in, byte-identical to `git diff de819a7d06 c53806-foldin-r3`, and it applies to main once the staging commit (test only) is in. `patches/foldin-on-c53806-handport.patch` is only a reading aid: it is relative to our hand-port, not to #53806's head. The minimal reference without the carrier's start-side hook is `patches/foldin-ref-on_compression_complete.patch`. The optional bounded variant is `patches/arm-foldin-bounded.patch`.

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
- It names the hook `on_compression_complete` and adds the payload.
- It adds the hook to `VALID_HOOKS` with a comment, to the "Shipped plugin-hook catalog" table in `website/docs/user-guide/features/hooks.md`, and to `hermes_cli/hooks.py` `_DEFAULT_PAYLOADS`. `VALID_HOOKS` doubles as the shell-hook allow-list, so `hermes hooks test on_compression_complete` gets the runtime payload shape.

**What the fold-in no longer does (round-1 change).** Round 0 also renamed the carrier's start-side `pre_context_compression` to `on_compression_start`. No test covered that rename, and it passes the full `conversation_history`. #118382 needs only the post-commit signal. The fold-in now leaves that hook exactly as #53806 wrote it. Its name (#64231 asks for `on_compression_start`), its payload, its missing docs row and hooks-CLI payload, and whether it stays at all are maintainer decision (a). `foldin-ref-r3` shows the fold-in passes 7/7 without the start-side hook too.

The table below is OBSERVED in **F05 r3** (main `aea969677c`, staging commit `de819a7d06`): every arm ran in the same run under the r3 egress guard, with 0 blocked connect or DNS attempts in its 78 cells. The clause probe (`tools/chs_clause_probe.py`, 9 scenarios per arm) supplies the timing and fire columns. "Own name" means the contract test with `HOOK` set to the carrier's hook name, 3 reps. Round 0 attributed this table to F05 r1 on `572e4f4fad`; that run had no `c53806-foldin` arm, and r1 is now INFRA and superseded.

| carrier | merge | hook (own name) | fires relative to summary / commit | 4 committing scenarios (rotated, in-place, manual, fallback commit) | 5 non-committing scenarios (aborted summary, would-grow refusal, in-place write fail, rotation write fail, manual discard) | manual-host deferral | payload keys | contract, own name |
|---|---|---|---|---|---|---|---|---|
| main | n/a | none | never | 0/4 fire | silent (trivially) | n/a | n/a | 4/7 pass (RED) |
| #53806 post | hand-port | `on_session_start` + `boundary_reason="compression"` | after durable commit | fires once, 4/4 | 4/5 silent; fires on manual discard | ignored (fires before finalize) | session_id, old_session_id, boundary_reason, platform, model, context_length, conversation_id | 3/7 |
| #53806 pre | hand-port | `pre_context_compression` | before summary | fires once, 4/4 | 0/5 silent | ignored | session_id, conversation_history, approx_tokens, focus_topic, force, model, platform, conversation_id | 0/7 (start-side by design) |
| #93391 | docs-only conflicts | `pre_compression` | before summary | fires once, 4/4 | 0/5 silent | ignored | session_id, messages, platform, compression_count, in_place | 0/7 (start-side) |
| #118847 | 1-hunk hand-port | `post_compaction` | after summary, **before** commit | fires once, 4/4, transcript not yet durable | 1/5 silent (aborted summary only); fires on the would-grow refusal (after_tokens 3,365 > before_tokens 1,672), both write failures and the manual discard | ignored | session_id (pre-rotation id), before_tokens, after_tokens, messages_removed, reason | 1/7 |
| #125881 | clean | `pre_compression_commit` (policy) | after summary, before commit | fires, but a non-`allow` subscriber **blocks** the compaction (state.db rows 13 → 0 vs baseline, output changed) in 4/4 | 1/5 silent (aborted summary only) | ignored | session_id, state{counts} | 1/7 (fail-closed control point by design) |
| #119347 | 3 semantic conflicts | `transform_compaction_input` | before summary (transform) | not run | not run | n/a | n/a | not run |
| **#53806 + fold-in** | built | `on_compression_complete` | after durable commit; after host finalize | fires once, 4/4 | 5/5 silent | honoured | session_id, old_session_id, in_place, tokens_before, tokens_after, platform | **7/7, 3/3 reps** |

Each carrier's own tests still pass on its arm. This is a fairness check: each carrier proves its own, different, contract (OWN r3).

- #93391: `test_compression_rotation_state.py`, 43/0 (base 40/0)
- #118847: `test_post_compaction_hook.py`, 7/0. These tests mock `hermes_cli.lifecycle.invoke_hook`, which is the seam itself.
- #125881: `test_context_governance.py`, 9/0

**WAVE row:** proposed text in `body.md`. Carrier #53806 + fold-in. Close #93391 and #118847 after it merges. Keep #125881 and #119347 open: they are different contracts and compose with the observer.

## Evidence

| experiment | receipt | verdict | label | n | result |
|---|---|---|---|---|---|
| F05 r3: carrier A/B, 9 arms with the clause probe + 9 negative/sabotage arms, main aea969677c | `receipts/F05-f05-r3.json` | KEEP | OBSERVED | 3 reps × 7 cases per arm (+3 own-name reps per carrier), 9 probe scenarios per probed arm; 78 cells, 0 INFRA (0 connect, 0 dns) | see the carrier table. base 4/7 (RED); c53806-foldin, foldin-ref, foldin-bounded 7/7; neg-prefire 1/7; neg-nodefer 5/7; sabotage h1 4/7, h2 6/7, h3 4/7, h4 4/7, h5/h6/h7 7/7 (unpinned). All reps agree |
| E12 r3: guards + 17 adjacent files on base, c53806-foldin and foldin-bounded | `receipts/E12-e12-r3.json` | PASS (recorded S16 exception) | OBSERVED (+ one structural note) | 1 run per arm per harness; 12 cells | replay_gates 11/11 PASS on all three, equal verdict maps. ab_checkpoint_preflight local compress calls identical (capture 0/0 cli and gateway, restore 0, over_threshold 0 then 1). test_region_scoping ALL PASS. Adjacent 17 files: base 302 / 3 / 2 skipped (the 3 are the new test) → 305 / 0 / 2 on both fold-in arms. Egress: 0 connect; 224 (adjacent) + 2 (region scoping) blocked DNS lookups per arm, all in upstream code and identical on base and arms (recorded S16 exception; INFRA without it). Observer fires are 0 in replay_gates and the preflight by construction (no SessionDB in their real-compression scenarios; the preflight stubs `_compress_context`), so 0 is not a native-route measurement |
| PROOF r3: gate columns | `receipts/PROOF-r3.json` | PASS (F05 0 INFRA; E12 under the recorded S16 exception) | OBSERVED | aggregation of F05 r3 + E12 r3 | RED marker matched; GREEN 3/3; NEG RED; unpinned hunks listed |
| OWN r3: carriers' own tests on their arms | `receipts/OWN-own-r3.json` | n/a (fairness) | OBSERVED | 4 cells | 43/0 (#93391), 7/0 (#118847), 9/0 (#125881); base rotation_state 40/0. The two rotation_state cells made 112/118 blocked DNS lookups from that upstream file (same S16 exception) |
| Guard canary r3 | `receipts/SANDBOX-guard-canary-r3.json` | PASS | OBSERVED | 5 cases | 5/5: connect to 1.1.1.1:443 refused, getaddrinfo('example.com') refused, loopback connect and localhost DNS still work, the openrouter-prewarm thread is not started while other threads are; the guard log holds exactly connect 1, dns 1, prewarm_suppressed 1 |

Superseded (kept as history, scrubbed of local paths, re-labelled): F05 r1, F05 r2, E12 r2, OWN r1 and PROOF r2 are **INFRA** under FACTORY S16. Every F05 r1/r2 cell built an `AIAgent` against the OpenRouter base URL. Each init made a synchronous model-metadata GET (`agent_init._enforce_minimum_context` → `model_metadata.get_model_context_length` → `fetch_model_metadata`), and the process started the `openrouter-prewarm` thread. The r1 guard refused the connects (4,560 in F05 r1, 1,980 in F05 r2) but not the DNS lookups, which left the process. E12 r2 (616) and OWN r1 (928) logged blocked connects per run, not per cell, so no cell can be shown clean. PROOF r2 aggregates those. Round 0 called the guard "loopback-only" and the results "unaffected"; both overstated it. The r1 canary is PASS for connect() only. `tools/chs_supersede_r1r2.py` did the re-labelling.

## Experiments run ($0 only)

- **F05 r3 (carrier A/B).** `python3 tools/chs_ab_runner.py --worktree $WORKTREE --run-id f05-r3 --arms "$(cat raw/f05-r3.arms)" --reps 3 --testhome $TESTHOME --python $PY`, then `--run-id f05-r3s --arms "$(cat raw/f05-r3s.arms)" --skip-probe` for the negative and sabotage arms. Arms were built by `python3 tools/chs_build_arms_r3.py $WORKTREE de819a7d06 77bbc5f9a4`. The probe is `tools/chs_clause_probe.py` (r3 adds `summary_aborted`, `would_grow_refused` and `fallback_committed`, and records the compressor's abort/refusal flags and state.db row counts). Raw logs are in `raw/f05-r3/` and `raw/f05-r3s/` (private).
- **E12 r3 (guards + adjacent).** `bash tools/chs_guards_r3.sh <arm> <commit> e12-r3 $WORKTREE $TESTHOME $PY` runs `evals/token_accounting/replay_gates.py` and `evals/native_compaction/ab_checkpoint_preflight.py` through `tools/chs_guard_wrap.py` (egress guard, observer counter), then `evals/compaction/test_region_scoping.py`, then 17 adjacent test files. Arms: base `de819a7d06`, `c53806-foldin-r3`, `foldin-bounded-r3`.
- **OWN r3.** Each carrier's own test file on its r3 arm, plus base for rotation_state.
- **Guard canary r3.** `tools/chs_guard_canary_r3.py` copied into the worktree and run through `scripts/run_tests.sh`.
- **Isolation for every run:**
  - HOME = `$S/testhome-sf-compaction-hook-salvage`; HERMES_HOME = `$HOME/.hermes`.
  - `HERMES_PYTHON` points at the live venv's interpreter, used read-only as an interpreter only. `run_tests.sh` uses `env -i` and `-j 2`.
  - The r3 egress guard `tools/chs_egress_guard.py` is loaded through the isolated HOME's `pytest_live_guard.py` shim. It refuses non-loopback `connect`/`connect_ex` and non-loopback `getaddrinfo`/`gethostbyname*`, and it does not start the `openrouter-prewarm` thread. Each line goes to `$HOME/chs-egress.log`, which the runner truncates and reads per cell. A cell with any `connect` or `dns` line is INFRA (S16).
  - Result: F05 r3 had 0 `connect`, 0 `dns` and 0 INFRA cells in 78 cells, and `prewarm_suppressed` appears at most once per pytest worker process. E12 r3 had 0 `connect`, and replay_gates and ab_checkpoint_preflight had 0 `dns`. The adjacent cell made 224 blocked DNS lookups per arm and test_region_scoping made 2 (OWN: 112/118 in the two rotation_state cells). All come from upstream code this item does not touch: the model-metadata GET at `AIAgent` init in sibling tests that do not pin the window, and the OpenRouter video-catalog GET while tool definitions are built. Per-file attribution (`raw/e12-r3/dns-attribution/summary.json`, from `tools/chs_dns_attribution.py`) is identical on base and `c53806-foldin`. Under a strict S16 reading those cells are INFRA. They are kept under a **recorded S16 exception** that is written into the E12 and OWN receipts for the owner to accept or reject. Without it, E12 is INFRA.
  - There is no bwrap or netns: FACTORY §6 layer 1 was not used. This is the in-process layer only, recorded in each receipt's `env.sandbox`.
- **Cost:** $0, T1, cpu lane, 0 GPU-s.

## Experiments queued (not run)

None of this item's gates needs a T2 or T3 experiment, because the contract does not depend on the model. Queued for completeness:

1. **T1 ($0, recommended before posting): consumer end-to-end for #118382.**
   - Setup: a minimal out-of-tree plugin subscribes to `on_compression_complete`, flags the session, and re-injects a context block through `pre_llm_call` on the next turn. It is driven through the real turn loop against the loopback fake provider from `evals/token_accounting/replay_gates.py`, with `session_db` set so the commit is durable.
   - Command, after writing `tools/chs_consumer_e2e.py`: `env -i PATH=/usr/bin:/bin HOME=$TESTHOME HERMES_HOME=$TESTHOME/.hermes $PY tools/chs_guard_wrap.py <worktree at c53806-foldin-r3> tools/chs_consumer_e2e.py raw/consumer/counts.json --out raw/consumer/result.json`
   - Pass: exactly one re-injection after each committed compaction, none after a refused one.
2. **T2 (local GPU, strictly serial, gated on OD-1 because `MINIMUM_CONTEXT_LENGTH = 64_000` exceeds the 8K router presets): real-summarizer smoke.**
   - Setup: the same probe with `_generate_summary` left real, and `auxiliary.compression` pointed at a ≥64K local preset in the arm's own `$HERMES_HOME/config.yaml` (not an env var).
   - Command: `flock <gpu lock> env -i PATH=/usr/bin:/bin HOME=$TH HERMES_HOME=$TH/.hermes-t2 HERMES_PYTHON=$PY bash scripts/run_tests.sh -j 1 tests/agent/test_zz_chs_clause_probe.py -q`, with sidecar `{"hook": "on_compression_complete", "out": "raw/t2/probe.jsonl", "real_summary": true}`. The `real_summary` switch still has to be added to `tools/chs_clause_probe.py`.
   - Expected: identical clause verdicts.
3. **T3:** none.

## Acceptance gates (selection)

| gate | status | evidence |
|---|---|---|
| Contract test is RED on main (no hook) and GREEN on the chosen carrier, or carrier plus fold-in | **met** | RED 3 of 7 failed × 3 reps on aea969677c. GREEN 7/7 × 3 reps on #53806 + fold-in (`c53806-foldin-r3`). F05 r3, PROOF r3 |
| Negative control: moving the fire before the commit makes the test fail | **met** | `neg-prefire-r3`: 6 of 7 failed × 3 reps |
| replay_gates PASS is unchanged | **met** | E12 r3 |
| ab_checkpoint_preflight verdicts are unchanged | **met** | E12 r3 |
| Observer-only (return ignored), unless the winner is the fail-closed pre_ variant | **met** | the winner is the observer; a `{"action": "block"}` return and a raising subscriber leave output byte-identical (contract case). #125881's fail-closed variant is recorded as a separate control point |
| The named consumer is cited (#118382) | **met** | body.md, this manifest |
| The disposition table is posted once (WAVE row) on #118382 or #53806 | **not met (owner action)** | text prepared in `body.md`. Posting is a GitHub write the factory does not perform; see [queue] for the target and the spray check |

## Gate checklist (FACTORY P1-P12)

| gate | status | basis |
|---|---|---|
| P1 Need | PASS | RED on aea969677c (≤24 h); invalidate_on paths unchanged since e496ccc7d7; freshness re-check in [base] |
| P2 Ownership | PASS | external carriers → salvage-support; no claimant-lane, hold or Hermes-lane overlap; #118382's verbal claim has no PR; heads re-checked 11:20Z |
| P3 Shape | **PENDING** | One invariant, a fire site and a named consumer (#118382). No new env var or config key, no shim. But AGENTS.md says "New behaviour goes in a new or topical sibling — never appended to a facade", and the fold-in appends the observer dispatch to `agent/conversation_compression.py`, which is already 4,579 lines on main (4,615 with the combined diff: +47/-11 there). It sits there because it must run inside the existing notify fence. A maintainer may want the dispatch in a `conversation_compression_*` sibling. That is surfaced as maintainer decision (d), and no sibling variant was built. `hermes_cli/plugins.py` is 2,331 → 2,341 (comment + entries). The staging commit adds only a new 152-line test. Round 0 scored this PASS |
| P4 Real path | PASS | real AIAgent/SessionDB/ContextCompressor/PluginManager; only the summary LLM call, the context-window lookup and, for one failure case, the SessionDB write are faked; seam not mocked |
| P5 Proof | PASS | RED marker matched; GREEN 3/3; NEG RED; sabotage per hunk (h1-h4 re-RED; h5 VALID_HOOKS entry, h6 the carrier's on_session_start post-commit call kept, h7 hooks-CLI payload + docs row: unpinned and listed); adjacent: 17 files identical to base apart from the new test (E12 r3); guards equal; flaky=false (all reps agree); F05 r3 0 INFRA cells; E12's adjacent and region-scoping cells stand under the recorded S16 exception (upstream DNS lookups, identical on base and arms) |
| P6 Numbers | N_A | no value claim |
| P7 Package | PENDING | one clean commit on fresh main with correct author/subject, merge-tree clean, 0 workflow matches. Push as `staged/compaction-hook-salvage` is an owner action (OD-0 resolved by the rename; OD-4 still decides whether the fold-in is pushed or stays a ledger patch) |
| P8 Freeze | PENDING | r3 receipts written with sha256 (front matter) in full xf.receipt.v1 form, repo-relative paths only; not frozen to z0evals |
| P9 Text | PENDING | body.md rewritten (template-free wave row, AI assistance disclosed, no @mentions, no bare fork links); needs an independent tone/jargon read |
| P10 Independent read | PENDING | round-0 verifier: accept=false; no blind re-verification of `de819a7d06` yet |
| P11 Demand | RECORDED | combined score 5.24; maintainer SALVAGE verdict; consumer #118382 |
| P12 Queue | PENDING | no fork board applies (see [queue]); owner posts once on #53806 or as a delta row on #130139, on a later day than today's waves |

## NOT_TESTED

- **Native and Codex app-server compaction.** Native means OpenAI Responses server-side compaction on gpt-5.6/Astra. Neither route has a client commit. `_route_codex_compaction` returns before `_commit_compaction`, and native checkpoint turns never call `_compress_context`: ab_checkpoint_preflight counts 0 calls on capture and restore. The observer therefore cannot fire on these routes by construction. That is a structural argument; no hook fire count was taken on a real native turn. Scope: local compressor only.
- **Agents without a SessionDB.** With `session_db=None` there is no durable commit, so neither the context engine nor the observer is notified. This is the same guard the context engine already has. It is not exercised; worth a maintainer note.
- **Micro-compaction and proactive-prune rewrites.** These are not compaction boundaries and are not exercised.
- **Real summarizer.** The summary is fixed text, or None for the failure scenarios. The payload does not depend on summary content.
- **Fallback-summary commit as a contract case.** It is observed only in the probe (`fallback_committed`: fires once on every fold-in arm). It is not a case in the committed test.
- **Host surfaces.** The manual deferral is exercised through `compress_context(defer_context_engine_notification=True)` + `finalize_context_engine_compression_notification`. It was not driven through `agent/conversation_compression_manual.py:compress_now`, `gateway/slash_commands_session.py`, `acp_adapter/commands.py` or TUI/Desktop.
- **Shell hooks.** VALID_HOOKS doubles as the shell-hook allow-list, so a `hooks:` config entry for `on_compression_complete` becomes valid, and `hermes hooks test` now has its payload. `tests/hermes_cli/test_hooks_cli.py` passes, but no shell hook was run against a real compaction.
- **The carrier's start-side hook.** `pre_context_compression` stays as #53806 wrote it. It has no contract case, no docs-catalog row and no `_DEFAULT_PAYLOADS` entry (the carrier's own hooks.py hunk was left out of the hand-port). Its rename to `on_compression_start` is maintainer decision (a).
- **Docs pages other than the hook catalog.** `website/docs/user-guide/features/plugins.md` keeps its own category list and a stale "27 lifecycle events" count on main. It points to the hooks.md catalog as canonical and was not edited.
- **Slow or hung subscriber.** In the fold-in, the observer runs synchronously while the compaction lease is still held, like today's context-engine callback, memory `on_session_switch` and `session:compress`. `foldin-bounded-r3` puts it in `_HOOK_TIMEOUT_BOUNDED_HOOKS` (worker thread, `plugins.hook_callback_timeout`, fail-open), and the contract still passes 7/7 × 3 reps there. An actual hang was not simulated.
- **Kernel-level sandbox.** There is no bwrap/netns (FACTORY §6 layer 1). The in-process guard cannot stop a native extension or a subprocess from reaching the network. None of the selected tests spawns one.
- **Credential, device, TTY and browser boundaries:** N/A.
- **Pre-guard exploratory runs (round 0).** The first exploratory RED/GREEN runs on 572e4f4fad (about 03:55-04:05 -0500) ran without any guard. The isolated home held no credentials; the key is the literal `test-key`. No round-1 receipt depends on them.
- **Static observation, unverified by test:** `session:compress` (`event_callback`) in `_finish_compaction_boundary` has no `session_commit_succeeded` guard, so it may fire for a failed split. Out of scope here.

## Origin action (owner only, not run)

Post `body.md` once, as **one comment on NousResearch/hermes-agent#53806** (the SALVAGE carrier; preferred). The alternative is one delta-row comment on NousResearch/hermes-agent#130139, using the table row alone. Do not open a new wave issue. kvnloo opened four wave tables upstream in the last 24 h, two of them today, so post on a later day (see [queue].spray_check).

Offer the fold-in as one production diff on current main: `patches/staging-compaction-hook-salvage.patch` (the test) + `patches/arm-c53806-foldin.patch` (#53806's compression commit hand-ported, plus the fold-in), with `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>`. Both apply to main in that order. #53806's own head conflicts in 11 files and is 33.6k commits behind, so a diff relative to it, or to our hand-port alone, would not apply. No new PR and no slot.

## Next steps

1. **Owner:** push `staging/compaction-hook-salvage` as `staged/compaction-hook-salvage` (`--no-follow-tags`; OD-0 resolved by the rename). Decide OD-4: push the fold-in on the carrier head, or keep ledger patches.
2. **Blind exact-head verification (P10)** of `de819a7d06` by a different worker. Inputs: `patches/staging-compaction-hook-salvage.patch`, `patches/arm-c53806-foldin.patch`, and the oracle: RED on main with marker `on_compression_complete fired 0 times`; GREEN 7/7 on carrier + fold-in; prefire negative control RED.
3. **Maintainer decisions to surface in the comment** (all four are in body.md):
   - (a) the start-side hook: keep #53806's `pre_context_compression`, rename it `on_compression_start` per #64231 (then add a contract case, a hooks.md catalog row and a `_DEFAULT_PAYLOADS` entry), or drop it from the PR
   - (b) manual-discard semantics (wait for the host, as the context engine does)
   - (c) whether to bound the hook under `plugins.hook_callback_timeout` (foldin-bounded)
   - (d) whether the observer dispatch should live in a `conversation_compression_*` sibling (AGENTS.md facade rule; resolves P3)
4. **Run the queued T1 consumer end-to-end** before posting. It answers the speculative-hook rule (#59758) with a working consumer.
5. **Freeze the cited r3 receipts (P8)**, and re-check freshness within 24 h of posting: `git merge-tree --write-tree main staging/compaction-hook-salvage`, then the RED cell.

## Round-1 fixes (phase-3 verifier, problems[0..8])

| # | verifier finding | fix | where |
|---|---|---|---|
| 0 | `summary_failed` actually tested the would-grow refusal; `not _durable_summary(...)` was vacuous; "stays silent when the summary fails" was false in general; body.md called the same scenario a "refused fallback summary" | The case was split into `summary_aborted` (`abort_on_summary_failure=True`, precondition `_last_compress_aborted`) and `would_grow_refused` (default config, precondition `_last_compress_refused_would_grow`). The non-commit precondition is now "session id and state.db rows unchanged". The probe gained `fallback_committed` (default config, realistic window: the observer fires once, correctly). Commit message, module docstring, this manifest and body.md were corrected. RED/GREEN/negative/sabotage were re-proved | staging commit `de819a7d06`; F05 r3 |
| 1 | queue target was stale: #402 closed 07:32Z, posted upstream as #130139 | [queue] now has no fork board, an owner choice between one #53806 comment and a delta row on #130139, and a recorded spray check (post on a later day) | [queue], Origin action, Links |
| 2 | the fold-in's `on_compression_start` rename had no test and was not disclosed | The fold-in no longer touches the start-side hook. #53806's `pre_context_compression` stays as written, and that is disclosed in body.md as maintainer decision (a). `foldin-ref-r3` passes 7/7 without it | arms `c53806-foldin-r3`, `foldin-ref-r3`; body.md |
| 3 | no hooks.md catalog row and no `_DEFAULT_PAYLOADS` entry; gap missing from NOT_TESTED/Next steps | The fold-in adds both for `on_compression_complete`, and `tests/hermes_cli/test_hooks_cli.py` + `test_plugins.py` joined the adjacent set. The carrier's start-side gap is listed in NOT_TESTED and Next steps (a) | `patches/arm-c53806-foldin.patch`; E12 r3 |
| 4 | receipts lacked §9.2 fields; S16 blocked connects not classified; DNS leaked; "loopback-only" overstated | The r3 receipts carry spec, gates, verdict, denominators, provenance, frozen, privacy, evidence_class, policy_revision and env. The test now pins the context window, and the harness does not start the prewarm thread. The r3 guard also blocks DNS and logs per cell. F05 r3 had 0 connect, 0 dns and 0 INFRA cells. The remaining DNS lookups come from upstream sibling tests and eval code in E12/OWN (identical on base and arms, attributed per file). They are classified under a recorded S16 exception, not as normal. The r1/r2 receipts are re-labelled INFRA (canary: connect() only) and marked superseded | `receipts/*-r3.json`, `tools/chs_egress_guard.py`, `tools/chs_supersede_r1r2.py` |
| 5 | the carrier table was attributed to F05 r1, which had no `c53806-foldin` arm | The table now comes from F05 r3, where every arm ran in the same run | Route and carrier choice |
| 6 | the origin action offered a diff relative to our unpublished hand-port | It now offers `patches/arm-c53806-foldin.patch`, the combined production diff on main, plus the staging patch. The hand-port-relative patch is labelled a reading aid | First-slice status, Origin action |
| 7 | receipts embedded local paths | All receipts (r3 and the superseded r1/r2) use repo-relative paths and placeholders (`$S`, `$TESTHOME`, `$WORKTREE`, `$PY`); the builders assert it | `receipts/` |
| 8 | AGENTS.md sibling rule; P3 scored PASS | P3 is now PENDING with the basis recorded. It is surfaced as maintainer decision (d) in body.md. No sibling variant was built | [gates], P3 row, body.md |

## History

| when (UTC) | status | worker | reason |
|---|---|---|---|
| 2026-10-01T08:50Z | CANDIDATE | builder (Claude Code, Opus 5.5) | selection read; premise re-checked on 572e4f4fad: VALID_HOOKS has no compression hook, fire site unchanged at conversation_compression.py:2564, no newer carrier found |
| 2026-10-01T09:03Z | CANDIDATE | builder | contract test committed on 572e4f4fad (`b3b8d73999`); RED 3/6 |
| 2026-10-01T09:12-09:30Z | EVIDENCED | builder | F05 r1 (12 arms) under the r1 connect-only guard |
| 2026-10-01T09:51-10:05Z | EVIDENCED | builder | staging commit cherry-picked onto bafb42b431 (`8c834af1e4`); F05 r2 + E12 r2 + OWN r1; local branch `staging/compaction-hook-salvage` created; worktree removed |
| 2026-10-01T10:10Z | EVIDENCED | phase-3 verifier | accept=false, manifest_accurate=false; 9 problems |
| 2026-10-01T11:04-12:15Z | EVIDENCED (v2) | round-1 fixer (Claude Code, Opus 5.5) | test case split + real non-commit preconditions + pinned context window; staging commit rebuilt on aea969677c (`de819a7d06`), local branch forced; fold-in reshaped (no start-side rename; docs row + hooks-CLI payload); r3 egress guard; F05 r3 + E12 r3 + OWN r3 + canary r3; r1/r2 receipts scrubbed and superseded (INFRA); queue re-targeted; worktree removed |
