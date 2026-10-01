+++
xf_staging = 1
id = "anthropic-context-editing"
version = 6
title = "Opt-in Anthropic server-side context editing (clear_tool_uses) behind a native_compaction-style gate (#526)"
branch = "staging/anthropic-context-editing-v2"
branch_fork = "staged/anthropic-context-editing"
branch_physical = "local-only in scratch h.git as staging/anthropic-context-editing-v2 (promotion head) next to the untouched staging/anthropic-context-editing (05d6dbc172); v2 is the one to push to kvnloo/hermes-agent as staged/anthropic-context-editing (OD-0 resolved by that rename: the fork's legacy refs/heads/staging 28790e597c blocks staging/<id>)"
branch_sha = "24cc2cc8699dd5b4792264728ea484daeac82356"
branch_prev = { ref = "staging/anthropic-context-editing", sha = "05d6dbc172d24db4b237f8ef130fb4dc2e8651df", relation = "v2 (24cc2cc869) differs from 05d6dbc172 ONLY in the commit message (#1147 is now described as 'OAuth token and header plumbing'). Same tree 2c45d3cd5381cbff8fdf95807af5b026d3b02f2c, same parent 44a1ce9724, same author and author date, same stable patch-id 352f5b8a44; so every proof and receipt measured on 05d6dbc172 (and on its cherry-pick da974f840c) carries over unchanged. Built with git commit-tree on 2026-10-01T18:35Z; the old ref was not rewritten", suffix_note = "the -v2 suffix counts staging/<id> refs; it is unrelated to refs/xf/superseded/anthropic-context-editing-v2 (b83e778103, an older head)" }
status = "STAGED"          # ceiling at $0 = LIMITED (P6 needs the paid F10 cache arm); P5 PASS since F14/r20261001-01 (Wave 0 F14 set EQUAL to the main baseline)
promotion_form = "core-pr"
route = "core-leaf"
feature = "anthropic-context-editing"
invariant = "With compression.anthropic_context_editing true, main-turn requests for Claude models on the native Anthropic API carry context_management.edits=[clear_tool_uses_20250919] plus the context-management-2025-06-27 beta, with a trigger below the local compression trigger, unless compression is disabled or checkpoint_required is set; every other request is unchanged; a structured 400 naming context_management disables the feature for the session and retries once."

[base]
repo = "NousResearch/hermes-agent"
sha = "44a1ce9724502b9c692faaef00af3054bf11f1a6"
fetched_at = "2026-10-01T16:10Z"
freshness_recheck = { main = "34f8ec3b407e50bad3ae27e4cd79d65212061356", checked_at = "2026-10-01T18:35Z", commits_after_base = 9, merge_tree_clean = true, merge_tree = "44e3f84714dfc14abc7e991e0012f1add6625c1f", invalidate_on = ["agent/turn_recovery.py", "agent/native_compaction.py", "agent/context_compressor.py", "agent/anthropic_adapter.py", "agent/chat_completion_helpers.py", "agent/agent_init.py", "agent/anthropic_endpoints.py", "agent/transports/anthropic.py", "tests/fakes/providers/anthropic_messages.py"], invalidate_on_hits = [], branch_file_hits = [], main_changed_files = ["agent/codex_responses_adapter.py", "agent/model_metadata.py", "gateway/media_policy.py", "tests/agent/test_codex_responses_adapter.py", "tests/agent/test_model_metadata.py", "tests/gateway/test_multiplex_process_memo_scope.py", "tests/hermes_cli/test_auth_codex_quota_probe.py", "tests/hermes_cli/test_gpt6_tiers_registration.py", "tests/scripts/install/test_install_ps1_json_failure_frame.py", "tests/scripts/install/test_install_ps1_staged_git.py"], note = "invalidate_on = union of the 3 specs' lists; git diff --name-only 44a1ce9724..34f8ec3b40 over it and over the 13 branch files is empty. merge-tree of 34f8ec3b40 with v2 (and with 05d6dbc172, same tree and parent) is clean, tree 44e3f84714, the same tree as the F14 arm da974f840c. Not re-based (polish round). Previous check: main 44a1ce9724 at 16:40Z, 0 commits after base" }

[upstream]
issues = ["NousResearch/hermes-agent#526 (teknium1, open, P3; never closed: no closed/reopened event. A bot comment on 2026-06-04 said 'Closing as resolved by merged PR(s): #1147' but did not close it; the 2026-06-29 triage comment 'reopening discussion' kept it open as the canonical feature spec)", "NousResearch/hermes-agent#525 (teknium1, open, /microcompact, related)"]
prior_art = [
  { pr = 1147, author = "teknium1", state = "MERGED 2026-03-13T09:13Z", note = "title 'feat: add Anthropic Context Editing API support', body 'Refs #526, supersedes #528'; but the merged diff (its one commit bb3f5ed32a 'fix: separate Anthropic OAuth tokens from API keys', 10 files +114/-43) only reorders Anthropic OAuth-token vs API-key resolution and updates setup/status/config/doctor for it (the doctor check sends OAuth beta headers). It sends no context_management. Re-read with git and gh at 2026-10-01T18:35Z" },
  { pr = 528, author = "aydnOktay", state = "CLOSED unmerged 2026-03-13T14:38Z by teknium1, no comment", note = "env-var design on the OpenAI-SDK path. On 2026-03-10 teknium1 wrote 'We're going to leave this PR open' until a native Anthropic transport existed; it was then closed as superseded by #1147 the day #1147 merged. The native transport now exists. No code reused, so no Co-authored-by" },
]
# Re-measured 2026-10-01T16:11Z-16:29Z on main 44a1ce9724: heads checked with gh, fetched read-only into refs/xf/pr/<n>, merge-trees in receipts/MERGE-r20261001-04.json.
# Re-checked 2026-10-01T18:35Z with gh (read-only): all 4 dependency heads, #71302 (e709540872) and both neighbour heads unchanged, all still OPEN; #129882 still CONFLICTING / CHANGES_REQUESTED; GitHub reported mergeable UNKNOWN (not yet computed) for #103476, #129620, #71302, #128432, #129364. The merge-trees were not re-run on main 34f8ec3b40 (MERGE receipt stays on 44a1ce9724); the 9 new main commits touch none of the branch's files.
dependencies = [
  { pr = 103476, author = "teknium1", head = "bc9511af3f", state = "OPEN, MERGEABLE", touches = "agent/anthropic_endpoints.py, agent/anthropic_message_convert.py, agent/message_sanitization.py, 2 tests", file_overlap = "none", merge_with_staging = "clean (main x PR, main + PR x branch, PR x branch)" },
  { pr = 129620, author = "JoaoMarcos44", head = "588b746cf6", state = "OPEN, MERGEABLE", touches = "agent/anthropic_message_convert.py, agent/turn_recovery.py, agent/message_sanitization.py and 5 more agent files, 1 test", file_overlap = "agent/turn_recovery.py", merge_with_staging = "clean (all 3 merge-trees; the shared file auto-merges)" },
  { pr = 129492, author = "SHL0MS", head = "7df230b4c3", state = "OPEN, MERGEABLE", touches = "agent/anthropic_message_convert.py, tests/agent/test_anthropic_adapter.py", file_overlap = "none", merge_with_staging = "clean (all 3 merge-trees)" },
  { pr = 129882, author = "Sahilvishnaliya", head = "66987608bc", state = "OPEN, CHANGES_REQUESTED, CONFLICTING", touches = "17 files incl. agent/anthropic_message_convert.py, agent/context_compressor.py, cron/lifecycle_guard.py", file_overlap = "none", merge_with_staging = "no file overlap; the PR itself conflicts with main in cron/lifecycle_guard.py, so PR x branch reports that same conflict (main + PR x branch not run: there is no main + PR tree)" },
]
related_open = [
  { pr = 71302, author = "TrueNix", head = "e709540872", state = "OPEN, CONFLICTING (last updated 2026-07-30)", claim = "OAuth request parity with the Claude Agent SDK (headers, billing block, system prefix, tool_choice)", touches = "agent/anthropic_adapter.py, tests/agent/test_anthropic_oauth_ua_prefix.py", file_overlap = "agent/anthropic_adapter.py", interaction = "on OAuth requests with thinking it sets extra_body['context_management'] = {edits: [{type: clear_thinking_20251015, keep: all}]} and adds context-management-2025-06-27 to _OAUTH_ONLY_BETAS. If both land as written, on OAuth + thinking + this flag its later write replaces our clear_tool_uses edit, and the beta appears twice in the header (we append it to a list that already holds the OAuth betas; _beta_header does not dedupe). Whichever lands second must build one edits list (clear_thinking first, as the API requires) and add the beta once", merge_with_staging = "main x PR conflicts (anthropic_adapter.py, its test); PR x branch conflicts in the same 2 files (the test only because the PR is behind main; the branch does not touch it); main + PR x branch not run", role = "related, not the owner: its claim is OAuth fingerprint parity, not context editing" },
]
neighbours = [
  { pr = 128432, author = "Julientalbot", head = "804222bf48", state = "OPEN, MERGEABLE", file_overlap = "agent/chat_completion_helpers.py, cli-config.yaml.example, context-compression-and-caching.md (xAI native compaction)", merge_with_staging = "clean (all 3 merge-trees)" },
  { pr = 129364, author = "thanosapollo", head = "e9ea24219b", state = "OPEN, MERGEABLE", file_overlap = "cli-config.yaml.example, context-compression-and-caching.md (gpt-6.1-sol native compaction)", merge_with_staging = "clean (all 3 merge-trees)" },
]
competitors = []
close_after = []
demand = { score = "n/a", source = "critic.md missing_features #1; judges maintainer-fit 6 / evidence 3 / impact 6" }
maintainer_signal = "teknium1 authored #526 and wrote on #528 (2026-03-10): 'this is definitely a feature we want to support', pending a native Anthropic transport"
fork_threads = ["kvnloo/hermes-agent#322 (factory thread, open)", "kvnloo/hermes-agent#404 (staged-PR queue, open, 39 rows)"]

