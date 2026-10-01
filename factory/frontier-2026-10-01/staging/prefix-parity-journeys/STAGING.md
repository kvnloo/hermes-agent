+++
xf_staging = 1
id = "prefix-parity-journeys"
version = 1
manifest_revision = 3      # r3 (2026-10-01): round-1 re-verifier fixes (text, receipt hygiene, freshness, r1 ref); branch and commit unchanged; receipts r03 re-issued from the r02 raw set
title = "Prefix-stability journeys for uncovered surfaces: messaging gateway, api_server /v1/runs, ACP (first slice); relay connector, A2A, /goal queued"
branch = "staging/prefix-parity-journeys"
branch_fork = "staged/prefix-parity-journeys"
branch_physical = "local-only in scratch h.git as staging/prefix-parity-journeys; pushed to kvnloo/hermes-agent as staged/prefix-parity-journeys. OD-0 resolved by that rename: the fork's legacy refs/heads/staging (28790e597c) blocks staging/<id>. ls-remote 2026-10-01T12:20Z: no staged/* refs on the fork yet; refs/heads/staging still 28790e597c."
branch_sha = "ddf4748d31cb5dc65e7cd0b0c5b27b98d63ae880"
branch_preserved = { r1 = "refs/heads/staging/prefix-parity-journeys-r1 -> 8df66fe4d74565d33b2bb91972a10609247afba8 (re-created in r3, local-only, never to be pushed). r2 moved the branch instead of rebuilding it as -v2 (FACTORY s10), which left no ref on the r1 head. The ledger artifact is private/superseded-r01/prefix-parity-journeys.patch (sha256 92b4df1755069579, byte-identical to git format-patch -1 8df66fe4d7)" }
patch = { path = "prefix-parity-journeys.patch", sha256 = "3c2d26ebf00da4916ce6da0ab15f9604d94bac3100c727854d6e59efbe238bc5", files = 5, size = "+302/-61" }
status = "STAGED"            # ceiling: STAGED until paired with a real prefix fix (D5); see [ride_with]
promotion_form = "eval-contribution"
route = "ride-along"
feature = "surface-parity-invariant-cells"
invariant = "On the messaging gateway, api_server /v1/runs and ACP, every main request of one durable session is a byte-identical extension of the previous one across process restarts, except exactly one break at the compaction, and the prompt rebuilt at that compaction never contains the previous prompt."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
fetched_at = "2026-10-01T11:04Z"
previous = "572e4f4fad32bbdcfc948fb2ec833177ed5734c0 (r1 parent; 47 commits before this base)"
freshness_recheck = { main = "aea969677c60a1bb72fe227fdfb98f196a2092cc", checked_at = "2026-10-01T11:04Z", merge_tree_clean = true, invalidate_on_hits = [], note = "branch rebuilt on this main; no commit in 572e4f4fad..aea969677c touches acp_adapter/, tests/e2e/ or tests/fakes/; RED/GREEN re-proved on it" }

[upstream]
rfc_or_issue = [
  "NousResearch/hermes-agent#104414 (closed completed 2026-09-09; motivation)",
  "NousResearch/hermes-agent#45499 (closed completed 2026-06-25; motivation)",
  "NousResearch/hermes-agent#120116 (closed completed 2026-09-23; motivation)",
  "NousResearch/hermes-agent#76215 (OPEN, dosenr; JoannaHoly reported 2026-09-25 (comment 12:14Z) three live repros in three days, seen on build ee5ee84a34 (2026-09-24): 279 -> 42 messages, restored as 279, first request 187,671 input tokens; and on 2026-09-24 466 -> 29, restored as 495) -- the red this branch found",
  "NousResearch/hermes-agent#49226 (OPEN, jakepresent; ACP session ids stranded by automatic compression rotation; #88364 targets it too)",
  "kvnloo/hermes-agent#319 (fork RFC: z0int shadow decisions; identity joins)",
]
related_prs = [
  { pr = 88364, author = "dosenr", head = "f02e1487a8", state = "OPEN, mergeStateStatus DIRTY (targets pre-#109610 acp_adapter/commands.py + tests/acp/)", note = "Fixes #76215 and #49226: sets compression_in_place at ACP agent construction and keeps _session_db attached on /compress. Builds on #76224 with Co-authored-by RelaxJonh. Carries the real-SessionDB restart regression (test_compact_survives_process_restart) that checks the compacted active transcript AND the archived inactive/compacted original rows. Does not touch the system_message argument (cause 2)." },
  { pr = 76224, author = "JonthanaHanh", commit_author = "RelaxJonh", head = "20a047b7f2", state = "OPEN, mergeStateStatus DIRTY (targets pre-refactor acp_adapter/server.py + tests/acp/)", note = "fixes #76215 cause 1 for manual /compress only. Sweeper review (teknium1, 2026-08-01, keep_open salvageability=high) and pestoura ask for a real-SessionDB regression that 'compacts a seeded session, restores the same session ID, and verifies the compacted live history plus retained inactive/compacted original rows'. dosenr posted exactly that test on #76224 on 2026-08-12 (tests/acp/test_76215_regression.py). acp_restarts is NOT that regression: it checks the replayed live history across real processes but never the retained inactive/compacted rows." },
  { pr = 110763, author = "enzoferrari-cc", state = "CLOSED by author 2026-09-19, no comments", note = "continuation of #88364 on post-refactor paths (dosenr's commits preserved, per enzoferrari-cc's comment on #88364); did not touch system_message" },
  { pr = 72694, author = "necoweb3", head = "48ef9c82d5", state = "OPEN (acp_adapter/session.py hard-delete path; different defect)" },
  { pr = 109610, author = "teknium1", state = "MERGED 2026-09-13 (7114da3de6): manual /compress has one core; the ACP caller kept system_message=_cached_system_prompt" },
]
competitors = []          # no open upstream PR edits tests/e2e/core/history/test_prefix_stability.py (gh search 2026-10-01T11:08Z)
close_after = []
demand = { score = "0 (judges)", source = "judges.json: maintainer-fit 4, evidence 6, impact 4" }
maintainer_signal = "C17 is teknium1's suite (51a1205be0, 09d62097a3). Outside e2e edits land only alongside fixes. The #76224 reviews (teknium1 sweeper + pestoura) asked for a real-SessionDB ACP reload regression; dosenr supplied it (#76224 comment 2026-08-12, and in #88364)."

