+++
xf_staging = 1
id = "anthropic-context-editing"
version = 1
title = "Opt-in Anthropic server-side context editing (clear_tool_uses) behind a native_compaction-style gate (#526)"
branch = "staging/anthropic-context-editing"
branch_fork = "staged/anthropic-context-editing"
branch_physical = "local-only in scratch h.git as staging/anthropic-context-editing; to be pushed to kvnloo/hermes-agent as staged/anthropic-context-editing (OD-0 resolved by that rename: the fork's legacy refs/heads/staging 28790e597c blocks staging/<id>)"
branch_sha = "b83e778103d36c48c7736bae07c01658dfb97158"
status = "STAGED"          # ceiling at $0 = LIMITED (P6 needs the paid F10 cache arm)
promotion_form = "core-pr"
route = "core-leaf"
feature = "anthropic-context-editing"
invariant = "With compression.anthropic_context_editing true, main-turn requests for Claude models on the native Anthropic API carry context_management.edits=[clear_tool_uses_20250919] plus the context-management-2025-06-27 beta, with a trigger below the local compression trigger; every other request is unchanged; a structured 400 naming context_management disables the feature for the session and retries once."

[base]
repo = "NousResearch/hermes-agent"
sha = "aea969677c60a1bb72fe227fdfb98f196a2092cc"
fetched_at = "2026-10-01T11:04Z"
freshness_recheck = { main = "e8c97320ac8691d4de92af49f98459f9ef9ddb08", checked_at = "2026-10-01T11:17Z", commits_after_base = 6, merge_tree_clean = true, invalidate_on_hits = ["website/docs/developer-guide/context-compression-and-caching.md (one -900k model-example line at :389, far from this change's hunks)"] }

[upstream]
issues = ["NousResearch/hermes-agent#526 (teknium1, open, P3, reopened by triage 2026-06-29)", "NousResearch/hermes-agent#525 (teknium1, /microcompact, related)"]
prior_art = [
  { pr = 1147, author = "teknium1", state = "MERGED 2026-03-13", note = "beta-header / OAuth plumbing only; triage says it did not implement context editing" },
  { pr = 528, author = "aydnOktay", state = "CLOSED unmerged 2026-03-13", note = "env-var design on the OpenAI-SDK path; teknium1: feature wanted, needed the native Anthropic transport (now exists). No code reused, so no Co-authored-by" },
]
# Measured 2026-10-01T11:16Z on main e8c97320ac with heads fetched read-only into refs/xf/pr/<n> (receipts/MERGE-r20261001-02.json).
dependencies = [
  { pr = 103476, author = "teknium1", head = "bc9511af3f", state = "OPEN", touches = "agent/anthropic_endpoints.py, agent/anthropic_message_convert.py, agent/message_sanitization.py, 2 tests", file_overlap = "none", merge_with_staging = "clean (main + PR merges clean, and that result merges clean with the branch)" },
  { pr = 129620, author = "JoaoMarcos44", head = "588b746cf6", state = "OPEN", touches = "agent/anthropic_message_convert.py, agent/turn_recovery.py, agent/message_sanitization.py and 5 more agent files, 1 test", file_overlap = "agent/turn_recovery.py", merge_with_staging = "clean (main + PR merges clean, and that result merges clean with the branch; the shared file auto-merges)" },
  { pr = 129492, author = "SHL0MS", head = "7df230b4c3", state = "OPEN", touches = "agent/anthropic_message_convert.py, tests/agent/test_anthropic_adapter.py", file_overlap = "none", merge_with_staging = "clean (main + PR merges clean, and that result merges clean with the branch)" },
  { pr = 129882, author = "Sahilvishnaliya", head = "66987608bc", state = "OPEN, CHANGES_REQUESTED, CONFLICTING", touches = "17 files incl. agent/anthropic_message_convert.py, agent/context_compressor.py, cron/lifecycle_guard.py", file_overlap = "none", merge_with_staging = "no file overlap with the branch; the PR itself conflicts with main in cron/lifecycle_guard.py, so merge-tree of the PR with the branch reports that same conflict" },
]
competitors = []
close_after = []
demand = { score = "n/a", source = "critic.md missing_features #1; judges maintainer-fit 6 / evidence 3 / impact 6" }
maintainer_signal = "teknium1 authored #526 and wrote on #528: 'this is definitely a feature we want to support'"
fork_threads = ["kvnloo/hermes-agent#322 (factory thread)", "kvnloo/hermes-agent#404 (staged-PR queue, 39 rows)"]