[[members]]
ref = "staging/anthropic-context-editing-v2"
sha = "24cc2cc8699dd5b4792264728ea484daeac82356"
role = "own leaf: first slice (gate + wire + recovery + config + 2 contract tests, the first parametrised over 6 eligibility cases + docs incl. the computer-use doc fix)"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
rebase_status = "parent 44a1ce9724 (61effa4dd8 cherry-picked clean: none of the 23 commits since e8c97320ac touch the branch's files), then amended, wording only: the 'local compressor stays armed as the fallback' claim now says local compression keys on the provider-reported (post-clear) size and fires later, in the commit message, the module docstring, the config_defaults comment, cli-config.yaml.example and the docs row. Code and tests unchanged (test blob fc48d77dbb). Then (round 5, polish) staging/anthropic-context-editing-v2 = git commit-tree of the same tree and parent with one corrected sentence in the message (#1147: 'OAuth token and header plumbing', not 'beta-header plumbing'); author and author date preserved"
supersedes = [
  "05d6dbc172d24db4b237f8ef130fb4dc2e8651df (parent 44a1ce9724, same tree as v2): still at refs/heads/staging/anthropic-context-editing (not rewritten); its patch is kept as superseded/anthropic-context-editing-v4.patch (sha256 fc7908647b...)",
  "v3 61effa4dd8a0b81c8eda50a6119239b2aa19e52a (parent e8c97320ac): kept at refs/xf/superseded/anthropic-context-editing-v3 and superseded/anthropic-context-editing-v3.patch",
  "v2 b83e778103d36c48c7736bae07c01658dfb97158 (parent aea969677c): kept at refs/xf/superseded/anthropic-context-editing-v2 and superseded/anthropic-context-editing-v2.patch",
  "v1 1ecde98a7164827a1b8005d9be0443f9310901ce (parent 572e4f4fad): kept at refs/xf/superseded/anthropic-context-editing-v1 and superseded/anthropic-context-editing-v1.patch (regenerated from the commit)",
]
version_policy = "FACTORY §10 asks for staging/<id>-v2, -v3 rather than rewriting the branch; the orchestrator told each fix round to force the local branch instead. Nothing is deleted: every earlier head stays reachable under refs/xf/superseded/ and its patch is kept under superseded/. Round 5 follows §10: the message fix is the new ref staging/anthropic-context-editing-v2 (built with commit-tree), and staging/anthropic-context-editing stays at 05d6dbc172."