[[members]]
ref = "staging/prefix-parity-journeys"
sha = "ddf4748d31cb5dc65e7cd0b0c5b27b98d63ae880"
role = "own: first slice (3 journeys + ACP known_gate pin + compaction-nesting invariant + harness fixes, incl. spawn_acp/close_acp extracted from drive_acp); test-only"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
rebase_status = "one commit on main aea969677c (rebuilt in r2 from 8df66fe4d7 on 572e4f4fad: cherry-pick clean, then the drive_acp reuse amend); merge-tree clean by construction"
superseded_sha = "8df66fe4d74565d33b2bb91972a10609247afba8 (r1 head; r2 moved the local branch to the r2 commit; r3 re-created refs/heads/staging/prefix-parity-journeys-r1 at it, see branch_preserved)"

[[members]]
ref = "refs/fork/lab/z0int/full-observer-v0"
sha = "1662a990a8374f30e047c35f2fb1a6091b2cfe94"
role = "reference only for the identity-join cells (E08); not shipped, no code reused"
live_head = "ce5c027bba (gh api 2026-10-01T11:08Z; local snapshot stale)"
rebase_status = "merge-base bddd22be7c; 5 ahead / 431 behind main aea969677c; merge-tree clean vs aea969677c (r1 said '5 ahead / 395 behind; clean vs 572e4f4fad', mixing two bases: it is 5/384 vs 572e4f4fad and 5/395 vs 234badf401)"

[ride_with]                # D5: never promoted alone. Candidates found by this branch:
own_leaf = { id = "acp-compress-prompt-nesting (proposed new staging item)", change = "acp_adapter/commands.py: call compress_now(agent, state.history, request, task_id=...) without system_message; update tests/acp_adapter/test_server.py::test_compact_compresses_context, which currently asserts the buggy argument", owner = "none found (ours): #76224, #88364 and #110763 all keep passing the cached prompt", evidence = "receipts/LEAF-acp-nesting-r20261001-03.json (unit, with raw logs) + receipts/ACP-arms-r20261001-03.json arm fixA; LEAF re-checked on main 040b6df2c4 in r3 (see [evidence].harness_check_r3)" }
salvage_support = { prs = [88364, 76224], authors = ["dosenr", "JonthanaHanh (commit author RelaxJonh)"], form = "support, not a carrier. #88364 already carries the real-SessionDB restart regression the #76224 reviews asked for (dosenr; also posted on #76224 as tests/acp/test_76215_regression.py) -- credit it, never re-offer it. What only this branch adds: the reload through real hermes acp processes on the provider's request bytes, and the finding that the cause-1 fix alone persists the nested prompt (arm hp76224), so cause 2 has to land as well. The hp76224 arm hand-ports the shared idea; folding it in would need Co-authored-by: RelaxJonh <92573950+RelaxJonh@users.noreply.github.com> and dosenr." }

