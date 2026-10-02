+++
xf_staging = 1
id = "anthropic-context-editing"
version = 7
title = "Opt-in Anthropic server-side context editing (clear_tool_uses) behind a native_compaction-style gate (#526)"
branch = "staging/anthropic-context-editing-v3"
branch_fork = "staged/anthropic-context-editing-v3"
branch_physical = "Published on kvnloo/hermes-agent as staged/anthropic-context-editing-v3 at 97efa68e9b7005f5c65624bf5f4f583ebf8e098f (verified by read-only GitHub ref lookup 2026-10-02). The superseded staged/anthropic-context-editing remains at 05d6dbc172d24db4b237f8ef130fb4dc2e8651df and must not be used for v3 promotion. Original scratch ref: staging/anthropic-context-editing-v3; no ref is rewritten by this manifest correction."
branch_sha = "97efa68e9b7005f5c65624bf5f4f583ebf8e098f"
branch_prev = { ref = "staging/anthropic-context-editing-v2", sha = "24cc2cc8699dd5b4792264728ea484daeac82356", relation = "v3 (97efa68e9b, tree c66e75b01f, parent af7287ed22) = v2 cherry-picked onto main af7287ed22 (clean; git auto-merged agent/agent_init.py, agent/chat_completion_helpers.py and agent/turn_recovery.py, no conflict to resolve), then amended once: the comment at tests/agent/test_anthropic_context_editing.py:75 now says local compression keys on the reported post-clear size and fires later (test blob fc48d77dbb -> 2ae0c4d73c; no assertion or code changed). Author and author date kept, committer Kevin Rajan; commit message unchanged (no stated fact changed). Stable patch-id 7b127f103d (v2: 352f5b8a44; the difference is the comment line only). Built 2026-10-01T19:48Z; v2 and the original ref were not rewritten", suffix_note = "the -v2/-v3 suffixes count staging/<id> refs; they are unrelated to refs/xf/superseded/anthropic-context-editing-v2/-v3 (older heads b83e778103, 61effa4dd8)" }
status = "STAGED"          # ceiling at $0 = LIMITED (P6 needs the paid F10 cache arm); every $0 proof re-run on af7287ed22 as r20261001-05 and F14/r20261001-02 (EQUAL to the af7287ed22 baseline)
promotion_form = "core-pr"
route = "core-leaf"
feature = "anthropic-context-editing"
invariant = "With compression.anthropic_context_editing true, main-turn requests for Claude models on the native Anthropic API carry context_management.edits=[clear_tool_uses_20250919] plus the context-management-2025-06-27 beta, with a trigger below the local compression trigger, unless compression is disabled or checkpoint_required is set; every other request is unchanged; a structured 400 naming context_management disables the feature for the session and retries once."

[base]
repo = "NousResearch/hermes-agent"
sha = "af7287ed220a5ce0b0d00e95841956b60a31cb06"
fetched_at = "before 2026-10-01T19:36Z (mirror main as handed to this round, on which the F14 baseline run base2-r1 started at 19:36:39Z; refs/heads/main left untouched)"
freshness_recheck = { main = "af7287ed220a5ce0b0d00e95841956b60a31cb06", checked_at = "2026-10-01T20:00Z", commits_after_base = 0, merge_tree_clean = true, merge_tree = "c66e75b01fada7d4317c08d86a43ce6e8d81e440", invalidate_on = ["agent/turn_recovery.py", "agent/native_compaction.py", "agent/context_compressor.py", "agent/anthropic_adapter.py", "agent/chat_completion_helpers.py", "agent/agent_init.py", "agent/anthropic_endpoints.py", "agent/transports/anthropic.py", "tests/fakes/providers/anthropic_messages.py"], note = "the branch now sits on main af7287ed22 (147 commits after the old parent 44a1ce9724). Between them, 4 invalidate_on paths changed: agent/turn_recovery.py and agent/context_compressor.py (#130645, 5d077106b8, plus codex reasoning-replay fixes), agent/chat_completion_helpers.py and agent/agent_init.py (stream-watch and reasoning-replay fixes). So RED, GREEN, sabotage, adjacent, F09 and F14 were all re-run on af7287ed22 (r20261001-05, F14/r20261001-02); merge-tree of main x v3 is v3's own tree. The SDK-oracle fake blob e46bb9b439 is unchanged" }

[upstream]
issues = ["NousResearch/hermes-agent#526 (teknium1, open, P3; never closed: no closed/reopened event. A bot comment on 2026-06-04 said 'Closing as resolved by merged PR(s): #1147' but did not close it; the 2026-06-29 triage comment 'reopening discussion' kept it open as the canonical feature spec)", "NousResearch/hermes-agent#525 (teknium1, open, /microcompact, related)"]
prior_art = [
  { pr = 1147, author = "teknium1", state = "MERGED 2026-03-13T09:13Z", note = "title 'feat: add Anthropic Context Editing API support', body 'Refs #526, supersedes #528'; but the merged diff (its one commit bb3f5ed32a 'fix: separate Anthropic OAuth tokens from API keys', 10 files +114/-43) only reorders Anthropic OAuth-token vs API-key resolution and updates setup/status/config/doctor for it (the doctor check sends OAuth beta headers). It sends no context_management. Re-read with git and gh at 2026-10-01T18:35Z" },
  { pr = 528, author = "aydnOktay", state = "CLOSED unmerged 2026-03-13T14:38Z by teknium1, no comment", note = "env-var design on the OpenAI-SDK path. On 2026-03-10 teknium1 wrote 'We're going to leave this PR open' until a native Anthropic transport existed; it was then closed as superseded by #1147 the day #1147 merged. The native transport now exists. No code reused, so no Co-authored-by" },
]
# Re-checked 2026-10-01T19:55Z-20:02Z with gh (read-only). The preserved-thinking work landed: #130645 merged at 5d077106b8 (2026-10-01T18:48:03Z) and #103476, #129620, #129492 were closed unmerged within a minute as superseded by it (kshitijk4poor's closing comments name #130645); issue #129476 closed 18:49:34Z. #129882 stays open: its maintainer comment says the preserved-thinking portion (66987608bc) is superseded and the PR stays open only for unrelated work. Merge-trees re-run on af7287ed22: receipts/MERGE-r20261001-05.json.
dependencies = []
dependencies_landed = [
  { pr = 130645, author = "kshitijk4poor (salvage of #129620 by JoaoMarcos44, 22 contributor commits kept)", state = "MERGED 2026-10-01T18:48:03Z, merge commit 5d077106b8, head 1dc2267d28", touches = "agent/anthropic_message_convert.py, agent/anthropic_thinking_policy.py, agent/anthropic_thinking_replay.py, agent/context_compressor.py, agent/conversation_compression.py, agent/message_sanitization.py, agent/model_metadata.py, agent/turn_context.py, agent/turn_recovery.py, agent/turn_request_assembly.py, 1 test", file_overlap = "agent/turn_recovery.py (branch file); agent/context_compressor.py (invalidate_on only)", effect = "on main; v3 is built on top of it (cherry-pick auto-merged turn_recovery.py). In _recover_format_errors its thinking-signature step (one-shot, _retry.thinking_sig_retry_attempted) runs before the branch's context-management step (one-shot, _retry.native_compaction_reject_retry_attempted). Keeps earlier-turn thinking on native Claude models by default and counts it in preflight/tail accounting" },
  { pr = 103476, author = "teknium1", head = "bc9511af3f", state = "CLOSED unmerged 2026-10-01T18:49:11Z, superseded by #130645" },
  { pr = 129620, author = "JoaoMarcos44", head = "588b746cf6", state = "CLOSED unmerged 2026-10-01T18:49:02Z, salvaged and merged via #130645" },
  { pr = 129492, author = "SHL0MS", head = "7df230b4c3", state = "CLOSED unmerged 2026-10-01T18:49:20Z, superseded by #130645" },
]
related_open = [
  { pr = 71302, author = "TrueNix", head = "e709540872", state = "OPEN (last updated 2026-07-30; GitHub mergeable UNKNOWN on 2026-10-01T19:55Z; merge-tree on af7287ed22 conflicts)", claim = "OAuth request parity with the Claude Agent SDK (headers, billing block, system prefix, tool_choice)", touches = "agent/anthropic_adapter.py, tests/agent/test_anthropic_oauth_ua_prefix.py", file_overlap = "agent/anthropic_adapter.py", interaction = "on OAuth requests with thinking it sets extra_body['context_management'] = {edits: [{type: clear_thinking_20251015, keep: all}]} and adds context-management-2025-06-27 to _OAUTH_ONLY_BETAS. If both land as written, on OAuth + thinking + this flag its later write replaces our clear_tool_uses edit, and the beta appears twice in the header (we append it to a list that already holds the OAuth betas; _beta_header does not dedupe). Whichever lands second must build one edits list (clear_thinking first, as the API requires) and add the beta once. Unchanged on af7287ed22: agent/anthropic_adapter.py did not change between 44a1ce9724 and af7287ed22, and the PR head is the same", merge_with_staging = "re-run on af7287ed22 (MERGE/r20261001-05): main x PR conflicts in agent/anthropic_adapter.py and tests/agent/test_anthropic_oauth_ua_prefix.py; PR x v3 conflicts in the same 2 files (the test only because the PR is behind main; the branch does not touch it); main + PR x branch not run (no main + PR tree)", role = "related, not the owner: its claim is OAuth fingerprint parity, not context editing" },
]
neighbours = [
  { pr = 128432, author = "Julientalbot", head = "804222bf48", state = "OPEN", file_overlap = "agent/chat_completion_helpers.py, cli-config.yaml.example, context-compression-and-caching.md (xAI native compaction)", merge_with_staging = "clean on af7287ed22 (all 3 merge-trees)" },
  { pr = 129364, author = "thanosapollo", head = "e9ea24219b", state = "OPEN", file_overlap = "cli-config.yaml.example, context-compression-and-caching.md (gpt-6.1-sol native compaction)", merge_with_staging = "clean on af7287ed22 (all 3 merge-trees)" },
  { pr = 129882, author = "Sahilvishnaliya", head = "66987608bc", state = "OPEN, CHANGES_REQUESTED, CONFLICTING", file_overlap = "none (it touches agent/context_compressor.py, an invalidate_on path)", merge_with_staging = "main x PR and PR x v3 both conflict in agent/anthropic_message_convert.py, cron/lifecycle_guard.py and locales/en.yaml, none a branch file; no longer a dependency (its thinking portion is superseded by #130645)" },
]
competitors = []
close_after = []
demand = { score = "n/a", source = "critic.md missing_features #1; judges maintainer-fit 6 / evidence 3 / impact 6" }
maintainer_signal = "teknium1 authored #526 and wrote on #528 (2026-03-10): 'this is definitely a feature we want to support', pending a native Anthropic transport"
fork_threads = ["kvnloo/hermes-agent#322 (factory thread, open)", "kvnloo/hermes-agent#404 (staged-PR queue, open, 39 rows)"]

