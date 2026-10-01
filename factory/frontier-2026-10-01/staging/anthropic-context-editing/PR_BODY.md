## What does this PR do?

This PR adds an opt-in setting, `compression.anthropic_context_editing` (default `false`), that turns on Anthropic's server-side context editing (#526) for Claude models on the native Anthropic API.

When the setting is on, each main-turn request carries:

```json
"context_management": {"edits": [{
  "type": "clear_tool_uses_20250919",
  "trigger": {"type": "input_tokens", "value": <local compression trigger - 8192>},
  "clear_at_least": {"type": "input_tokens", "value": <20% of trigger>}
}]}
```

The request also gets the `context-management-2025-06-27` beta header. The API then clears the oldest tool results on its side once the prompt crosses the trigger. Hermes keeps the full transcript locally.

The design follows `agent/native_compaction.py`:

- the gate is re-checked on every request;
- it stays off when `compression.enabled` is false or `checkpoint_required` is set;
- the trigger is set below the local compression trigger, so the server clears first. Local compression stays enabled, but it decides on the prompt size the provider reports, and after a clear that is the smaller post-clear size, so it fires later. I have not tested that regime against the real API (see "Not tested" below);
- a structured 400 that names `context_management` turns the feature off for the session and retries the request once without it.

The retry uses the same recovery step native compaction already has, generalised from one api_mode to two.

**This manages the context window. It does not save money.** #526 says context editing works "without destroying prompt cache prefixes". Anthropic's documentation says otherwise: clearing tool results invalidates the cached prefix from the first cleared result onward, and each clear incurs a cache write. That is why the trigger sits high (just under the local one) and `clear_at_least` keeps clears large and infrequent.

There is one benefit beyond window management. On models with preserved thinking, a server-side clear is not treated as a history edit, so it does not invalidate the thinking blocks of later turns. Local compaction does.

Scope is deliberately narrow:

- Only `clear_tool_uses` is sent. `clear_thinking_20251015` is left out until the open thinking-replay work settles (#103476 and the related preserved-thinking PRs) and until #71302 settles. That PR already sends `clear_thinking_20251015` on OAuth requests (see the open questions at the end).
- `keep`, `exclude_tools` and `clear_tool_inputs` use the server defaults.
- Only the native Anthropic API is covered. Bedrock, Azure, Nous Portal, MiniMax, Kimi and other Anthropic-compatible endpoints never see the field.

Behaviour changes: with the setting off (the default), none; request bodies and headers stay byte-identical. With it on, eligible requests change as described above. The computer-use docs page changes too, because it already described this feature as active (see below).

## Related Issue

Refs #526 (this implements the `clear_tool_uses` half)

Prior art: #528 by aydnOktay was closed as superseded by #1147. The merged diff of #1147 only touched beta-header and OAuth plumbing (see the 2026-06-29 triage note on #526). On #528, teknium1 said the feature was wanted once a native Anthropic transport existed, and Hermes now has one. No code from #528 is reused here.

Related open PR: #71302 by TrueNix (OAuth request parity with the Claude Agent SDK) also writes `extra_body["context_management"]` in `build_anthropic_kwargs` and adds the same beta to the OAuth beta list. No code from it is reused here; the overlap is described under the open questions.

## Type of Change

- [x] ✨ New feature (non-breaking change that adds functionality)

## Changes Made

- `agent/anthropic_context_editing.py` (new, 52 lines): the per-request gate. It returns the `context_management` payload or `None`, and reuses `resolve_compact_threshold` from native compaction for the trigger.
- `agent/chat_completion_helpers.py`: `_build_anthropic_kwargs` passes the gate's result to the transport, the same way `_build_codex_kwargs` does for native compaction.
- `agent/anthropic_adapter.py` and `agent/transports/anthropic.py`: `build_anthropic_kwargs(context_management=...)` puts the payload in `extra_body` and adds the beta to the per-request header. This reuses the fast-mode code that rebuilds the full beta list, so a fast-mode-only header is byte-identical to before.
- `agent/turn_recovery.py`: the structured-400 step now maps api_mode to the feature flag. The native compaction message and log text are unchanged.
- `hermes_cli/config_defaults.py`, `agent/agent_init.py`: the new key (default false) is parsed onto the agent.
- `gateway/run.py`: the key busts the gateway's cached agent, like `codex_responses_native`.
- `tui_gateway/session_compression.py`: the key hot-reloads in TUI sessions, like `codex_responses_native`.
- `cli-config.yaml.example` and `website/docs/developer-guide/context-compression-and-caching.md`: the key is documented, including the caching caveat and the later local compression after a clear.
- `website/docs/user-guide/features/computer-use.md`: the "Server-side context editing" bullet already said the adapter sends `clear_tool_uses_20250919`, which was not true on `main` (the triage note on #526 points this out). It now says the feature is opt-in and names `compression.anthropic_context_editing`. The zh-Hans mirror has the same sentence. I left it alone because that page already lags the English one in other places.
- `tests/agent/test_anthropic_context_editing.py`: two behaviour tests. The first is parametrised over six cases: flag off, flag on, and flag on with each of the four conditions that must keep the field off (compression disabled, `checkpoint_required`, a non-Claude model, a third-party endpoint).

## How to Test

The tests run the real `AIAgent` turn loop on the production native route, `https://api.anthropic.com`. An in-process `HTTPS_PROXY` terminates TLS for that host with a throwaway CA and serves it from `tests/fakes/providers/anthropic_messages.py`. That fake validates every request body against the installed SDK's beta request types. Only the vendor HTTP boundary is faked, and the config comes from `config.yaml` in a temporary `HERMES_HOME`.

1. `scripts/run_tests.sh tests/agent/test_anthropic_context_editing.py`
   - Opt-in: with the flag on, every main request carries `clear_tool_uses_20250919` and the beta, the trigger is below the local compression trigger, and there are no SDK schema errors.
   - Eligibility: neither the field nor the beta is sent when the flag is off, or when the flag is on but compression is disabled, `checkpoint_required` is set, the model is not Claude, or the base URL is an Anthropic-compatible third-party endpoint.
   - Rejection: a 400 `context_management: Extra inputs are not permitted` is followed by one retry without the field, and the next turn also goes without it. The per-request sequence is `[True, False, False]`.
2. On `main`, 2 of the 7 cases fail: the two flag-on cases. The beta is missing from the header, and the request sequence is `[False, False]` instead of `[True, False, False]`. The other 5 cases expect no field, so they pass on both.
3. I broke each hunk on the request path one at a time, and each break turned at least one test red. Most breaks deleted the added line or condition: the call site, `extra_body`, the beta header, the agent attribute, the recovery row, the recovery flag reset, the transport default, and each of the five gate conditions (flag, `compression.enabled`, `checkpoint_required`, Claude model, third-party endpoint). Two breaks changed a value instead: the config parse was forced to `False`, and the trigger was set to the local trigger + 1. These two tests do not cover the gateway cache-key and TUI hot-reload lines, which follow the existing `codex_responses_native` lines. They also do not pin the exact `clear_at_least` fraction; the test only checks that it is above zero and below the trigger.

   I also broke the two existing paths this PR refactors, one at a time, and ran the existing tests that own them. Removing the fast-mode beta from the rebuilt header fails `test_fast_command`. Removing the native-compaction row from the recovery table fails nothing: `test_native_compaction` only covers the rejection classifier, and I found no existing test that reaches that recovery step. This PR does not add one.

Results I measured locally (Linux, Python 3.11), on `main` at `44a1ce9724` and this branch rebased onto it:

- New tests: 7 of 7 pass, in each of 3 repeated runs.
- Adjacent suites: 518 of 518 pass on both `main` and this branch. These were `test_anthropic_adapter`, `test_fast_command`, `test_fast_mode_auto`, `test_native_compaction`, `test_nous_portal_anthropic_wire`, `tests/gateway/test_agent_cache`, `tests/tui_gateway/test_compression_config_hot_reload`, `test_config_edit_seed`, `test_config_unversioned_migration`, `test_413_compression`, `transports/test_transport`, `test_anthropic_stream_fallbacks`, `test_codex_token_expired_replay_recovery`, `test_error_classifier` and `e2e/core/providers/test_anthropic_oracle`.
- Offline eval probes under `evals/`, run unmodified from each checkout with a fresh temporary home per probe: 22 probes give the same result on both `main` and this branch: `token_accounting/replay_gates.py` (11 of 11 gates pass on both), `ab_image_cost_calibration.py`, `worktree_prompt_prefix.py`, `native_compaction/ab_checkpoint_preflight.py`, the three `provider_fallback` probes, `goal_command_parity.py`, `compaction/test_region_scoping.py`, the 9 non-live probes of `python -m evals.postmortem.run`, and 4 of the hand-run post-mortem review probes (`context_cap`, `deadline`, `goal_scope`, `finalizer_schedule`). 19 of the 22 pass on both. The other 3 fail on both: the post-mortem probes `subagent_context_cap.py`, `notice_delivery_probe.py` and `cache_estimator_probe.py` already fail on `main`, because they lag the code they probe. I did not run `goal_repaste_probe.py`, which reads a copy of a real session database.
- A separate loopback probe of the gate:
  - It repeats the gate matrix outside pytest: the field is sent only when the flag is on, compression is enabled, `checkpoint_required` is off, the model is Claude and the host is native.
  - With real usage over the local trigger, local compression still fires on the next turn, with the flag on and with it off. The fake reports the same usage whether or not the field is sent, so this does not model usage after a real clear.
  - With the key absent, request bodies and headers are byte-identical to `main`. The system prompt differs only in host details that change on every run, such as the temporary home path.

### Cache behaviour (not yet measured)

I have not measured `cache_read_input_tokens` or `cache_creation_input_tokens` before and after a clear against the real API, and none of the numbers above come from a real provider. Before this leaves draft I will add per-turn cache-read and cache-write figures, flag on vs off, from `evals/postmortem/live_ab/cache_concurrency_probe.py --provider anthropic` run from this branch with `compression.threshold_tokens: 150000`. That puts the server trigger at 141,808 tokens, which the probe's tool loop crosses. If the numbers show the clears costing more than local compaction on realistic sessions, this should stay an opt-in window tool, or be declined.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. I ran the new file plus 15 adjacent files through `scripts/run_tests.sh`, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux, Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A (request-payload change only; no OS-specific code)
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Not tested, and open questions for review:

- Not tested: whether the real API accepts the payload, and the exact wording of a real rejection. The fallback matches on `context_management` plus rejection language in a 400, the same as native compaction.
- Not tested: OAuth (Claude subscription) requests. The beta header is sent there too, and a structured rejection falls back.
- Not tested: the local fallback after a real server-side clear. Hermes resends the full transcript every turn, and local compression decides on the prompt size the provider reports (the usage anchor from `agent/usage_anchor.py`, used by the turn-start, pre-request and after-tool checks). After a clear, that is the post-clear size. So local compression fires later, while the transcript and the request body keep growing. My probe's fake reports the same usage whether or not the field is sent, so it does not cover this.
- Not tested: recall after clears. For example, the compaction exam in `evals/compaction` has no server-side context-editing arm yet, so I could not compare the flag on vs off.
- Open question: old `skill_view` results can be cleared on the server without the local compressor's "reload with skill_view" marker. `exclude_tools: ["skill_view"]` could be a default, but on OAuth it would need the wire-name mapping, so I left it out of this PR.
- Open question: is `clear_thinking` wanted at all, once #103476 lands and given #71302? #71302 (open, currently conflicting with `main`) sets `extra_body["context_management"] = {"edits": [{"type": "clear_thinking_20251015", "keep": "all"}]}` on OAuth requests with thinking, and adds `context-management-2025-06-27` to `_OAUTH_ONLY_BETAS`. If both PRs land as written, on OAuth requests with thinking and this setting on, its later write replaces this PR's `clear_tool_uses` edit, and the beta appears twice in the header, because this PR appends it to a list that already contains the OAuth betas. Whichever lands second should build one `edits` list (Anthropic requires `clear_thinking_20251015` to come first when both are sent) and add the beta once. I have not made that change here, because #71302 is not on `main`.

AI assistance: this change, its tests, the local probes and this PR description were written with Claude Code (Claude Opus 5.5).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