[ownership]
searched_at = "2026-10-01T16:40Z"
queries = ["context_management", "context_management anthropic", "clear_tool_uses", "clear_tool_uses_20250919", "context editing", "context-management-2025-06-27", "context-management", "clear_thinking", "clear_thinking_20251015", "anthropic_context_editing"]
recheck = { at = "2026-10-01T18:35Z", queries = ["clear_tool_uses", "context_management anthropic", "anthropic_context_editing", "context-management-2025-06-27", "clear_thinking_20251015", "context_management"], state = "open", result = "unchanged since 16:1xZ: 0, 0, 0, 0, [71302], and the same 8 open PRs for the bare context_management (71302, 80950, 87303, 99447, 103070, 106321, 128432, 129364); no new related PR" }
queries_note = "round 3 added the bare 'context_management', the two dated edit types and 'context-management'; the bare query and 'clear_thinking_20251015' find #71302, which the round-1/2 query set missed"
open_external = []          # no open PR implements clear_tool_uses or the opt-in on the Anthropic path
related_open = [71302]      # same request field and beta on OAuth (clear_thinking); related, not the owner
merged_overlap = [1147]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
verdict = "OURS (no open implementation of clear_tool_uses or of an opt-in; maintainer-authored issue). #71302 writes the same field on OAuth for a different claim; recorded as an interaction (P12), not an owner"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
specs = { path = "specs/PREREG.json", sha256 = "02b22505a4422c7bc8c5388c474ab1366f9bb0cf97694ddbcaa741e0cf375323", recorded_at = "2026-10-01T16:28:00Z", note = "rev-4 specs hashed before run r20261001-04 started (16:28:09Z); G-guards rev 4 is the full runnable F14 set; not on claude/ledger" }
receipts = [
  { id = "P-redgreen/r20261001-04", path = "receipts/P-redgreen-r20261001-04.json", sha256 = "31895f8e1808384ea9aa363ab23ce5f393f893d92fd38f6baf8b010db316d966" },
  { id = "F09/r20261001-04", path = "receipts/F09-r20261001-04.json", sha256 = "634594dc1a8780e284fd96dac4f263e9564603c81c6853548bdad7c98f0ade2d" },
  { id = "G-guards/r20261001-04", path = "receipts/G-guards-r20261001-04.json", sha256 = "adcbed9417b3f66e026ae934bb91003aa15155144572afbe4f310b20893c32d2" },
  { id = "MERGE/r20261001-04", path = "receipts/MERGE-r20261001-04.json", sha256 = "94f64b77aeb494b86edb623cf7bbe794b2cb86474c0906250e74ef0314b60d28" },
  { id = "F14/r20261001-01", path = "receipts/F14-r20261001-01.json", sha256 = "d8c9b5352579a269c6a5aeb2c541b28b188ca53e26253896a459939b090f74b5", prev_sha256 = "4cb29671e674e15bc18f682f2a2cd61a796826b7b21530fef651fb38d623847c", note = "round 6: changed_files corrected (the compression doc is website/docs/developer-guide/context-compression-and-caching.md; the old user-guide path does not exist at 34f8ec3b40), recorded in the receipt's corrections field; no verdict, count or map changed; not frozen" },
]
superseded_receipts = "Everything under superseded/ is excluded from any public freeze (P8): it is history, not evidence. r20261001-03 (head 61effa4dd8 on e8c97320ac): receipts, raw, harness, specs, STAGING.md and PR_BODY.md archived under superseded/r20261001-03/; its receipt hashes still match the values its STAGING.md records; that STAGING.md had one sentence naming the local host, redacted in round 3 (sha256 a931003fa7... -> 79519a15fb...). r20261001-02 (head b83e778103 on aea969677c): kept under superseded/r20261001-02/; round 3 replaced the local host name with '<local-host>' in its 3 receipts and its write_receipts.py, so the hashes its STAGING.md records no longer match. New sha256: P-redgreen 92086d3f38..., F09 8d4470d13a..., G-guards 42c959be74..., write_receipts.py 613a108e2e.... r20261001-01 (head 1ecde98a71) receipts were removed in round 1 before any freeze, because they carried local absolute paths."
patch = { path = "anthropic-context-editing.patch", sha256 = "3e973c079066da0fa0f7608ad43b5ed4b1c0aa1fe4ca48fa79f390c9ef272d2e", regen = "git -C <h.git> -c core.abbrev=10 format-patch -1 --stdout staging/anthropic-context-editing-v2 (core.abbrev pinned: the default auto length grows with the shared object store and changes the index lines)", note = "regenerated from v2 in round 5; it differs from the 05d6dbc172 patch (superseded/anthropic-context-editing-v4.patch, sha256 fc7908647b82e263732ab04e83a0f513c89b0db8340b9014b8497bf2856eb1c7) only in the From line and 3 message lines" }
red = { test = "tests/agent/test_anthropic_context_editing.py", main = "44a1ce9724", marker = "assert 'context-management-2025-06-27' in [...] / assert [False, False] == [True, False, False]", observed = "2 of 7 cases fail on main (the 2 flag-on cases); the 5 cases that expect no field pass on both arms by design", receipt = "P-redgreen/r20261001-04" }
green = { reps = "3 of 3 reps pass (7 of 7 cases each)", receipt = "P-redgreen/r20261001-04" }
negative_control = { mutation = "one hunk at a time: 14 reverts (added line or condition deleted) + 2 value mutations (config parse forced False, trigger = local trigger + 1)", result = "14 of 16 re-RED, incl. each of the 5 gate conditions removed on its own (flag, compression.enabled, checkpoint_required, Claude model, third-party endpoint); unpinned: tui-hot-reload, gateway-cache-key", adjacent_rows = "fast-mode beta removal fails test_fast_command (1 of 17 fail; pinned); codex row removal fails nothing in test_native_compaction (64 of 64 pass; unpinned on main too)", receipt = "P-redgreen/r20261001-04" }
adjacent = { identical = true, files = 15, base = "518 of 518 pass", head = "518 of 518 pass", pre_existing = [] }
guards = { F14 = "EQUAL: Wave 0 pinned set rev 1 (set sha256 aba79fe8f09d...), main 34f8ec3b40 + this commit cherry-picked clean (arm da974f840c, same patch-id), 2 runs, each equal to the main baseline on all 40 verdict ids (verdict, marker, fingerprint); 36 PASS / 4 FAIL on both arms, the 4 FAILs pre-existing on main; flaky none", F14_receipt = "F14/r20261001-01", g_guards_rev4 = "superseded for P5 by F14/r20261001-01; kept as history: run r20261001-04, base 44a1ce9724 vs head 05d6dbc172, equal verdicts on all 22 items it ran (22 of 24). Its judges are weaker than F14's for two hand-run review probes: context_cap counted as PASS only because it finished (rc 0 and its 'DONE arm' line), and goal_scope only on rc 0. context_cap only prints values for a reviewer and has no verdict of its own; the F14 pinned judge (child trigger 200,000, the #103513 cap) fails it on both arms on 34f8ec3b40, and the child cap was already off by default on 44a1ce9724 (tools/delegate_tool.py:139, config_defaults delegation.compression_threshold_tokens = 0; read from the code, not re-judged), so the rev-4 PASS was not a cap check. goal_scope passes F14's pinned judge", replay_gates = "G-guards rev 4 history (44a1ce9724 vs 05d6dbc172): 11 of 11 pass on both arms, maps equal. F14 on 34f8ec3b40 agrees (11 of 11 PASS on both)", postmortem_runner = "G-guards rev 4 history (44a1ce9724 vs 05d6dbc172, python -m evals.postmortem.run): 6 of 9 pass on both arms; the same 3 fail on both (pre-existing on main: subagent_context_cap, notice_delivery_probe, cache_estimator_probe). F14 runs that runner's 5 review_probes one by one and excludes its 4 live_ab probes at set level (the sandbox denylists live_ab/*)", not_run = ["G-guards rev 4 only: postmortem/goal_repaste_probe (needs a copy of a real session state.db; the Wave 0 F14 set excludes it at set level)", "G-guards rev 4 only: readtool fixtures (now run by F14/r20261001-01 as 9 direct read_file cases)"], receipt = "G-guards/r20261001-04" }
quantitative = []
cache_read_ratio = { status = "NOT_MEASURED", needs = "F10 (paid, OD-3)" }
route_scope = "native Anthropic API, Claude models; local compressor code unchanged (it fires later after a real clear; untested)"
not_tested = ["real Anthropic API acceptance and real rejection wording", "cache_read/cache_creation per turn around a clear (F10)", "OAuth subscription route", "interaction with #71302 if both land (two writers of context_management on OAuth + thinking, duplicate beta)", "server behaviour when the full uncleared history is resent each turn", "local fallback after a real server-side clear (local compression decides on the provider-reported prompt size, which is the post-clear size, so it fires later while the resent transcript and request body grow; F09's fake reports 60K whether or not the payload is sent)", "skill_view results cleared server-side without the local ghost-skill reload marker", "compaction-exam recall with clears", "the codex_responses row of the generalised recovery table (no test reaches that step on main)", "the Wave 0 F14 set's set-level exclusions (live/paid probes, goal_repaste_probe which needs a private state.db copy, the sandbox-denylisted live_ab probes, the readtool model arm)"]
resource_usage = { wall_s = 628.0, cpu_core_s = 606.9, api_cost_usd = 0.0, source = "raw/run_meta.json (merge checks add under 1 s)" }
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-anthropic-context-editing", commit = "" }

[gates]
P1 = "PASS"       # RED on 44a1ce9724 (16:28Z); main is now 34f8ec3b40, 9 commits later, none touching an invalidate_on path or a branch file (checked 18:35Z), so that RED SHA still qualifies; re-run RED within 24 h of queueing
P2 = "PASS"       # no open or merged implementation; #71302 recorded as related (same field/beta on OAuth), not an owner
P3 = "PASS"
P4 = "PASS"
P5 = "PASS"       # F14 EQUAL (F14/r20261001-01, 2 runs on main 34f8ec3b40 + this commit); RED marker matched, GREEN 3/3, sabotage 14/16 with unpinned hunks listed, adjacent identical, flaky false (P-redgreen/r20261001-04, on 44a1ce9724; the 9 main commits since share no file with the branch)
P6 = "PENDING"    # caching-adjacent: needs OBSERVED cache-read before/after (F10) -> LIMITED until then
P7 = "PASS"       # local: one commit (v2 24cc2cc869) on 44a1ce9724, merge-tree clean on current main 34f8ec3b40 (9 commits ahead, no shared or invalidate_on files), 0 workflow files; not pushed yet (fork name staged/<id>)
P8 = "PENDING"
P9 = "PENDING"    # body drafted; cache section waits on F10; tone gate by a second reader
P10 = "PENDING"   # no blind verifier on the promotion head 24cc2cc869 yet (same tree as 05d6dbc172)
P11 = "RECORDED"
P12 = "PENDING"   # preserved-thinking carriers (#103476, #129620, #129492, #129882) must settle first, and the #71302 interaction must be resolved by whichever lands second; OD-0 resolved

