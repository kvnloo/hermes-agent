+++
xf_staging = 1
id = "tool-result-projection-support"
title = "Evidence and rebase support for #107731 boundary-stable tool-result projection"
version = 3                # branch version: v3 = 3b47753d54 (round 3: same test blob, rebuilt on main 44a1ce9724, commit message corrected); the fold-in gate is at v4 (v3 code, corrected docstring)
promotion_form = "salvage-support"
branch = "staging/tool-result-projection-support"
branch_fork = "staged/tool-result-projection-support"
branch_physical = "local-only in the scratch bare mirror h.git; never pushed. On kvnloo/hermes-agent it goes up as staged/tool-result-projection-support, because the fork's legacy refs/heads/staging blocks staging/<id> (OD-0 resolved by that rename)"
branch_sha = "3b47753d54be51a06a7f9a939f9edea579f3c949"
naming_exception = "FACTORY section 10 names a rebuild staging/<id>-vN and forbids force-push. The orchestrator fixes the local name staging/tool-result-projection-support and the fork name staged/tool-result-projection-support to the newest version, so the local ref is force-moved on each rebuild (round 1: v1 d5854fdd7b -> v2 8c783ff4ac; round 3: v2 8c783ff4ac -> v3 3b47753d54). Nothing was ever pushed. Waiver recorded here for the moving name only. Every version stays reachable and is never deleted: refs/archive/staging/tool-result-projection-support-v1 (d5854fdd7b, the phase-3 verdict head), -v2 (8c783ff4ac) and -v3 (3b47753d54, the current head) in h.git, outside refs/heads so no branch push picks them up, plus one patch per version next to this manifest."
versions = [
  { v = 1, sha = "d5854fdd7b7f8082c529c975c3d8d6a39513d76c", ref = "refs/archive/staging/tool-result-projection-support-v1", base = "234badf401", note = "round 0 (phase-3 verdict head); patch patches/tool-result-projection-support.v1-d5854fdd7b.patch; test blob 7347ad045b" },
  { v = 2, sha = "8c783ff4ac2fcd7906e074eefec7f0d3fcfc0782", ref = "refs/archive/staging/tool-result-projection-support-v2", base = "aea969677c", note = "round 1 cherry-pick of v1, same test blob; head in rounds 1-2; patch patches/tool-result-projection-support.v2-8c783ff4ac.patch" },
  { v = 3, sha = "3b47753d54be51a06a7f9a939f9edea579f3c949", ref = "refs/heads/staging/tool-result-projection-support + refs/archive/staging/tool-result-projection-support-v3", base = "44a1ce9724", note = "round 3: v2 cherry-picked onto main 44a1ce9724 and the commit message corrected (attribution of the fixed-boundary ask and of the stickiness question); same test blob 7347ad045b; current head; patch patches/tool-result-projection-support.v3-3b47753d54.patch" },
]
status = "STAGED"        # class ceiling at $0: LIMITED (P6 waits on an OBSERVED cache-read ratio, OD-3). Not LIMITED yet: P5 is PENDING (F14 not run) and P8, P9, P10, P12 are pending. Rounds 0-2 said LIMITED while P5 was overstated as PASS. The carrier fails the preserved-thinking gate without the fold-in, and the fold-in gate itself fails across a restart (see the gate section)
route = "support-note"
feature = "boundary-stable-tool-result-projection"
invariant = "An opt-in wire-only projection of stale tool results must break the request prefix only at a paid batch boundary, never undo an archived row, and never rewrite a prefix that a replayed signed thinking block is bound to."

[base]
repo = "NousResearch/hermes-agent"
sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
fetched_at = "2026-10-01T11:10-05:00 (gh api commits/main; commit time 10:56:40-05:00). Every count, SHA and test result in this round was re-measured on this main. The staging commit's parent is this main. e8c97320ac..44a1ce9724 is 23 commits; none touch the carrier's 13 files, the test file, its helpers and fakes, or the converter files cited (git diff --quiet on those paths)"

[upstream]
issues = ["NousResearch/hermes-agent#107731 (carrier PR, open)", "NousResearch/hermes-agent#39691 (open)", "NousResearch/hermes-agent#47866 (merged)", "NousResearch/hermes-agent#129620 (open)", "NousResearch/hermes-agent#129492 (open)", "NousResearch/hermes-agent#129882 (open)", "NousResearch/hermes-agent#106426 (open)", "NousResearch/hermes-agent#70107 (open)", "NousResearch/hermes-agent#526 (open)"]
fork_rfc = ["kvnloo/hermes-agent#310 ([RFC-2] Track 2 - SoL-Pi ObservationPack deep integration, open)"]
eval_prs = []
carrier = { pr = 107731, author = "lorencato23", head = "069adfb67e57287ac8df996ef48e082fe8455e2c" }
competitors = []
adjacent_open = [
  { pr = 110874, author = "wojciechwiesner", note = "JIT Context Engine, 'deterministic history projection' - different mechanism, not a duplicate" },
  { pr = 124273, author = "defurniture2025", note = "proactive prune rewrites changed rows in place - prune path, not projection" },
  { pr = 106426, author = "teknium1", note = "drop_block opt-in on Claude 5.1+: turns a projection-induced 400 into silently dropped thinking" },
  { pr = 70107, author = "Eklps", note = "ordered-carrier thinking recovery (the gap the enforced emulation hit)" },
]
close_after = []
demand = { score = 55, source = "selection.json (#39691 r=17, #47866 r=27)" }
maintainer_signal = "teknium1 2026-09-23 harness-scout note ('design evidence, not a review verdict'), addressed 'for whoever salvages this': keep the wire-only projection, move the trigger to a fixed boundary, measure the cache-read ratio before/after in the PR body. kshitijk4poor 2026-09-22 read-only review: three maintainer-only questions open (second wire view, in-memory stickiness that a restart, resume or gateway rebuild empties, 4 keys vs prune mode) plus defects to fix regardless. Neither has an answer from the author on the thread (checked read-only 2026-10-01 ~11:15 -05:00)."

[[donors]]
sha = "069adfb67e57287ac8df996ef48e082fe8455e2c"
author = "lorencato23"
role = "carrier (6 commits, +1936, unmodified)"

[[donors]]
sha = "3b47753d54be51a06a7f9a939f9edea579f3c949"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "fold-in test (wire contract, 2 scenarios) - the staging commit v3; same test blob 7347ad045b as v1 d5854fdd7b and v2 8c783ff4ac"
trailer = "Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"

[[donors]]
sha = "patches/foldin-preserved-thinking-gate-v4.diff (sha256 0d2b808bd2a9d581e23411fcfbffa429109706360218425c96e0917e2013712c)"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
role = "fold-in gate v4 (+54, ledger patch on the carrier's agent/tool_result_projection.py, blob a76fb42f76 -> a3227c92a7). v4 = v3 with the docstring corrected: v3 said sticky rows are 'already part of the bound prefix', which holds only inside one agent; v4 says the gate needs stickiness that survives a restart. No code line differs from v3 (+50). Supersedes v3 (patches/foldin-preserved-thinking-gate-v3.diff), v2 (+40) and v1 (+27), all kept for the record. Known defect, disclosed: across a restart the gate sends archived rows back in full (RESTART/r20261001-01)"