[[members]]
ref = "staging/anthropic-context-editing"
sha = "b83e778103d36c48c7736bae07c01658dfb97158"
role = "own leaf: first slice (gate + wire + recovery + config + 2 contract tests + docs incl. the computer-use doc fix)"
author = "Kevin Rajan <7121943+kvnloo@users.noreply.github.com>"
rebase_status = "parent aea969677c (rebased from 572e4f4fad, 47 commits, cherry-pick clean, then amended with the doc fix); merge-tree clean on main e8c97320ac (6 commits later)"
supersedes = "1ecde98a7164827a1b8005d9be0443f9310901ce (parent 572e4f4fad; local branch forced to the new commit as instructed)"

[ownership]
searched_at = "2026-10-01T11:13Z"
queries = ["context_management anthropic", "clear_tool_uses", "context editing", "context-management-2025-06-27", "clear_thinking", "anthropic_context_editing"]
open_external = []
merged_overlap = [1147]
claimant_lanes = [127373, 127374, 127375, 127332, 127228]   # all TUI/HUD; no overlap
hard_hold = [69, 70]
design_holds = ["CU/Jev", "realtime-voice", "agents-overlay", "row-budget", "glyph"]
hermes_lane_overlap = "none found"
verdict = "OURS (no open implementation; maintainer-authored issue)"

excluded_paths = ["hermes_cli/kanban_db.py", "tests/hermes_cli/test_kanban_external_receipts.py"]

[evidence]
specs = { path = "specs/PREREG.json", sha256 = "36f9f6439a3c383f8e5c3871ad9f716f2817321d3a13ca587e627447890598dd", recorded_at = "2026-10-01T11:08:35Z", note = "rev-2 specs hashed before run r20261001-02 started (11:09:29Z); not on claude/ledger" }
receipts = [
  { id = "P-redgreen/r20261001-02", path = "receipts/P-redgreen-r20261001-02.json", sha256 = "6b0a3dbba5556762901d02e334bcba512f0e8fb735c5fd6533268fb1a649b32f" },
  { id = "F09/r20261001-02", path = "receipts/F09-r20261001-02.json", sha256 = "57738a1f1651d0ef3d38a922217efbb76b354a36c5f82ae93b2a7a63cde26b56" },
  { id = "G-guards/r20261001-02", path = "receipts/G-guards-r20261001-02.json", sha256 = "8f3e16afa58ebcf76cfc9a52fe559f816fd4b3bae0c924f990445ab02c1281de" },
  { id = "MERGE/r20261001-02", path = "receipts/MERGE-r20261001-02.json", sha256 = "fba494b79b32e8b3524bcf515686a2ee46621de772d9e7a39255586f537b6ff2" },
]
superseded_receipts = "P-redgreen, F09 and G-guards /r20261001-01 (head 1ecde98a71 on 572e4f4fad) were removed before any freeze: they carried local absolute paths and pointed at the replaced commit"
patch = { path = "anthropic-context-editing.patch", sha256 = "9f3f6746458967722f1b7a0ae6dcad7b40c9b72fe9b7afe46f0c4684530e6fbf" }
red = { test = "tests/agent/test_anthropic_context_editing.py", main = "aea969677c", marker = "assert 'context-management-2025-06-27' in [...] / assert [False, False] == [True, False, False]", receipt = "P-redgreen/r20261001-02" }
green = { reps = "3/3", receipt = "P-redgreen/r20261001-02" }
negative_control = { mutation = "per-hunk revert", result = "10/12 re-RED; unpinned: tui-hot-reload, gateway-cache-key", receipt = "P-redgreen/r20261001-02" }
adjacent = { identical = true, files = 15, base = "518 passed", head = "518 passed", pre_existing = [] }
guards = { replay_gates = "equal (11/11 PASS both arms)", ab_checkpoint_preflight = "equal (4 scenarios)" }
quantitative = []
cache_read_ratio = { status = "NOT_MEASURED", needs = "F10 (paid, OD-3)" }
route_scope = "native Anthropic API, Claude models; local compressor unchanged"
not_tested = ["real Anthropic API acceptance and real rejection wording", "cache_read/cache_creation per turn around a clear (F10)", "OAuth subscription route", "server behaviour when the full uncleared history is resent each turn", "skill_view results cleared server-side without the local ghost-skill reload marker", "compaction-exam recall with clears"]
resource_usage = { wall_s = 377.0, cpu_core_s = 479.5, api_cost_usd = 0.0, source = "raw/run_meta.json" }
z0evals_study = { repo = "kvnloo/z0evals", branch = "study/hermes-anthropic-context-editing", commit = "" }