[verification]
verifier = ""
provenance = "independent"
exact_head = "24cc2cc8699dd5b4792264728ea484daeac82356"   # promotion head; same tree and parent as 05d6dbc172
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "34f8ec3b407e50bad3ae27e4cd79d65212061356"
head = "24cc2cc8699dd5b4792264728ea484daeac82356"
checked_at = "2026-10-01T18:35Z"
clean = true
tree = "44e3f84714dfc14abc7e991e0012f1add6625c1f"
recheck = "git -C <h.git> merge-tree --write-tree main staging/anthropic-context-editing-v2"
note = "same tree for 05d6dbc172 (identical tree and parent) and for the F14 arm da974f840c. Previous check: main 44a1ce9724 at 16:40Z, clean, tree 2c45d3cd53 (main was the parent)"

[push]
fork_ref = "staged/anthropic-context-editing"
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = false, no_labor = false, no_internal_leak = false, smallest_ask = false, self_service = false, local_voice = false, easy_decline = false }
jargon_lint = "CLEAN (round 6, 2026-10-01T19:15Z, after the eval-probe paragraph rewrite): 0 hits in PR_BODY.md and the v2 commit message for P-gate, OD, xf, F##, E##, envelope, lane, receipt, @mention, fork-ref (staged/, kvnloo, fork), placeholder, absolute-path, factory words (wave, G-guards, factory, staging, manifest), host name, or upstream refs not written #N. Previous: CLEAN in round 5 (18:40Z)"
privacy_scan = "CLEAN (round 6, 2026-10-01T19:15Z): STAGING.md, PR_BODY.md, both patches, receipts/, raw/, harness/ and specs/ (29 files): no absolute local paths, no host name, no secrets, no user email, no bytecode. The pattern hits are all benign: the '<run>/home' placeholder in the F14 receipt, the fake test key 'sk-ant-api03-fake-key' (the test file in both patches, harness/f09_gate_probe.py, and this note), the upstream HERMES_HOME default (tilde form) quoted in the F10 command comment, and the tmp-path redaction regex in harness/f14_guards.py"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after the existing 39 rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/anthropic-context-editing

**Promotion form:** core-pr (route core-leaf). **Status:** STAGED. The best class reachable at $0 is LIMITED: the change is caching-adjacent, so the PR body has to carry an OBSERVED cache-read before/after, and that needs the paid F10 run. P5 is now PASS: the Wave 0 F14 run (F14/r20261001-01, main 34f8ec3b40 with this commit cherry-picked) is EQUAL to the main baseline, and the other P5 parts were already recorded as met. Round 3 did not change the form: #71302 is a related open PR, not an owner, and nothing showed a reason to hold. Round 5 (polish) changed only text: the commit message (as the new ref `staging/anthropic-context-editing-v2`, same tree), PR_BODY.md and this manifest. Round 6 changed only PR_BODY.md (the eval-probe results now come from F14/r20261001-01), one field of the F14 receipt and this manifest; the v2 ref is unchanged.

