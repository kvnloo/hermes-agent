## What does this PR do?

The Langfuse plugin bounds `_TRACE_STATE` (cap `_MAX_TRACE_STATE`) by evicting the **least-recently-updated** turn in `_get_or_start_state_locked`. Only the LLM-request path (and the retryable branch of `on_api_request_error`) refreshes `TraceState.last_updated_at`. `on_pre_tool_call`, `on_post_tool_call`, `on_subagent_start` and `on_subagent_stop` never do, so a live turn that has moved on to tool or subagent dispatch keeps the clock of its last LLM request.

When the cap is full, that live turn can be picked as the stalest entry ahead of turns that really are idle. Eviction ends its root span and drops its in-flight tool/subagent observation (the result is never recorded). The turn's next LLM request then opens a **second root trace for the same turn**. Nothing raises. `_MAX_TRACE_STATE` is 256, so this only happens in a long-running process (e.g. the gateway) that has built up about that many unfinished turn states.

This PR refreshes `last_updated_at` inside the existing `_STATE_LOCK` block of those four hooks, the same way the LLM-path hooks already do.

Scope note: the bump fires at dispatch start/end, so it fixes the ordering against turns that were idle before the dispatch. It does not keep refreshing during one very long tool call; that would need a heartbeat and is out of scope.

The source change was first proposed by detail-app[bot] (Detail) in kvnloo/hermes-agent#22. This PR rebuilds it on current main and replaces that PR's two regression tests (about 170 lines) with one parametrized test.

## Related Issue

No upstream issue found. Searched PRs and issues for `last_updated_at`, `langfuse evict(ion)` and `_MAX_TRACE_STATE`. #45326 (open) adds a TTL reaper keyed on the same `last_updated_at` clock but does not refresh it from the tool/subagent hooks, so the two changes are complementary. The per-turn state and cap were introduced in #48292.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `plugins/observability/langfuse/__init__.py`: adds `state.last_updated_at = time.time()` in `on_pre_tool_call`, `on_post_tool_call`, `on_subagent_start` and `on_subagent_stop`, inside the existing lock (4 lines).
- `tests/plugins/test_langfuse_plugin.py`: adds `TestTurnTraceIsolation::test_tool_and_subagent_activity_refreshes_eviction_clock[tool|subagent]`. The test caps state at 4 and pins the clocks so the live turn is the oldest. It then fires the dispatch hook, forces one eviction, and asserts that the live turn survives and its next LLM request reuses the same root trace. `TestAtexitFinalization` inherits this class, so the test runs twice.

## How to Test

1. `scripts/run_tests.sh tests/plugins/test_langfuse_plugin.py -q -k refreshes_eviction_clock`
2. With only the test change applied to `main` (fix reverted), all 4 collected cases ([tool] and [subagent], each under TestTurnTraceIsolation and TestAtexitFinalization) fail: `AssertionError: assert 'task:live:turn:live-turn' in {...}`, meaning the live turn was evicted.
3. With the patch, the same `-k` selection gives 4 passed, and `tests/plugins/test_langfuse_plugin.py`, `tests/plugins/test_langfuse_max_depth.py` and `tests/plugins/test_scoped_secret_readers_fail_closed.py` give 105 passed, 0 failed. `ruff check` is clean. (Run on `main` @ f8489405; no later upstream commits touch these files.)

Negative controls, each fix line reverted on its own:
- Without the `on_pre_tool_call` bump, the `[tool]` cases fail.
- Without the `on_subagent_start` bump, the `[subagent]` cases fail.

The `on_post_tool_call` and `on_subagent_stop` bumps follow the same pattern, but no test asserts them directly.

Not tested: a live Langfuse backend (the regression test uses a fake in-process client), and the full `scripts/run_tests.sh` suite.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted langfuse files were run (listed above), not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), Python venv

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