[ownership]
searched_at = "2026-10-01"
queries = ["tool result projection", "stale tool results", "ObservationPack", "projection boundary", "clear_tool_uses", "context editing", "#107731"]
open_external = [107731]
merged_overlap = [47866]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
carrier_activity = "lorencato23's last commit (069adfb67e) and last comment on #107731 are both 2026-09-11 (15:02 UTC). No reply since to kshitijk4poor (2026-09-22) or teknium1 (2026-09-23). The account is active elsewhere on GitHub (public events as late as 2026-10-01). No salvage PR exists (gh search prs '107731' and 'tool result projection', read-only 2026-10-01)."
verdict = "EXTERNAL (lorencato23 owns the open PR; quiet on it since 2026-09-11) -> support, never a competing PR. teknium1's note invites a salvage; that is an owner decision (OD-S below), not taken here"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
receipts = [
  { id = "F04/r20261001-04", path = "receipts/F04-r20261001-04.json", sha256 = "997b0c8d6365bf1198b1f03381bf6ff187947357d051d3ac44cf79055880fe76" },
  { id = "F04-enforced/r20261001-04", path = "receipts/F04-enforced-r20261001-04.json", sha256 = "b4144dcec03e1f0639e059ae5f84069344e0e2ee831853ef1c629fec360a41af" },
  { id = "F04-bedrock/r20261001-03", path = "receipts/F04-bedrock-r20261001-03.json", sha256 = "6aa60de612d9502024f3ae4c446641a1b2214f033647373afe0e88ff8e9011d7" },
  { id = "F04-thirdparty/r20261001-02", path = "receipts/F04-thirdparty-r20261001-02.json", sha256 = "ea5a836e99d4ea70efc432fc128bc4fb8b27f118e58a4a0b6f949d491eed526e" },
  { id = "RESTART/r20261001-01", path = "receipts/RESTART-r20261001-01.json", sha256 = "99d4ffed267d98f17235c38607c360cad5effcbf771acf24c03f39eb2da1d9a4" },
  { id = "PREDICATE/r20261001-03", path = "receipts/PREDICATE-r20261001-03.json", sha256 = "ff00d21f98eda188a6b73980f728edb72efa4ecb8b1da7774806d98e8219d668" },
  { id = "E37-synthetic/r20261001-04", path = "receipts/E37-synthetic-r20261001-04.json", sha256 = "85e09c041fad3b03e6c891b004b5d5761df45885098ebcb76931c50eadd7da47" },
  { id = "GUARDS/r20261001-04", path = "receipts/GUARDS-r20261001-04.json", sha256 = "6c265ba844e105a23c3dbe1e504887d2157eba588f5be2135bb85538c1591d04" },
  { id = "CARRIER-rebase/r20261001-04", path = "receipts/CARRIER-rebase-r20261001-04.json", sha256 = "df0defd8a3beb91691dbd695a80ac2cd99afc37939c87ffa82e32b1c2b5207c4" },
  { id = "SRC-preserved-thinking/r20261001-04", path = "receipts/SRC-preserved-thinking-r20261001-04.json", sha256 = "9eb7ad53014e6baefed1f0cfefaf37671b1174cf0c308fc404748e7f4184a633" },
]
superseded_receipts = "round 0 (r20261001-01, on 572e4f4fad / 234badf401), round 1 (r20261001-02 plus F04-bedrock/r20261001-01 and PREDICATE/r20261001-01, on aea969677c) and round 2 (r20261001-03 plus F04-bedrock/r20261001-02, F04-thirdparty/r20261001-01 and PREDICATE/r20261001-02, on e8c97320ac) stay in receipts/ with corrections blocks and superseded_by; see History"
red = { test = "test_projection_breaks_the_prefix_once_per_paid_batch_and_never_undoes_itself", main = "44a1ce9724 (also e8c97320ac in round 2, aea969677c in round 1, 572e4f4fad and 234badf401 in round 0)", marker = "no tool result was ever archived on the wire: 28 requests, 14 tool rows", reps = "3/3 canonical runner + 3/3 probe", receipt = "F04/r20261001-04" }
green = { reps = "3/3 canonical runner per arm: test A on the carrier; A+B on carrier + gate v4, and also on carrier + v2 and carrier + v1", note = "the test file passes with v1, v2 and v4 alike, so it does not pin what v2 and v3/v4 add (the anthropic_content_blocks and bedrock_content_blocks reads, the third-party skip); those are pinned only by harnesses outside the repo: PREDICATE/r20261001-03, F04-bedrock/r20261001-03, F04-thirdparty/r20261001-02. It also runs inside one agent, so it does not cover the restart case (RESTART/r20261001-01)", receipt = "F04/r20261001-04" }
negative_control = { mutation = "per-hunk revert of every non-test hunk (17 carrier + 2 gate v4); named: S1 trigger=1, S2 stickiness dropped, fold-in reverted; the gate's third-party skip removed (= the v2 arm)", result = "10 of 19 hunks re-RED one at a time: 4 by assertion, 2 by assertion via an exception the carrier's fail-open guard swallows (tools/tool_result_storage.py ImportError; gate hunk 1 NameError), 4 by a crash reaching the test; 9 unpinned and listed. S1 RED 3/3, S2 RED 3/3, fold-in reverted (gate hunk 2): B RED plus 214 invalidated Converse replays; the third-party skip removed (= v2): MiniMax probe 0 passes vs 3, test file GREEN either way. The restart defect is not a sabotage result: no test asserts it (RESTART/r20261001-01)", receipt = "F04/r20261001-04" }
adjacent = { identical = true, pre_existing = [], note = "4 touched-module test files: 75 of 75 pass on main 44a1ce9724; the same 4 plus the carrier's tests/agent/test_tool_result_projection.py: 130 of 130 pass on carrier + test and on carrier + test + v4. Of the 130, 55 come from the carrier: 53 in its new test file and 2 added to tests/tui_gateway/test_compression_config_hot_reload.py (14 on main, 16 on the carrier). No failures on either side" }
guards = { F14 = "NOT_RUN (the F14 standing set is not built; it lives on staging/factory-replay-gate)", replay_gates = "11 of 11 pass on main, carrier and carrier + v4 with projection forced on; measurements equal to main (all three from one checkout path; inert: no projectable rows) (one F14 member)", region_scoping = "ALL PASS x3 (one F14 member)", readtool_direct = "11 of 11 identical outputs x3 (one F14 member)" }
seam_coverage = "harness/seam_trace.py (sys.settrace line tracer; no coverage package in the venv): with gate v4 the wire test executes 296 of 388 executable lines of agent/tool_result_projection.py (every function but _estimate_region_tokens, the cache-capable path; in the gate it skips only the non-dict return, the Bedrock reasoningContent branch and the third-party early return) and every added executable line in agent/turn_request_assembly.py, agent/context_compressor.py and hermes_cli/config_defaults.py"
quantitative = []                  # OBSERVED-only headline slot is empty: no real-cache measurement exists yet
cache_read_ratio = { status = "MODELED_ONLY", before = 0.917, after = 0.802, after_cached_trigger = 0.872, note = "perfect prefix cache model on a synthetic 20-turn session (E37-synthetic/r20261001-04); OBSERVED needs the paid arm" }
route_scope = "local request assembly (all routes). With gate v4 (= v3 code), a fresh pass is declined only on native Messages (anthropic.com or Nous Portal, per the URL the converter gets) and on Bedrock Converse, whenever any assistant row in the request holds a signed thinking block in any stored copy (reasoning_details, anthropic_content_blocks, bedrock_content_blocks). Projection therefore does not run on those sessions, including the rest of a session that once had signed Claude thinking there. It reads more than main replays (Messages sends only the latest turn's signed block; Converse only bedrock_content_blocks, or redacted reasoning_details without that sidecar), so it also declines in two cases with nothing bound on the wire (PREDICATE/r20261001-03: native, only an older row signed; Converse, rows carrying only Messages copies). Across a restart it does worse than decline: ProjectionState is in memory, so after a restart, resume or agent rebuild every archived row counts as fresh, the gate declines the re-projection, and on those routes rows archived earlier go out in full under a block signed over their stubs (RESTART/r20261001-01). Reaching that takes rows archived while nothing signed was in the history (route or provider switch, fallback round trip, thinking turned on later), then a restart. It does not decline on other Anthropic-compatible endpoints (MiniMax, Kimi, DeepSeek, the AnthropicBedrock SDK URL), on chat completions or on Codex"
not_tested = ["real provider prompt cache", "real Anthropic or Bedrock enforcement (server rule emulated; Converse binding assumed)", "Vertex Claude", "Claude over chat completions (OpenRouter, Nous Portal's chat wire): Hermes replays signed reasoning_details there (_route_replays_reasoning_details), the gate does not look at that wire, and whether the binding is checked through it is unknown", "Nous Portal on the wire (covered by direct call only)", "remote terminal backends (docker/ssh/modal)", "CLI and TUI subprocess surfaces (test_prefix_stability / test_transcript_ledger spawn the hermes CLI; denylisted without OD-2)", "preserved-thinking replay on every assistant turn on the native route (#129620 family not applied)", "drop_block (#106426) applied", "the gate across a restart is shown by harness only (RESTART/r20261001-01), not by the test file; the real /model, fallback-provider and gateway-rebuild code paths into it were not run (the direct call switches the route in place, the end-to-end run turns thinking on and resumes from SessionDB); Bedrock Converse across a restart not run", "the F14 standing regression set (three members ran: replay_gates, region_scoping, readtool direct)"]
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-tool-result-projection-support", commit = "" }

