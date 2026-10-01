## What does this PR do?

Docs-only. Six statements in the gateway-facing docs no longer match the code. Each item gives the doc location, the old and new claim, the source the new text matches, and the change that caused the drift. No behaviour changes. Source line numbers are at the base commit f848940560.

1. **`developer-guide/programmatic-integration.md:194`**: the "Provider/agent failure" row listed only `completed: false`, `error`. It now adds `partial` when applicable (reply text was already streamed before a retry-exhausted or non-retryable provider error). Source: `agent/turn_recovery.py:1092` and `:1240` set `result["partial"] = True` when already-delivered text is kept (#119001), and `terminal_run_status()` in `gateway/platforms/api_server_runs.py:181-193` puts `partial` on every terminal event and status. Drift from e947f60689 (#121628).
2. **`user-guide/features/api-server.md:617`**: the `POST /api/sessions/{id}/chat/stream` event list had no `approval.request`. It now lists it, keyed by the run id, with the run waiting in `waiting_for_approval` until `POST /v1/runs/{run_id}/approval` resolves it. Source: `gateway/platforms/api_server.py:3673` registers the approval callback, `:3751-3761` sets `waiting_for_approval` and enqueues `approval.request`, and the route is at `api_server_runs.py:238`. Drift from 583d5b407b (#121769).
3. **`developer-guide/gateway-session-lifecycle.md:173`**: the `switch_session` signature had no `preserve_prompt_pin`. It now shows `preserve_prompt_pin=True` and adds one sentence saying when callers pass `False`. Source: `gateway/session.py:1235-1238`. `/resume` (`gateway/slash_commands_session.py:902`) and the CLI handoff (`gateway/run_startup.py:1794`) pass `False`. Drift from 0ba9e1b7f0 (#126137).
4. **`developer-guide/multiplexing-gateway.md:282-283`**: said profile RPCs "run under the target profile's HERMES_HOME override". It now says `profiles.describe`, `profiles.configure` and `profiles.create`'s seeding run under the profile's full runtime scope (home + secrets + terminal). Source: `tui_gateway/methods_profiles.py:60-68` (`_hermes_home_scope()`), used at `:352`, `:497`, `:516`, `:531` and `:712`. Drift from 49064ce4dd (#126160).
5. **`developer-guide/multiplexing-gateway.md:127-128` and `:303`**: said the scope "merges the profile's `.env` with its configured secret sources" and that "a secondary resolves from its own files only". Both passages now include the administrator-managed `.env`, which is applied last with override. Source: `agent/secret_scope.py:391-419` (`build_profile_secret_scope()`), with the managed overlay at `:409-418`. Drift from b543b1053c (#126982).
6. **`user-guide/bot-mode.md:235-238`** (and zh-Hans `bot-mode.md:148`): said local delivery prefers the entrypoint next to the Python interpreter, then `PATH`. It now gives the order as the install's published launcher (`.hermes/bin/hermes`), then the interpreter sibling, then `PATH`. Source: `tools/bot_relay.py:502-517` (`_hermes_cli()`, published launcher at `:513`), used by `local_delivery_command()` at `:520-522`. Drift from 8024105d71 (#125559).

zh-Hans: only `bot-mode.md` has the affected passage, and it is updated here. The other four pages have no translated version of the changed text: `gateway-session-lifecycle.md` and `multiplexing-gateway.md` have no zh-Hans page, and the shorter zh-Hans `programmatic-integration.md` and `api-server.md` lack the affected table and row.

## Related Issue

No issue tracks these drifts. Supersedes my earlier single-item PRs #127355, #127356 and #127362 (closed in favour of this combined PR).

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/developer-guide/programmatic-integration.md`: add `partial` to the "Provider/agent failure" row of the terminal run status table.
- `website/docs/user-guide/features/api-server.md`: add `approval.request` to the `/api/sessions/{id}/chat/stream` row.
- `website/docs/developer-guide/gateway-session-lifecycle.md`: add `preserve_prompt_pin` to the `switch_session` signature, with one sentence on its use.
- `website/docs/developer-guide/multiplexing-gateway.md`: add the managed `.env` overlay to two secret-scope passages, and describe the full runtime scope for the profiles RPCs.
- `website/docs/user-guide/bot-mode.md` and `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/bot-mode.md`: list the published launcher first in the local-delivery launcher order.

## How to Test

1. For each item, read the cited source lines at f848940560. The old text contradicts them and the new text matches. On current `main` the cited code is unchanged; only `gateway/platforms/api_server.py` has moved, 17 lines further down.
2. Targeted test files, run on this branch (docs-only on top of f848940560): tests/gateway/test_session_chat_approval.py tests/gateway/test_resume_command.py tests/gateway/test_handoff_secondary_profile_adapter.py tests/tui_gateway/test_profiles_describe_secret_scope.py tests/hermes_cli/test_managed_scope_env.py tests/gateway/test_sse_agent_cancel.py -> 46 passed.
   - Items 2, 3 and 4 map to `test_session_chat_approval.py`, `test_resume_command.py` (with `test_handoff_secondary_profile_adapter.py`), and `test_profiles_describe_secret_scope.py`.
   - `test_managed_scope_env.py` covers the launch-process managed overlay (`load_hermes_dotenv`), not `build_profile_secret_scope()`. The scope-level test for item 5 is `tests/cron/test_cron_multiplex_desktop_ticker_scope.py`, which was not run.
   - `test_sse_agent_cancel.py` covers the neighbouring chat-completions path and backs none of the six items.
   - Item 1 is backed by an ad-hoc probe at f848940560. Calling `terminal_run_status()` on a failed-turn result with `partial=True` returned `('failed', {'completed': False, 'partial': True, 'interrupted': False})`. `tests/agent/test_retry_exhaustion_partial_retention.py` was not run.
   - Item 6: no test was run. It was checked by reading `tools/bot_relay.py`.
3. The Python steps of `docs-site-checks.yml` passed: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` was clean, and `python3 website/scripts/check_doc_links.py` returned OK. Not run: `npm run lint:diagrams` (no diagrams are touched) and `npm run build:fast`. The added lines have no MDX-sensitive `{}` or raw tags outside code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not done: only the targeted files listed above were run, since this is a docs-only change.
- [ ] I've added tests for my changes. N/A: documentation only.
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Based on f848940560. Merges cleanly onto main aeff051a18 (checked with `git merge-tree`). 6 files changed, 17 insertions(+), 11 deletions(-).