[gates]
P1 = "PASS"       # RED on aea969677c; merge re-check on e8c97320ac clean, invalidate_on hit unrelated (re-run RED within 24 h of queueing)
P2 = "PASS"
P3 = "PASS"
P4 = "PASS"
P5 = "PASS"       # 2 sibling config hunks unpinned (listed)
P6 = "PENDING"    # caching-adjacent: needs OBSERVED cache-read before/after (F10) -> LIMITED until then
P7 = "PASS"       # local; not pushed yet (fork name staged/<id>)
P8 = "PENDING"
P9 = "PENDING"    # body drafted; cache section waits on F10; tone gate by a second reader
P10 = "PENDING"
P11 = "RECORDED"
P12 = "PENDING"   # preserved-thinking carriers (#103476, #129620, #129492, #129882) must settle first; OD-0 resolved

[verification]
verifier = ""
provenance = "independent"
exact_head = "b83e778103d36c48c7736bae07c01658dfb97158"
inputs = "raw diff + repo + oracle block only"
verdict = ""
qa_class = ""

[merge_check]
main_sha = "e8c97320ac8691d4de92af49f98459f9ef9ddb08"
checked_at = "2026-10-01T11:17Z"
clean = true
tree = "8330fd0fe5fc271bf94cf4a5c64ad1a39b0bee86"
recheck = "git -C <h.git> merge-tree --write-tree main staging/anthropic-context-editing"

[push]
fork_ref = "staged/anthropic-context-editing"
no_follow_tags = true
workflow_push_matches = 0
pushed_at = ""

[body]
path = "PR_BODY.md"
kind = "pr-body"
tone_gate = { peer = false, no_labor = false, no_internal_leak = false, smallest_ask = false, self_service = false, local_voice = false, easy_decline = false }
jargon_lint = "PENDING"
privacy_scan = "PENDING"

[queue]
board = "kvnloo/hermes-agent#404"
position = "after the existing 39 rows"
slot_claimed = false

[hitl]
linear_issue = ""
origin_actions_taken = 0
+++

# staging/anthropic-context-editing

**Promotion form:** core-pr (route core-leaf). **Status:** STAGED. The best class reachable at $0 is LIMITED: the change is caching-adjacent, so the PR body has to carry an OBSERVED cache-read before/after, and that needs the paid F10 run.

**Branch.** Local ref `staging/anthropic-context-editing` at `b83e778103` in the scratch h.git. On the fork it will be pushed as `staged/anthropic-context-editing`, because the fork still has a legacy branch named `staging`, which blocks `staging/<id>`. That rename resolves OD-0 for this item. Nothing has been pushed.

**Links.** Upstream: NousResearch/hermes-agent#526 (the feature spec, teknium1), NousResearch/hermes-agent#525 (related /microcompact), NousResearch/hermes-agent#1147 (merged, header plumbing only), NousResearch/hermes-agent#528 (closed prior attempt), NousResearch/hermes-agent#103476, NousResearch/hermes-agent#129620, NousResearch/hermes-agent#129492, NousResearch/hermes-agent#129882 (the preserved-thinking replay PRs this waits on). Fork: kvnloo/hermes-agent#322 (factory thread), kvnloo/hermes-agent#404 (staged-PR queue, 39 rows). No fork thread exists for this feature yet.

## Invariant

With `compression.anthropic_context_editing: true`, main-turn requests for Claude models on the native Anthropic API carry `context_management.edits = [clear_tool_uses_20250919]` and the `context-management-2025-06-27` beta. The trigger sits below the local compression trigger. Every other request is unchanged. A structured 400 that names `context_management` disables the feature for the session and retries once.