[[members]]
ref = "staging/anthropic-context-editing-v3"
sha = "97efa68e9b7005f5c65624bf5f4f583ebf8e098f"
role = "own leaf: first slice (gate + wire + recovery + config + 2 contract tests, the first parametrised over 6 eligibility cases + docs incl. the computer-use doc fix)"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
rebase_status = "parent af7287ed22: v2 24cc2cc869 cherry-picked clean (3 files auto-merged, no conflicts), then amended for the test comment at line 75 (the next-step-8 fix carried since round 3). Code unchanged; commit message unchanged"
supersedes = [
  "v2 ref 24cc2cc8699dd5b4792264728ea484daeac82356 (parent 44a1ce9724, tree 2c45d3cd53): still at refs/heads/staging/anthropic-context-editing-v2 (not rewritten); its patch is kept as superseded/anthropic-context-editing-v5.patch (sha256 3e973c0790...)",
  "05d6dbc172d24db4b237f8ef130fb4dc2e8651df (parent 44a1ce9724, same tree as v2): still at refs/heads/staging/anthropic-context-editing; its patch is superseded/anthropic-context-editing-v4.patch (sha256 fc7908647b...)",
  "61effa4dd8a0b81c8eda50a6119239b2aa19e52a (parent e8c97320ac): refs/xf/superseded/anthropic-context-editing-v3 and superseded/anthropic-context-editing-v3.patch",
  "b83e778103d36c48c7736bae07c01658dfb97158 (parent aea969677c): refs/xf/superseded/anthropic-context-editing-v2 and superseded/anthropic-context-editing-v2.patch",
  "1ecde98a7164827a1b8005d9be0443f9310901ce (parent 572e4f4fad): refs/xf/superseded/anthropic-context-editing-v1 and superseded/anthropic-context-editing-v1.patch (regenerated from the commit)",
  "the F14 arm da974f840c (34f8ec3b40 + 05d6dbc172) stays at refs/xf/w0/anthropic-context-editing; not moved",
]
version_policy = "FACTORY section 10: new refs staging/<id>-v2, -v3 rather than rewriting. Round 7 created staging/anthropic-context-editing-v3; staging/anthropic-context-editing (05d6dbc172) and -v2 (24cc2cc869) are untouched. Nothing is deleted: older heads stay reachable under refs/xf/superseded/ and their patches under superseded/ (the superseded/*-vN.patch numbers count patch files, not refs)."

[ownership]
searched_at = "2026-10-01T16:40Z"
queries = ["context_management", "context_management anthropic", "clear_tool_uses", "clear_tool_uses_20250919", "context editing", "context-management-2025-06-27", "context-management", "clear_thinking", "clear_thinking_20251015", "anthropic_context_editing"]
recheck = { at = "2026-10-01T20:02Z", queries = ["clear_tool_uses", "context_management anthropic", "anthropic_context_editing", "context-management-2025-06-27", "clear_thinking_20251015", "context_management"], state = "open", result = "0; [71302, 87303]; 0; 0; [71302]; and the same 8 open PRs for the bare context_management (128432, 99447, 103070, 106321, 129364, 71302, 80950, 87303). New in a result list: #87303 for 'context_management anthropic' (it was already in the bare list). It is 'feat(replay): cut re-sent tool output and thinking by up to 80%', a client-side replay trimmer on the chat-completions path; it sends no context_management to Anthropic and does not implement clear_tool_uses, so not an owner. No new related PR" }
queries_note = "round 3 added the bare 'context_management', the two dated edit types and 'context-management'; the bare query and 'clear_thinking_20251015' find #71302, which the round-1/2 query set missed"
open_external = []          # no open PR implements clear_tool_uses or the opt-in on the Anthropic path
related_open = [71302]      # same request field and beta on OAuth (clear_thinking); related, not the owner
merged_overlap = [1147]
merged_neighbour = [130645] # preserved thinking; shares agent/turn_recovery.py; on main under v3
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
verdict = "OURS (no open implementation of clear_tool_uses or of an opt-in; maintainer-authored issue). #71302 writes the same field on OAuth for a different claim; recorded as an interaction (P12), not an owner"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
specs = { path = "specs/PREREG.json", sha256 = "5df6163bc39856878e6a07e9dc77c1f4e47e1d885e4f20ea50a6a875cdea5ab8", recorded_at = "2026-10-01T19:51:04Z", note = "rev-5 P-redgreen and F09 specs plus the F14 set/baseline hashes and rule, hashed before run r20261001-05 started (first step 19:51Z+); decision rules unchanged from rev 4 (same decision_rule_sha256). G-guards is retired (rev 4 kept under superseded/r20261001-04/specs/). Not on claude/ledger" }
receipts = [
  { id = "P-redgreen/r20261001-05", path = "receipts/P-redgreen-r20261001-05.json", sha256 = "e0261a13cf754a465056ef2adc8d42e9a73dd9d015a8fe64da7ac80548693711" },
  { id = "F09/r20261001-05", path = "receipts/F09-r20261001-05.json", sha256 = "fa1915aace503b342cefa0990a44024a96864226c1a734e302913e7980683d39" },
  { id = "F14/r20261001-02", path = "receipts/F14-r20261001-02.json", sha256 = "196370626768d267aed9b12c6ed8bd491c0a0e426a7213dad6a871ff732bf702" },
  { id = "MERGE/r20261001-05", path = "receipts/MERGE-r20261001-05.json", sha256 = "c78e7f3dabfe2a1a6536b068e9ccbb8ceba37ac6bea2937d246afb2928f2c21e" },
]
superseded_receipts = "Everything under superseded/ is excluded from any public freeze (P8): it is history, not evidence. r20261001-04 (base 44a1ce9724, head 05d6dbc172, plus F14/r20261001-01 on 34f8ec3b40): receipts, raw, specs (incl. G-guards rev 4), harness (incl. the retired f14_guards.py), STAGING.md, PR_BODY.md and the v2 patch archived byte-for-byte under superseded/r20261001-04/ in round 7; its receipt hashes still match the values that STAGING.md records. r20261001-03 (head 61effa4dd8 on e8c97320ac): archived under superseded/r20261001-03/; its receipt hashes still match; that STAGING.md had one sentence naming the local host, redacted in round 3 (sha256 a931003fa7... -> 79519a15fb...). r20261001-02 (head b83e778103 on aea969677c): kept under superseded/r20261001-02/; round 3 replaced the local host name with '<local-host>' in its 3 receipts and its write_receipts.py, so the hashes its STAGING.md records no longer match. New sha256: P-redgreen 92086d3f38..., F09 8d4470d13a..., G-guards 42c959be74..., write_receipts.py 613a108e2e.... r20261001-01 (head 1ecde98a71) receipts were removed in round 1 before any freeze, because they carried local absolute paths."
patch = { path = "anthropic-context-editing.patch", sha256 = "87c663943aed206dc89b65c43cf31940e2f460886af0a4269455d24440eea748", regen = "git -C <h.git> -c core.abbrev=10 format-patch -1 --stdout staging/anthropic-context-editing-v3 (core.abbrev pinned: the default auto length grows with the shared object store and changes the index lines)", note = "regenerated from v3 in round 7; the v2 patch is kept as superseded/anthropic-context-editing-v5.patch (sha256 3e973c079066da0fa0f7608ad43b5ed4b1c0aa1fe4ca48fa79f390c9ef272d2e). The diff between them: the From line, index lines and hunk offsets of 4 files that moved on main, and the test-comment line" }
red = { test = "tests/agent/test_anthropic_context_editing.py", main = "af7287ed22", marker = "assert 'context-management-2025-06-27' in [...] / assert [False, False] == [True, False, False]", observed = "2 of 7 cases fail on main af7287ed22 (the 2 flag-on cases), both markers matched; the 5 cases that expect no field pass on both arms by design", receipt = "P-redgreen/r20261001-05" }
green = { reps = "3 of 3 reps pass (7 of 7 cases each)", receipt = "P-redgreen/r20261001-05" }
negative_control = { mutation = "one hunk at a time: 14 reverts (added line or condition deleted) + 2 value mutations (config parse forced False, trigger = local trigger + 1)", result = "14 of 16 re-RED, incl. each of the 5 gate conditions removed on its own (flag, compression.enabled, checkpoint_required, Claude model, third-party endpoint); unpinned: tui-hot-reload, gateway-cache-key", adjacent_rows = "fast-mode beta removal fails test_fast_command (1 of 17 fail; pinned); codex row removal fails nothing in test_native_compaction (64 of 64 pass; unpinned on main too)", receipt = "P-redgreen/r20261001-05" }
adjacent = { identical = true, files = 15, base = "518 of 518 pass", head = "518 of 518 pass", pre_existing = [] }
guards = { F14 = "EQUAL: pinned set rev 1 (set sha256 aba79fe8f09d...), arm = v3 97efa68e9b itself (on main af7287ed22, no separate arm commit), 2 runs, each EQUAL to baseline-af7287ed22.json on all 40 verdict ids (verdict, marker, fingerprint), r1 vs r2 EQUAL; 37 PASS / 3 FAIL on both arms, the 3 FAILs pre-existing on main (notice_delivery_probe, context_cap_probe, readtool lying_extension); 0 blocked execs; flaky none", F14_receipt = "F14/r20261001-02", F14_prev = "F14/r20261001-01 (34f8ec3b40 + 05d6dbc172 vs baseline-34f8ec3b40: EQUAL, 36/4) is history under superseded/r20261001-04/; the one id that changed between the two baselines, cache_estimator_probe FAIL -> PASS, is attributed to #130645 in factory/w0/f14/ERRATA.md E2", g_guards_rev4 = "retired; history under superseded/r20261001-04/ (its context_cap PASS was completion-only, see the round-6 history entry)", not_run = ["the F14 set-level exclusions (live/paid probes, goal_repaste_probe, the sandbox-denylisted live_ab probes, the readtool model arm)"] }
quantitative = []
cache_read_ratio = { status = "NOT_MEASURED", needs = "F10 (paid, OD-3)" }
route_scope = "native Anthropic API, Claude models; local compressor code unchanged (it fires later after a real clear; untested)"
not_tested = ["real Anthropic API acceptance and real rejection wording", "cache_read/cache_creation per turn around a clear (F10)", "OAuth subscription route", "interaction with #71302 if both land (two writers of context_management on OAuth + thinking, duplicate beta)", "server behaviour when the full uncleared history is resent each turn", "local fallback after a real server-side clear (local compression decides on the provider-reported prompt size, which is the post-clear size, so it fires later while the resent transcript and request body grow; F09's fake reports 60K whether or not the payload is sent)", "server-side clear_tool_uses together with the earlier-turn thinking blocks main now keeps (#130645); F09 and the contract test send no thinking", "skill_view results cleared server-side without the local ghost-skill reload marker", "compaction-exam recall with clears", "the codex_responses row of the generalised recovery table (no test reaches that step on main)", "the F14 set's set-level exclusions (live/paid probes, goal_repaste_probe which needs a private state.db copy, the sandbox-denylisted live_ab probes, the readtool model arm)"]
resource_usage = { wall_s = 516.4, cpu_core_s = "not captured (child rusage stops at the bwrap boundary)", api_cost_usd = 0.0, source = "raw/run_meta.json (409.8 s: RED, adjacent x2, F09 x2, GREEN x3, sabotage) + F14 runner wall clocks 54.8 s and 51.8 s; merge checks under 1 s" }
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-anthropic-context-editing", commit = "" }

