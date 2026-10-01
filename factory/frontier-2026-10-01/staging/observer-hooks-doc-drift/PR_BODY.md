## What does this PR do?

Docs-only. `post_api_request` already passes three fields that the observer hooks guide doesn't list, so plugin authors can't find them without reading the emitter. This adds them to the guide's `post_api_request` field list. Each description was checked against the code that produces the value, not just the comments next to it; that's where the retry caveat below comes from. No behaviour changes.

- **Was:** website/docs/developer-guide/observer-hooks.md:151-158 lists `api_duration`, `started_at`, `ended_at`, `finish_reason`, `message_count`, `response_model`, `usage`, `assistant_content_chars`, `assistant_tool_call_count`, `response` and `assistant_message`. The page never mentions `first_chunk_at`, `context_length` or `moa_references`.
- **Source on main:** agent/turn_response_intake.py:83-97 passes all three:

  ```python
  # First stream chunk time (epoch s); None if not streamed / no chunk.
  # TTFB = first_chunk_at - started_at.
  first_chunk_at=getattr(agent, "_last_api_first_chunk_at", None),
  ...
  context_length=getattr(getattr(agent, "context_compressor", None), "context_length", None),
  ...
  moa_references=_moa_reference_metrics_for_hook(agent),
  ```

  The sample payload in hermes_cli/hooks.py:141-153 carries the same three fields.
- **Now:** The list includes the three fields:
  - `first_chunk_at` is the epoch time of the attempt's first stream chunk. It is reset before every attempt (agent/turn_api_request.py:107) and set by the shared chat-completions/Anthropic stream (agent/chat_completion_helpers.py:3005-3012, :4063-4065) and the Codex Responses runner (agent/codex_runtime.py:1090-1096). Those are the only two places that set it. It stays `None` for non-streamed responses, for a stream that fails after sending output (the partial-stream stub returns at chat_completion_helpers.py:4057-4059, before the timestamp is copied at :4063-4065), and for `bedrock_converse` streams. The page lists these cases, so nobody expects a value from Bedrock.
  - The source comment above says TTFB is `first_chunk_at - started_at`. The page says that holds only when nothing was retried. `started_at` is set once per API call, before the retry loop (agent/conversation_loop.py:1650), and a retry doesn't reset it. A retry after an error goes back through `build_api_request`, so it gets a new `first_chunk_at` but keeps the old `started_at`. A dropped stream that reconnects inside one attempt keeps it too (chat_completion_helpers.py:3571-3590). So after a retry the difference can also count the failed tries and the backoff between them, just as `api_duration` always does (agent/turn_response_check.py:119).
  - `context_length` is the context engine's window (`agent.context_compressor`, either the built-in compressor or a context-engine plugin).
  - `moa_references` is `client.last_reference_metrics()` (agent/conversation_loop.py:307-318), and `None` off the MoA path. Each entry is `slot_metrics()` output (agent/moa_trace.py:64-72): `label`, `model`, `provider`, `temperature`, `usage`, the three cost fields, and the advisor's `output` text. That text is privacy-redacted only when `moa.privacy_filter` is set (agent/moa_loop.py:1293-1307). The page also notes that `response` and `usage` describe only the aggregator call, because advisor spend is folded into session totals separately (agent/turn_usage.py:48-58).
- `first_chunk_at` landed in #100425 and was extended to Codex Responses in #115819. The guide's list wasn't updated either time.

Not changed here:
- The plugin hook table in website/docs/user-guide/features/hooks.md also leaves these three fields out of its `post_api_request` row. I didn't touch it because #123978 is editing that row (it adds `cost`). The fields can go in there after that settles, so the two PRs don't conflict.
- How this PR and #123978 interact: they share no file, but #123978 also changes what `post_api_request` sends. It adds a `cost` kwarg to the same call in agent/turn_response_intake.py, and a second emitter in agent/codex_runtime.py for the Codex app-server runtime that sends `started_at`, `first_chunk_at` and `moa_references` as `None`. If #123978 lands first, I'll rebase this PR and add `cost` and the app-server `None` case to the list. If this PR lands first, I can send the `cost` line as a small follow-up once #123978 merges.
- `moa_references` is only refreshed when the advisors actually run, so an attempt that reuses cached advisor answers carries the previous fan-out's list again (agent/moa_loop.py: `_last_reference_metrics` is assigned only on the cache-miss path). The page uses the accessor's own wording, "the most recent fan-out", and doesn't promise more than that. Anyone summing advisor cost per call should know about it.

## Related Issue

Refs #16106: `first_chunk_at` is the per-attempt first-chunk timestamp that issue's provider timing trace can build on.
Refs #64231: payload documentation for an existing hook, no hook change.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/developer-guide/observer-hooks.md`: adds `first_chunk_at`, `context_length` and `moa_references` to the `post_api_request` field list (+15 lines, nothing removed). There's no zh-Hans copy of this page.

## How to Test

1. Read agent/turn_response_intake.py:83-97 on `main` next to the `post_api_request` list in the new page. Every kwarg the call passes is now listed in one of three places: the "identity/runtime fields" carried over from `pre_api_request`, the Correlation IDs table (that's where `api_call_count` is), or the list itself.
2. The documented behaviour is already covered by tests/agent/test_first_chunk_at_hook.py (streamed attempts carry a value between `started_at` and `ended_at`, non-streamed and failed attempts carry `None`, values don't leak across attempts) and tests/agent/test_moa_observability_bridge.py (entry keys, `None` off the MoA path). Both pass on this branch: 17 passed, 0 failed. It's docs-only, so no new tests.
3. No existing test covers the retry caveat, so I checked it with a throwaway test (not included here). The test makes one attempt fail and then streams a reply on the retry. Both `pre_api_request` events and the final `post_api_request` carried the first try's `started_at`. `first_chunk_at - started_at` came out at 0.64 s, while the attempt that answered got its first chunk after 0.005 s. A stream that drops and reconnects inside one attempt showed the same thing (0.31 s against 0.000 s).
4. Docs CI steps that run offline: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` is clean, and `python3 website/scripts/check_doc_links.py` reports OK.
5. Not run here: the Docusaurus build (`npm run build:fast`) and `npm run lint:diagrams`. The added lines are plain bullets with no `{}`, raw tags or box-drawing characters outside code spans, and they parse as one 9-item list with CommonMark + GFM.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs-only: I ran the two test files that cover these fields (17 passed), not the full suite.
- [ ] I've added tests for my changes (required for bug fixes, strongly encouraged for features). N/A, docs-only.
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

N/A

---

Prepared with AI assistance (Claude Code). Every statement above was checked against the cited source lines on `main`.