**Branch.** The promotion head is the local ref `staging/anthropic-context-editing-v2` at `24cc2cc869` in the scratch h.git, one commit on `44a1ce9724` (now 9 commits behind main `34f8ec3b40`, none touching the branch's files; merge-tree clean). It has the same tree (`2c45d3cd53`), parent, author and patch-id as `05d6dbc172`, which stays at `staging/anthropic-context-editing`; only the commit message differs, so every receipt below carries over. On the fork it will be pushed as `staged/anthropic-context-editing`, because the fork still has a legacy branch named `staging`, which blocks `staging/<id>`. That rename resolves OD-0 for this item. Nothing has been pushed. Earlier heads stay reachable: `61effa4dd8` at `refs/xf/superseded/anthropic-context-editing-v3`, `b83e778103` at `-v2` and `1ecde98a71` at `-v1`. Their patches are in `superseded/`.

**Links.** Upstream: NousResearch/hermes-agent#526 (the feature spec, teknium1), NousResearch/hermes-agent#525 (related /microcompact), NousResearch/hermes-agent#1147 (merged; despite its title, OAuth token and header plumbing only), NousResearch/hermes-agent#528 (closed prior attempt), NousResearch/hermes-agent#71302 (open, related: writes the same field on OAuth), NousResearch/hermes-agent#103476, NousResearch/hermes-agent#129620, NousResearch/hermes-agent#129492, NousResearch/hermes-agent#129882 (the preserved-thinking replay PRs this waits on). Fork: kvnloo/hermes-agent#322 (factory thread), kvnloo/hermes-agent#404 (staged-PR queue, 39 rows). No fork thread exists for this feature yet.

## Invariant

With `compression.anthropic_context_editing: true`, main-turn requests for Claude models on the native Anthropic API carry `context_management.edits = [clear_tool_uses_20250919]` and the `context-management-2025-06-27` beta. The exceptions are when compression is disabled or `checkpoint_required` is set. The trigger sits below the local compression trigger. Every other request is unchanged. A structured 400 that names `context_management` disables the feature for the session and retries once.

Call path exercised: `AIAgent.run_conversation` → `turn_api_request.build_api_request` → `chat_completion_helpers._build_api_kwargs_for_mode` (the `anthropic_messages` branch) → `_build_anthropic_kwargs` → `anthropic_context_editing.anthropic_context_management` (the gate) → `AnthropicTransport.build_kwargs` → `anthropic_adapter.build_anthropic_kwargs` (`extra_body` and the per-request beta header) → SDK `messages.stream` over TLS to `api.anthropic.com`. The test intercepts that host with a throwaway CA and serves it from the SDK-oracle fake. The third-party case points the agent at the fake's loopback `/anthropic` URL instead. On a 400: `turn_recovery._recover_format_errors` → `is_native_compaction_rejection` → flag off → the next attempt is rebuilt without the field.

## Route and carrier choice

**Route: core-leaf, our own single commit.** There is no carrier to salvage and no competitor to support:

- No open PR implements `clear_tool_uses`, or an opt-in for context editing, on the Anthropic path. One open PR does write the same request field: **#71302** (TrueNix, OPEN, CONFLICTING, head `e709540872`). Its claim is OAuth request parity with the Claude Agent SDK. As part of that, on OAuth requests with thinking it sets `extra_body["context_management"] = {"edits": [{"type": "clear_thinking_20251015", "keep": "all"}]}`, and it adds `context-management-2025-06-27` to `_OAUTH_ONLY_BETAS`. That makes it related, not the owner: it never sends `clear_tool_uses`, has no opt-in and no fallback. Rounds 1 and 2 missed it, because their six queries never searched the bare `context_management` or the dated `clear_thinking_20251015` type. The interaction is recorded under P12 and in the PR body's `clear_thinking` question.
- #1147 (merged) is titled "feat: add Anthropic Context Editing API support", but its merged diff only separated Anthropic OAuth tokens from API keys (token resolution order, setup, status, and the doctor check's OAuth headers). It sends no `context_management`.
- #528 (aydnOktay) was closed unmerged as superseded by #1147. On 2026-03-10 teknium1 wrote "We're going to leave this PR open" until Hermes had a native Anthropic transport. He then closed it without comment on 2026-03-13T14:38Z, the day #1147 merged; #1147's body says "Refs #526, supersedes #528". #1147's merged diff only changed OAuth token and header plumbing (the 2026-06-29 triage note on #526 says "beta-header / OAuth plumbing"). teknium1 said the feature was wanted once a native Anthropic transport existed, and it now does. No code from #528 is reused, so no Co-authored-by trailer is added; the PR body credits it as prior art.
- #526 is authored by teknium1, and on #528 he called the feature "definitely a feature we want to support". So a support-note or salvage row would have nothing to attach to.

**What #71302 means if both land.** Both PRs write `extra_body["context_management"]` in `build_anthropic_kwargs`. #71302's block runs after ours, at the end of the function. On OAuth requests with thinking and this flag on, its write would replace our `clear_tool_uses` edit. The beta would also appear twice in the header: we append `_CONTEXT_MANAGEMENT_BETA` to `common + _OAUTH_ONLY_BETAS`, and `_beta_header` does not dedupe. Whichever PR lands second has to build one `edits` list, with `clear_thinking_20251015` first (the API requires that order when both edits are sent), and add the beta once. This branch does not pre-empt that, because #71302 is not on main and conflicts with it (main × #71302 conflicts in `agent/anthropic_adapter.py` and its test). #71302 × branch conflicts in the same two files; the test conflicts only because the PR is behind main.

**Why core-pr and not decision-request (for now).** FACTORY §11.4 lists this item as "LIMITED → decision-request". The slice is complete and proven at $0, but P6 needs OBSERVED cache-read numbers (F10, paid, OD-3). If the owner does not fund F10, the fallback is to post the PR body's design and open questions on #526 as a decision request instead of opening the PR. The promotion form stays core-pr until that decision is made.

**The preserved-thinking PRs are ordering dependencies, not carriers.** #103476, #129620, #129492 and #129882 change Anthropic thinking replay, not context editing. The branch waits for them only so that `clear_thinking` and replay interactions are settled before a reviewer sees this PR (P12). Only #129620 shares a file with the branch (`agent/turn_recovery.py`), and that file auto-merges.

WAVE.md row form (own leaf, no carrier):

> | #526 (clear_tool_uses half) | own leaf `24cc2cc8` (kvnloo; message-only successor of `05d6dbc1`, same tree) on `44a1ce97`, merge-tree clean on main `34f8ec3b` | main: 2 of 7 cases fail (beta missing; `[False, False]` vs `[True, False, False]`); head: 7 of 7 pass (3 of 3 reps); F09 head: payload on 1 of 6 gate cells (the eligible one), base on 0 of 6 | none (whole slice is ours) | no open implementation; #71302 (open) writes the same field on OAuth (clear_thinking), interaction noted; #528 closed as superseded by #1147, #1147 OAuth/header plumbing only | sabotage: 14 of 16 hunks re-RED, incl. each of the 5 gate conditions (2 sibling config hunks unpinned); 15 adjacent files 518 of 518 pass on both arms; F14 (Wave 0 set, main 34f8ec3b) equal to the main baseline on all 40 verdict ids in 2 of 2 runs |

## Premise re-check (current main)

- **Still needed.** At 44a1ce9724, `git grep` finds no `clear_tool_uses` in any Python file and no `context_management` on the Anthropic path. The only `context_management` code is for Responses native compaction (`agent/native_compaction.py`, `agent/chat_completion_helpers.py::_build_codex_kwargs`, `agent/codex_responses_adapter.py`, `agent/transports/codex.py`, `agent/turn_recovery.py`), plus a comment in `agent/auxiliary_client.py`. None of the 23 commits between e8c97320ac and 44a1ce9724 touches the branch's files, and none of the 9 commits between 44a1ce9724 and 34f8ec3b40 does either (checked 18:35Z).
- **A doc already claims the feature exists.** `website/docs/user-guide/features/computer-use.md:408-410` says "Server-side context editing (Anthropic only) — when active, the adapter enables `clear_tool_uses_20250919` via `context_management`". That is false on main; the 2026-06-29 triage comment on #526 notes the feature exists "only in website docs". The commit rewrites that bullet to say it is opt-in and names `compression.anthropic_context_editing` (+3/−2 lines). The zh-Hans mirror (`website/i18n/zh-Hans/.../computer-use.md:105`) has the same sentence. It is left unchanged, because that page already lags the English one elsewhere in the same section (it still describes the old 3-screenshot eviction and macOS-only support). The PR body says so.
- **No competing implementation; one related PR.** Open-PR searches at 16:1xZ: the bare `context_management` returns 8 open PRs. Of those, only #71302 touches the Anthropic path. The others are Responses or xAI native compaction, DeepSeek web search and replay trimming: #128432, #99447, #103070, #106321, #129364, #80950, #87303. `clear_thinking_20251015` returns #71302 only. `context_management anthropic`, `clear_tool_uses`, `clear_tool_uses_20250919`, `context-management-2025-06-27` and `anthropic_context_editing` return no open PR. `context editing` and `clear_thinking` return only unrelated hits (#75327, #84278, #105910, #130374, #73370, #92485). `context-management` returns at least 40 broad matches (the query limit) (dashboard, skills, gateway, memory). Judging by title, none implements Anthropic context editing; the compaction-related ones are local or Responses compaction (#12693, #9597, #30901, #94102, #98858, plus the native-compaction PRs above). All-state searches at 16:40Z add only #1147 (merged), #528 (closed), #6318 (closed, tool_search), #3816 and #14817 (closed, computer use) and #17169 (closed issue, 429s), plus the open issue #526. The open related issues #525 and #29300 are named in the triage comment. GitHub's secondary rate limit cut off the last two all-state queries (`anthropic_context_editing`, `context editing anthropic`); their open-state runs at 16:1xZ found nothing.
- **History.** #528 (aydnOktay) was kept open by teknium1 on 2026-03-10, pending a native Anthropic transport. It was closed without comment on 2026-03-13 as superseded by #1147, which merged that day; its diff only changed OAuth token and header plumbing. #526 itself was never closed: a bot comment on 2026-06-04 called it "resolved by merged PR(s): #1147" without closing it, another user questioned that, and the 2026-06-29 triage comment reopened the discussion and kept #526 open as the canonical spec. The native transport now exists.
- **Correction carried into the body.** #526's "without destroying prompt cache prefixes" is not supported. Anthropic's context-editing docs say tool-result clearing invalidates the cached prefix when content is cleared, and that each clear incurs a cache write. The body says this plainly.

## Design choices in the slice

- **Gate.** The gate mirrors `native_compaction_context_management`. It is re-checked per request and requires the flag on, `compression.enabled` true, `checkpoint_required` not set, a Claude model, and a native Anthropic base URL. Bedrock, Azure, Portal, MiniMax, Kimi and proxies all count as third-party under `_is_third_party_anthropic_endpoint`. The gate is called only from the `anthropic_messages` branch of `_build_api_kwargs_for_mode`. So round 2 dropped its `api_mode` check: no request could reach it, so no test could pin it. Native compaction's gate likewise leaves the api_mode choice to its caller.
- **Payload.** Only `clear_tool_uses_20250919`. `trigger` = `resolve_compact_threshold(None, local_trigger)`, which is the local trigger minus 8,192 (reused from native compaction). `clear_at_least` = 20% of the trigger. `keep`, `exclude_tools` and `clear_tool_inputs` are left at server defaults. `clear_thinking_20251015` is not sent (#103476 interaction, and #71302 sends it on OAuth).
- **Beta header.** Added only when a payload is sent. It reuses the fast-mode rebuild of the per-request beta list, so fast mode alone produces a byte-identical header.
- **Recovery.** The existing native-compaction rung is generalised to an api_mode → flag table. The codex message and log text are unchanged.
- **Local compression.** Unchanged code. It decides on the provider-reported prompt size (the usage anchor). That anchor feeds the turn-start check in `agent/turn_context_compaction.py`, and the pre-request and after-tool checks in `agent/turn_preflight.py`. After a real server-side clear, it therefore fires later than it would without the clear. Round 3 made the commit message, the module docstring, the config_defaults comment, `cli-config.yaml.example` and the docs row say so, instead of "stays armed as the fallback". One shipped comment still has the old framing: `tests/agent/test_anthropic_context_editing.py:75` says "the local compressor stays the fallback at its own trigger". Changing it changes the tree, so round 5 left it; align it on the next amend (next step 8).
- **Config propagation.** `config_defaults` (default false), `agent_init`, the gateway agent-cache key, TUI hot reload, `cli-config.yaml.example`, one docs row in the compression guide, and the corrected computer-use bullet.
- **Contract test.** Two tests. The first is parametrised over six cases: off, on, and on with compression disabled, `checkpoint_required`, a non-Claude model (`glm-4.6` on the native URL, as in F09) or a third-party endpoint (the fake's loopback URL). The second is the structured-400 retry.

Footprint: 13 files, +201/−15 lines, including a 52-line module and a 91-line test file.

## Evidence

All rows except "F14 (Wave 0 set)" are run r20261001-04: base 44a1ce9724 (tree 6a18f0eebd), head 05d6dbc172 (tree 2c45d3cd53). The promotion head 24cc2cc869 has that same tree and parent (message-only change), so every row applies to it unchanged. The F14 row is run F14/r20261001-01 on main 34f8ec3b40 with the branch commit cherry-picked (arm da974f840c, tree 44e3f84714). Specs (rev 4) were pre-registered by hash at 16:28:00Z, before the run started at 16:28:09Z. Isolated HOME/HERMES_HOME throughout; every F14 probe got its own fresh home. Whole run: 628 s wall, 607 CPU-s, $0.

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| RED on base | receipts/P-redgreen-r20261001-04.json | PASS | OBSERVED | 7 cases | 2 of 7 fail on 44a1ce9724 (beta missing; `[False, False] != [True, False, False]`). The 5 cases that expect no field pass on both arms by design |
| GREEN | same | PASS | OBSERVED | 3 reps | 7 of 7 pass in each of 3 reps |
| Sabotage, one hunk at a time | same + raw/sabotage.json | PASS | OBSERVED | 16 hunks + 2 adjacent rows | 14 of 16 re-RED. 14 are reverts (added line or condition deleted), including each gate condition removed on its own: flag, `compression.enabled`, `checkpoint_required`, Claude model, third-party endpoint. 2 are value mutations: config parse forced `False`, trigger = local trigger + 1. Unpinned: TUI hot reload, gateway cache key (sibling config paths). Adjacent rows: removing the fast-mode beta append makes 1 of 17 `test_fast_command` tests fail; removing the codex row of the recovery table leaves all 64 `test_native_compaction` tests passing, and no test on main reaches that step. Not mutated: config default entry, cli-config example, the 2 docs pages, the adapter constant/signature/docstring, the `clear_at_least` fraction value (bounded only), and the recovery display/log text |
| Adjacent | same | PASS | OBSERVED | 15 files | 518 of 518 pass on base, 518 of 518 on head |
| F09 gate probe | receipts/F09-r20261001-04.json | KEEP | OBSERVED | 10 cells × 2 arms | Head: payload on the eligible cell only (1 of 6 gate cells), 0 of 5 ineligible cells (flag false, compression off, checkpoint_required, non-Claude, third-party endpoint). Base: 0 of 6. 400 path: head `[True, False, False]`, base `[False, False]`. Local compressor over threshold (60K reported vs 50K): 1 compression on turn 2 in both arms, flag on and off. The fake reports 60K whether or not the payload is sent, so this does not model the post-clear regime. Head trigger 41,808 < 50,000. Flag-absent wire, base vs head: bodies (minus system) and headers IDENTICAL, and the system prompts are identical after host normalisation (temp HOME path, host/kernel line and python version replaced by placeholders; only the hash is stored). SDK schema errors 0. Egress blocked 0 |
| Guards: G-guards rev 4 (history; superseded for P5 by the F14 row) | receipts/G-guards-r20261001-04.json | EQUAL (partial) | OBSERVED | 22 of 24 F14 items × 2 arms | History from run r20261001-04 (base 44a1ce9724 vs head 05d6dbc172), judged with rev 4's own criteria. Judge difference: rev 4 counted context_cap as PASS only because it finished (rc 0 and its "DONE arm" line). That probe only prints values for a reviewer; the F14 pinned judge (child trigger 200,000, the #103513 cap) fails it on both arms on 34f8ec3b40, and the child cap was already off by default on 44a1ce9724 (read from the code, not re-judged), so the rev-4 PASS below is not a cap check. Every probe that ran has the same verdict on both arms: replay_gates (11 of 11 gates pass on both, maps equal), ab_image_cost_calibration, worktree_prompt_prefix, ab_checkpoint_preflight (capture/restore/over-threshold scenarios equal), probe_104120/104260/104360, goal_command_parity, compaction/test_region_scoping (run as the script it is; FACTORY's run_tests.sh form collects 0 tests), the postmortem runner's 9 non-live probes, and 4 of the 5 hand-run review probes (context_cap, deadline, goal_scope, finalizer_schedule). Under rev 4's criteria 19 of the 22 pass on both arms (context_cap's PASS being completion-only, see above). The same 3 postmortem probes fail on both (subagent_context_cap, notice_delivery_probe, cache_estimator_probe): pre-existing on main. The first two lag the code they probe; cache_estimator_probe checks the fix in #103476, which is still open (corrected in round 5). Normalised output differs on 6 probes, each explained in the receipt (temp names, timings, pids, timestamps, and the run-time fixture commit SHA inside one prompt hash). Not run: goal_repaste_probe (it reads RF_STATE_COPY, a copy of a real session state.db, which this run may not touch) and "readtool fixtures via direct read_file only" (F14 names no command). Superseded for P5 by the F14 (Wave 0 set) row below |
| F14 (Wave 0 set) | receipts/F14-r20261001-01.json | EQUAL | OBSERVED | 40 verdict ids × 2 runs vs the main baseline | Pinned set rev 1 (set sha256 `aba79fe8f09d...`, 19 probes, 40 verdict ids), runner `2323a59184...`, sandbox `c9586195c4...`, readtool helper `0df21aee5f...`, all the same as the baseline's. Arm: main 34f8ec3b40 + 05d6dbc172 cherry-picked clean (da974f840c at `refs/xf/w0/anthropic-context-editing`, same stable patch-id `352f5b8a44`). r1 and r2 each compare EQUAL to the baseline map (main 34f8ec3b40, base-r2) on every id: verdict, marker and fingerprint; r1 vs r2 also EQUAL. 36 PASS / 4 FAIL on both arms; the 4 FAILs are the baseline's own (cache_estimator_probe, notice_delivery_probe, context_cap_probe, readtool lying_extension), with identical markers. 0 blocked execs, 0 sandbox refusals, worktree clean after both runs, no id marked flaky. This set runs the readtool fixtures (9 direct read_file cases); goal_repaste_probe and the live/paid probes are excluded at set level, for every item alike. Wall 129.2 s and 82.2 s (other workers ran concurrently), $0 |
| Merge checks | receipts/MERGE-r20261001-04.json | CLEAN | OBSERVED | 20 merge-trees | Branch × main 44a1ce9724 clean (1). #103476, #129620, #129492: main × PR, main + PR × branch and PR × branch all clean (3 each). #129882: main × PR and PR × branch both conflict in `cron/lifecycle_guard.py`, no file overlap with the branch (2). #71302 (related): main × PR and PR × branch both conflict in `agent/anthropic_adapter.py` and its test (2). Neighbours #128432 and #129364: all clean (3 each) |
| F10 cache arm | not run | — | NOT_MEASURED | — | queued (paid) |

Example payload (OBSERVED, head, local trigger 150,000 for a 200K window): `{"edits":[{"type":"clear_tool_uses_20250919","trigger":{"type":"input_tokens","value":141808},"clear_at_least":{"type":"input_tokens","value":28361}}]}`.

Receipt format: all four receipts carry the `xf.receipt.v1` fields from FACTORY §9.2. That covers spec (path, rev, sha256, decision_rule_sha; `prereg_commit` is null because xf/claude-ledger does not exist yet), runner_revision, policy_revision, changed_files, denominators, evidence_class, resource_usage, frozen (`NOT_FROZEN`, P8) and privacy (`public-aggregate`). They contain no absolute local paths and no host name. Commands use the placeholders `<worktree>`, `<testhome>`, `<venv-python>`, `<private>` and `<h.git>`. `env.host` is `<local-host>`. `harness/f14_guards.py` keeps full probe output in a private scratch directory outside the artifact tree, and publishes only a placeholder-only summary (`raw/f14_<arm>.json`). It refuses to write the summary if an absolute path is left in it. A stray `harness/__pycache__/` (bytecode that embedded the local harness path) was deleted in round 3; the harness now runs with `-B`.

## Experiments queued (exact commands, not run)

**F10. T3, paid, OD-3; the owner launches it with the owner's key.** Measures `cache_read` and `cache_creation` per turn before and after a clear, flag on and off, in ABBA order. It runs the upstream probe unmodified from the staging checkout; the probe records usage per call and classifies consecutive pairs as ideal/stuck/collapse. `threshold_tokens: 150000` puts the server trigger at 141,808, which a 10-call read_file loop crosses (≈30K tokens per read). After a clear with keep=3, about 100K tokens remain, under the local trigger. In the off arm, local compaction fires at 150K instead. Cost estimate (MODELED): roughly $2–4 per session on claude-opus-5-5, so 8 sessions come to about $16–32. Proposed cap: $35.

```bash
# from a checkout of staging/anthropic-context-editing-v2 @24cc2cc869 (repo root; same tree as 05d6dbc172)
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

**F10-exam. T3, paid; the harness is NOT written.** This arm would run the frozen-lineage compaction exam (evals/compaction) after a long tool session, flag on vs off. `evals/compaction` has no server-side context-editing arm, so a new arm is needed. Queued as a design item, not a command.

**F14 completion: done by the Wave 0 set (F14/r20261001-01).** The Wave 0 F14 set pins a command for the readtool fixtures (9 direct read_file cases), and excludes `goal_repaste_probe` at set level for every item, because it needs `RF_STATE_COPY` pointing at a private state.db copy. A synthetic state.db built from a fixture session would let that probe join the set later; that is a set change, not an item task. The old `harness/f14_guards.py` route is no longer needed for P5.

**T2 (local GPU): N/A.** Context editing is an Anthropic server feature. llama.cpp and ollama cannot emulate it, and the 64K floor (OD-1) blocks local Hermes arms anyway.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| With the flag off, the request is byte-identical to today | met | F09 flag_absent_wire: identical bodies and headers across arms, and identical host-normalised system prompts. The contract test's off case asserts no field and no beta |
| Gate tests RED on main, GREEN with the change | met | P-redgreen: on 44a1ce9724, 2 of 7 fail; on the head, 7 of 7 pass in each of 3 reps |
| Every eligibility condition pinned by the contract test | met | sabotage: each of the 5 gate-condition removals re-REDs (flag, compression.enabled, checkpoint_required, Claude model, third-party endpoint) |
| Negative control | met | sabotage: 14 of 16 hunks re-RED. 2 sibling config hunks unpinned (listed) |
| Structured-400 disable-and-retry proven | met | contract test 2 and F09 (`[True, False, False]`) |
| Local compressor still fires over threshold | partly met | F09 over_threshold cells: 1 compression on turn 2 with the flag on (trigger 41,808 < local 50,000). Not tested: the regime after a real clear, where reported usage drops while the resent transcript grows, so local compression fires later. The shipped text now says this |
| F14 guards equal | met | F14/r20261001-01: Wave 0 set, 2 runs on main 34f8ec3b40 + this commit, each EQUAL to the main baseline on all 40 verdict ids |
| Existing docs no longer claim the feature is always on | met | computer-use.md bullet rewritten in the commit; zh-Hans mirror called out in the body |
| PR body reports measured cache-read before/after and says it is not a savings feature | not met | the "not a savings feature" text is in the body. Cache-read numbers wait on F10 (OD-3) |
| Opened only after the preserved-thinking replay PRs settle | pending | #103476, #129620, #129492, #129882 all OPEN. #103476, #129620, #129492: each merged onto main 44a1ce9724, then merged with the branch: clean (#129620 shares `agent/turn_recovery.py`, no conflict). #129882: no file overlap with the branch; the PR itself conflicts with main in `cron/lifecycle_guard.py` |
| #71302 interaction resolved | pending | #71302 OPEN and CONFLICTING with main. If it lands first, rebase this branch to merge the two `context_management` writers into one edits list (clear_thinking first) and drop the duplicate beta; if this lands first, the same falls to #71302's rebase. Named in the PR body |

## Gate checklist (P1–P12)

- P1 PASS: RED on 44a1ce9724 (P-redgreen/r20261001-04). Upstream main is now 34f8ec3b40, 9 commits later; none of them touches an `invalidate_on` path (union of the three specs' lists) or a branch file (checked 18:35Z), so the RED SHA still qualifies. Re-run RED within 24 h of queueing.
- P2 PASS: no open or merged implementation of `clear_tool_uses` or an opt-in. #71302 is open and related: it writes the same field (clear_thinking) and beta on OAuth for its OAuth-parity claim. It is recorded under [upstream].related_open and [ownership].related_open, and in P12. It is not an owner. Claimant lanes are TUI/HUD.
- P3 PASS: one invariant, a config.yaml key, no env var, no hook. turn_recovery.py goes 1925→1933 lines and stays under 2k. The touched files that were already over 2k lines grow by 0–9 lines each: agent_init 2510→2513 (+3), chat_completion_helpers 4086→4089 (+3), cli-config.yaml.example 2321→2330 (+9), config_defaults 3188→3193 (+5), gateway/run.py 6154→6154 (0). All measured on 44a1ce9724.
- P4 PASS: real turn loop on the native route. Only the HTTP vendor boundary is faked.
- P5 PASS: RED with both markers matched, GREEN 3 of 3, sabotage 14 of 16 with every gate condition pinned (2 sibling config hunks unpinned, listed), adjacent identical, `flaky = false` (P-redgreen/r20261001-04, base 44a1ce9724, head 05d6dbc172). The codex row of the generalised recovery table is also unpinned and listed: no test on main reaches it. F14 guards equal: F14/r20261001-01 ran the Wave 0 pinned set twice on main 34f8ec3b40 with this commit cherry-picked (same patch-id), and both runs are EQUAL to the main baseline on all 40 verdict ids. The 9 main commits between 44a1ce9724 and 34f8ec3b40 share no file with the branch. The earlier G-guards rev 4 run (22 of 24 items) is kept as history.
- P6 PENDING: F10.
- P7 PASS (local): one commit (v2 24cc2cc869) on 44a1ce9724, correct author, `feat(anthropic):`, 0 workflow files touched, merge-tree clean on current main 34f8ec3b40 (tree 44e3f84714). Not re-based in round 5: the 9 newer main commits share no file with the branch. Not pushed; the fork ref will be `staged/anthropic-context-editing`, pushed from v2.
- P8 PENDING: receipts carry the full §9.2 field set and the specs are pre-registered by hash, but nothing is frozen (no write-once bundle, nothing in z0evals). superseded/ is excluded from any public freeze.
- P9 PENDING: body drafted, with an AI disclosure that covers the code, tests, probes and the PR text, and credit for #528 (prior art) and #71302 (related). Jargon lint and privacy scan clean (round 6, after the eval-probe paragraph was rewritten from F14/r20261001-01). The cache section is a placeholder until F10. Tone gate by a second reader.
- P10 PENDING: no blind verifier on the promotion head 24cc2cc869 yet (same tree as 05d6dbc172, so a read of either tree counts for the code, but the message must be read on 24cc2cc869).
- P11 RECORDED: teknium1-authored issue, explicit "we want to support" on #528.
- P12 PENDING: the dependency PRs, the #71302 interaction, and the staging cap. OD-0 is resolved by the `staged/<id>` fork name.

## NOT_TESTED

- **Real Anthropic API:** acceptance of the payload, the real rejection wording, and whether a non-structured failure could occur (the gpt-5.1 lesson from native compaction).
- **Cache behaviour after a clear.** It is also unknown whether the server re-clears on every request, because Hermes resends the full uncleared history (F10).
- **Local fallback after a real clear.** Hermes resends the full uncleared history every turn. Local compression decides on the provider-reported prompt size (the usage anchor; the turn-start, pre-request and after-tool checks all use it). After a server clear, that is the post-clear size. So local compression fires later, while the transcript and the request body keep growing. F09's over-threshold cell does not cover this, because the fake reports 60K whether or not the payload is sent. The commit message, the shipped comments and docs, and the PR body all say this.
- **OAuth / Claude subscription route:** whether the beta is accepted there. A structured 400 would fall back.
- **#71302 together with this branch:** not merged or run together. The overwrite and the duplicate beta are read from the two diffs, not observed.
- **skill_view results:** a server-side clear can drop them without the local compressor's ghost-skill "reload with skill_view" marker. `exclude_tools` is not set; it would also need the OAuth wire-name mapping.
- **Recall:** compaction-exam recall with clears (the F10-exam harness is not written). In the PR body's "Not tested" list.
- **Codex recovery row:** the generalised recovery table keeps the codex row's flag and text, but no test on main reaches that step, and this slice does not add one. The PR body says so.
- **F14:** the Wave 0 set's set-level exclusions: live or paid probes, goal_repaste_probe (needs a private state.db copy), the sandbox-denylisted live_ab probes and the readtool model arm. No F14 probe drives the `anthropic_messages` request path with the flag on, so F14 EQUAL shows no regression in the guarded surfaces, not coverage of the feature (that is the contract test and F09).
- **Test scope:** the full test suite was not run (targeted files only); no Windows or macOS runs. The docs site build was not run (two Markdown edits, no new links).

## Origin action (owner only)

When F10 numbers exist, the dependency PRs settle and the #71302 interaction is resolved: fill the cache section of PR_BODY.md, re-run RED/GREEN and F14 on the newest main, push `staging/anthropic-context-editing-v2` (24cc2cc869) to the fork as `staged/anthropic-context-editing`, then run `gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/anthropic-context-editing --title "feat(anthropic): opt-in server-side context editing (clear_tool_uses)" --body-file PR_BODY.md`. The factory does not run this command. If F10 is not funded, post the body's design and open questions on #526 as a decision request instead.

## Next steps

1. Owner: OD-3 (F10 budget, about $35). OD-0 is resolved by the `staged/<id>` name.
2. Before F10: add the read-only `applied_edits` capture to the probe run (a wrapper only, no core change), and consider one longer on-arm session that logs reported vs local transcript tokens per turn (post-clear fallback regime).
3. F14 is done (F14/r20261001-01, EQUAL; P5 PASS). Re-run it with the Wave 0 runner after any rebase or amend, against the baseline map of the main the arm sits on.
4. A blind verifier reads exact head 24cc2cc869 (P10).
5. Watch #71302. If it lands first, rebase and merge the two `context_management` writers into one edits list (clear_thinking first), with the beta added once, plus a test for OAuth + thinking + flag on.
6. When #103476 and the other preserved-thinking PRs merge: rebase, then re-run the contract tests, F09 and F14 (`harness/run_proofs.py`, then `harness/write_receipts.py`), and `harness/merge_check.py`.
7. Ask on #526 whether `skill_view` should be in `exclude_tools` by default (a follow-up slice), and whether `clear_thinking` is wanted after #103476 and #71302.
8. On the next amend (any rebase that already re-runs the proofs): change the test comment at `tests/agent/test_anthropic_context_editing.py:75` ("the local compressor stays the fallback at its own trigger") to the post-clear wording used elsewhere. Code-tree change, so not done in the round-5 polish.

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
  - **BLOCKING: PR body counted a vacuous pass.** "19 of the 22 pass on both" came from G-guards rev 4, which counted context_cap_probe as PASS only because it finished (rc 0 and "DONE arm"). That probe prints values and has no verdict; its README check ("cap holds through repeated compression") cannot hold because the child cap is off by default, on 44a1ce9724 as on 34f8ec3b40 (checked with git grep: tools/delegate_tool.py:139, config_defaults compression_threshold_tokens = 0). The eval-probe paragraph is rewritten from F14/r20261001-01: main 34f8ec3b40 and this commit on top, 2 runs each in fresh homes, 19 probes / 40 results, 36 pass and 4 fail identically on both, all 4 failing on main already (cache_estimator_probe: fix open in #103476; notice_delivery_probe: calls the private batch helper with an older signature; context_cap_probe: main makes the #103513 cap opt-in, child trigger 850,000; the lying-extension read_file fixture: PNG bytes in a .txt are not flagged binary). It names the main it used, says the readtool fixtures are read directly by a small helper, says value-printing probes were judged against criteria fixed before the runs, and lists what was not run (live/paid probes, the 4 offline live_ab probes the local sandbox blocks, goal_repaste_probe). The results header now says items default to 44a1ce9724 unless they name another commit. subagent_context_cap.py is no longer cited (F14 excludes it).
  - **Advisory: F14 receipt changed_files.** website/docs/user-guide/features/context-compression-and-caching.md (absent at 34f8ec3b40) corrected to website/docs/developer-guide/context-compression-and-caching.md, matching `git diff --name-only 34f8ec3b40 da974f840c`; the change is recorded in the receipt's new corrections field. New sha256 d8c9b53525... (was 4cb29671e6...) in [evidence].receipts. No verdict, count or map changed.
  - **Advisory: rev-4 guards labelled as history.** guards.replay_gates and guards.postmortem_runner now say they are G-guards rev 4 history (44a1ce9724 vs 05d6dbc172); guards.g_guards_rev4 and the renamed Evidence row "Guards: G-guards rev 4 (history; superseded for P5 by the F14 row)" state the judge difference (rev-4 context_cap PASS is completion-only; F14's pinned judge fails it on both arms). P5 still rests on F14/r20261001-01 and is unchanged.
  - **Still open (code):** the test comment at tests/agent/test_anthropic_context_editing.py:75 (blob fc48d77dbb); next step 8, unchanged.
  - Jargon lint (PR body + v2 message) and privacy scan (29 files) re-run: clean; [body] updated. Gates unchanged: P1-P5, P7 PASS; P11 RECORDED; P6, P8, P9, P10, P12 PENDING; status STAGED. Nothing pushed; no GitHub writes.