[gates]
P1 = "PASS"       # RED on af7287ed22 (r20261001-05, 19:5xZ), both markers matched; that is current mirror main; re-run RED within 24 h of queueing
P2 = "PASS"       # no open or merged implementation; #71302 related (same field/beta on OAuth), not an owner; #87303 (client-side replay trimming) not an owner
P3 = "PASS"
P4 = "PASS"
P5 = "PASS"       # on af7287ed22 / v3 97efa68e9b: RED marker matched, GREEN 3/3, sabotage 14/16 with unpinned hunks listed, adjacent 518/518 identical, flaky false (P-redgreen/r20261001-05); F14 EQUAL x2 vs baseline-af7287ed22 (F14/r20261001-02)
P6 = "PENDING"    # caching-adjacent: needs OBSERVED cache-read before/after (F10) -> LIMITED until then
P7 = "PASS"       # local: one commit (v3 97efa68e9b) on main af7287ed22, author kept, feat(anthropic):, merge-tree = its own tree, 0 workflow files; fork v3 identity verified 2026-10-02; publication does not clear the remaining promotion gates
P8 = "PENDING"
P9 = "PENDING"    # body rewritten for v3; cache section waits on F10; tone gate by a second reader
P10 = "PENDING"   # no blind verifier on the v3 head 97efa68e9b yet
P11 = "RECORDED"
P12 = "PENDING"   # the preserved-thinking ordering is settled (#130645 merged, v3 on top of it); still pending: the #71302 interaction (resolved by whichever lands second), the staging cap and the queue row

[verification]
verifier = ""
provenance = "independent"
exact_head = "97efa68e9b7005f5c65624bf5f4f583ebf8e098f"   # promotion head v3
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "af7287ed220a5ce0b0d00e95841956b60a31cb06"
head = "97efa68e9b7005f5c65624bf5f4f583ebf8e098f"
checked_at = "2026-10-01T19:5xZ (run with the r20261001-05 proofs)"
clean = true
tree = "c66e75b01fada7d4317c08d86a43ce6e8d81e440"
recheck = "git -C <h.git> merge-tree --write-tree main staging/anthropic-context-editing-v3"
note = "main is v3's parent, so the merge tree is v3's own tree (MERGE/r20261001-05). Before the rebase: merge-tree of af7287ed22 with v2 was also clean (tree 1c38863f36)"

[push]
fork_ref = "staged/anthropic-context-editing-v3"
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = false, no_labor = false, no_internal_leak = false, smallest_ask = false, self_service = false, local_voice = false, easy_decline = false }
jargon_lint = "CLEAN (round 7, 2026-10-01T20:12Z): 0 hits in PR_BODY.md and the v3 commit message for P-gate, OD, xf, F##, E##, envelope, lane, receipt, @mention, fork-ref (staged/, kvnloo, fork), placeholder, absolute-path, factory words (wave, G-guards, factory, staging, manifest, errata, baseline, verifier, sabotage), host name, or upstream refs not written #N. Remaining pattern hits are ordinary words: 'gate' (the code's own term) and the config value 150000"
privacy_scan = "CLEAN (round 7, 2026-10-01T20:12Z): every file under the item directory except private/ (none exists), 110 files incl. superseded/: no absolute local paths, no host name, no secrets, no user email, no bytecode or __pycache__ (scan run with python3 -B, PYTHONDONTWRITEBYTECODE=1). Benign pattern hits only: the fake test key 'sk-ant-api03-fake-key' (test file in the patches, harness/f09_gate_probe.py and an archived manifest note) and the /tmp redaction regex in the archived superseded/r20261001-04/harness/f14_guards.py. The author address is the public GitHub noreply address"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after the existing 39 rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/anthropic-context-editing

**Promotion form:** core-pr (route core-leaf). **Status:** STAGED. The best class reachable at $0 is LIMITED: the change is caching-adjacent, so the PR body has to carry an OBSERVED cache-read before/after, and that needs the paid F10 run. Round 7 rebuilt the branch as `staging/anthropic-context-editing-v3` on main `af7287ed22` and re-ran every $0 proof there: P-redgreen/r20261001-05, F09/r20261001-05, MERGE/r20261001-05 and F14/r20261001-02 (EQUAL to the `af7287ed22` baseline). P1–P5 and P7 hold on v3; P6, P8, P9, P10 and P12 are PENDING.

**Branch.** The promotion head is the local ref `staging/anthropic-context-editing-v3` at `97efa68e9b` in the scratch h.git, one commit on main `af7287ed22` (tree `c66e75b01f`). It is v2 (`24cc2cc869`) cherry-picked onto `af7287ed22`. The cherry-pick was clean: git auto-merged `agent/agent_init.py`, `agent/chat_completion_helpers.py` and `agent/turn_recovery.py`, and there was no conflict to record. It was then amended once, for the test comment at line 75 (old next step 8). The author and author date are kept; the commit message is unchanged, because none of its facts changed. `staging/anthropic-context-editing` (`05d6dbc172`) and `staging/anthropic-context-editing-v2` (`24cc2cc869`) stay where they were, on `44a1ce9724`. On the fork, v3 is published as `staged/anthropic-context-editing-v3` at `97efa68e9b` (read-only ref check, 2026-10-02). The unsuffixed `staged/anthropic-context-editing` remains at superseded `05d6dbc172`; keep that ref intact and use the v3 ref for any later authorized promotion. Earlier heads stay reachable: `61effa4dd8` at `refs/xf/superseded/anthropic-context-editing-v3`, `b83e778103` at `-v2` and `1ecde98a71` at `-v1`; the old F14 arm `da974f840c` stays at `refs/xf/w0/anthropic-context-editing`. Their patches are in `superseded/`.

