## What does this PR do?

A streamed Discord reply is finished with `edit_message(..., finalize=True)`. When the final text fits, the in-place branch records the delivery in the missed-message recovery ledger with `_record_response_async(reply_to_message_id, result, content, True)`. That marks the user's source message `responded` and advances the channel's backfill cursor.

A final reply over the 2,000-char cap goes through `_edit_overflow_split` from one of two early returns: the pre-flight length check, or a reactive 50035 length rejection after pre-flight passed. Both return before the ledger write. With `DISCORD_MISSED_MESSAGE_BACKFILL` enabled, every oversized final reply leaves its source message incomplete. Each reconnect re-evaluates it, and backfill can dispatch it again.

Both overflow returns now pass the split result through the same `_record_response_async` call as the in-place branch. A failed split is recorded as not completed and stays retryable, which matches what `send()` already does with its failures.

## Related Issue

No upstream issue or PR found for this gap. Searched PRs and issues for `_edit_overflow_split`, `_record_discord_response`, "oversized final reply ledger" and "discord overflow backfill".

Related, but a different change: #120094 (open) makes a failed overflow *continuation* return `success=False` so the stream consumer re-sends the tail. The two compose. With #120094, a partial split records "not completed", and the tail that the consumer re-sends goes through `send()`, which records completion.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `plugins/platforms/discord/adapter.py`: in `edit_message`, the pre-flight and reactive-50035 `finalize=True` overflow returns wrap `_edit_overflow_split(...)` in `_record_response_async(...)`.
- `tests/gateway/test_discord_missed_message_backfill.py`: new test `test_oversized_final_edit_records_recovery_completion`, with `[preflight]` (5,000 chars) and `[reactive_50035]` (first edit raises the 50035 length error) cases. Each asserts that the source message is persistently complete after the final edit.

## How to Test

1. `scripts/run_tests.sh tests/gateway/test_discord_missed_message_backfill.py -q -k oversized_final_edit`
2. On unpatched `main` both cases fail with `assert False is True` (`_discord_message_is_persistently_complete('93')`). `edit_message` itself returns `success=True`.
3. With the patch both pass. Reverting only the pre-flight wrap fails only `[preflight]`. Reverting only the reactive wrap fails only `[reactive_50035]`.
4. Adjacent: all 48 `tests/gateway/test_discord*.py` files give 317 passed. `ruff check` is clean.

Not tested: a live Discord bot (no token in the sandbox).

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the Discord gateway files listed above were run, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), Python venv

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
