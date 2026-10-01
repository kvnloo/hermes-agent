## What does this PR do?

The Raft adapter (`plugins/platforms/raft/adapter.py`) keeps module-global sets of turn ids:

- `_RAFT_TURN_IDS`, for attributing hook payloads to Raft;
- `_RAFT_PROMPT_TURN_IDS`, for emitting one `UserPromptSubmit` per turn.

Only `_forget_raft_context(session_id, turn_id)` removes them, and it only gets a `turn_id` from the per-turn `on_session_end` that `agent/turn_finalizer.finalize_turn` fires. Some turns never reach `finalize_turn`. `agent/conversation_loop.py::_close_durable_failed_turn` lists the cases: the terminal-failure paths "(content-policy refusal, `_Trunc.end_turn`, retry exhaustion, interrupt before any assistant text) ... return without reaching `finalize_turn`". Those turn ids stay in both sets for the life of the gateway process. The session's own finalize (`gateway/run_shutdown.py::_finalize_session_off_loop` → `on_session_finalize`) carries no `turn_id`, so it removes only the session id.

This PR records which session registered each live turn (`_RAFT_TURN_SESSIONS`, turn id → session id). When a session is forgotten, every turn it still owns is released. The per-turn release also drops the mapping, so a normal turn leaves nothing behind, as before.

Behaviour change: after a session is finalized, a late per-turn hook for one of its turns counts as Raft only if the payload has `platform="raft"`. Before, the leftover turn id still matched.

## Related Issue

No upstream issue or PR found. Searched PRs and issues for `_RAFT_TURN_IDS`, "raft turn ids", "raft adapter leak" and "raft session_finalize". The turn-id sets and the turn_id-only release were introduced with the Raft plugin in #48210.

First flagged by an automated Detail scan on my fork (kvnloo/hermes-agent#44). This is a rework against current `main` with different bookkeeping and a single test.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `plugins/platforms/raft/adapter.py`:
  - adds `_RAFT_TURN_SESSIONS`, guarded by the existing `_RAFT_CONTEXT_LOCK`;
  - `_is_raft_context` (for an explicit `platform="raft"`) and `_on_pre_llm_call` record the owning session when they register a turn id;
  - `_forget_raft_context(..., forget_session=True)` releases every turn owned by that session from both sets and from the map.
- `tests/gateway/test_raft_adapter.py`: new test `TestRaftTurnTracking::test_session_finalize_without_turn_id_releases_the_sessions_turn_ids`. Two sessions each register a turn through `_on_pre_llm_call`. Finalizing one session with no `turn_id` releases its turn and leaves the other session's turn alone.

## How to Test

1. `scripts/run_tests.sh tests/gateway/test_raft_adapter.py -q`
2. On `main` at f848940560 (the touched files are unchanged on current `main`), the new test fails with `AssertionError: assert 't1' not in ({'t1', 't2'} | {'t1', 't2'})`.
3. With the patch, 8/8 pass. With only the `released.update(...)` line removed, the test fails again with the same assertion.
4. Other suites that exercise the Raft plugin (`tests/gateway/test_kanban_wake_acceptance.py`, `tests/plugins/platforms/test_interactive_setup_reconfigure_gate.py`, `tests/tools/test_spawn_site_child_env.py`) plus `test_raft_adapter.py`: 34 passed. `ruff check` clean.

Not tested: a live Raft bridge (needs the `raft` CLI).

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted files listed above were run, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), Python venv

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