**Links.** Upstream: NousResearch/hermes-agent#526 (the feature spec, teknium1), NousResearch/hermes-agent#525 (related /microcompact), NousResearch/hermes-agent#1147 (merged; despite its title, OAuth token and header plumbing only), NousResearch/hermes-agent#528 (closed prior attempt), NousResearch/hermes-agent#71302 (open, related: writes the same field on OAuth), NousResearch/hermes-agent#130645 (merged preserved-thinking salvage; v3 sits on it), NousResearch/hermes-agent#103476, NousResearch/hermes-agent#129620, NousResearch/hermes-agent#129492 (closed as superseded by #130645), NousResearch/hermes-agent#129882 (open; its thinking portion is superseded, so it is no longer a dependency). Fork: kvnloo/hermes-agent#322 (factory thread), kvnloo/hermes-agent#404 (staged-PR queue, 39 rows). No fork thread exists for this feature yet.

## Invariant

With `compression.anthropic_context_editing: true`, main-turn requests for Claude models on the native Anthropic API carry `context_management.edits = [clear_tool_uses_20250919]` and the `context-management-2025-06-27` beta. The exceptions are when compression is disabled or `checkpoint_required` is set. The trigger sits below the local compression trigger. Every other request is unchanged. A structured 400 that names `context_management` disables the feature for the session and retries once.

Call path exercised: `AIAgent.run_conversation` → `turn_api_request.build_api_request` → `chat_completion_helpers._build_api_kwargs_for_mode` (the `anthropic_messages` branch) → `_build_anthropic_kwargs` → `anthropic_context_editing.anthropic_context_management` (the gate) → `AnthropicTransport.build_kwargs` → `anthropic_adapter.build_anthropic_kwargs` (`extra_body` and the per-request beta header) → SDK `messages.stream` over TLS to `api.anthropic.com`. The test intercepts that host with a throwaway CA and serves it from the SDK-oracle fake. The third-party case points the agent at the fake's loopback `/anthropic` URL instead. On a 400: `turn_recovery._recover_format_errors` → `is_native_compaction_rejection` → flag off → the next attempt is rebuilt without the field. Since #130645, `_recover_format_errors` first tries its own one-shot thinking-signature step (`_retry.thinking_sig_retry_attempted`); the context-management step keeps its own one-shot flag (`_retry.native_compaction_reject_retry_attempted`).

## Route and carrier choice

**Route: core-leaf, our own single commit.** There is no carrier to salvage and no competitor to support:

- No open PR implements `clear_tool_uses`, or an opt-in for context editing, on the Anthropic path. One open PR does write the same request field: **#71302** (TrueNix, OPEN, head `e709540872`, conflicting with main `af7287ed22`). Its claim is OAuth request parity with the Claude Agent SDK. As part of that, on OAuth requests with thinking it sets `extra_body["context_management"] = {"edits": [{"type": "clear_thinking_20251015", "keep": "all"}]}`, and it adds `context-management-2025-06-27` to `_OAUTH_ONLY_BETAS`. That makes it related, not the owner: it never sends `clear_tool_uses`, has no opt-in and no fallback. Rounds 1 and 2 missed it, because their six queries never searched the bare `context_management` or the dated `clear_thinking_20251015` type. The interaction is recorded under P12 and in the PR body's `clear_thinking` question.
- #87303 (open) now also shows up for `context_management anthropic`. It is a client-side replay trimmer ("cut re-sent tool output and thinking"); it sends no `context_management` and does not implement `clear_tool_uses`. Not an owner.
- #1147 (merged) is titled "feat: add Anthropic Context Editing API support", but its merged diff only separated Anthropic OAuth tokens from API keys (token resolution order, setup, status, and the doctor check's OAuth headers). It sends no `context_management`.
- #528 (aydnOktay) was closed unmerged as superseded by #1147. On 2026-03-10 teknium1 wrote "We're going to leave this PR open" until Hermes had a native Anthropic transport. He then closed it without comment on 2026-03-13T14:38Z, the day #1147 merged; #1147's body says "Refs #526, supersedes #528". #1147's merged diff only changed OAuth token and header plumbing (the 2026-06-29 triage note on #526 says "beta-header / OAuth plumbing"). teknium1 said the feature was wanted once a native Anthropic transport existed, and it now does. No code from #528 is reused, so no Co-authored-by trailer is added; the PR body credits it as prior art.
- #526 is authored by teknium1, and on #528 he called the feature "definitely a feature we want to support". So a support-note or salvage row would have nothing to attach to.

**What #71302 means if both land (re-checked on `af7287ed22`).** Both PRs write `extra_body["context_management"]` in `build_anthropic_kwargs`. #71302's block runs after ours, at the end of the function. On OAuth requests with thinking and this flag on, its write would replace our `clear_tool_uses` edit. The beta would also appear twice in the header: we append `_CONTEXT_MANAGEMENT_BETA` to `common + _OAUTH_ONLY_BETAS`, and `_beta_header` does not dedupe. Whichever PR lands second has to build one `edits` list, with `clear_thinking_20251015` first (the API requires that order when both edits are sent), and add the beta once. This analysis still holds on `af7287ed22`: `agent/anthropic_adapter.py` did not change between `44a1ce9724` and `af7287ed22`, and #71302's head is unchanged. MERGE/r20261001-05 on `af7287ed22`: main × #71302 conflicts in `agent/anthropic_adapter.py` and `tests/agent/test_anthropic_oauth_ua_prefix.py`, and #71302 × v3 conflicts in the same two files (the test only because the PR is behind main). The overwrite and the duplicate beta are read from the two diffs, not observed. This branch does not pre-empt the fix, because #71302 is not on main.

**Why core-pr and not decision-request (for now).** FACTORY §11.4 lists this item as "LIMITED → decision-request". The slice is complete and proven at $0, but P6 needs OBSERVED cache-read numbers (F10, paid, OD-3). If the owner does not fund F10, the fallback is to post the PR body's design and open questions on #526 as a decision request instead of opening the PR. The promotion form stays core-pr until that decision is made.

**The preserved-thinking ordering is settled.** Rounds 1–6 waited on #103476, #129620, #129492 and #129882 so that thinking replay was settled before a reviewer saw this PR (P12). That happened on 2026-10-01: #130645 (a salvage of #129620) merged at `5d077106b8`, and #103476, #129620 and #129492 were closed unmerged as superseded by it. #129882 stays open only for unrelated work. v3 is built on main after #130645. #130645 shares `agent/turn_recovery.py` with the branch; the cherry-pick auto-merged it, and the contract tests, adjacent suites, F09 and F14 all pass or match on top of it.

**Does the `clear_thinking` question still stand? Yes, with a new premise.** The old body asked whether `clear_thinking` was wanted "once #103476 lands". #103476 will not land, but its goal did, via #130645, which goes further: on native Claude models it keeps earlier-turn thinking by default ("Keep historical thinking on the native routes/models that support it"; "The original latest-only policy prevented historical-prefix reuse"), and it counts those blocks in preflight and tail accounting. Evidence that the accounting change is real: the F14 probe `cache_estimator_probe` (Fable 5.1 fixture) went from FAIL to PASS across exactly #130645's commits (preflight estimate 9,265 → 326,510; ERRATA E2). So two facts now pull in opposite directions. Server-side `clear_thinking_20251015` would drop those kept blocks and break the cached prefix at the first cleared block, which works against what #130645 was for. But the kept blocks now take window space that `clear_tool_uses` does not free. That is a maintainer call. The body still leaves `clear_thinking` out and asks it as an open question; #71302 still sends it on OAuth.

WAVE.md row form (own leaf, no carrier):

> | #526 (clear_tool_uses half) | own leaf `97efa68e` (kvnloo; v2 `24cc2cc8` cherry-picked, test comment reworded) on main `af7287ed`, merge-tree clean | main: 2 of 7 cases fail (beta missing; `[False, False]` vs `[True, False, False]`); head: 7 of 7 pass (3 of 3 reps); F09 head: payload on 1 of 6 gate cells (the eligible one), base on 0 of 6 | none (whole slice is ours) | no open implementation; #71302 (open) writes the same field on OAuth (clear_thinking), interaction noted; #528 closed as superseded by #1147, #1147 OAuth/header plumbing only; preserved thinking landed as #130645 | sabotage: 14 of 16 hunks re-RED, incl. each of the 5 gate conditions (2 sibling config hunks unpinned); 15 adjacent files 518 of 518 pass on both arms; F14 equal to the `af7287ed` baseline on all 40 verdict ids in 2 of 2 runs |

## Premise re-check (current main)