Call path exercised: `AIAgent.run_conversation` → `turn_api_request.build_api_request` → `chat_completion_helpers._build_anthropic_kwargs` → `anthropic_context_editing.anthropic_context_management` (the gate) → `AnthropicTransport.build_kwargs` → `anthropic_adapter.build_anthropic_kwargs` (`extra_body` and the per-request beta header) → SDK `messages.stream` over TLS to `api.anthropic.com`. The test intercepts that host with a throwaway CA and serves it from the SDK-oracle fake. On a 400: `turn_recovery._recover_format_errors` → `is_native_compaction_rejection` → flag off → the next attempt is rebuilt without the field.

## Route and carrier choice

**Route: core-leaf, our own single commit.** There is no carrier to salvage and no competitor to support:

- No open PR implements `context_management` on the Anthropic path. The searches return nothing relevant (see Premise re-check).
- #1147 (merged) changed header plumbing only.
- #528 (aydnOktay) was closed unmerged. It used env vars on the OpenAI-SDK path, which the maintainer turned down for lack of a native transport. No code is reused, so no Co-authored-by trailer is added; the PR body credits it as prior art.
- #526 is authored by teknium1, and on #528 he called the feature "definitely a feature we want to support". So a support-note or salvage row would have nothing to attach to.

**Why core-pr and not decision-request (for now).** FACTORY §11.4 lists this item as "LIMITED → decision-request". The slice is complete and proven at $0, but P6 needs OBSERVED cache-read numbers (F10, paid, OD-3). If the owner does not fund F10, the fallback is to post the PR body's design and open questions on #526 as a decision request instead of opening the PR. The promotion form stays core-pr until that decision is made.

**The preserved-thinking PRs are ordering dependencies, not carriers.** #103476, #129620, #129492 and #129882 change Anthropic thinking replay, not context editing. The branch waits for them only so that `clear_thinking` and replay interactions are settled before a reviewer sees this PR (P12). Only #129620 shares a file with the branch (`agent/turn_recovery.py`), and that file auto-merges.

WAVE.md row form (own leaf, no carrier):

> | #526 (clear_tool_uses half) | own leaf `b83e7781` (kvnloo) on main `aea96967` | main: FAIL 2/3 (beta missing; `[False, False]` vs `[True, False, False]`); head: PASS 3/3 (3/3 reps); F09 head 1/6 gate cells carry the payload (the eligible one), base 0/6 | none (whole slice is ours) | none open; #528 closed, #1147 header-only | per-hunk sabotage re-REDs 10/12 (2 sibling config hunks unpinned); 15 adjacent files 518/0 on both arms; replay_gates 11/11 equal |

## Premise re-check (current main)

