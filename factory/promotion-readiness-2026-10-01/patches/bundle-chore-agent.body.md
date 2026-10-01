## What does this PR do?

Removes `_safe_text` from `agent/anthropic_message_convert.py`. Nothing on current `main` calls it.

The Anthropic request path no longer coerces blank text blocks in place. `_replay_text` / `_is_blank_text_block` drop them, and `_EMPTY_TEXT_PLACEHOLDER` is appended only when nothing survives. That left the old coerce-in-place helper with no callers. Its only references were its own unit tests (`TestSafeText`), and `agent.anthropic_adapter` no longer re-exports it. `bedrock_adapter._safe_text` is a separate helper that is still used, and this PR leaves it alone.

## Related Issue

No upstream issue. This is a dead-code cleanup, originally proposed downstream in kvnloo/hermes-agent#15 and rebuilt here on current `main`.

## Type of Change

- [x] ♻️ Refactor (no behavior change)

## Changes Made

- `agent/anthropic_message_convert.py`: delete `_safe_text` (8 lines).
- `tests/agent/test_anthropic_whitespace_text_blocks.py`: drop the `TestSafeText` cases for the deleted helper and the `pytest` import they left unused. The blank-block behaviour tests for `_sanitize_replay_block` / `_convert_assistant_message` stay.

## How to Test

1. Reference check on the branch: `git grep -n -w _safe_text` now matches only `agent/bedrock_adapter.py`, `tests/agent/test_bedrock_empty_text_blocks.py`, and a docstring in the whitespace test that names `bedrock_adapter._safe_text`. On `main` the only other hits are the definition and its own tests. The name is not in `tests/compat/old_updater_surface.json` (bare or guarded).
2. `scripts/run_tests.sh tests/agent/test_anthropic_whitespace_text_blocks.py tests/agent/test_anthropic_request_blank_block_guard.py tests/agent/test_anthropic_adapter.py tests/agent/test_bedrock_empty_text_blocks.py tests/agent/test_anthropic_thinking_block_order.py tests/agent/test_anthropic_output_field_leak.py tests/test_old_updater_compat_surface.py -q`: 684 passed, 0 failed. The whitespace file goes from 10 to 5 tests: the 5 removed are the `TestSafeText` cases (1 plain plus 4 parametrized).
3. `python -c "import agent.anthropic_message_convert, agent.anthropic_adapter, agent.bedrock_adapter"` imports cleanly. `ruff check` and `scripts/check-windows-footguns.py` are clean on both touched files.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate. No open PR uses `anthropic_message_convert._safe_text`. #71935 only has the old import as an unchanged context line, and the other `_safe_text` PRs touch bedrock's copy.
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not done: I ran only the targeted files listed above via `scripts/run_tests.sh`.
- [ ] I've added tests for my changes. N/A: pure deletion, and the remaining behaviour tests cover the live path.
- [x] I've tested on my platform: Linux (CachyOS, Python 3.11)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Tested on `main` @ `f8489405600c9a7d9d2f307dace086f18d7173ba`.

```
=== Summary: 7 files, 684 tests passed, 0 failed (100% complete) in 44.0s (20 workers) ===
```