- **Still needed.** At `af7287ed22`, `git grep` finds no `clear_tool_uses` in any Python file and no `context_management` in `agent/anthropic*.py` or `agent/transports/anthropic.py`. The only `context_management` code is for Responses/xAI native compaction (`agent/native_compaction.py`, `agent/chat_completion_helpers.py::_build_codex_kwargs`, `agent/codex_responses_adapter.py`), plus a comment in `agent/auxiliary_client.py`.
- **A doc already claims the feature exists.** `website/docs/user-guide/features/computer-use.md:409` (on `af7287ed22`) says the adapter "enables `clear_tool_uses_20250919` via `context_management`". That is false on main; the 2026-06-29 triage comment on #526 notes the feature exists "only in website docs". The commit rewrites that bullet to say it is opt-in and names `compression.anthropic_context_editing`. The zh-Hans mirror (`website/i18n/zh-Hans/.../computer-use.md:105`) has the same sentence. It is left unchanged, because that page already lags the English one elsewhere in the same section (it still describes the old 3-screenshot eviction and macOS-only support). The PR body says so.
- **No competing implementation; one related PR.** Open-PR searches, re-run at 20:02Z: `clear_tool_uses`, `anthropic_context_editing` and `context-management-2025-06-27` return no open PR; `clear_thinking_20251015` returns #71302 only; `context_management anthropic` returns #71302 and #87303 (client-side replay trimming, not an owner); the bare `context_management` returns the same 8 open PRs as before (#128432, #99447, #103070, #106321, #129364, #71302, #80950, #87303). Of those, only #71302 touches the Anthropic request field. Round-3 searches (16:1xZ/16:40Z) for `context editing`, `clear_thinking`, `context-management` and the all-state queries found only unrelated hits, #1147 (merged), #528 (closed) and the open issue #526; they were not repeated.
- **History.** #528 (aydnOktay) was kept open by teknium1 on 2026-03-10, pending a native Anthropic transport. It was closed without comment on 2026-03-13 as superseded by #1147, which merged that day; its diff only changed OAuth token and header plumbing. #526 itself was never closed: a bot comment on 2026-06-04 called it "resolved by merged PR(s): #1147" without closing it, another user questioned that, and the 2026-06-29 triage comment reopened the discussion and kept #526 open as the canonical spec. The native transport now exists.
- **Correction carried into the body.** #526's "without destroying prompt cache prefixes" is not supported. Anthropic's context-editing docs say tool-result clearing invalidates the cached prefix when content is cleared, and that each clear incurs a cache write. The body says this plainly.

## Design choices in the slice