[ownership]
searched_at = "2026-10-01T11:08Z"
queries = ["prefix stability", "test_prefix_stability", "prompt cache prefix journey", "acp compress", "acp /compress duplicated", "_cached_system_prompt compress", "compress_now system_message", "compress_now", "system prompt duplication", "76215", "acp_adapter/commands.py (open)"]
open_external = [88364, 76224, 72694]
merged_overlap = [109610]
closed_overlap = [110763]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # TUI/HUD lanes; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
verdict = "journeys: OURS (no competitor). #76215 cause 1: EXTERNAL (#88364 by dosenr, the issue filer, building on #76224) -> support and credit. Nesting cause 2: unowned -> own leaf. r1 missed #88364; found by the r2 '76215' search."

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
revision = "r03 re-issues r02 from the same sealed raw set (no run repeated): corrected env.host_load, raw set and as-run harness moved under private/, parametrized harness. r02 superseded r01. Both earlier sets are kept unchanged: private/superseded-r02/ (clean, but carries the wrong host-load range) and private/superseded-r01/ (carried local paths, the host name and synthetic session/turn ids)"
public = ["receipts/ (the 7 r03 receipts + SHA256SUMS)", "harness/ (no local paths, host or user names: they come from the environment)", "arms/", "prefix-parity-journeys.patch", "PR_BODY.md", "STAGING.md"]
private = "private/: raw-r02 (sealed raw set), harness-r02 (the as-run harness, local paths inline), harness-check-r03 (r3 fixer runs), superseded-r01, superseded-r02. Cited by sha256 only; never published, never frozen."
freeze_set = "exactly the 7 receipts below plus receipts/SHA256SUMS; nothing under private/"
errata = [
  "r02 env.host_load said '(5-15 on 10 cores)' in all 7 receipts; the recorded per-run load1_end values (raw runs.jsonl, 25 runs) range 7.91-18.43 on 10 cores / 20 threads. Fixed in r03, which computes the range from runs.jsonl instead of typing it.",
  "r02 receipts cite raw at receipts/raw-r02/ and the harness at harness/; since r3 the same bytes are at private/raw-r02/ (manifest sha256 unchanged) and private/harness-r02/ (sha256 values unchanged).",
]
receipts = [
  { id = "E07/r20261001-03", path = "receipts/E07-r20261001-03.json", sha256 = "093c0fce1eae966e2785861097a13477d91e8445b9a6efcfdcfca86e335e6cd4", supersedes = "E07/r20261001-02 (6a0957c7d76c)" },
  { id = "E08/r20261001-03", path = "receipts/E08-r20261001-03.json", sha256 = "de5b16641a0460236b55b47bd6e4921d903f7c4f6f9751084e1f281b98be21e2", supersedes = "E08/r20261001-02 (957d635781b8)" },
  { id = "NC/r20261001-03", path = "receipts/NC-sabotage-r20261001-03.json", sha256 = "46159ad07392fdbdef556d927dea10b06fabf17562593da1ef8668df2d97b34f", supersedes = "NC/r20261001-02 (29bc24b06729)" },
  { id = "ACP-arms/r20261001-03", path = "receipts/ACP-arms-r20261001-03.json", sha256 = "8d9822bbf8f8517bbae6d120ef9410344ffe4b6e59501d2de3d682d797f7e06c", supersedes = "ACP-arms/r20261001-02 (10101db1b650)" },
  { id = "LEAF-acp-nesting/r20261001-03", path = "receipts/LEAF-acp-nesting-r20261001-03.json", sha256 = "7c5c7bf501ef55ff9bb33c174213ec853bcb144572a536de9de680eaa19de57f", supersedes = "LEAF-acp-nesting/r20261001-02 (da28c7333692)" },
  { id = "ADJ/r20261001-03", path = "receipts/ADJ-r20261001-03.json", sha256 = "f0328f39ee54ebdf5cbee08d430b72e0c413255f6ad7ea6b9497d2d691092f99", supersedes = "ADJ/r20261001-02 (b65b077875fa)" },
  { id = "E09-smoke/r20261001-03", path = "receipts/E09-smoke-r20261001-03.json", sha256 = "4804c886eeabbfc95359246e1c61c75c5697d305d15e6d65a030e1a5b04f71ba", supersedes = "E09-smoke/r20261001-02 (8a5c3d586aa5)" },
]
r03_diff_check = "field-by-field diff of each r03 receipt against its r02: 18 changed leaves each, all in id, supersedes, reissue, env.host_load, raw.dir, raw.manifest, inputs.harness and inputs.harness_as_run; every measurement, outcome and command is unchanged"
raw_manifest = { path = "private/raw-r02/MANIFEST.sha256", sha256 = "99cb8fdfe8896a88b28a88e623659c4f5f958424a0ac16c049ad5a997923e635", note = "private; path-scrubbed before sealing; never published or frozen; moved from receipts/raw-r02/ in r3, bytes unchanged (sha256sum -c OK)" }
harness_check_r3 = { raw = "private/harness-check-r03/ (MANIFEST.sha256 19e9d229d5f35c9e)", label = "OBSERVED (fixer, self; not a receipt)", what = "the parametrized harness/sandbox.sh + harness/run_receipts.sh run end to end in the sandbox (egress canary blocked, errno 101). LEAF with MAIN_REF = main 040b6df2c4: 37 passed; 36 / 1 failed ('assert 'system' is None'); 37 passed; 36 / 1 failed ('assert None == 'system''), as in r02. Gated file on the merge of main 040b6df2c4 and the head (tree a0f5d700fc): 5 passed + 1 xfailed (acp_restarts), file 140 s at load1 5.6; gate off: the RED marker below, byte 5377" }
red = { test = "test_request_prefix_is_byte_stable_across_processes[acp_restarts]", main = "aea969677c", how = "head with known_gate off (arms/red-ungate-known.patch)", marker = "prompt-cache prefix broke outside the compaction boundary: request 9 (in hop 4 (acp in work-a)): messages[0] (system) changed; first diverging byte at 5377", receipt = "E07/r20261001-03" }
green = { result = "5 passed + 1 xfailed (acp_restarts) on the head (gated file)", receipt = "E07/r20261001-03" }
negative_control = { mutation = "NC1 per-request timestamp in the system message; NC2 stored prompt stale on every fresh agent + per-build nonce", result = "NC1 (per-request timestamp in the system message) fails 6/6 journeys and NC2 (#104414 shape) fails 6/6; the ACP gate excused neither", receipt = "NC/r20261001-03" }
adjacent = { identical = true, files = ["tests/e2e/core/parity/test_entrypoint_parity.py 8/8 both (exercises the refactored drive_acp)", "tests/e2e/core/history/test_transcript_ledger.py 10/10 both"], main = "aea969677c", pre_existing = [], receipt = "ADJ/r20261001-03" }
leaf = { result = "on main: base 37 passed; updated unit test alone 36 passed / 1 failed (Compression failed: assert 'system' is None); fix + updated test 37 passed; fix + current test 36 / 1 failed (assert None == 'system'), so the current test pins the bug", main = "aea969677c (re-checked on 040b6df2c4 in r3: same four results)", receipt = "LEAF-acp-nesting/r20261001-03" }
quantitative = []
cache_read_ratio = { status = "NOT_MEASURED", note = "fake provider records bytes, not cache billing; real-cache arm queued (T3)" }
route_scope = "n/a"
not_tested = ["real provider cache billing", "Relay exporters (venv nemo-relay older than tree)", "serve WS / A2A / relay connector / /goal journeys", "cwd change between lives on msg/api/acp", "retained inactive/compacted rows after ACP /compress (covered by dosenr's test in #88364, not here)"]

[gates]
P1 = "PASS (ACP red reproduced on aea969677c with the gate off; branch rebuilt on that main)"
P2 = "PASS (no competitor for the journeys; #76215 cause 1 owned by #88364/#76224 -> support with credit; nesting unowned)"
P3 = "PASS (test-only, one invariant family, no env vars, no new hooks; +302/-61 in 5 test files; drive_acp reuse instead of a copy)"
P4 = "PASS (real entrypoints in subprocesses; only the LLM is faked; Telegram adapter is the parity suite's recording fake)"
P5 = "PASS (RED: ACP on main, gate off, marker matched; GREEN 5 passed + 1 xfailed (acp_restarts); NC1+NC2 NC1 6/6 + NC2 6/6 FAIL; ADJ identical; LEAF RED/GREEN with raw logs)"
P6 = "N_A (no value claim)"
P7 = "PASS (one commit on fresh main aea969677c, author + conventional subject; push-trigger scan of the head's workflows: 11 have push triggers, none matches staged/prefix-parity-journeys; never pushed)"
P8 = "PENDING (r03 receipts written locally, scrubbed of paths/host/ids; raw and as-run harness sealed under private/; freeze set = the 7 r03 receipts + SHA256SUMS only; not frozen to z0evals)"
P9 = "PASS (PR_BODY.md: template sections, honest NOT_TESTED, AI disclosure, no @mentions, no factory jargon; r2 corrected the NC2 and #76224 statements)"
P10 = "PENDING (the r1 blind verification covered 8df66fe4d7; the r2 head needs its own exact-head read)"
P11 = "FAIL alone (D5): test-only; promotable only with the ACP nesting fix plus a cause-1 fix, or on maintainer request (see [ride_with])"
P12 = "PENDING (owner queue)"