[gates]
P1 = "PASS"      # RED 3/3 on 44a1ce9724 (and e8c97320ac, aea969677c, 572e4f4fad, 234badf401 earlier); carrier gap (test B) reproduced 3/3
P2 = "PASS"      # external owner -> support route; no competing PR (author quiet since 2026-09-11; salvage is OD-S)
P3 = "PASS"      # one test file +295; gate v4 +54 in the carrier module (v3's +50 code, longer docstring); no env vars; config.yaml only
P4 = "PASS"      # real AIAgent/read_file/request assembly/Anthropic converter/SessionDB (TLS-intercepted api.anthropic.com, api.minimax.io); only the vendor HTTP boundary faked; seam execution shown by a line trace and by sabotage flips
P5 = "PENDING"   # RED 3/3, GREEN 3/3, per-hunk sabotage with unpinned hunks listed, adjacent identical, flaky = false all hold on 44a1ce9724; F14 guards NOT run (only three members, equal), so not PASS. Rounds 0-2 said PASS (overstated). The test file also does not pin v2/v3/v4's additions or the restart case (harness-only, stated)
P6 = "FAIL"      # no OBSERVED cache-read ratio; MODELED only -> class ceiling LIMITED
P7 = "PASS"      # one commit (parent 44a1ce9724), author Kevin Rajan, merge-tree clean on 44a1ce9724 (the commit's own tree), workflow push triggers matching staged/* and staging/* = 0
P8 = "PENDING"   # receipts hashed and carry z0evals_study, not frozen to z0evals
P9 = "PENDING"   # body.md redrafted in round 3; tone gate self-checked only; jargon/privacy scan by a second reader pending
P10 = "PENDING"  # v1 read by the phase-3 verifier, v2 + gate v2 by the round-1 re-verifier, v2 + gate v3 by the round-2 re-verifier (none accepted); v3 3b47753d54, gate v4 and the round-3 receipts need a fresh blind read
P11 = "RECORDED" # demand 55; test-only content rides the carrier, never alone
P12 = "PENDING"  # not on a board: see [queue]

[verification]
verifier = ""
provenance = "independent"
exact_head = "3b47753d54be51a06a7f9a939f9edea579f3c949"
exact_gate = "patches/foldin-preserved-thinking-gate-v4.diff sha256 0d2b808bd2a9d581e23411fcfbffa429109706360218425c96e0917e2013712c"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""
previous = ["phase-3 verifier on v1 d5854fdd7b: accept = false (6 findings, addressed in round 1)", "round-1 re-verifier on v2 8c783ff4ac + gate v2: 7 findings, addressed in round 2", "round-2 re-verifier on v2 8c783ff4ac + gate v3: 5 findings (gate undoes archived rows after a restart; AI disclosure too narrow; internal HTML comment in body.md; S2 and guard wording; commit-message attribution), addressed in round 3; see History"]

[merge_check]
main_sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
checked_at = "2026-10-01"
clean = true
tree = "70a3bd18653dc5f97ec86cd01a75c96e7a7d5576"
previous_main_check = "round 2: v2 8c783ff4ac merged cleanly onto e8c97320ac (tree 7016f82dc2); v2 also merges cleanly onto 44a1ce9724 (tree 70a3bd1865, the same tree as v3)"
carrier_check = "refs/pr/107731 against 44a1ce9724: one add/add conflict (tests/tui_gateway/test_compression_config_hot_reload.py); merge-base 67764dc086 is 13,523 commits behind 44a1ce9724"
recheck = "git merge-tree --write-tree main staging/tool-result-projection-support"
post_measurement_recheck = "after the round-3 runs, local main moved to aaa863f7ff (4 commits past 44a1ce9724): the staging commit still merges cleanly (tree 9fe378107e), the carrier still conflicts only in the hot-reload test file, and none of the 4 commits touch the carrier's 13 files, the test file, its helpers and fakes, or the cited converter files. Nothing was re-run there; the declared main stays 44a1ce9724"

[push]
no_follow_tags = true
workflow_push_matches = 0
fork_ref = "refs/heads/staged/tool-result-projection-support"
archive_refs_pushed = false
pushed_at = ""

[body]
path = "body.md"
kind = "support-note"
tone_gate = { peer = true, no_labor = true, no_internal_leak = true, smallest_ask = true, self_service = true, local_voice = true, easy_decline = true }
jargon_lint = "PENDING"
privacy_scan = "PENDING"
draft_note = "body.md is the comment text only. It is not posted; the owner decides whether and when to post it (Origin action below). Round 3 removed the internal HTML comment that headed the file"

[queue]
board = "none yet: the salvage board kvnloo/hermes-agent#402 is closed and its wave went upstream as NousResearch/hermes-agent#130139, which does not list this item (nor does NousResearch/hermes-agent#130140, from kvnloo/hermes-agent#403); kvnloo/hermes-agent#404 is the staged-PR queue for own-leaf branches (39 rows) and does not list it either, and none of the tracking issues kvnloo/hermes-agent#407-#411 is for it (re-checked read-only 2026-10-01). This item's only origin action is one comment on NousResearch/hermes-agent#107731; the owner decides whether it also gets a row"
position = "after existing rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
open_decisions = ["OD-3 (paid E37-live and the small real-API check)", "OD-7 (private lineage arm)", "OD-S: whether to move from a support comment to a salvage PR (carrier commits rebased with lorencato23's authorship kept, plus the test and a gate) if the author stays quiet after the comment; teknium1's note invites a salvage, and Teknium's bar (an OBSERVED cache-read ratio) applies to either form. A salvage PR could not ship gate v4 as is: it needs persisted stickiness first, or a different route for Claude (#526 or #106426)"]
+++

# Evidence and rebase support for NousResearch/hermes-agent#107731 (boundary-stable tool-result projection)

**Promotion form:** salvage-support (unchanged). This is evidence for lorencato23's open PR NousResearch/hermes-agent#107731, plus an optional fold-in for it. It is never our own PR. Whether to escalate to a salvage PR is an open owner decision (OD-S, see Route).
**Status:** STAGED, with LIMITED as the best class reachable at $0. The headline number (an OBSERVED cache-read ratio) needs the paid arm (OD-3). P5 is PENDING because the F14 standing set has not run (rounds 0-2 marked it PASS, which overstated it). The carrier fails the preserved-thinking gate unless a fold-in gate is applied, and the fold-in gate (v4, same code as v3) fails across a restart: it sends archived rows back in full.
**Branch:** local `staging/tool-result-projection-support` @ `3b47753d54` (v3) in the scratch mirror. On the fork it is pushed as `staged/tool-result-projection-support`: the fork's legacy `staging` branch makes `staging/<id>` impossible, and that rename resolves OD-0 for this item. Versions 1, 2 and 3 stay reachable under `refs/archive/staging/` (see Member branches and `naming_exception`).
**Declared main:** `44a1ce9724`. Every count, SHA and test result below was re-measured on it in round 3.

## Invariant

An opt-in, wire-only projection of stale tool results must meet three conditions:
- it breaks the request prefix only at a batch boundary paid for by `tool_result_projection_min_tokens` of newly archived output;
- it never undoes or re-stubs an archived row, including across a resume;
- it never rewrites a prefix that a replayed signed thinking block is bound to.

Real call path exercised:
- **Test A (OpenAI-compatible route):** `InProcessSession` → `AIAgent.run_conversation` → `assemble_api_request` → `project_stale_tool_results` (carrier) → the recording `FakeLLMServer` over loopback HTTP. The `read_file` tool runs for real and `SessionDB` is on disk.
- **Test B (native Anthropic route, no `base_url`):** the same path through the real Anthropic converter. `api.anthropic.com` is TLS-intercepted to `AnthropicMessagesServer`, with a responder that signs each thinking block over its documented prefix and audits every replay.
- **Bedrock probe (harness only, not in the test file):** the same scenario with `provider: bedrock`, `anthropic.claude-opus-5-5`, real boto3 against the repo's `FakeBedrock` (SigV4 re-verified), signing each `reasoningText` over its prefix.
- **Third-party probe (harness only):** the same scenario with `provider: minimax` at its production base URL `https://api.minimax.io/anthropic`, TLS-intercepted to `AnthropicMessagesServer` with the same signing responder.
- **Restart probe (harness only, new in round 3):** test B's route with a real `SessionDB`. Six turns run with reasoning off. Then a new agent with reasoning on takes over the same history (what `/reasoning` does through `_retire_agent`) and runs four turns with signed thinking. The last two turns come either from a third agent whose history is loaded with `SessionDB.get_resume_conversations` (restart) or from the same agent (continue). A direct-call companion (`harness/restart_direct.py`) runs the arm's real `project_stale_tool_results` through a chat-completions → native-Messages switch in place and then a new agent, and compares the prefix bound to the latest signed block with the real converter.

## RFC / issue links

All states re-checked read-only on 2026-10-01 (~11:15 -05:00).
- Carrier: NousResearch/hermes-agent#107731. Author lorencato23, head `069adfb67e`, OPEN, last update 2026-09-23 (teknium1's comment); last author activity 2026-09-11.
- Demand: NousResearch/hermes-agent#39691 (headroom tool-output compression, open, r=17) and NousResearch/hermes-agent#47866 (merged evaluation report, r=27).
- Preserved-thinking replay carriers that change what is replayed: NousResearch/hermes-agent#129620, NousResearch/hermes-agent#129492, NousResearch/hermes-agent#129882 (all open).
- Maintainer `drop_block` opt-in for Claude 5.1+: NousResearch/hermes-agent#106426 (teknium1, open).
- Ordered-carrier signature recovery: NousResearch/hermes-agent#70107 (open).
- Server-side alternative: NousResearch/hermes-agent#526 (Anthropic context editing, open issue).
- Fork RFC: kvnloo/hermes-agent#310 (open).