- **Gate.** The gate mirrors `native_compaction_context_management`. It is re-checked per request and requires the flag on, `compression.enabled` true, `checkpoint_required` not set, a Claude model, and a native Anthropic base URL. Bedrock, Azure, Portal, MiniMax, Kimi and proxies all count as third-party under `_is_third_party_anthropic_endpoint`. The gate is called only from the `anthropic_messages` branch of `_build_api_kwargs_for_mode`. So round 2 dropped its `api_mode` check: no request could reach it, so no test could pin it. Native compaction's gate likewise leaves the api_mode choice to its caller.
- **Payload.** Only `clear_tool_uses_20250919`. `trigger` = `resolve_compact_threshold(None, local_trigger)`, which is the local trigger minus 8,192 (reused from native compaction). `clear_at_least` = 20% of the trigger. `keep`, `exclude_tools` and `clear_tool_inputs` are left at server defaults. `clear_thinking_20251015` is not sent: since #130645 main keeps earlier-turn thinking for prefix stability, clearing it is a separate maintainer question, and #71302 sends it on OAuth.
- **Beta header.** Added only when a payload is sent. It reuses the fast-mode rebuild of the per-request beta list, so fast mode alone produces a byte-identical header.
- **Recovery.** The existing native-compaction rung is generalised to an api_mode → flag table. The codex message and log text are unchanged.
- **Local compression.** Unchanged code. It decides on the provider-reported prompt size (the usage anchor). That anchor feeds the turn-start check in `agent/turn_context_compaction.py`, and the pre-request and after-tool checks in `agent/turn_preflight.py`. After a real server-side clear, it therefore fires later than it would without the clear. The commit message, the module docstring, the config_defaults comment, `cli-config.yaml.example`, the docs row and (since v3) the test comment at line 75 all say so.
- **Config propagation.** `config_defaults` (default false), `agent_init`, the gateway agent-cache key, TUI hot reload, `cli-config.yaml.example`, one docs row in the compression guide, and the corrected computer-use bullet.
- **Contract test.** Two tests. The first is parametrised over six cases: off, on, and on with compression disabled, `checkpoint_required`, a non-Claude model (`glm-4.6` on the native URL, as in F09) or a third-party endpoint (the fake's loopback URL). The second is the structured-400 retry.

Footprint: 13 files, +201/−15 lines, including a 52-line module and a 91-line test file.

## Evidence

All rows are on base `af7287ed22` (tree `ac44bc0ecb`) and head v3 `97efa68e9b` (tree `c66e75b01f`). P-redgreen and F09 are run r20261001-05; F14 is F14/r20261001-02; merges are MERGE/r20261001-05. Specs (rev 5, same decision rules as rev 4) and the F14 set and baseline hashes were pre-registered at 19:51:04Z, before the run's first step. Every test and probe ran inside the xf sandbox (bwrap, loopback-only network, a fresh run dir with its own HOME/HERMES_HOME per step, Hermes console scripts stubbed): 0 blocked execs, 0 sandbox refusals. Whole run: about 516 s wall (409.8 s proofs + 106.6 s F14), CPU not captured, $0.

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| RED on base | receipts/P-redgreen-r20261001-05.json | PASS | OBSERVED | 7 cases | 2 of 7 fail on `af7287ed22` (beta missing; `[False, False] != [True, False, False]`), both markers matched. The 5 cases that expect no field pass on both arms by design |
| GREEN | same | PASS | OBSERVED | 3 reps | 7 of 7 pass in each of 3 reps |
| Sabotage, one hunk at a time | same + raw/sabotage.json | PASS | OBSERVED | 16 hunks + 2 adjacent rows | 14 of 16 re-RED. 14 are reverts (added line or condition deleted), including each gate condition removed on its own: flag, `compression.enabled`, `checkpoint_required`, Claude model, third-party endpoint. 2 are value mutations: config parse forced `False`, trigger = local trigger + 1. Unpinned: TUI hot reload, gateway cache key (sibling config paths). Adjacent rows: removing the fast-mode beta append makes 1 of 17 `test_fast_command` tests fail; removing the codex row of the recovery table leaves all 64 `test_native_compaction` tests passing, and no test on main reaches that step. Not mutated: config default entry, cli-config example, the 2 docs pages, the adapter constant/signature/docstring, the `clear_at_least` fraction value (bounded only), and the recovery display/log text. Same result as r20261001-04 on `44a1ce9724` |
| Adjacent | same | PASS | OBSERVED | 15 files | 518 of 518 pass on base, 518 of 518 on head |
| F09 gate probe | receipts/F09-r20261001-05.json | KEEP | OBSERVED | 10 cells × 2 arms | Head: payload on the eligible cell only (1 of 6 gate cells), 0 of 5 ineligible cells (flag false, compression off, checkpoint_required, non-Claude, third-party endpoint). Base: 0 of 6. 400 path: head `[True, False, False]`, base `[False, False]`. Local compressor over threshold (60K reported vs 50K): 1 compression on turn 2 in both arms, flag on and off. The fake reports 60K whether or not the payload is sent, so this does not model the post-clear regime. Head trigger 41,808 < 50,000. Flag-absent wire, base vs head: bodies (minus system) and headers IDENTICAL, and the system prompts are identical after host normalisation (only the hash is stored). SDK schema errors 0. Egress blocked 0 |
| F14 (Wave 0 set) | receipts/F14-r20261001-02.json | EQUAL | OBSERVED | 40 verdict ids × 2 runs vs the main baseline | Pinned set rev 1 (set sha256 `aba79fe8f09d...`, 19 probes, 40 verdict ids), runner `2323a59184...`, sandbox `c9586195c4...`, readtool helper `0df21aee5f...`, all the same as the baseline's. Arm: v3 `97efa68e9b` itself (it sits on main, so no separate arm commit). r1 and r2 each compare EQUAL to `baseline-af7287ed22.json` (main `af7287ed22`, base2-r2) on every id: verdict, marker and fingerprint; r1 vs r2 also EQUAL. 37 PASS / 3 FAIL on both arms; the 3 FAILs are the baseline's own: notice_delivery_probe (calls a private batch helper with an older signature), context_cap_probe (expects the 200,000-token default from the first draft of #103513; as merged, #103513 made `delegation.compression_threshold_tokens` opt-in, default 0, so the child trigger stays at 850,000; ERRATA E1), readtool lying_extension (PNG bytes in a `.txt` not flagged binary). cache_estimator_probe now passes on both arms (#130645; ERRATA E2). 0 blocked execs, worktree clean after both runs, no id marked flaky. Wall 54.8 s and 51.8 s, $0 |
| Merge checks | receipts/MERGE-r20261001-05.json | CLEAN | OBSERVED | 11 merge-trees | v3 × main `af7287ed22` clean (tree = v3's own). #71302 (related): main × PR and PR × v3 both conflict in `agent/anthropic_adapter.py` and its test (2). #129882 (neighbour): main × PR and PR × v3 both conflict in `agent/anthropic_message_convert.py`, `cron/lifecycle_guard.py`, `locales/en.yaml`, none a branch file (2). Neighbours #128432 and #129364: all clean (3 each). The former dependencies #103476, #129620, #129492 are closed and not re-checked |
| F10 cache arm | not run | — | NOT_MEASURED | — | queued (paid) |

History rows (r20261001-04 on `44a1ce9724`, F14/r20261001-01 on `34f8ec3b40`, G-guards rev 4) are archived under `superseded/r20261001-04/` and are not cited for any gate.

Example payload (OBSERVED, head, local trigger 150,000 for a 200K window): `{"edits":[{"type":"clear_tool_uses_20250919","trigger":{"type":"input_tokens","value":141808},"clear_at_least":{"type":"input_tokens","value":28361}}]}`.

Receipt format: all four receipts carry the `xf.receipt.v1` fields from FACTORY §9.2: spec (path, rev, sha256, decision_rule_sha; `prereg_commit` is null because xf/claude-ledger does not exist yet), runner_revision (incl. the sandbox hash), policy_revision, changed_files, denominators, evidence_class, resource_usage, frozen (`NOT_FROZEN`, P8) and privacy (`public-aggregate`). They contain no absolute local paths and no host name. Commands use the placeholders `<worktree>`, `<run>`, `<runs>`, `<xf-sandbox.sh>`, `<xf-root>`, `<venv-python>` and `<h.git>`. `env.host` is `<local-host>`. `harness/run_proofs.py` now wraps every step in the sandbox; the retired `harness/f14_guards.py` is kept only under `superseded/r20261001-04/harness/`.

## Experiments queued (exact commands, not run)

**F10. T3, paid, OD-3; the owner launches it with the owner's key.** Measures `cache_read` and `cache_creation` per turn before and after a clear, flag on and off, in ABBA order. It runs the upstream probe unmodified from the staging checkout; the probe records usage per call and classifies consecutive pairs as ideal/stuck/collapse. `threshold_tokens: 150000` puts the server trigger at 141,808, which a 10-call read_file loop crosses (≈30K tokens per read). After a clear with keep=3, about 100K tokens remain, under the local trigger. In the off arm, local compaction fires at 150K instead. Cost estimate (MODELED): roughly $2–4 per session on claude-opus-5-5, so 8 sessions come to about $16–32. Proposed cap: $35.

```bash
# from a checkout of staging/anthropic-context-editing-v3 @97efa68e9b (repo root)
for arm in off on on off; do
  R=$(mktemp -d "<artifact dir>/f10-$arm-XXXX")
  mkdir -p "$R/.hermes"
  printf 'compression:\n  threshold_tokens: 150000\n  anthropic_context_editing: %s\n' \
    "$([ "$arm" = on ] && echo true || echo false)" > "$R/.hermes/config.yaml"
  # HERMES_HOME MUST be explicit: the probe does os.environ.setdefault("HERMES_HOME", "~/.hermes")
  env -i PATH=/usr/bin:/bin HOME="$R" HERMES_HOME="$R/.hermes" ANTHROPIC_API_KEY="$OWNER_ANTHROPIC_KEY" \
    "$VENV_PY" -m evals.postmortem.live_ab.cache_concurrency_probe --repo . --provider anthropic \
      --model claude-opus-5-5 --workers 2 --calls 10 --ttl 5m --out "$R/f10_$arm.jsonl"
done
# report per arm: hit, collapse pairs, cache_creation total, cost_usd from f10_<arm>.summary.json;
# PR body gets OBSERVED cache_read before/after the first clear (on) vs the local compaction (off).
```

Known gaps in F10:

- The probe does not record `context_management.applied_edits` from the response, so clears are inferred from collapse pairs. A small read-only wrapper on `get_final_message().model_extra` would make clears observable (a follow-up before launch).
- With 10 calls per session, F10 also cannot show how long local compression is deferred after a clear while the resent transcript keeps growing. A longer on-arm session that logs reported input tokens against local transcript tokens per turn would cover that.
- Since #130645, main keeps earlier-turn thinking on native Claude models. If F10 runs with thinking on, the kept thinking blocks add to the input-token count that the trigger sees; the on-arm report should say whether thinking was on.

**F10-exam. T3, paid; the harness is NOT written.** This arm would run the frozen-lineage compaction exam (evals/compaction) after a long tool session, flag on vs off. `evals/compaction` has no server-side context-editing arm, so a new arm is needed. Queued as a design item, not a command.

**F14: done on `af7287ed22` (F14/r20261001-02).** The set pins a command for the readtool fixtures (9 direct read_file cases), and excludes `goal_repaste_probe` at set level for every item, because it needs `RF_STATE_COPY` pointing at a private state.db copy. A synthetic state.db built from a fixture session would let that probe join the set later; that is a set change, not an item task.

**T2 (local GPU): N/A.** Context editing is an Anthropic server feature. llama.cpp and ollama cannot emulate it, and the 64K floor (OD-1) blocks local Hermes arms anyway.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| With the flag off, the request is byte-identical to today | met | F09/r20261001-05 flag_absent_wire: identical bodies and headers across arms, and identical host-normalised system prompts. The contract test's off case asserts no field and no beta |
| Gate tests RED on main, GREEN with the change | met | P-redgreen/r20261001-05: on `af7287ed22`, 2 of 7 fail; on v3, 7 of 7 pass in each of 3 reps |
| Every eligibility condition pinned by the contract test | met | sabotage: each of the 5 gate-condition removals re-REDs (flag, compression.enabled, checkpoint_required, Claude model, third-party endpoint) |
| Negative control | met | sabotage: 14 of 16 hunks re-RED. 2 sibling config hunks unpinned (listed) |
| Structured-400 disable-and-retry proven | met | contract test 2 and F09 (`[True, False, False]`) |
| Local compressor still fires over threshold | partly met | F09 over_threshold cells: 1 compression on turn 2 with the flag on (trigger 41,808 < local 50,000). Not tested: the regime after a real clear, where reported usage drops while the resent transcript grows, so local compression fires later. The shipped text says this |
| F14 guards equal | met | F14/r20261001-02: 2 runs on v3 (on `af7287ed22`), each EQUAL to `baseline-af7287ed22.json` on all 40 verdict ids |
| Existing docs no longer claim the feature is always on | met | computer-use.md bullet rewritten in the commit; zh-Hans mirror called out in the body |
| PR body reports measured cache-read before/after and says it is not a savings feature | not met | the "not a savings feature" text is in the body. Cache-read numbers wait on F10 (OD-3) |
| Opened only after the preserved-thinking replay PRs settle | met | #130645 merged at `5d077106b8`; #103476, #129620, #129492 closed as superseded by it; #129882's thinking portion superseded (it stays open for unrelated work). v3 is on main after #130645, with every $0 proof re-run there |
| #71302 interaction resolved | pending | #71302 OPEN, conflicting with main `af7287ed22` (MERGE/r20261001-05). If it lands first, rebase this branch to merge the two `context_management` writers into one edits list (clear_thinking first) and drop the duplicate beta; if this lands first, the same falls to #71302's rebase. Named in the PR body |

## Gate checklist (P1–P12)

- P1 PASS: RED on `af7287ed22` (P-redgreen/r20261001-05), both markers matched; that is the current mirror main. Re-run RED within 24 h of queueing.
- P2 PASS: no open or merged implementation of `clear_tool_uses` or an opt-in. #71302 is open and related: it writes the same field (clear_thinking) and beta on OAuth for its OAuth-parity claim. It is recorded under [upstream].related_open and [ownership].related_open, and in P12. It is not an owner. #87303 (client-side replay trimming) is not an owner. Claimant lanes are TUI/HUD.
- P3 PASS: one invariant, a config.yaml key, no env var, no hook. Measured on `af7287ed22` → v3: turn_recovery.py 1952→1960 lines, under 2k. The touched files that were already over 2k lines grow by 0–9 lines each: agent_init 2512→2515 (+3), chat_completion_helpers 4131→4134 (+3), cli-config.yaml.example 2321→2330 (+9), config_defaults 3188→3193 (+5), gateway/run.py 6154→6154 (0).
- P4 PASS: real turn loop on the native route. Only the HTTP vendor boundary is faked.
- P5 PASS: on base `af7287ed22` and head v3 `97efa68e9b`: RED with both markers matched, GREEN 3 of 3, sabotage 14 of 16 with every gate condition pinned (2 sibling config hunks unpinned, listed), adjacent 518/518 identical, `flaky = false` (P-redgreen/r20261001-05). The codex row of the generalised recovery table is also unpinned and listed: no test on main reaches it. F14 guards equal: F14/r20261001-02, 2 runs, both EQUAL to the `af7287ed22` baseline on all 40 verdict ids.
- P6 PENDING: F10.
- P7 PASS (local): one commit (v3 `97efa68e9b`) on main `af7287ed22`, correct author, `feat(anthropic):`, 0 workflow files touched, merge-tree clean (its own tree). The fork ref `staged/anthropic-context-editing-v3` is published at `97efa68e9b`; the superseded unsuffixed ref remains unchanged (verified 2026-10-02).
- P8 PENDING: receipts carry the full §9.2 field set and the specs are pre-registered by hash, but nothing is frozen (no write-once bundle, nothing in z0evals). superseded/ is excluded from any public freeze.
- P9 PENDING: body rewritten for v3, with an AI disclosure ("written and run with Claude Code") and credit for #528 (prior art), #71302 (related) and #130645 (merged neighbour). Jargon lint and privacy scan: see [body]. The cache section is a placeholder until F10. Tone gate by a second reader.
- P10 PENDING: no blind verifier on the v3 head `97efa68e9b` yet.
- P11 RECORDED: teknium1-authored issue, explicit "we want to support" on #528.
- P12 PENDING: the preserved-thinking ordering is settled (#130645 merged, v3 on top). Still pending: the #71302 interaction and the staging cap / queue row. OD-0 is resolved by the `staged/<id>` fork name.

## NOT_TESTED

- **Real Anthropic API:** acceptance of the payload, the real rejection wording, and whether a non-structured failure could occur (the gpt-5.1 lesson from native compaction).
- **Cache behaviour after a clear.** It is also unknown whether the server re-clears on every request, because Hermes resends the full uncleared history (F10).
- **Local fallback after a real clear.** Hermes resends the full uncleared history every turn. Local compression decides on the provider-reported prompt size (the usage anchor; the turn-start, pre-request and after-tool checks all use it). After a server clear, that is the post-clear size. So local compression fires later, while the transcript and the request body keep growing. F09's over-threshold cell does not cover this, because the fake reports 60K whether or not the payload is sent. The commit message, the shipped comments and docs, and the PR body all say this.
- **Kept thinking plus clears.** Since #130645, main keeps earlier-turn thinking on native Claude models. Neither the contract test nor F09 sends thinking, so a server-side clear_tool_uses with kept thinking blocks in the request is not exercised.
- **OAuth / Claude subscription route:** whether the beta is accepted there. A structured 400 would fall back.
- **#71302 together with this branch:** not merged or run together. The overwrite and the duplicate beta are read from the two diffs, not observed.
- **skill_view results:** a server-side clear can drop them without the local compressor's ghost-skill "reload with skill_view" marker. `exclude_tools` is not set; it would also need the OAuth wire-name mapping.
- **Recall:** compaction-exam recall with clears (the F10-exam harness is not written). In the PR body's "Not tested" list.
- **Codex recovery row:** the generalised recovery table keeps the codex row's flag and text, but no test on main reaches that step, and this slice does not add one. The PR body says so.
- **F14:** the set-level exclusions: live or paid probes, goal_repaste_probe (needs a private state.db copy), the sandbox-denylisted live_ab probes and the readtool model arm. No F14 probe drives the `anthropic_messages` request path with the flag on, so F14 EQUAL shows no regression in the guarded surfaces, not coverage of the feature (that is the contract test and F09).
- **Test scope:** the full test suite was not run (targeted files only); no Windows or macOS runs. The docs site build was not run (two Markdown edits, no new links).

## Origin action (owner only)

When F10 numbers exist and the #71302 interaction is resolved: fill the cache section of PR_BODY.md, re-run RED/GREEN and F14 on the newest main, recheck that the existing fork ref `staged/anthropic-context-editing-v3` still resolves to the exact approved v3 head (currently `97efa68e9b`), then, only with owner authorization, run `gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/anthropic-context-editing-v3 --title "feat(anthropic): opt-in server-side context editing (clear_tool_uses)" --body-file PR_BODY.md`. The factory does not run this command. If F10 is not funded, post the body's design and open questions on #526 as a decision request instead.

## Next steps

1. Owner: OD-3 (F10 budget, about $35). OD-0 is resolved by the `staged/<id>` name.
2. Before F10: add the read-only `applied_edits` capture to the probe run (a wrapper only, no core change), and consider one longer on-arm session that logs reported vs local transcript tokens per turn (post-clear fallback regime), with thinking on and off.
3. Re-run the proofs and F14 after any rebase or amend: `harness/run_proofs.py` (sandboxed), `harness/write_receipts.py`, `harness/merge_check.py`, and the factory `f14_run.py` against the baseline map of the main the arm sits on.
4. A blind verifier reads exact head `97efa68e9b` (P10).
5. Watch #71302. If it lands first, rebase and merge the two `context_management` writers into one edits list (clear_thinking first), with the beta added once, plus a test for OAuth + thinking + flag on.
6. Ask on #526 whether `skill_view` should be in `exclude_tools` by default (a follow-up slice), and whether `clear_thinking` is wanted now that #130645 keeps earlier-turn thinking.

## History

- 2026-10-01T09:24Z | STAGED | builder (Claude Code, Opus 5.5) | first slice committed 1ecde98a71 on 572e4f4fad. $0 proofs and F09 KEEP; F10 queued.
- 2026-10-01T11:20Z | STAGED | stfix round 1 (Claude Code, Opus 5.5) | Fixed the phase-3 verifier findings:
  - Rebased onto aea969677c and amended the commit with the computer-use doc fix: new head b83e778103. The local branch was forced to it as instructed.
  - Corrected the #129882 merge claim (no overlap; the PR itself conflicts with main) and #129620's head (588b746cf6).
  - Plain AI disclosure in the body; P3 now includes cli-config.yaml.example (+8).
  - Added the Route and carrier choice section.
  - Pre-registered rev-2 specs, re-ran every $0 proof (r20261001-02), and wrote full §9.2 receipts with no local paths. Removed the r20261001-01 receipts.
  - F09 now stores only host-normalised system-prompt hashes.
  - Fork branch name is staged/<id> (OD-0 resolved).
- 2026-10-01T12:00Z | STAGED | stfix round 2 (Claude Code, Opus 5.5) | Fixed the round-1 re-verifier findings:
  - **#528 history corrected** in the PR body and here. #528 was closed as superseded by #1147. teknium1 had kept it open pending a native transport, which now exists. It was not "turned down for lack of a native transport".
  - **Negative control.** The contract test now has four more ineligible cases: compression disabled, checkpoint_required, non-Claude model, third-party endpoint. The gate drops the `api_mode` check that no request could reach. The amended commit 61effa4dd8 sits on main e8c97320ac. Each gate condition removed on its own now re-REDs (sabotage 14/16). PR body step 3 now says exactly what was broken and how (reverts vs mutations), and what is not covered.
  - **MERGE count** is 12 (`harness/merge_check.py` counts the merge-trees it runs), not 13.
  - **PR body "Not tested"** adds the post-clear local-fallback regime and compaction recall with clears. The "local compressor stays armed" claim is softened.
  - **Superseded heads kept reachable:** refs/xf/superseded/anthropic-context-editing-v1 (1ecde98a71) and -v2 (b83e778103), with both patches under superseded/. The r20261001-02 run is archived unchanged under superseded/r20261001-02/.
  - **Receipts:** env.host is now `<local-host>`.
  - Re-ran every $0 proof as r20261001-03 against pre-registered rev-3 specs.
  - Found while doing this: the codex row of the generalised recovery table has no test on main. Recorded as unpinned in the receipt, here and in the body.
- 2026-10-01T16:45Z | STAGED | stfix round 3 (Claude Code, Opus 5.5) | Fixed the round-2 re-verifier findings:
  - **Missed related PR #71302.** Recorded under [upstream].related_open, [ownership].related_open, P2, P12, Route and carrier choice, and the premise re-check. The ownership queries now include the bare `context_management` and the dated edit types. The PR body credits #71302 as related, and its `clear_thinking` question explains what happens if both land: the overwrite on OAuth + thinking, the duplicate beta, and the one-list fix with clear_thinking first. MERGE now covers #71302 (conflicts, as the verifier measured) and two neighbours (#128432, #129364; clean).
  - **P5 overstated.** G-guards rev 4 runs the F14 set through `harness/f14_guards.py`, on both arms: 22 of 24 items, all with equal verdicts. The two items not run are listed with reasons. P5 is now PENDING (partial), not PASS.
  - **Privacy.** The local host name is gone from this manifest. Round 3 redacted it to `<local-host>` in the 3 r20261001-02 receipts, its write_receipts.py and the archived r20261001-03 STAGING.md, and recorded the new hashes. superseded/ is excluded from any public freeze. A stray `harness/__pycache__` that embedded the local harness path was deleted.
  - **Wording.** The commit message and the 4 shipped places (module docstring, config_defaults comment, cli-config.yaml.example, docs row) no longer say the local compressor "stays armed as the fallback". They say it keys on the provider-reported post-clear size and fires later. The commit was amended on a fresh worktree of main 44a1ce9724: new head 05d6dbc172, code and tests unchanged. RED/GREEN/sabotage/adjacent/F09/F14 were re-proved as r20261001-04 against pre-registered rev-4 specs. The local branch was forced to 05d6dbc172, and 61effa4dd8 stays at refs/xf/superseded/anthropic-context-editing-v3.
- 2026-10-01T18:30Z | STAGED | w0 F14 guard (Claude Code, Opus 5.5) | Wave 0 F14 comparison, receipt F14/r20261001-01 (OBSERVED):
  - Cherry-picked 05d6dbc172 onto main 34f8ec3b40, author kept, applied clean: arm da974f840c (same stable patch-id 352f5b8a44), ref `refs/xf/w0/anthropic-context-editing`. The staging branch itself is unchanged.
  - Ran the pinned F14 set (rev 1, set sha256 aba79fe8f09d...) twice in the sandbox (labels anthropic-context-editing-r1, -r2). Both runs are EQUAL to the main baseline map on all 40 verdict ids, and to each other: 36 PASS / 4 FAIL, the same 4 baseline FAILs with identical markers. No blocked execs, no sandbox refusals, worktree clean.
  - guards.F14 = EQUAL. P5 PENDING -> PASS: the other P5 parts were already recorded as met in P-redgreen/r20261001-04. Updated the status comment, the Evidence table (new F14 row), the acceptance-gate row, the P5 checklist line, NOT_TESTED, the F14 completion note and next step 3 to match. The G-guards rev 4 row stays as history.
  - The worktree was removed and pruned. Nothing was pushed.
- 2026-10-01T18:45Z | STAGED | polish round 5 (Claude Code, Opus 5.5) | Text and manifest only; no code change, no new proof runs:
  - **Commit message.** "#1147 only changed beta-header plumbing" now reads "#1147 only changed OAuth token and header plumbing" (verified against #1147's merged diff: its one commit bb3f5ed32a separates OAuth tokens from API keys). The old ref was not rewritten: `staging/anthropic-context-editing-v2` = 24cc2cc869 is a `git commit-tree` of the same tree 2c45d3cd53 and parent 44a1ce9724, author and author date preserved, same stable patch-id 352f5b8a44. v2 differs only in the message, so all proofs carry over. `staging/anthropic-context-editing` stays at 05d6dbc172. The patch was regenerated from v2; the 05d6dbc172 patch is kept as superseded/anthropic-context-editing-v4.patch.
  - **PR body.** #1147 described precisely (OAuth/API-key separation, no `context_management`). Added two sentences on the AGENTS.md rule that compression is the only sanctioned cache break: a clear is a second kind, and the cost to weigh is clears against the local compactions they defer. Corrected the cause of the 3 probes that fail on both arms: `cache_estimator_probe.py` checks a fix still open in #103476, while the other two lag the code.
  - **Manifest.** #526 was never closed (the bot comment did not close it; triage "reopened discussion"); fixed in [upstream].issues and the premise History bullet. #1147 wording fixed in prior_art, Links, Route and carrier choice and the WAVE row. Freshness: main 34f8ec3b40 is 9 commits past 44a1ce9724, and no `invalidate_on` path or branch file changed; merge-tree clean (tree 44e3f84714); [base].freshness_recheck, [merge_check], P1, P7 updated. Dependency heads and the ownership queries re-checked with gh (unchanged). Jargon lint and privacy scan recorded as clean.
  - **Not fixed (code).** The test comment "the local compressor stays the fallback at its own trigger" (test file line 75) needs a tree change; it is next step 8.
  - Nothing pushed; no GitHub writes.
- 2026-10-01T19:15Z | STAGED | fix round 6 (Claude Code, Opus 5.5) | Fixed the fresh verifier's findings on 24cc2cc869. Text and manifest only: no code change, no new proof runs, no git writes (the v2 ref and the commit message are unchanged; the message makes no probe claim):
  - **BLOCKING: PR body counted a vacuous pass.** "19 of the 22 pass on both" came from G-guards rev 4, which counted context_cap_probe as PASS only because it finished (rc 0 and "DONE arm"). That probe prints values and has no verdict; its README check ("cap holds through repeated compression") cannot hold because the child cap is off by default, on 44a1ce9724 as on 34f8ec3b40 (checked with git grep: tools/delegate_tool.py:139, config_defaults compression_threshold_tokens = 0). The eval-probe paragraph is rewritten from F14/r20261001-01: main 34f8ec3b40 and this commit on top, 2 runs each in fresh homes, 19 probes / 40 results, 36 pass and 4 fail identically on both, all 4 failing on main already (cache_estimator_probe: fix open in #103476; notice_delivery_probe: calls the private batch helper with an older signature; context_cap_probe: [wording corrected in round 7: it expects the 200,000-token default from the first draft of #103513; as merged, #103513 made the cap opt-in (off by default), so the child trigger stays at 850,000]; the lying-extension read_file fixture: PNG bytes in a .txt are not flagged binary). It names the main it used, says the readtool fixtures are read directly by a small helper, says value-printing probes were judged against criteria fixed before the runs, and lists what was not run (live/paid probes, the 4 offline live_ab probes the local sandbox blocks, goal_repaste_probe). The results header now says items default to 44a1ce9724 unless they name another commit. subagent_context_cap.py is no longer cited (F14 excludes it).
  - **Advisory: F14 receipt changed_files.** website/docs/user-guide/features/context-compression-and-caching.md (absent at 34f8ec3b40) corrected to website/docs/developer-guide/context-compression-and-caching.md, matching `git diff --name-only 34f8ec3b40 da974f840c`; the change is recorded in the receipt's new corrections field. New sha256 d8c9b53525... (was 4cb29671e6...) in [evidence].receipts. No verdict, count or map changed.
  - **Advisory: rev-4 guards labelled as history.** guards.replay_gates and guards.postmortem_runner now say they are G-guards rev 4 history (44a1ce9724 vs 05d6dbc172); guards.g_guards_rev4 and the renamed Evidence row "Guards: G-guards rev 4 (history; superseded for P5 by the F14 row)" state the judge difference (rev-4 context_cap PASS is completion-only; F14's pinned judge fails it on both arms). P5 still rests on F14/r20261001-01 and is unchanged.
  - **Still open (code):** the test comment at tests/agent/test_anthropic_context_editing.py:75 (blob fc48d77dbb); next step 8, unchanged.
  - Jargon lint (PR body + v2 message) and privacy scan (29 files) re-run: clean; [body] updated. Gates unchanged: P1-P5, P7 PASS; P11 RECORDED; P6, P8, P9, P10, P12 PENDING; status STAGED. Nothing pushed; no GitHub writes.
- 2026-10-01T20:10Z | STAGED | rebuild round 7 (Claude Code, Opus 5.5) | v3 on the new upstream main, after the fresh verifier's blocking findings:
  - **Upstream changed (blocking 1).** Read with gh (read-only): #130645 (salvage of #129620) MERGED at 5d077106b8 (18:48:03Z); #103476, #129620, #129492 CLOSED unmerged as superseded by it (maintainer closing comments name #130645); issue #129476 closed; #129882 stays open for unrelated work. [upstream].dependencies is now empty, with dependencies_landed; #129882 moved to neighbours; P12, the acceptance-gate row, Links, Route and the design notes rewritten. Decision on the clear_thinking question: it still stands with a new premise. #130645 keeps earlier-turn thinking on native Claude models (its body: "Keep historical thinking on the native routes/models that support it") and counts it in accounting (cache_estimator_probe FAIL -> PASS across exactly its commits, ERRATA E2), so clear_thinking would undo part of #130645's prefix stability, while the kept blocks take window space clear_tool_uses does not free. The body keeps clear_thinking out and asks it without the "once #103476 lands" premise.
  - **context_cap framing (blocking 2).** PR body, the F14 row and the round-6 history line now say the probe expects the 200,000 default from #103513's first draft, and that the merged #103513 (e5f8420be8) made the cap opt-in (default 0), so the child trigger stays at 850,000. The old guards notes were retired with G-guards.
  - **Branch.** Worktree wt-w0/anthropic-context-editing-v3 detached at af7287ed22; v2 24cc2cc869 cherry-picked with the author kept (committer Kevin Rajan): clean, 3 files auto-merged (agent_init.py, chat_completion_helpers.py, turn_recovery.py), no conflicts. Amended for the test comment at line 75 (advisory; old next step 8). Commit message unchanged (no stated fact changed). New ref refs/heads/staging/anthropic-context-editing-v3 = 97efa68e9b (tree c66e75b01f, patch-id 7b127f103d). main, staging/anthropic-context-editing and -v2 untouched; no ref moved or deleted.
  - **Proofs re-run on af7287ed22, all inside the xf sandbox** (rev-5 specs pre-registered 19:51:04Z; harness/run_proofs.py now wraps each step in xf-sandbox.sh): RED 2 of 7 with both markers; GREEN 7 of 7 in 3 of 3 reps; sabotage 14 of 16 (unpinned: tui-hot-reload, gateway-cache-key; adjacent rows: fast-mode 1 of 17 fail, codex row 64 of 64 pass); adjacent 518 of 518 on both arms; F09 KEEP (1 of 6 gate cells, 400 path [True, False, False], flag-absent wire identical); F14 x2 on v3 EQUAL to baseline-af7287ed22 (37/3, 40 of 40 ids), r1 vs r2 EQUAL; 0 blocked execs. Receipts P-redgreen/r20261001-05, F09/r20261001-05, F14/r20261001-02, MERGE/r20261001-05.
  - **#71302 re-checked on af7287ed22** (merge-tree): main x PR and PR x v3 both conflict in agent/anthropic_adapter.py and its test; the overwrite/duplicate-beta analysis is unchanged (the adapter file and the PR head did not change).
  - **Advisories.** PR body: "for this recovery step, test_native_compaction only covers the rejection classifier"; AI disclosure "written and run with Claude Code"; #130645 named as a related merged PR (recovery-step order).
  - **Archive.** Round-6 receipts, raw, specs (incl. G-guards rev 4), harness (incl. f14_guards.py), STAGING.md, PR_BODY.md and the v2 patch copied to superseded/r20261001-04/; the v2 patch also as superseded/anthropic-context-editing-v5.patch; new patch from v3.
  - Worktree removed and pruned. Nothing pushed; no GitHub writes. Status STAGED: P1-P5, P7 PASS; P11 RECORDED; P6 (paid F10), P8, P9, P10, P12 (#71302, queue) PENDING.