[acceptance_gates]       # from selection.json
each_journey_green_or_typed_pin = "MET: messaging + api_server GREEN; ACP pinned with known_gate on its own signature + repro comment"
sabotage_negative_control = "MET: NC1 (per-request timestamp in the system message) fails 6/6 journeys and NC2 (#104414 shape) fails 6/6; the ACP gate excused neither"
within_e2e_runtime_budget = "MET (OBSERVED local, busy host): file 213 s for 6 journeys on the head vs 87 s for the 3 existing journeys on main in the same pass (load1 15.3 and 12.4); per-test sums 192.9 s vs 83.7 s. r1 measured 137 s vs 68 s at load1 about 4-5; per-file CI timeout 900 s; adds about one minute to one of 3 e2e workers (MODELED)"
promote_only_with_real_fix = "HOLD (by design): candidates exist (own nesting leaf; #88364/#76224 support)"

[verification]
verifier = ""
provenance = "independent"
exact_head = "ddf4748d31cb5dc65e7cd0b0c5b27b98d63ae880"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
prior = "r1 phase-3 verifier (8df66fe4d7): code sound, manifest inaccurate; all listed problems addressed in r2. Round-1 re-verifier (ddf4748d31): not accepted, code sound, reruns on current main reproduced GREEN, RED, the three ACP arms, NC1, NC2, LEAF and ADJ (reported); 7 text/receipt/hygiene problems, all addressed in r3 (see History)"

[merge_check]
main_sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
checked_at = "2026-10-01T11:04Z"
clean = true
note = "the branch is one commit on this main"
later_checks = [
  { main = "e8c97320ac8691d4de92af49f98459f9ef9ddb08", checked_at = "2026-10-01T11:46Z", merge_tree_clean = true, tree = "5e69382ef6", note = "6 commits after the base; none touches acp_adapter/, tests/e2e/, tests/fakes/, tests/acp_adapter/, gateway/ or the compression/prompt modules; tests not re-run on it" },
  { main = "040b6df2c40b0f4f88f51e4c2062eafc4d7463c5", checked_at = "2026-10-01T12:09Z (git ls-remote: still the upstream head)", merge_tree_clean = true, tree = "a0f5d700fc", note = "8 commits after the base aea969677c, 2 after e8c97320ac (f1df745d71, 040b6df2c4: test(auth) only, touching tests/agent/test_credential_pool_codex_quota_probe_rotation.py and tests/hermes_cli/test_auth_codex_quota_probe.py). None of the 8 touches acp_adapter/, tests/e2e/, tests/fakes/, tests/acp_adapter/, gateway/ or the prompt/compression modules. Re-run on the merged tree in r3: gated file 5 passed + 1 xfailed, RED marker unchanged, LEAF unchanged ([evidence].harness_check_r3)" },
]
recheck = "git -C <h.git> merge-tree --write-tree main staging/prefix-parity-journeys"

[push]
remote_branch = "staged/prefix-parity-journeys"
no_follow_tags = true
workflow_push_matches = 0
workflow_push_triggered = 11
pushed_at = ""

[body]
path = "frontier-2026-10-01/staging/prefix-parity-journeys/PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PASS (manual)"
privacy_scan = "PASS (no home paths, emails, session ids or message text in the body)"

[queue]
board = "kvnloo/hermes-agent#404"
position = "no row (the board lists 39 ready/* branches); add one only together with a ride_with item"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

## Invariant

On the messaging gateway, the api_server (`/v1/runs`) and ACP, a session driven through four fresh process lives must keep a byte-stable request prefix. Every main request extends the previous one byte for byte. There is exactly one break, at the compaction. The prompt rebuilt at that compaction never contains the previous prompt.

Call paths exercised (only the LLM is faked, by `FakeLLMServer` on loopback):