- **Still needed.** At aea969677c, `git grep` finds no `context_management` or `clear_tool_uses` on the Anthropic path. The only `context_management` code is for Responses native compaction (`agent/native_compaction.py`, `agent/chat_completion_helpers.py::_build_codex_kwargs`, `agent/turn_recovery.py`), plus a comment in `agent/auxiliary_client.py`.
- **A doc already claims the feature exists.** `website/docs/user-guide/features/computer-use.md:408-410` says "Server-side context editing (Anthropic only) — when active, the adapter enables `clear_tool_uses_20250919` via `context_management`". That was false on main; the 2026-06-29 triage comment on #526 notes the feature exists "only in website docs". The commit now rewrites that bullet to say it is opt-in and names `compression.anthropic_context_editing` (+3/−2 lines). The zh-Hans mirror (`website/i18n/zh-Hans/.../computer-use.md:105`) has the same sentence. It is left unchanged, because that page already lags the English one elsewhere in the same section (it still describes the old 3-screenshot eviction and macOS-only support). The PR body says so.
- **No competing implementation.** Open-PR searches on 2026-10-01T11:13Z for "context_management anthropic", "clear_tool_uses", "context-management-2025-06-27" and "anthropic_context_editing" return nothing. "context editing" and "clear_thinking" give the same unrelated hits as before (#75327, #84278, #105910, #73370, #92485). Searches across all states add only #1147 (merged), #528 (closed), #6318 (closed, tool_search), #3816 (closed, computer use) and #17169 (closed, 429s), plus the open related issues #525 and #29300 that the triage comment names. None of them is an implementation.
- **History.** #528 (aydnOktay) was closed unmerged. teknium1 said the feature was wanted but needed the native Anthropic SDK transport, which now exists. #1147 was merged as header plumbing. Triage reopened #526 on 2026-06-29.
- **Correction carried into the body.** #526's "without destroying prompt cache prefixes" is not supported. Anthropic's docs say a tool-result clear invalidates the cached prefix from the clear point onward. The body says this plainly.

## Design choices in the slice

- **Gate.** The gate mirrors `native_compaction_context_management`. It is re-checked per request and requires the flag on, `compression.enabled` true, `checkpoint_required` not set, `api_mode == anthropic_messages`, a Claude model, and a native Anthropic base URL. Bedrock, Azure, Portal, MiniMax, Kimi and proxies all count as third-party under `_is_third_party_anthropic_endpoint`.
- **Payload.** Only `clear_tool_uses_20250919`. `trigger` = `resolve_compact_threshold(None, local_trigger)`, which is the local trigger minus 8,192 (reused from native compaction). `clear_at_least` = 20% of the trigger. `keep`, `exclude_tools` and `clear_tool_inputs` are left at server defaults. `clear_thinking_20251015` is not sent (#103476 interaction).
- **Beta header.** Added only when a payload is sent. It reuses the fast-mode rebuild of the per-request beta list, so fast mode alone produces a byte-identical header.
- **Recovery.** The existing native-compaction rung is generalised to an api_mode → flag table. The codex message and log text are unchanged.
- **Config propagation.** `config_defaults` (default false), `agent_init`, the gateway agent-cache key, TUI hot reload, `cli-config.yaml.example`, one docs row in the compression guide, and the corrected computer-use bullet.

Footprint: 13 files, +192/−15 lines, including a 52-line module and an 84-line test file.

## Evidence

All rows are run r20261001-02: base aea969677c (tree aefff2f588), head b83e778103 (tree 0dc2aa7d97). Specs were pre-registered by hash at 11:08:35Z, before the run started at 11:09:29Z. Isolated HOME/HERMES_HOME throughout. Whole run: 377 s wall, 480 CPU-s, $0.

| Experiment | Receipt | Verdict | Label | n | Result |
|---|---|---|---|---|---|
| RED on base | receipts/P-redgreen-r20261001-02.json | PASS | OBSERVED | 3 cases | 2 failed / 3 on aea969677c (beta missing; `[False, False] != [True, False, False]`). The flag-off case passes on both arms by design |
| GREEN | same | PASS | OBSERVED | 3 reps | 3/3 passed in each of 3 reps |
| Per-hunk sabotage | same + raw/sabotage.json | PASS | OBSERVED | 12 hunks | 10/12 re-RED (now including the config-parse hunk). Unpinned: TUI hot reload, gateway cache key (sibling config paths). Not mutated, no behaviour to pin: config default entry, cli-config example, the 2 docs pages, the adapter constant/signature/docstring |
| Adjacent | same | PASS | OBSERVED | 15 files | 518 passed / 0 failed on base, 518 / 0 on head |
| F09 gate probe | receipts/F09-r20261001-02.json | KEEP | OBSERVED | 10 cells × 2 arms | Head: payload on the eligible cell only (1/6 gate cells), 0/5 ineligible cells (flag false, compression off, checkpoint_required, non-Claude, third-party endpoint). Base: 0/6. 400 path: head `[True, False, False]`, base `[False, False]`. Local compressor over threshold (60K real vs 50K): 1 compression on turn 2 in both arms, flag on and off. Head trigger 41,808 < 50,000. Flag-absent wire, base vs head: bodies (minus system) and headers IDENTICAL, and the system prompts are identical after host normalisation (temp HOME path, host/kernel line and python version replaced by placeholders; only the hash is stored). SDK schema errors 0. Egress blocked 0 |
| Guards (replay_gates, ab_checkpoint_preflight) | receipts/G-guards-r20261001-02.json | EQUAL | OBSERVED | 11 + 4 scenarios | replay_gates 11/11 PASS on both arms, maps equal. ab_checkpoint_preflight 4 scenarios equal |
| Merge checks | receipts/MERGE-r20261001-02.json | CLEAN | OBSERVED | 13 merges | Branch × main e8c97320ac clean. #103476, #129620, #129492: main + PR clean, and that result × branch clean. #129882: no file overlap; the PR conflicts with main in `cron/lifecycle_guard.py` |
| F10 cache arm | not run | — | NOT_MEASURED | — | queued (paid) |

Example payload (OBSERVED, head, local trigger 150,000 for a 200K window): `{"edits":[{"type":"clear_tool_uses_20250919","trigger":{"type":"input_tokens","value":141808},"clear_at_least":{"type":"input_tokens","value":28361}}]}`.

Receipt format: all four receipts carry the `xf.receipt.v1` fields from FACTORY §9.2. That covers spec (path, rev, sha256, decision_rule_sha; `prereg_commit` is null because xf/claude-ledger does not exist yet), runner_revision, policy_revision, changed_files, denominators, evidence_class, resource_usage, frozen (`NOT_FROZEN`, P8) and privacy (`public-aggregate`). They contain no absolute local paths. Commands use the placeholders `<worktree>`, `<testhome>`, `<venv-python>` and `<h.git>`. The harness takes its paths as arguments or env vars and does not hard-code them.

## Experiments queued (exact commands, not run)

**F10. T3, paid, OD-3; the owner launches it with the owner's key.** Measures `cache_read` and `cache_creation` per turn before and after a clear, flag on and off, in ABBA order. It runs the upstream probe unmodified from the staging checkout; the probe records usage per call and classifies consecutive pairs as ideal/stuck/collapse. `threshold_tokens: 150000` puts the server trigger at 141,808, which a 10-call read_file loop crosses (≈30K tokens per read). After a clear with keep=3, about 100K tokens remain, under the local trigger. In the off arm, local compaction fires at 150K instead. Cost estimate (MODELED): roughly $2–4 per session on claude-opus-5-5, so 8 sessions come to about $16–32. Proposed cap: $35.

```bash
# from a checkout of staging/anthropic-context-editing @b83e778103 (repo root)
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

Known gap in F10: the probe does not record `context_management.applied_edits` from the response, so clears are inferred from collapse pairs. A small read-only wrapper on `get_final_message().model_extra` would make clears observable (a follow-up before launch).

**F10-exam. T3, paid; the harness is NOT written.** This arm would run the frozen-lineage compaction exam (evals/compaction) after a long tool session, flag on vs off. `evals/compaction` has no server-side context-editing arm, so a new arm is needed. Queued as a design item, not a command.

**T2 (local GPU): N/A.** Context editing is an Anthropic server feature. llama.cpp and ollama cannot emulate it, and the 64K floor (OD-1) blocks local Hermes arms anyway.

## Acceptance gates (selection)

| Gate | Status | Evidence |
|---|---|---|
| With the flag off, the request is byte-identical to today | met | F09 flag_absent_wire: identical bodies and headers across arms, and identical host-normalised system prompts. The contract test's off case asserts no field and no beta |
| Gate tests RED on main, GREEN with the change | met | P-redgreen: RED 2/3 on aea969677c, GREEN 3/3 ×3 |
| Negative control | met | per-hunk sabotage 10/12 re-RED. 2 sibling config hunks unpinned (listed) |
| Structured-400 disable-and-retry proven | met | contract test 2 and F09 (`[True, False, False]`) |
| Local compressor fallback still fires over threshold | met | F09 over_threshold cells: 1 compression on turn 2 with the flag on (trigger 41,808 < local 50,000) |
| replay_gates PASS | met | 11/11 on both arms, equal maps |
| Existing docs no longer claim the feature is always on | met | computer-use.md bullet rewritten in the commit; zh-Hans mirror called out in the body |
| PR body reports measured cache-read before/after and says it is not a savings feature | not met | the "not a savings feature" text is in the body. Cache-read numbers wait on F10 (OD-3) |
| Opened only after the preserved-thinking replay PRs settle | pending | #103476, #129620, #129492, #129882 all OPEN. #103476, #129620, #129492: each merged onto main e8c97320ac, then merged with the branch: clean (#129620 shares `agent/turn_recovery.py`, no conflict). #129882: no file overlap with the branch; the PR itself conflicts with main in `cron/lifecycle_guard.py` |

## Gate checklist (P1–P12)

- P1 PASS: RED on aea969677c (P-redgreen/r20261001-02). Re-checked on e8c97320ac, 6 commits later: merge clean. The one invalidate_on hit is an unrelated -900k model-example line in the compression guide.
- P2 PASS: no open or merged implementation. Claimant lanes are TUI/HUD.
- P3 PASS: one invariant, a config.yaml key, no env var, no hook. turn_recovery.py goes 1925→1933 lines and stays under 2k. The touched files that were already over 2k lines grow by 0–8 lines each: agent_init 2510→2513 (+3), chat_completion_helpers 4086→4089 (+3), cli-config.yaml.example 2321→2329 (+8), config_defaults 3188→3192 (+4), gateway/run.py 6154→6154 (0).
- P4 PASS: real turn loop on the native route. Only the HTTP vendor boundary is faked.
- P5 PASS: RED, GREEN 3/3, sabotage 10/12 (2 unpinned, listed), adjacent identical, guards equal, not flaky.
- P6 PENDING: F10.
- P7 PASS (local): one commit on aea969677c, correct author, `feat(anthropic):`, merge-clean on e8c97320ac, 0 workflow files touched. Not pushed; the fork ref will be `staged/anthropic-context-editing`.
- P8 PENDING: receipts now carry the full §9.2 field set and the specs are pre-registered by hash, but nothing is frozen (no write-once bundle, nothing in z0evals).
- P9 PENDING: body drafted, with plain AI disclosure; the cache section is a placeholder until F10; tone gate by a second reader.
- P10 PENDING: no blind verifier on b83e778103 yet.
- P11 RECORDED: teknium1-authored issue, explicit "we want to support" on #528.
- P12 PENDING: the dependency PRs and the staging cap. OD-0 is resolved by the `staged/<id>` fork name.

## NOT_TESTED

- **Real Anthropic API:** acceptance of the payload, the real rejection wording, and whether a non-structured failure could occur (the gpt-5.1 lesson from native compaction).
- **Cache behaviour after a clear.** It is also unknown whether the server re-clears on every request, because Hermes resends the full uncleared history (F10).
- **OAuth / Claude subscription route:** whether the beta is accepted there. A structured 400 would fall back.
- **skill_view results:** a server-side clear can drop them without the local compressor's ghost-skill "reload with skill_view" marker. `exclude_tools` is not set; it would also need the OAuth wire-name mapping.
- **Recall:** compaction-exam recall with clears (the F10-exam harness is not written).
- **Test scope:** the full test suite was not run (targeted files only); no Windows or macOS runs. The docs site build was not run (two Markdown edits, no new links).

## Origin action (owner only)

When F10 numbers exist and the dependency PRs settle: fill the cache section of PR_BODY.md, re-run RED/GREEN on the newest main, push the branch to the fork as `staged/anthropic-context-editing`, then run `gh pr create -R NousResearch/hermes-agent --head kvnloo:staged/anthropic-context-editing --title "feat(anthropic): opt-in server-side context editing (clear_tool_uses)" --body-file PR_BODY.md`. The factory does not run this command. If F10 is not funded, post the body's design and open questions on #526 as a decision request instead.

## Next steps

1. Owner: OD-3 (F10 budget, about $35). OD-0 is resolved by the `staged/<id>` name.
2. Before F10: add the read-only `applied_edits` capture to the probe run (a wrapper only, no core change).
3. A blind verifier reads exact head b83e778103 (P10).
4. When #103476 and the other preserved-thinking PRs merge: rebase, re-run the contract tests, F09 and the guards (`harness/run_proofs.py`, then `harness/write_receipts.py`).
5. Ask on #526 whether `skill_view` should be in `exclude_tools` by default (a follow-up slice), and whether `clear_thinking` is wanted after #103476.

## History

- 2026-10-01T09:24Z | STAGED | builder (Claude Code, Opus 5.5) | first slice committed 1ecde98a71 on 572e4f4fad. $0 proofs and F09 KEEP; F10 queued.
- 2026-10-01T11:20Z | STAGED | stfix round 1 (Claude Code, Opus 5.5) | Fixed the phase-3 verifier findings:
  - Rebased onto aea969677c and amended the commit with the computer-use doc fix: new head b83e778103. The local branch was forced to it as instructed; the old commit 1ecde98a71 is still an object in h.git.
  - Corrected the #129882 merge claim (no overlap; the PR itself conflicts with main) and #129620's head (588b746cf6).
  - Plain AI disclosure in the body; P3 now includes cli-config.yaml.example (+8).
  - Added the Route and carrier choice section.
  - Pre-registered rev-2 specs, re-ran every $0 proof (r20261001-02), and wrote full §9.2 receipts with no local paths. Removed the r20261001-01 receipts.
  - F09 now stores only host-normalised system-prompt hashes.
  - Fork branch name is staged/<id> (OD-0 resolved).