## Member branches

All counts and SHAs below are measured against the declared main `44a1ce9724`.

| ref | sha | role | rebase status |
|---|---|---|---|
| `refs/pr/107731` | `069adfb67e57287ac8df996ef48e082fe8455e2c` | Carrier (lorencato23): 6 commits, +1936, 13 files | Not clean. Merge-base `67764dc086`, 13,523 commits behind `44a1ce9724` (`git rev-list --count 67764dc086..44a1ce9724`). `merge-tree` against `44a1ce9724` conflicts only in `tests/tui_gateway/test_compression_config_hot_reload.py`, an add/add at the end of the file. Keeping both sides resolves it (`patches/carrier-rebase-handport-hot-reload-test.diff`, resolved blob `b94e723f76`; in round 3 `git rerere` replayed that recorded resolution and produced the same blob). Local evidence arms: `5d4adb3280` (carrier on `44a1ce9724`, tree `a7b3340eca`) and `15dff75cc8` (plus the test, tree `b733be3f0d`), kept reachable in h.git as `refs/xf/arms/tool-result-projection-support/r04-carrier-merge` and `…/r04-carrier-plus-test` (outside `refs/heads`, never pushed). Earlier counts: 13,447 against `572e4f4fad`, 13,458 against `234badf401`, 13,494 against `aea969677c`, 13,500 against `e8c97320ac`. |
| `staging/tool-result-projection-support` (local; `staged/tool-result-projection-support` on the fork) | `3b47753d54be51a06a7f9a939f9edea579f3c949` | v3. Fold-in test commit: one file, `tests/e2e/core/history/test_tool_result_projection_wire.py`, +295 (blob `7347ad045b`, unchanged since v1). Round 3 changed only the commit message | One commit, parent `44a1ce9724` (tree `70a3bd1865`), so `merge-tree` onto `44a1ce9724` is trivially clean. The RED arm is the commit itself. Merges cleanly onto the rebased carrier (`15dff75cc8`). It needs the rebase: `tests/e2e/core/history/_helpers.py` and `tests/fakes/*` do not exist at the carrier's base. |
| `refs/archive/staging/tool-result-projection-support-v3` | `3b47753d54` | v3 (round 3), same commit as the branch | Kept so the version survives any later move of the branch name. Patch `patches/tool-result-projection-support.v3-3b47753d54.patch`. |
| `refs/archive/staging/tool-result-projection-support-v2` | `8c783ff4ac` | v2 (rounds 1-2), superseded; same test blob, parent `aea969677c` | Kept, not re-measured as a commit (its tree on `44a1ce9724` equals v3's). Patch `patches/tool-result-projection-support.v2-8c783ff4ac.patch`. |
| `refs/archive/staging/tool-result-projection-support-v1` | `d5854fdd7b` | v1 (round 0, the phase-3 verdict head), superseded; same test blob | Kept, not re-measured. Patch `patches/tool-result-projection-support.v1-d5854fdd7b.patch`. |
| `patches/foldin-preserved-thinking-gate-v4.diff` | sha256 `0d2b808b…712c` | Fold-in gate v4: `_is_signed_thinking()` + `replays_bound_thinking()` (with the third-party skip) plus a fresh-pass decline, +54 lines in the carrier's `agent/tool_result_projection.py` (resulting blob `a3227c92a7`). Code identical to v3; the docstring now states the restart limit | Applies to blob `a76fb42f76`, identical at the PR head and on the rebased arms. Replaces v3 (`patches/foldin-preserved-thinking-gate-v3.diff`, +50), v2 (+40) and v1 (+27), all kept for the record. |

## Route and carrier choice

The route is support-note, with an optional fold-in. lorencato23 owns the open PR. Their last commit and last comment there are both from 2026-09-11, after three review rounds and live A/Bs. Neither kshitijk4poor's read-only review (2026-09-22) nor teknium1's harness-scout note (2026-09-23) has an answer from them yet; the account is active elsewhere on GitHub. teknium1's note calls itself "design evidence, not a review verdict" and is addressed "for whoever salvages this". It asks to keep the wire-only projection, move the trigger to a fixed boundary, and measure the cache-read ratio before and after in the PR body. kshitijk4poor's review asks, among other things, whether in-memory stickiness (emptied by a restart, a resume or a gateway rebuild) is acceptable.

A support comment is still within policy and is the smallest ask: the PR is open, nobody has opened a salvage PR, and the evidence answers the boundary question and kshitijk4poor's stickiness question on the author's own branch. It also exposes a gap nobody had raised: on Claude routes that replay signed thinking, every projection pass is a history edit. The gate offered for that gap has its own restart defect, which the comment states. So the gate is offered as a sketch with a known limit, not as a ready fold-in: on Claude routes it needs stickiness that survives a restart. A salvage PR (the carrier's commits rebased with lorencato23's authorship kept, plus the test and a gate) is the next form if the author stays quiet after the comment. That is OD-S, the owner's call. It does not change what is missing: Teknium's bar, an OBSERVED cache-read ratio, applies to either form. The single origin action for now is one comment on NousResearch/hermes-agent#107731 (`body.md`).

## What the gate does, and what it costs

Gate v4 (the same code as v3) declines a *fresh* pass when the request holds a signed thinking block on a route that checks it: `anthropic_messages` against anthropic.com or Nous Portal, and `bedrock_converse`. On `anthropic_messages` it first reads `agent._anthropic_base_url`, the same URL `_build_anthropic_kwargs` hands the converter. If that URL is any other Anthropic-compatible endpoint, it returns False: `_manage_thinking_signatures` strips signed thinking for those endpoints (`anthropic_message_convert.py:577`, `:593`), and Kimi, which gets the blocks as-is, checks no Claude signature. Rows the same agent already archived keep replaying.

What it reads, plainly: every assistant row, and on each row all three stored copies (`reasoning_details`, `anthropic_content_blocks`, `bedrock_content_blocks`), on both wires. That is a superset of what main replays. Messages keeps only the latest assistant turn's signed block, and Converse replays `bedrock_content_blocks` (or, without that sidecar, only redacted `reasoning_details`). The direct call against the real converters (PREDICATE/r20261001-03) shows the consequences: the v3/v4 predicate is exact on 8 of 10 in-scope cases and over-declines on 2, where nothing bound is on the wire: (1) a native session whose latest assistant turn has no signed thinking but an earlier turn does; (2) a Converse session whose rows carry only Messages copies (it started on native Messages). It misses none. The wider read is deliberate: if every-turn replay on the native route lands (#129620 family), a latest-turn-only gate would turn case (1) into a miss.

**Across a restart, the gate undoes archived rows (round-2 re-verifier finding; reproduced in RESTART/r20261001-01).** `ProjectionState` lives in memory on `agent._tool_result_projection_state`. After a process restart, a session resume or a gateway agent rebuild, every row archived earlier counts as fresh again. If the history then holds a signed thinking block on native Messages or Converse (a resumed `SessionDB` history keeps `reasoning_details`, which carries the signature), the gate declines that re-projection and the archived rows go out in full, under a block that was signed over their stubs. v3's docstring ("Sticky rows are already part of the bound prefix") and the round-2 body ("Rows that are already stubbed keep replaying") held only within one agent; v4's docstring and the round-3 body say so. Reaching it takes rows archived while nothing signed was in the history, then signed thinking, then a restart: a `/model` or provider switch to native Claude or Converse, a fallback-provider round trip, or thinking turned on after projection ran, followed by a restart, resume or rebuild (editing any of the four keys rebuilds the gateway agent). Measured on `44a1ce9724`, 3 reps each, all reps equal:
- **End to end (thinking turned on, then a `SessionDB` resume):** with gate v4, 4 of 4 archived rows went out in full on the first request after the resume, and that request replayed 1 thinking block over a rewritten prefix. With no resume (the same agent continues), no row went back and 0 blocks were invalidated. The plain carrier, on the same first request after the resume, re-stubbed its 7 archived rows byte-identically but also archived 1 more row, which invalidated the same block (it had invalidated 1 more in phase B, its known gap). Main: 0 rows archived, 0 invalidated. The resumed history held signed `reasoning_details` on 8 assistant rows.
- **Direct call (route switch in place, then a new agent):** 9 rows archived on chat completions; the same agent, switched to native Messages, still sent the 9 stubs after a signed turn. A new agent with the gate projected 0 rows and sent all 9 in full, and the prefix bound to the latest signed block changed. The carrier's new agent re-stubbed the same 9 byte-identically, and the bound prefix was unchanged.

No narrower predicate fixes this without more state: after a restart nothing tells which rows the latest block saw as stubs. Letting the first pass after a restart through would instead invalidate sessions that had signed thinking from the start and were never projected. So on Claude routes the gate needs persisted stickiness first (kshitijk4poor's question 2). The test file does not cover the restart case.

How v4 differs from the earlier gates:
- v1 returned False unless `api_mode == "anthropic_messages"` and read only `reasoning_details`. It missed Bedrock Converse (F04-bedrock: the plain carrier and v1 both invalidate 214 block replays over 17 of 24 requests; v2 and v4: 0) and a row whose only signed copy is `anthropic_content_blocks` (PREDICATE: a MISS for v1). That second case is mechanism evidence only; no end-to-end run reaches a fresh pass in that state.
- v2 read the endpoint nowhere. On a third-party Anthropic-compatible endpoint it declined every pass although the converter sends no thinking: on the MiniMax-shaped run (F04-thirdparty), v1 and v2 make 0 passes, while the plain carrier and v4 make 3 passes at requests `[9, 15, 21]` with 0 thinking blocks on the wire. In the direct call v2 over-declines on 5 of 10 in-scope cases (MiniMax, Kimi, the AnthropicBedrock SDK URL, plus the two v3/v4 still has).
- v3 added the endpoint check. v4 changes only v3's docstring (the restart limit); no code line differs, so every v3 result carries over and round 3 re-ran the arms with v4.

The cost: **with gate v4, projection does not run on native Claude (anthropic.com, Nous Portal) or Bedrock Converse sessions whose history holds a signed thinking block,** including the rest of a session that once had signed Claude thinking on those routes, **and without persisted stickiness a restart sends rows archived earlier back in full on those routes.** On the native route, carrier + gate sends exactly the bytes main sends (sum of request chars 3,539,687 on both, 3/3), so zero passes ran. On Bedrock Converse, zero passes ran too. The predicate goes by route and history, not by model, so it also switches projection off for older Claude models that do not bind thinking to the prefix. It does not switch projection off on other Anthropic-compatible endpoints, on chat completions or on Codex. body.md states this plainly and names the alternatives: NousResearch/hermes-agent#526 (server-side context editing, which the binding rule does not count as an edit) or NousResearch/hermes-agent#106426 (`drop_block`, which loses the reasoning instead of failing).

What the in-repo test pins, plainly: test B passes with v1, v2 and v4 alike (3/3 each on `44a1ce9724`). The test file therefore pins only "some gate exists on native Messages, within one agent". The `anthropic_content_blocks` and `bedrock_content_blocks` reads, the third-party skip and the restart behaviour are shown only by harnesses outside the repo: PREDICATE/r20261001-03 (direct call), F04-bedrock/r20261001-03 and F04-thirdparty/r20261001-02 (wire probes), RESTART/r20261001-01 (restart probe and direct call).

## First-slice status

The slice is **committed** at `3b47753d54` (v3; v1 `d5854fdd7b` and v2 `8c783ff4ac` are kept under `refs/archive/`). It is one commit, a test-only fold-in, authored by Kevin Rajan, with parent `44a1ce9724`. Round 3 changed the commit message only: the round-2 message credited "the review there" with asking for a stable boundary; the fixed-boundary ask is teknium1's harness-scout note (not a review verdict), and the stickiness question is kshitijk4poor's read-only review. The test blob is unchanged.
- On main (`44a1ce9724` + the commit), test A is RED by design: the feature is absent, and the assertion reads "no tool result was ever archived on the wire: 28 requests, 14 tool rows". Test B is GREEN on main.
- On the rebased carrier, A is GREEN and B is RED: 3 thinking blocks were replayed over a rewritten prefix.
- On the carrier plus gate v4, A and B are both GREEN (as with v2 and v1).

The branch exists to carry the fold-in. It is not meant to merge to main alone (D5).

## Evidence

n counts independent runs. Every probe arm was run 3 times this round, on `44a1ce9724`, and all reps agreed exactly.

| experiment | receipt | verdict | label | n | numbers |
|---|---|---|---|---|---|
| F04 wire contract, RED / GREEN / NEG / ADJ | `receipts/F04-r20261001-04.json` | KEEP (support) | OBSERVED (loopback wire) | 3 canonical-runner reps per proof arm (base, carrier, carrier + v1, + v2, + v4); 3 probe reps per arm (7 arms); 1 seam trace; 1 run per sabotaged hunk | **Main:** 0 rows archived; A RED 3/3. **Carrier:** 6 passes in 28 requests at `[7,11,15,19,23,27]`, 2 rows per pass at about 11.7K estimator tokens (11,692 here, as in round 2; the count is per-environment because the stub embeds sandbox paths: round 1 11,694, round 0 11,696, phase-3 verifier 11,800–11,802), 0 unexplained breaks, 0 unstable rows, resume byte-identical; A GREEN 3/3. **S1** (trigger = 1): 12 passes, each archiving one row of about 5.8K tokens (5,846 here); A RED 3/3. **S2** (no stickiness): 11 passes, the first archiving 2 rows (11,692 tokens), each of the other 10 one row (5,846); A RED 3/3. **Native Anthropic:** 23 replayed thinking blocks, 3 invalidated on the carrier, 0 with v1, v2 or v4. **Per-hunk sabotage:** each of the 19 non-test hunks (17 carrier, 2 gate) reverted alone; 10 re-RED. By assertion (4): `agent_init.py` `_build_context_engine` hunk, the second `context_compressor.py` hunk, `turn_request_assembly.py` (test A) and gate hunk 2 (test B; its Bedrock probe shows 214 invalidated replays). By assertion via a swallowed exception (2): `tools/tool_result_storage.py` (ImportError `spillover_path_is_readable`) and gate hunk 1 (NameError `replays_bound_thinking`); the carrier's fail-open guard catches the error and sends the request unprojected, so test A fails by assertion. By crash reaching the test (4): two `agent_init.py` hunks, the first `context_compressor.py` hunk and the new module. 9 hunks are unpinned (listed under the gate checklist). |
| Preserved thinking, enforced-account emulation | `receipts/F04-enforced-r20261001-04.json` | KEEP (risk) | MODELED server rule; OBSERVED Hermes behaviour | 3 reps per arm (5 arms) | **Carrier:** 16 × 400 in 12 turns (3/3): the recovery strips `reasoning_details` while `anthropic_content_blocks` still carries the block. **Carrier + v1, v2 or v4:** 0 × 400 (within one agent). **Main:** 0. |
| Preserved thinking on Bedrock Converse | `receipts/F04-bedrock-r20261001-03.json` | KEEP (gap) | OBSERVED wire; binding rule MODELED and assumed for Converse | 3 reps per arm (5 arms) | Converse replays every earlier assistant turn's signed reasoning (276 replays in 24 requests on every arm). **Carrier:** 5 passes, 214 invalidated replays over 17 of 24 requests. **Carrier + v1:** identical (214 / 17). **Carrier + v2 or v4:** 0 passes, 0 invalidated. **Main:** 0. |
| Third-party Messages endpoint (MiniMax) | `receipts/F04-thirdparty-r20261001-02.json` | KEEP (v3/v4 fix) | OBSERVED (loopback wire) | 3 reps per arm (5 arms) | `provider: minimax` at `https://api.minimax.io/anthropic`, TLS-intercepted. All 24 stored assistant rows carry signed copies; 0 thinking blocks reach the wire on every arm. **Carrier and carrier + v4:** 3 passes at requests `[9, 15, 21]`, 9 rows, 0 unstable. **Carrier + v1 or v2:** 0 passes (request bytes equal to main's, 3,536,108). |
| Gate across a restart (new) | `receipts/RESTART-r20261001-01.json` | KEEP (gate defect) | OBSERVED (end-to-end loopback wire; direct call = mechanism) | 3 reps per arm and mode (3 arms × restart/continue); direct call 3 reps per arm (2 arms) | **End to end** (6 turns reasoning off, then 4 with signed thinking, then 2 more after a `SessionDB` resume): **carrier + v4** 4 of 4 archived rows sent in full on the first request after the resume, 1 block invalidated there; without the resume 0 rows back, 0 invalidated. **Carrier:** on that request 7 of 7 archived rows re-stubbed byte-identically plus 1 newly archived row, 1 block invalidated (plus 1 in phase B, its known gap). **Main:** 0. The resumed history held signed `reasoning_details` on 8 assistant rows. **Direct call** (route switch in place, then a new agent): v4 9 of 9 archived rows back in full, bound prefix changed; carrier 9 of 9 re-stubbed identically, bound prefix unchanged. |
| Gate predicate vs the real converters | `receipts/PREDICATE-r20261001-03.json` | RECORDED | OBSERVED (mechanism, not wire) | 12 cases, 1 run | Rows built by the real normalizers; for each case the harness also runs the real converter for that route. In scope (10 cases): **v3 = v4 code** exact 8, over-declines 2, misses 0; **v2** exact 5, over-declines 5, misses 0; **v1** exact 4, over-declines 4, misses 2. Out of scope (2): on chat completions to OpenRouter, Hermes does send signed `reasoning_details`; no gate looks at that wire and whether the binding is checked there is unknown. One request and one agent per case: the harness does not model a restart. |
| E37 synthetic (substitute for the private E37 offline arm) | `receipts/E37-synthetic-r20261001-04.json` | RECORDED | Wire OBSERVED; economics MODELED | 20 turns, 1 run per arm (deterministic) | See the table after this one. |
| Three F14 members (not the F14 set) | `receipts/GUARDS-r20261001-04.json` | RECORDED | OBSERVED | 1 run per arm (3 arms) | `replay_gates`: 11 of 11 pass on main, carrier and carrier + v4 with projection forced on; measurements equal to main's (all three arms ran from the same checkout path; inert: no projectable rows). Region-scoping ALL PASS ×3. `readtool` direct calls: identical ×3. The rest of F14 was not run. |
| Carrier rebase | `receipts/CARRIER-rebase-r20261001-04.json` | RECORDED | OBSERVED | 1 | One add/add conflict, resolved (same blob `b94e723f76`); 13,523 behind `44a1ce9724`. Author activity on the PR: last 2026-09-11. |
| Source verification | `receipts/SRC-preserved-thinking-r20261001-04.json` | CONFIRMED (Messages); assumed (Converse) | static | n/a | claude-api reference, Breaking change 3, which states the check for the Messages API on every platform and lists Bedrock Converse as out of its scope. Code facts at `44a1ce9724` (byte-identical to `e8c97320ac` in every cited file): `anthropic_message_convert.py:393`, `:567`, `:577`, `:593`; `anthropic_endpoints.py:28`, `:107`; `chat_completion_helpers.py:1420`, `:1731`; `turn_recovery.py:495-500`; `bedrock_adapter.py:435`, `:709-748`, `:861`; `transports/chat_completions.py:259`. New for the restart case: `hermes_state.py` `_CONVERSATION_ROW_COLUMNS` (SessionDB resumes `reasoning_details`, not `anthropic_content_blocks`); `cli_commands_mixin.py:2603-2604` (`/reasoning` retires the agent). |

E37 synthetic results by arm (on `44a1ce9724`):

| arm | prefix breaks | compaction | sum of request chars | modeled cache-read ratio | modeled billed input (cached pricing) |
|---|---|---|---|---|---|
| prune off (default) | 1 | yes (at request 27) | 6,337,345 | 0.917 | 309,711 |
| prune on (48000) | 2 | no | 6,707,342 (+5.8%) | 0.896 | 368,596 (+19.0%) |
| projection (auto, uncached trigger) | 6 | no | 3,338,725 (-47.3%) | 0.802 | 273,491 (-11.7%) |
| projection (provider-cached trigger) | 3 | no | 4,613,013 (-27.2%) | 0.872 | 284,629 (-8.1%) |

A/A checks: with projection off, the carrier's per-request wire sizes are identical to main's (prune-off and prune-on). With projection on, gate v4 changes nothing on this OpenAI-compatible route (identical per-request sizes, both trigger modes). Round 2's figures on `e8c97320ac` are the same (309,711 baseline, -47.3%, -27.2%).

## Experiments run

These are the $0 tiers only. Probes ran under `env -i` with a fresh `HOME`/`HERMES_HOME` and a loopback-only `socket.connect`/`getaddrinfo` guard. Tests ran through `scripts/run_tests.sh -j 2` with an isolated `HOME`/`HERMES_HOME`. Blocked egress: 2× `getaddrinfo('openrouter.ai')` inside `evals/compaction/test_region_scoping.py` on every arm (the script still passed), and 2× `getaddrinfo('bedrock-runtime.us-east-1.amazonaws.com')` per Bedrock probe run on every arm, main included, before the endpoint override applies (all 24 requests reached the fake). No other guarded run attempted egress, the restart probe included. The two direct-call harnesses (`predicate_wire_truth.py`, `restart_direct.py`) make no network calls and run without the socket guard. The shared venv's `nemo-relay 0.8.4` fails to initialize under main's Relay host ("Hermes Relay plugin initialization failed", visible in the logs of failing test runs), so no Relay plugin was active in any run; every receipt records this as `env.relay`.

- **F04** (T1): `harness/f04_probe.py` ×3 per arm, plus `scripts/run_tests.sh` ×3 per proof arm, `harness/seam_trace.py`, `harness/per_hunk_sabotage_r2.py`.
- **F04-enforced** (T1): `harness/f04_probe.py … enforce` ×3 per arm.
- **F04-bedrock** (T1): `harness/f04_bedrock_probe.py` ×3 per arm.
- **F04-thirdparty** (T1): `harness/f04_thirdparty_probe.py` ×3 per arm.
- **RESTART** (T1 and T0, new): `harness/f04_restart_probe.py` ×3 per arm and mode (base, carrier, carrier + v4; restart and continue), `harness/restart_direct.py` ×3 per arm (carrier, carrier + v4).
- **PREDICATE** (T0): `harness/predicate_wire_truth.py` (unchanged; it names the v3 predicate, which is v4's code).
- **E37-synthetic** (T1): `harness/e37_synthetic.py`.
- **Guards** (T1/T0): `harness/guarded_run.py` around `evals/token_accounting/replay_gates.py`, `evals/compaction/test_region_scoping.py` and `harness/readtool_direct.py`. These are three members of the F14 standing set, not the set.
- **Carrier rebase** and **source verification** (T0).

Raw outputs are in `receipts/raw/r04/` (round 3), `receipts/raw/r03/` (round 2), `receipts/raw/r02/` (round 1) and `receipts/raw/` (round 0), scrubbed of absolute local paths and sha256-pinned inside each receipt.

## Experiments queued (not run)

1. **E37-live, T3 paid** (OD-3, owner launches with injected credentials; about $50 per arm on Fable 5.1, cheaper on DeepSeek). This is Teknium's bar. Use a caching route where projection is active: with the gate, native Claude and Bedrock Converse sessions with signed thinking are gated off. Make three `HERMES_HOME` copies that differ only in `config.yaml` (no overlay / `compression: {proactive_prune_tokens: 48000}` / `compression: {tool_result_projection: auto}`), then:
   ```
   # base arms on main, projection arm on the rebased carrier + gate v4
   HERMES_HOME=$H_PRUNE_OFF  python -m evals.postmortem.live_ab.cache_concurrency_probe --repo <main checkout>    --provider openrouter --model deepseek/deepseek-v4.1-flash --workers 10 --calls 8 --out e37-live-prune-off.jsonl
   HERMES_HOME=$H_PRUNE_ON   python -m evals.postmortem.live_ab.cache_concurrency_probe --repo <main checkout>    --provider openrouter --model deepseek/deepseek-v4.1-flash --workers 10 --calls 8 --out e37-live-prune-on.jsonl
   HERMES_HOME=$H_PROJECTION python -m evals.postmortem.live_ab.cache_concurrency_probe --repo <carrier+gate v4> --provider openrouter --model deepseek/deepseek-v4.1-flash --workers 10 --calls 8 --out e37-live-projection.jsonl
   # repeat with --provider nous --wire chat (Fable 5.1) only if the owner approves the ~$50/arm budget
   ```
   Metric: per-call `cache_read / prompt`, plus the ideal/stuck/collapse pair classes, before vs after. These must be OBSERVED, and reported before any value claim. ABBA order, n=3 arms each.
2. **E37-offline on private data, T0 priv** (OD-7). The harness supports only synthetic sessions today: lineage replay mode is still to build in `harness/e37_synthetic.py`.
   ```
   python evals/compaction/scripts/reconstruct_lineage.py <COPY of state.db in the private store> <root_session_id> <private>/lineage.json
   # then replay lineage.json through the arms prune-off / prune-on 48000 / projection (MODELED billed-input delta, prefix-rewrite count)
   ```
3. **readtool model arm, T2 local GPU** (OD-1: needs a preset of at least 64K; the router presets are 8K; strictly serial, under the shared GPU flock):
   ```
   flock <gpu lock> python3 evals/readtool/runner.py --model <64K local model> --provider custom --reps 3 --label baseline
   flock <gpu lock> python3 evals/readtool/runner.py --model <64K local model> --provider custom --reps 3 --label projection-auto   # HERMES_HOME config: compression.tool_result_projection: auto
   python3 evals/readtool/report.py --labels baseline projection-auto
   ```
4. **Preserved-thinking real-API check, T3 paid, small** (OD-3): one enforced or opted-in account. Send `thinking.block_binding.prefix_mismatch_behavior: "drop_block"` with the `thinking-binding-controls-2026-08-01` header, run 6 turns on the carrier with and without gate v4, and log `input_transformations`. The expected `thinking_dropped` / `prefix_binding_mismatch` count equals the projection passes without the gate, and 0 with it within one agent. Add one restart (resume the session in a new process) after archived rows exist, one Bedrock Converse session (the `anthropic_beta` body field) to replace the Converse assumption with an observation, and one OpenRouter chat-completions session with Claude thinking to settle whether the binding is checked on that wire.
5. **F14 standing set** ($0, blocked on the `staging/factory-replay-gate` harness): run it on main and on carrier + gate v4 with projection forced on, and require equal verdict maps (P5).
6. **Persisted stickiness** (design, not ours): the restart probe is ready to re-run against any carrier revision that persists `ProjectionState` per session; with it, the gate arm should show 0 archived rows back in full after the resume.

## Acceptance gates

| gate | status | evidence |
|---|---|---|
| The carrier, rebased onto main, passes its own tests plus `replay_gates` and `test_region_scoping` | met | Own tests: 69 of 69 pass on `44a1ce9724` (per-file counts inside the 130-of-130 run: 53 in its new file + the hot-reload file's 16, 2 of them the carrier's), also with gate v4. `replay_gates`: 11 of 11 pass with projection on and off. Region-scoping: ALL PASS. Caveat: `replay_gates` and region-scoping transcripts have no rows projection could archive, so they never exercise it; "gate decisions after projection" is covered by E37-synthetic instead: with projection on, the compaction gate did not fire although the durable transcript held about 472K chars of tool output. |
| The byte-stability test is GREEN on the carrier and RED under sabotage (projection re-evaluated every turn) | met | GREEN 3/3. S1 RED 3/3 (12 one-row passes) and S2 RED 3/3 (11 passes: one of 2 rows, then 10 one-row passes). |
| Preserved-thinking routes: no invalidation, or projection disabled there (fixture-asserted) | not met on the carrier as-is; met with gate v4 within one agent on native Messages (test B, 3/3) and on Bedrock Converse (probe, 3/3; Converse binding assumed); NOT met with gate v4 across a restart (RESTART/r20261001-01) | Carrier: 3 invalidations (Messages), 214 over 17 requests (Converse), 16 × 400 under enforced emulation. Gate v4 within one agent: 0 everywhere, by turning projection off on those routes; it leaves projection on for third-party Messages endpoints (MiniMax probe: 3 passes, 0 thinking on the wire). Across a restart: archived rows go back to full bytes under a block signed over their stubs. Fixture-asserted only for native Messages within one agent: test B cannot tell v1, v2 and v4 apart; the rest is harness evidence. Not covered: Claude thinking over chat completions (OpenRouter, the Portal's chat wire). |
| An OBSERVED cache-read ratio before/after on a caching route, before any upstream claim | pending | MODELED only (0.917 → 0.802 or 0.872). Queued item 1 (T3, OD-3). |
| Evidence posted once on #107731 as one concrete comment; no competing PR | pending | `body.md` redrafted in round 3. Owner action only. |

## Gate checklist (P1-P12)

- **P1 PASS:** RED 3/3 on `44a1ce9724` (F04/r20261001-04); also RED on `e8c97320ac` (round 2), `aea969677c` (round 1), and `572e4f4fad` and `234badf401` (round 0).
- **P2 PASS:** external owner; support route. The author has been quiet on the PR since 2026-09-11 and teknium1's note invites a salvage; escalating is OD-S, not taken.
- **P3 PASS:** one test file; gate v4 is +54 lines (v3's code, a longer docstring).
- **P4 PASS:** real path; vendor boundary faked only. Seam execution is shown by a line trace: the wire test runs 296 of 388 executable lines in the projection module (with gate v4) and every function but `_estimate_region_tokens` (the cache-capable break-cost path, not reached on these routes). Within the gate it never runs the non-dict return, the Bedrock branch of `_is_signed_thinking` or the third-party early return; those are covered by the Bedrock and MiniMax probes and the direct call. This is a `sys.settrace` tracer because the venv has no `coverage` package.
- **P5 PENDING:** RED, GREEN 3/3, per-hunk sabotage over all 19 non-test hunks (carrier + gate v4) with the unpinned hunks listed below and the swallowed-exception flips labelled as such, adjacent identical, not flaky: all hold. The F14 standing guards have not run: only three of their members (`replay_gates`, region-scoping, readtool direct calls) ran, and those are equal. FACTORY P5 needs F14 guards equal, so this is not PASS. Rounds 0-2 marked P5 PASS on those three members, which overstated it. The test file also does not pin v2's or v3/v4's additions or the restart case; the harnesses show them (F04-bedrock, F04-thirdparty, PREDICATE, RESTART).
- **P6 FAIL:** MODELED only.
- **P7 PASS:** one commit (parent `44a1ce9724`); author correct; `merge-tree` clean on the declared main (the commit's own tree `70a3bd1865`); 0 workflow push triggers match `staged/*` or `staging/*`.
- **P8 PENDING:** every receipt carries `z0evals_study`; nothing is frozen yet.
- **P9 PENDING:** a second reader is needed for the jargon and privacy scan.
- **P10 PENDING:** v3 `3b47753d54`, gate v4 and the round-3 receipts need a fresh blind read.
- **P11 RECORDED.**
- **P12 PENDING:** see `[queue]`.

Unpinned hunks (reverting each alone leaves both tests GREEN; reported as surface the wire test does not pin, mostly config plumbing, docs and the benchmark script):

- `cli-config.yaml.example` `+830,40`: the example config block for the four keys (docs).
- `gateway/run.py` `+4410,10`: the four keys in the gateway's config-key list.
- `hermes_cli/config_defaults.py` `+621,30`: defaults for the four keys (the test sets every key explicitly).
- `scripts/bench_tool_result_projection.py` `+1,159`: the carrier's benchmark script (new file, not imported).
- `tui_gateway/session_compression.py` `+78,8`, `+121,10`, `+133,12`: hot-reload of the four keys (the carrier's own hot-reload tests target these; that pairing was not sabotage-checked here).
- `website/docs/user-guide/configuration.md` `+1013,10`, `+1060,16`: user docs.

Inside gate hunk 1, the third-party skip is not separately pinned by the test file. Its negative control is the v2 arm, which is v3/v4 without the skip: on the MiniMax probe v2 makes 0 passes and v4 makes 3. The gate's restart behaviour is a defect, not a pin: the restart probe shows it, and no test asserts it.

## NOT_TESTED

- **Real provider prompt caches:** `cache_read_input_tokens` was never observed. Every cache and billing figure is MODELED.
- **Real enforcement:** the server rule is emulated from the claude-api reference. `drop_block` (#106426) was not applied. Binding on Bedrock Converse is assumed (the reference covers the Messages API only).
- **Other routes:** Vertex Claude; Nous Portal's Messages route on the wire (direct call only); Claude thinking over chat completions (OpenRouter, the Portal's chat wire). Hermes replays signed `reasoning_details` on that wire, gate v4 does not look at it, and whether the binding is checked through it is unknown.
- **Restart paths:** the restart case is shown by the restart probe (thinking turned on, then a `SessionDB` resume) and by direct call (route switch in place, then a new agent). The real `/model`, fallback-provider and gateway-rebuild code paths into it, and Bedrock Converse across a restart, were not run. The test file does not cover a restart.
- **Real third-party endpoints:** the MiniMax run fakes the vendor boundary; Kimi and DeepSeek are covered by the direct call only.
- **Remote terminal backends:** docker, ssh and modal for the spillover recovery path. The tests use the local backend.
- **Subprocess surfaces:** the CLI and TUI subprocess surfaces, and `test_prefix_stability.py` / `test_transcript_ledger.py` (they spawn the hermes CLI; denylisted without OD-2).
- **F14:** the standing regression set beyond its three members above.
- **Not combined in one run:** compaction and projection together in the F04 scenario (no compaction fired in its 28 requests; E37-synthetic covers the gate side); preserved-thinking replay of every assistant turn on the native route (#129620 / #129492 / #129882 not applied; the Bedrock probe is the every-turn replay case on another wire).
- **Out of scope:** task-success parity of projection, model behaviour after archiving (needs a model), and the 24 h spillover prune un-stubbing a row (kshitijk4poor's defect).

## Origin action (owner only)

Post `body.md` once, as one comment on NousResearch/hermes-agent#107731. The file holds only the comment text; it carries no draft notes. Optionally offer the test file and the gate v4 diff as a fold-in on the author's branch, with a `Co-authored-by: Kevin Rajan <7121943+kvnloo@users.noreply.github.com>` trailer, but say with it that the gate needs persisted stickiness first (the comment does). Do not open a PR (a salvage PR is OD-S, decided separately). Ideally, wait for the E37-live number before claiming any value. The comment makes no value claim beyond clearly labelled modeled numbers. It states that the gate turns projection off for native Claude and Bedrock Converse sessions with signed thinking, and that across a restart it sends archived rows back in full on those routes. It discloses that the comment, harness, tests and gate diff were written with Claude Code.

## Next steps

1. A blind verifier reads `3b47753d54`, the gate v4 diff and the round-3 receipts (P10).
2. Run F14 once the factory-replay-gate harness exists (P5).
3. The owner decides OD-3 for E37-live (queued item 1) and the small real-API check (queued item 4), OD-7 if the private lineage arm is wanted, and OD-S if the author stays quiet after the comment.
4. Once #129620, #129492 or #129882 settles, rerun F04 on top of it. When every assistant turn replays thinking on the native route, test B should show more invalidations on the carrier and still 0 with the gate within one agent (v4 already reads every row).
5. Re-check freshness within 24 h of posting: `git merge-tree --write-tree main staging/tool-result-projection-support`, plus a re-merge of `refs/pr/107731` onto main.
6. Freeze the cited receipts to z0evals (P8) only when the comment is posted.

## History

- 2026-10-01 | CANDIDATE → LIMITED | builder (Claude Code, Opus 5.5) | slice committed (`c1ed8c9f08` on `572e4f4fad`, then rebased to `d5854fdd7b` on `234badf401`). F04, E37-synthetic and the guards were run at $0. Gate v1 written and proven on native Messages. T2 and T3 runs queued.
- 2026-10-01 | phase-3 verifier | accept = false, 6 findings: wrong interpreter in every receipt; 13,447 placed next to the `234badf401` run; "3 reps per arm" overstated n and the estimator figures were per-environment; gate and body claims broader than v1 (Bedrock Converse, `anthropic_content_blocks`); body did not say the gate turns projection off for native Claude with thinking; P4/P5 marked PASS without coverage or per-hunk sabotage, and receipts missing xf.receipt.v1 fields.
- 2026-10-01 | LIMITED (round-1 fix) | Claude Code, Opus 5.5 | all six addressed. Commit cherry-picked to `8c783ff4ac` on `aea969677c` (test blob unchanged; local branch force-moved, which broke the FACTORY §10 version rule; repaired in round 2). Gate widened to v2 and proven on Messages (test B), Bedrock Converse (new probe) and by direct call. Every probe arm re-run ×3. Seam line trace and per-hunk sabotage added. Receipts re-issued as r20261001-02 with the required fields. The r01 receipts corrected in place (interpreter 3.11.14, n wording, the 13,447 base, absolute paths scrubbed from receipts and raw outputs with before/after hashes) and marked superseded. body.md rewritten: scoped claims, the Bedrock finding, and a plain statement of the gate's cost. Branch named `staged/tool-result-projection-support` for the fork (OD-0 resolved by the rename). Promotion form unchanged (salvage-support).
- 2026-10-01 | round-1 re-verifier | 7 findings: (1) gate v2 ignored the endpoint, so it declined on third-party Messages endpoints whose converter sends no thinking, and it read rows main does not replay, which body.md and route_scope understated; (2) body.md test count wrong (55 of the 130 tests are the PR's, not 53); (3) body.md called `aea969677c` current main (it was `e8c97320ac`); (4) ownership record called lorencato23 "the active owner" and left out teknium1's salvage invitation; (5) the force-move left v1 `d5854fdd7b` with no ref (FACTORY §10); (6) proof described too strongly: the test file passes with v1 too, gate hunk 1's flip is a swallowed NameError, PREDICATE counted chat_completions as correct; (7) GUARDS r02 had no verdict, no receipt carried `z0evals_study` or `env.relay`.
- 2026-10-01 | LIMITED (round-2 fix) | Claude Code, Opus 5.5 | all seven addressed. (1) Gate v3 (+50): skips Messages endpoints other than anthropic.com and Nous Portal, read from the same `_anthropic_base_url` the converter gets; new MiniMax wire probe (v2 0 passes, v3 3 passes, 0 thinking on the wire) and a direct-call harness that compares each gate with the real converters (v3: 8 exact, 2 over-declines, 0 misses); the remaining over-reach (every row, every copy) is kept on purpose and stated in body.md, route_scope and the gate section. (2) body.md: 130/130, 55 of them the PR's (53 + 2). (3) Everything re-measured on `e8c97320ac` (13,500 behind, same conflict and blob `b94e723f76`, 130/130, 69/69, 75/75, RED/GREEN 3/3, probes ×3, sabotage, seam, guards, E37); body.md and STAGING now declare that main. (4) Ownership facts recorded (last author activity 2026-09-11, two unanswered maintainer comments, the salvage invitation); route kept as support-note with OD-S added for the owner; promotion form unchanged (salvage-support). (5) `refs/archive/staging/tool-result-projection-support-v1` → `d5854fdd7b` and `-v2` → `8c783ff4ac` created in h.git, one patch per version saved, waiver for the moving name recorded in `naming_exception`; the branch did not move in round 2. (6) STAGING, body.md and the receipts state that the test file passes with v1, v2 and v3, that two sabotage flips go through a swallowed exception (gate hunk 1 and `tools/tool_result_storage.py`), and that chat completions is out of the gate's scope, not shown safe. (7) GUARDS r02 given its verdict by a corrections block; every receipt now carries `z0evals_study` and `env.relay` (nemo-relay 0.8.4 fails to initialize; no Relay plugin active). Receipts re-issued as r20261001-03 (F04, F04-enforced, E37, GUARDS, CARRIER-rebase, SRC), F04-bedrock r20261001-02, PREDICATE r20261001-02 and the new F04-thirdparty r20261001-01; earlier receipts marked superseded.
- 2026-10-01 | round-2 re-verifier | accept = false, 5 findings: (1) gate v3 undoes archived rows after a restart (ProjectionState is in memory; with signed thinking in the history the gate declines the re-projection and the rows go out in full under a block signed over their stubs); body.md, the gate docstring, the gate section, route_scope and NOT_TESTED said sticky rows keep replaying, which holds only within one agent; (2) body.md's AI disclosure did not cover the gate diff; (3) body.md began with an internal HTML comment; (4) body.md's "12 (or 11) of 28 requests with one-row passes" was wrong for S2 (its first pass archives 2 rows) and "replay_gates and region-scoping match main" left out that those transcripts never exercise projection; (5) the staging commit message credited "the review there" with the stable-boundary ask, which is teknium1's harness-scout note; kshitijk4poor's review raised the stickiness question.
- 2026-10-01 | STAGED (round-3 fix; class ceiling LIMITED) | Claude Code, Opus 5.5 | all five addressed, plus three more corrections found while re-checking. (1) Reproduced and receipted in RESTART/r20261001-01 (new `harness/f04_restart_probe.py`, end to end with a `SessionDB` resume, and `harness/restart_direct.py`, direct call through a route switch; 3 reps each, all equal). Gate v4 = v3 with a corrected docstring (no code change); body.md gains a section "The gate does not survive a restart" with both runs and states that on Claude routes the gate needs persisted stickiness (kshitijk4poor's question 2); the gate section, route_scope, NOT_TESTED, the acceptance-gate row and OD-S say the same. (2) body.md's disclosure now covers the comment, harness, tests and gate diff; every round-3 receipt's `ai_assistance` says the same. (3) The HTML comment is gone; the draft note lives in `[body].draft_note` and Origin action. (4) S1/S2 stated separately (S1: 12 one-row passes; S2: 11 passes, the first of 2 rows at 11,692 tokens here, then 10 one-row passes); the guard sentence says those transcripts never exercise projection; counts are written "N of M pass". (5) Commit message corrected: new commit `3b47753d54` (v3) cherry-picked onto main `44a1ce9724`, same test blob; local branch force-moved from `8c783ff4ac`; `refs/archive/staging/tool-result-projection-support-v3` created and its patch saved. Everything re-measured on `44a1ce9724` (13,523 behind, same conflict and resolved blob, RED/GREEN 3/3 for base, carrier, v1, v2, v4, probes ×3, per-hunk sabotage over 19 hunks with v4, seam trace, adjacent, guards, E37, predicate). Extra: (6) P5 PASS → PENDING, because the F14 standing set never ran (only three members did), and status LIMITED → STAGED with LIMITED kept as the ceiling (P5, P8-P10 and P12 are not met; LIMITED means everything but P6 holds); (7) every earlier receipt carried the workstation's host name in `env.host`: replaced by "withheld" with a corrections entry; (8) 18 raw outputs in `receipts/raw/r03/` held repr-truncated scratch-path fragments: scrubbed, and the round-2 receipts' artifact hashes updated with before/after values in their corrections blocks. Receipts re-issued as r20261001-04 (F04, F04-enforced, E37, GUARDS, CARRIER-rebase, SRC), F04-bedrock r20261001-03, F04-thirdparty r20261001-02, PREDICATE r20261001-03 and the new RESTART r20261001-01; the round-2 receipts are marked superseded. Promotion form unchanged (salvage-support); the gate is now offered as a sketch with a disclosed restart limit, not as a ready fold-in.
