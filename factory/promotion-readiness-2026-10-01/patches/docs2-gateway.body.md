## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs: note partial flag on failed provider turns

- **Was:** website/docs/developer-guide/programmatic-integration.md:194 — "| Provider/agent failure | `failed` | `run.failed` | `completed: false`, `error` |"
- **Source on main:** agent/turn_recovery.py:1092 and :1240 set result["partial"] = True when _with_delivered_partial() keeps already-delivered text (non-retryable and retry-exhausted paths, #119001); gateway/platforms/api_server_runs.py:181 terminal_run_status() emits {"completed": finished, "partial": bool(result.get("partial")), ...} (:193) on every terminal event/status.
- **Check:** Probe on main: terminal_run_status(_failed_turn_result(...) + partial=True) -> ('failed', {'completed': False, 'partial': True, 'interrupted': False}); the doc row lists no partial.
- **Now:** Row now reads "`completed: false`, `error`, `partial` when applicable (e.g. reply text was already streamed before a retry-exhausted or non-retryable provider error)".
- **Mirrors:** website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/developer-guide/programmatic-integration.md has no terminal-run-status table (older, shorter translation) — nothing to mirror.
- Drift introduced by e947f60689 (#121628).

### docs: add approval.request to /api/sessions/{id}/chat/stream event list

- **Was:** website/docs/user-guide/features/api-server.md:617 — chat/stream row lists assistant.delta, assistant.commentary, tool.started, tool.completed, tool.failed, then terminal run.* (no approval.request).
- **Source on main:** gateway/platforms/api_server.py:3673 wires approval_notify = self._register_session_stream_approval(run_id, ...); :3751-3761 builds the approval.request event, sets status waiting_for_approval and events.enqueue("approval.request", event) (:3760); route POST /v1/runs/{run_id}/approval (api_server_runs.py:238).
- **Check:** Event list on main omits an event the handler enqueues.
- **Now:** Row now lists approval.request (run-id keyed, parks in waiting_for_approval until POST /v1/runs/{run_id}/approval). tests/gateway/test_session_chat_approval.py passes on main.
- **Mirrors:** website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/features/api-server.md has no /api/sessions chat/stream row — nothing to mirror.
- Drift introduced by 583d5b407b (#121769).

### docs: document preserve_prompt_pin on SessionStore.switch_session

- **Was:** website/docs/developer-guide/gateway-session-lifecycle.md:173 — "`switch_session(session_key, target_session_id, *, expected_session_id=None)`"
- **Source on main:** gateway/session.py:1235-1238 signature with preserve_prompt_pin: bool = True (docstring: pins follow non-boundary repoints by default); callers passing False: gateway/slash_commands_session.py:902 (/resume), gateway/run_startup.py:1794 (CLI handoff).
- **Check:** inspect.signature(SessionStore.switch_session) on main includes preserve_prompt_pin: bool = True; doc signature does not.
- **Now:** Signature + one sentence added. tests/gateway/test_resume_command.py and test_handoff_secondary_profile_adapter.py pass on main.
- **Mirrors:** No zh-Hans gateway-session-lifecycle.md.
- Drift introduced by 72a2271d0e (#126137).

### docs: correct profiles RPC scope binding description in multiplexing-gateway

- **Was:** website/docs/developer-guide/multiplexing-gateway.md:282-283 — "Reads and writes run under the target profile's HERMES_HOME override."
- **Source on main:** tui_gateway/methods_profiles.py:60-68 _hermes_home_scope(): 'Bind path's full runtime scope (home + secrets + terminal) ... Home alone is half-bound ... UnscopedSecretError' -> _session_profile_runtime_scope(...); used by profiles.describe (:352), configure (_configure_cfg_sections :712) and create's seeding (:497, :516, :531).
- **Check:** Doc describes the pre-#126160 half-bound behaviour.
- **Now:** Paragraph now names describe/configure/create seeding and the full runtime scope. tests/tui_gateway/test_profiles_describe_secret_scope.py passes on main.
- **Mirrors:** No zh-Hans multiplexing-gateway.md.
- Drift introduced by 49064ce4dd (#126160).

### docs: reflect managed .env overlay in multiplex secret scope description

- **Was:** website/docs/developer-guide/multiplexing-gateway.md:127-128 — "merges the profile's `.env` with its configured secret sources, skipping globals."; :303 — "a secondary resolves from its own files only."
- **Source on main:** agent/secret_scope.py:391-419 build_profile_secret_scope(): .env, then secret sources (globals skipped), then load_managed_env() applied last with override (:409-418, #111187).
- **Check:** Doc omits the managed overlay.
- **Now:** Both passages mention the managed .env overlay. tests/hermes_cli/test_managed_scope_env.py passes on main.
- **Mirrors:** No zh-Hans multiplexing-gateway.md.
- Drift introduced by b543b1053c (#126982).

### docs(bot-mode): correct local-delivery launcher resolution order

- **Was:** website/docs/user-guide/bot-mode.md:235-238 — "The transport prefers the Hermes entrypoint beside the sending runtime's Python interpreter ..."; zh-Hans bot-mode.md:148 same.
- **Source on main:** tools/bot_relay.py:502-517 _hermes_cli(): published = <install>/.hermes/bin/hermes(.exe) (:513) if it exists, else the sibling of sys.executable, else shutil.which('hermes'); local_delivery_command() uses it (:520-522).
- **Check:** Doc omits the first rung of the ladder.
- **Now:** en + zh-Hans now list published launcher -> interpreter sibling -> PATH.
- **Mirrors:** zh-Hans bot-mode.md:148 fixed in the same commit.
- Drift introduced by 5ce2c7d5aa (#125559).

## Related Issue

Supersedes our own parked docs PRs #127355, #127356, #127362 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `website/docs/developer-guide/gateway-session-lifecycle.md`
- `website/docs/developer-guide/multiplexing-gateway.md`
- `website/docs/developer-guide/programmatic-integration.md`
- `website/docs/user-guide/bot-mode.md`
- `website/docs/user-guide/features/api-server.md`
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/bot-mode.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: tests/gateway/test_session_chat_approval.py tests/gateway/test_resume_command.py tests/gateway/test_handoff_secondary_profile_adapter.py tests/tui_gateway/test_profiles_describe_secret_scope.py tests/hermes_cli/test_managed_scope_env.py tests/gateway/test_sse_agent_cancel.py -> 46 passed.
3. Docs CI equivalent: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run here: the Docusaurus build (`npm run build:fast`); added lines contain no MDX-sensitive `{}`/raw tags outside code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — targeted files only (listed above); docs-only change
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-gateway` @ c497e7abe5c3, 6 files changed, 17 insertions(+), 11 deletions(-).