- **Messaging gateway:** `gateway.run.main` → `GatewayRunner` → session store → `AIAgent`. The Telegram adapter instance is the parity suite's recording fake. `/compress` arrives as a DM.
- **api_server:** `python -m gateway.run` with api_server only → `POST /v1/runs` addressed by `session_id`. Compaction is triggered by context pressure that the provider reports.
- **ACP:** `hermes acp` (spawned and initialized by the parity driver's `spawn_acp`) → `session/new`, then `session/load` → `session/prompt`. `/compress` goes through `acp_adapter/commands.py` into `compress_now`.

## Route and promotion form

The route is ride-along under the `eval-contribution` form (FACTORY D5: test infrastructure never goes upstream alone). The form does not change in r2. The ownership refresh found a second external fix for cause 1 (#88364), which strengthens the support route. It does not touch the journeys or the nesting defect.

**Premise re-check on main `aea969677c`:**

- C17 still covers only `tui_gateway`, the oneshot CLI and `surface_switch` between them.
- No open upstream PR touches `test_prefix_stability.py`.

**What changed since selection.** The selection expected all journeys to stay green, or to need a `ToolsArrayDrift` pin. One journey went red instead (ACP), and the break is in the system prompt and messages, not in the tools array. So the pin is a `known_gate` keyed on that failure's own message, using the suite's merge-order-safe pattern from `tests/e2e/core/_pending_fixes.py`, and not `raises=ToolsArrayDrift`.

**Two real defects sit behind the ACP red:**

| # | Defect | Owner | Route |
|---|---|---|---|
| 1 | `/compress` state is not persisted, so `session/load` replays the pre-compaction rows | NousResearch/hermes-agent#76215 (open, filed by dosenr). Two open fixes, both DIRTY against current main (they target pre-#109610 paths): NousResearch/hermes-agent#76224 (JonthanaHanh; commit author RelaxJonh; manual `/compress` only) and NousResearch/hermes-agent#88364 (dosenr; builds on #76224 with Co-authored-by RelaxJonh; sets `compression_in_place` at ACP agent construction, so it also covers #49226). #110763 (enzoferrari-cc) refreshed #88364 onto current paths and was closed by its author. | **Support, with credit.** The sweeper review on #76224 (pestoura asked the same) wanted "a real-SessionDB ACP regression that compacts a seeded session, restores the same session ID, and verifies the compacted live history plus retained inactive/compacted original rows". dosenr already wrote such a test: posted on #76224 on 2026-08-12 (`tests/acp/test_76215_regression.py`), and #88364 carries `test_compact_survives_process_restart`, which checks the compacted active transcript and the archived original rows. `acp_restarts` is not that regression and must never be offered as it: it checks that the replay equals the persisted rows and that no active row is duplicated, but never that the original rows survive as inactive/compacted. What it adds: the same reload through real `hermes acp` processes, judged on the provider's request bytes, and the finding that a cause-1 fix alone persists the nested prompt. If the hand-port is ever folded in: Co-authored-by RelaxJonh and dosenr. |
| 2 | The ACP caller passes `system_message=agent._cached_system_prompt` to `compress_now`, so the rebuilt prompt nests the old one (the shape #15281 fixed for the CLI) | None found. #109610 kept the argument when it unified `/compress`. #76224, #88364, #110763 and #72694 do not touch it. | **Own leaf.** Candidate in `arms/candidate-acp-compress-no-nesting.patch`: 2 production lines, plus 2 lines in the existing unit test, which currently asserts the buggy argument. |

**Arm results** (WAVE-row style; `ACP-arms-r20261001-03`, on head `ddf4748d31`):

| Arm | Gated journey | Gate off: failing assertion | System prompt chars (req 6 → 7 → 9) | Summary after reload |
|---|---|---|---|---|
| main | XFAIL | request 9 (hop 4): `messages[0]` (system) changed | 6242 → 12486 → 6242 | lost |
| fixA (drop `system_message`) | XFAIL | request 9 (hop 4): `messages[4]` (assistant) changed, the stale transcript | 6242 → 6242 → 6242 | lost |
| hp76224 (hand-port of the #76224/#88364 idea: `compression_in_place=True` instead of detaching `_session_db`) | XFAIL | the nesting assertion at request 7: 6470 → 12942 chars in the pytest run | 6242 → 12486 → 12486: the nested prompt is persisted and restored | kept |
| both | **PASS** (gate on and off) | none | 6242 throughout | kept |

The char columns come from the probe (`harness/journey_probe.py`), which runs outside pytest. The probe and the assertion measure the system message with the same function (`test_prefix_stability._system_text`). The numbers differ only because the runs differ: the prompt contains the run's tmp/cwd paths, and pytest's are longer than the probe's. So the pytest prompt is 228 chars longer before the compaction (6470 vs 6242) and 456 longer after it (12942 vs 12486), since the nested prompt holds the old one a second time. The round-1 re-verifier's own pytest rerun also gave 6470 → 12942.

## Evidence

Receipts r03 are in `receipts/`, with sha256 values in `receipts/SHA256SUMS`. They re-issue the r02 receipts from the same sealed raw set; no run was repeated. Each r03 receipt carries a `reissue` field saying what changed, and a field-by-field diff against r02 confirms nothing else did:

- `env.host_load`: r02 said "5-15 on 10 cores". The recorded per-run load1 at run end is 7.91-18.43 over 25 runs (10 cores / 20 threads), and r03 now computes the range from `runs.jsonl` (erratum in `[evidence].errata`).
- Raw path: the raw set moved from `receipts/raw-r02/` to `private/raw-r02/`, bytes and `MANIFEST.sha256` unchanged.
- Harness: `harness/` now takes every local path, the user and the host from the environment. The files that produced the raw set are kept byte-identical and private in `private/harness-r02/`, cited by sha256 in `inputs.harness_as_run`.

The receipts carry no local paths, host name, session or turn ids, or prompt text: paths are placeholders (`<wt>`, `<venv>`, `<raw>`), E08 samples are dropped, and failure messages are cut after the diverging byte offset. Earlier sets are kept unchanged and private: r02 in `private/superseded-r02/`, and r01 (receipts, raw and harness) in `private/superseded-r01/`. Each receipt names the one it supersedes, with its sha256. Everything under `private/` is cited by sha256 only and is never published or frozen. The freeze set is the 7 r03 receipts plus `receipts/SHA256SUMS`.

Every r02 run happened inside the as-run `sandbox.sh`, in one sequential `run_receipts.sh` pass on head `ddf4748d31` with `MAIN_REF=aea969677c` (both now in `private/harness-r02/`):

- bwrap network namespace, loopback only;
- egress canary `1.1.1.1:443` blocked with errno 101 (loopback connected);
- `<live-home>` masked, except the read-only venv bind;
- scratch HOME/HERMES_HOME (`testhome-sf-prefix-parity-journeys`).

The host was shared with other workers (load average 7.9-18.4 on 10 cores / 20 threads at run ends), so wall times run long.

In r3 the parametrized `harness/` was run end to end in the same sandbox (`[evidence].harness_check_r3`, private raw). LEAF on main `040b6df2c4` gave the same four results as r02. On the merge of `040b6df2c4` and the head, the gated file gave 5 passed + 1 xfailed, and with the gate off the RED marker was unchanged. These are fixer checks, not receipts.

| Experiment | Receipt | sha256 | Verdict | Label | n | Key numbers |
|---|---|---|---|---|---|---|
| E07 first slice: GREEN gated, RED gate-off, request-stream metrics | `receipts/E07-r20261001-03.json` | `093c0fce1eae` | KEEP | OBSERVED | 6 journeys (pytest) + 1 RED run + probe | See note 1 |
| E08 identity joins on `turn_id` | `receipts/E08-r20261001-03.json` | `de5b16641a04` | KEEP (no gap found) | OBSERVED | 6 journeys, 5 surfaces, 67 hook records for 67 main requests | See note 2 |
| NC sabotage (acceptance gate 2) | `receipts/NC-sabotage-r20261001-03.json` | `46159ad07392` | PASS | OBSERVED | 2 mutations × 6 journeys | See note 3 |
| ACP arms (main / fixA / hp76224 / both) | `receipts/ACP-arms-r20261001-03.json` | `8d9822bbf8f8` | `both` is the only PASS | OBSERVED | 4 arms × (gated + gate-off + probe) | See the arm table above |
| Candidate leaf at unit level, with raw logs | `receipts/LEAF-acp-nesting-r20261001-03.json` | `7c5c7bf501ef` | KEEP (candidate) | OBSERVED | 4 runs × 2 files, 37 tests | See note 4 |
| Adjacent suites | `receipts/ADJ-r20261001-03.json` | `f0328f39ee54` | identical | OBSERVED | 2 files × 2 trees | parity 8/8 and ledger 10/10 on main `aea969677c` and on the head |
| E09 smoke (harness validation) | `receipts/E09-smoke-r20261001-03.json` | `4804c886eeab` | HARNESS_OK (not evidence) | OBSERVED (smoke) | 3 surfaces × 5 reps | See note 5 |

Notes:

1. **E07.** Gated file on the head: 5 passed, 1 xfailed (`acp_restarts`). With the gate off, `acp_restarts` fails with the RED marker above. Probe: messaging gateway and api_server each send 11 requests over 4 lives with 1 break, at the compaction, and 0 unexpected. ACP has 1 unexpected break at request 9, and its compaction nests the previous prompt (6242 → 12486 chars). Usage equals what was billed on all 6 journeys.
2. **E08.** Hook records per journey: 11, 10, 13, 11, 11, 11, which is 67 for 67 main requests. r1 and the phase-3 build report said 66, although the r1 receipt itself also adds up to 67. 100% join completeness on every surface. Every `turn_id` is well-formed (`<session>:<task>:<8hex>`) and its session is in the lineage. There is one `turn_id` per user turn, and `api_request_id` and `first_chunk_at` are present 100%. The recorder changes no E07 verdict.
3. **NC sabotage.** NC1 fails 6 of 6 journeys. Its first break is request 1, inside the first process life, everywhere except `oneshot_restarts`, whose first life sends a single request. NC2 fails 6 of 6. For 5 journeys the first NC2 break is the first request of the second process life (request 4, or request 1 for the oneshot). For api_server it is request 1, inside the first life (see Observations).
4. **Candidate leaf.** On main `aea969677c`, `tests/acp_adapter/test_server.py` + `test_acp_commands.py`: 37 passed as is. The updated unit test alone fails once (`Compression failed: assert 'system' is None`). With the fix, 37 passed. The fix with the current unit test fails once (`assert None == 'system'`), because that test pins the bug. r1 had no raw output for these claims; since r02 the logs are in the raw set. r3 re-ran the four runs on main `040b6df2c4` with the same results.
5. **E09 smoke.** Medians with provider TTFT fixed at 50 ms, load1 about 8: tui_gateway 142 ms, api_server 101 ms, ACP 77 ms submit → first delta; pre-API 91 / 50 / 26 ms. These numbers are not a measurement.

Inputs pinned:

- **Commits:** base `aea969677c60a1bb72fe227fdfb98f196a2092cc` (tree `aefff2f588`), head `ddf4748d31cb5dc65e7cd0b0c5b27b98d63ae880` (tree `98f58755a4`). r1 for reference: base `572e4f4fad` (tree `6ec691f75d`; r1 wrongly gave `7c5bdaf2cc`, which is the tree of `234badf401`), head `8df66fe4d7` (tree `14c23c2fa1`).
- **Test blobs at head:** `test_prefix_stability.py` `1133468e43a4`, history `_helpers.py` `f13dbc84a5a3`, `_drive_acp.py` `37627770f32e`, `_drive_gateway.py` `dae72c6a23ee`, `_gateway_child.py` `91b33976cdab`. `fake_llm_provider.py` `339adb7e87ea` is unchanged.
- **Arm patches and harness files:** sha256 values in `receipts/*.json` → `inputs`: `harness` (the public, parametrized files) and `harness_as_run` (the private files that produced the raw set).

**Observations, not findings:**

- **`surface_switch` (an existing journey).** The sanctioned rebuild at its compaction grows the prompt from 6931 to 13558 chars. It adds the skills index and rewords a help paragraph. There is one identity block and no nesting, which is the documented "converges at the next rebuild boundary" behaviour.
- **api_server restores per turn.** Under NC2 its first break is at request 1, inside the first process life, while every other journey first breaks in its second life. So api_server re-runs the stored-prompt restore on every turn, and its within-life byte stability depends on that path.
- **A cwd change between lives rebuilds the prompt by design** (`agent/conversation_loop.py::_stored_prompt_matches_runtime`). The new journeys keep one cwd. An earlier draft that flipped cwd turned api_server and ACP red for that reason alone.

## Gate checklist (P1-P12)

| Gate | Status | Basis |
|---|---|---|
| P1 Need | PASS | ACP red reproduced on `aea969677c` with the gate off; the branch is one commit on that main |
| P2 Ownership | PASS | Journeys: no competitor. #76215 cause 1 belongs to #88364 (and #76224), so we support and credit dosenr's test. The nesting defect is unowned. |
| P3 Shape | PASS | Test-only, one invariant family, no new env vars or hooks, +302/-61 across 5 files; ACP spawn/initialize reused from the parity driver instead of copied |
| P4 Real path | PASS | Real entrypoints in subprocesses; only the LLM and the Telegram adapter instance are fake |
| P5 Proof | PASS | RED (gate off) + GREEN 5 passed + 1 xfailed (acp_restarts), NC1 6/6 + NC2 6/6 FAIL, ADJ identical, LEAF with raw logs |
| P6 Numbers | N/A | No value claim |
| P7 Package | PASS | One commit on `aea969677c`, correct author and subject; 11 workflows have push triggers and none matches `staged/prefix-parity-journeys`; not pushed |
| P8 Freeze | PENDING | r03 receipts are local, write-once and scrubbed; raw and as-run harness sealed under `private/`; the freeze set is the 7 r03 receipts + `SHA256SUMS`; not frozen to z0evals |
| P9 Text | PASS | `PR_BODY.md` (r2 corrected the NC2 and #76224 statements and credits #88364) |
| P10 Independent read | PENDING | The r1 verifier read `8df66fe4d7`; the r2 head needs its own exact-head read |
| P11 Not lone substrate | FAIL alone (by design) | Promote only together with the nesting leaf plus a cause-1 fix, or on maintainer request |
| P12 Queue | PENDING | Owner's call; never claims a slot |

## Acceptance gates (selection)

1. **Each new journey is green, or pinned with a typed known failure plus a repro: MET.** Messaging gateway and api_server are green. ACP has a `known_gate` with an anchored pattern and the mechanism written in the test as a comment.
2. **The sabotage negative control fails a journey: MET.** NC1 (per-request timestamp in the system message) fails 6/6 journeys and NC2 (#104414 shape) fails 6/6; the ACP gate excused neither.
3. **The suite stays within the e2e runtime budget: MET, measured locally on a busy host.** file 213 s for 6 journeys on the head vs 87 s for the 3 existing journeys on main in the same pass (load1 15.3 and 12.4); per-test sums 192.9 s vs 83.7 s. r1 measured 137 s vs 68 s at load1 about 4-5. The per-file CI timeout is 900 s.
4. **Promote only together with a real prefix fix: HOLD (by design).** Real fixes now exist to ride with; see Next steps.

## Experiments queued (not run)

Paths below are placeholders: `<h.git>` the scratch bare repo, `<wt>` a worktree of the branch, `<staging>` this directory, `<venv>` the test venv, `<live-home>` the live Hermes home that the sandbox masks, `<testhome>` a scratch test home, `<probe-tmp>` the probes' scratch root, `<raw>` a new directory under `<staging>/private/`, `<router>` the local model router.

1. **E09 measurement** (T1, $0, `cpu-quiet` lane: exclusive, run only when load1 < 4). Recreate a worktree first:
   ```
   git -C <h.git> worktree add --detach <wt> staging/prefix-parity-journeys
   cd <wt>
   H=<staging>/harness
   export HERMES_VENV=<venv> LIVE_HOME=<live-home> TH=<testhome>
   for aa in 1 2; do until [ "$(cut -d. -f1 /proc/loadavg)" -lt 4 ]; do sleep 30; done
     flock <cpu-quiet.lock> $H/sandbox.sh /bin/bash -c "PROBE_TMP=<probe-tmp> <venv>/bin/python $H/e09_first_delta.py --surfaces gw,api,acp --reps 30 --warmup 1 --delay 0.05 --order ABBA --label E09-aa$aa --out <raw>/e09_aa$aa.json"; done
   ```
   - Run A/A (two identical runs) before any comparison.
   - Report median and p95 per surface, with the A/A spread as the minimum detectable effect.
   - Still to build: the messaging-gateway surface and the `_create_agent` share probe (a timed hook inside the api_server process). The `chat -q` arm needs OD-2.
2. **E11 and the rest of the title's surfaces** (T1, $0, next slice, harness work needed): journeys for the relay connector (`tests/gateway/relay/stub_connector.py`), A2A JSON-RPC (`plugins/platforms/a2a`), `/goal` continuation (`hermes_cli/goals.py`), a kanban worker, and MoA. MoA needs its aggregator's user/user wire adjacency whitelisted. Frame each as a narrow control point (#47092's universal gate was rejected in #64231). After implementing:
   `scripts/run_tests.sh --include-integration tests/e2e/core/history/test_prefix_stability.py -k "relay or a2a or goal or kanban or moa"`
3. **T2: real local KV-cache reuse per surface** (local GPU, strictly serial; blocked by OD-1). The journeys' first request is about 14K chars of system prompt plus 19 tool schemas, which does not fit the router's 8K presets. It also needs a recording-proxy mode in `harness/journey_probe.py` (not written), so request bytes are still recorded while llama.cpp answers. Command once both exist:
   ```
   flock <gpu.lock> $H/sandbox-router.sh <venv>/bin/python $H/journey_probe.py --provider-proxy <router>/v1 --model <64K preset> --journeys messaging_gateway_restarts,api_server_runs_restarts,acp_restarts --out <raw>/e07_t2.json
   ```
   Metric: llama.cpp `timings.cache_n` / `prompt_n` on the first request after each restart.
4. **T3: the real-provider cost of #76215** (paid; needs OD-3; the owner launches; credentials never in the worker). Seed a 12-turn ACP session on Anthropic, `/compress` at turn 9, restart, and record `usage.cache_read_input_tokens` and `input_tokens` on the first request after `session/load`. Arms: main vs `arms/acp-both.patch`. Estimated cost: about 0.25M input tokens per arm, roughly $1–3 total (MODELED). Command once `harness/acp_reload_cache.py` exists (not written):
   ```
   $H/sandbox-paid.sh python $H/acp_reload_cache.py --provider anthropic --model <owner choice> --turns 12 --compress-at 9 --arms main,both --out <raw>/t3_acp_reload.json
   ```

## NOT_TESTED

- **Real provider prompt caches.** `FakeLLMServer` records bytes and scripted usage; it does not bill cache reads. That is the T3 above.
- **Relay exporters (ATOF/ATIF) and Relay `TURN_SCOPE` equality.** The venv's nemo-relay predates this tree, so Relay init failed with a warning and every run was Relay-off.
- **Surfaces not covered:** serve WebSocket, cron, A2A, the relay connector, `/goal`, kanban and MoA journeys (queued).
- **E09 latency numbers.** Smoke only. The real measurement is queued for the quiet lane.
- **Messaging adapters other than the recording Telegram fake.** The real Telegram, Discord and other SDKs, and their delivery paths, are untested.
- **Retained inactive/compacted rows after ACP `/compress`.** The journey does not assert them; dosenr's real-SessionDB test in #88364 does.
- **Non-local terminal backends** (docker, ssh, modal). They print a different runtime block.
- **Windows and macOS.** The suite is Linux-only by construction.

## Next steps

1. **Pair before promoting (D5).** Open a new staging item, `acp-compress-prompt-nesting` (core-leaf, ours), from `arms/candidate-acp-compress-no-nesting.patch`. Its behaviour test is this branch's nesting assertion, plus the updated unit test (`LEAF-acp-nesting-r20261001-03`).
2. **Support #88364 (and #76224), owner action only.** At most one comment, on #88364, the more complete of the two. It would:
   - credit dosenr's restart test as the real-SessionDB regression the #76224 reviews asked for, and not offer `acp_restarts` in its place;
   - report cause 2: even with in-place compaction (arm hp76224), the prompt rebuilt by ACP `/compress` nests the cached one (6242 → 12486 chars) and is then persisted and restored, so a reloaded session keeps the doubled prompt;
   - offer the process-level journey only as an optional complement, and note that both PRs need a rebase onto the post-#109610 `acp_adapter/commands.py` and `tests/acp_adapter/`.
3. **Blind exact-head verification** of `ddf4748d31` by a different worker (P10).
4. **Freeze the cited r03 receipts** to z0evals once STAGING is accepted (P8): the 7 files listed in `[evidence].receipts` plus `receipts/SHA256SUMS`, and nothing under `private/` (the raw set and the as-run harness stay private, sha256 only).
5. **Freshness re-check** within 24 h of any queue action (last: main `040b6df2c4`, 2026-10-01T12:09Z, clean; see `[merge_check].later_checks`):
   ```
   git -C <h.git> merge-tree --write-tree main staging/prefix-parity-journeys
   ```
   Then re-run `-k acp_restarts`. A merge of #88364, #76224 or the nesting fix changes the gate outcome, as the arm table shows.
6. **OD-0: resolved by the rename.** The branch goes to the fork as `staged/prefix-parity-journeys`; the fork's legacy `staging` branch stays untouched. Run the `ls-remote` collision check again right before the push.

## Origin action (owner only)

One of these, never run by the factory:

- (a) Ship together with the nesting leaf:
  ```
  gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/prefix-parity-journeys --title "test(e2e): prefix-stability journeys for the messaging gateway, api_server and ACP" --body-file PR_BODY.md
  ```
  This only makes sense after the leaf PR exists, or bundled with it on maintainer request.
- (b) Post one support comment on #88364, as described in Next step 2.

## History

| Time (UTC) | Status | Worker | Reason |
|---|---|---|---|
| 2026-10-01T08:46Z | CANDIDATE | builder (Claude Code) | Worktree on main `572e4f4fad`; C17 baseline 3/3 in 71 s |
| 2026-10-01T09:32Z | STAGED | builder | Commit `8df66fe4d7`. ACP red found and gated. Messaging gateway and api_server green. |
| 2026-10-01T09:34–09:55Z | EVIDENCED | builder | Sandboxed receipts r01: E07, E08, NC, ACP arms, ADJ, E09 smoke, candidate leaf |
| 2026-10-01 (phase 3) | STAGED | verifier | Not accepted: code sound, manifest inaccurate (E08 count, base tree, fork-ref counts, NC2 and #76224 overstatements, dosenr's test uncredited, LEAF without raw output, stale freshness, drive_acp copy, receipt privacy) |
| 2026-10-01T11:04–11:50Z | STAGED | fixer (Claude Code) | r2: rebuilt on main `aea969677c` with `spawn_acp`/`close_acp` reuse (`ddf4748d31`); receipts r02 (scrubbed, LEAF raw included); #88364 added to ownership; text corrected; branch on the fork will be `staged/prefix-parity-journeys` (OD-0) |
| 2026-10-01 (round-1 re-verify) | STAGED | verifier | Not accepted; code sound, reruns on current main reproduced every claim. Problems: harness/ held local paths and the host name although receipts cite it; raw set inside receipts/; STAGING named two local paths; r02 host_load range wrong; hp76224 char-count reason wrong; #76215 repro date wrong; freshness stopped at `e8c97320ac`; no ref kept on the r1 head |
| 2026-10-01T12:05–12:25Z | STAGED | fixer (Claude Code) | r3, branch and commit unchanged (`ddf4748d31`). harness/ parametrized (paths, user, host from the environment), as-run copy moved to `private/harness-r02/`; raw moved to `private/raw-r02/`; receipts r03 re-issued from the same raw (host_load corrected, diff-checked against r02), r02 kept in `private/superseded-r02/`; STAGING placeholders `<live-home>`/`<probe-tmp>`; arm-table and #76215 wording fixed; freshness at main `040b6df2c4` (clean, tree `a0f5d700fc`; gated file, RED and LEAF re-run). r1 head: r2 had moved the branch rather than rebuilding it as `-v2`. The preserved artifact is `private/superseded-r01/prefix-parity-journeys.patch` (identical to `git format-patch` of `8df66fe4d7`), and `refs/heads/staging/prefix-parity-journeys-r1` now points at `8df66fe4d7` again |
