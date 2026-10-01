## What does this PR do?

`GET /api/sessions/{id}/messages`, `/timeline` and `/messages/around` return a bare `500 Internal Server Error` when `state.db` is corrupt in the `messages` b-tree but the `sessions` primary key is intact.

Each endpoint looks the session up first, and that lookup only reads the `sessions` b-tree. `/messages` uses `_resolve_session_id`, which already turns a malformed store into the 503 "run `hermes doctor`" response, but only for the resolve step (ba7743b / #99529). `/timeline` and `/messages/around` use `_timeline_session_id`, an exact-id read with no classifier. With this partial-corruption shape the lookup succeeds, and the transcript read (`db.get_messages(...)` or the `hermes_state_timeline` queries) is the first query to hit the damage. Its `sqlite3.DatabaseError` escapes the handler unclassified, so FastAPI's default 500 replaces the repair guidance. `GET /api/sessions` already maps a malformed store to the `state_db_corrupt` 503 (#120274), and `corrupt_store_as_status` produces the same payload plus the store `path` (current shape from #121428).

The fix adds a small `_read_transcript(profile, fn)` helper and routes all three transcript reads through it. It wraps the existing read-only `asyncio.to_thread(_with_db, ...)` call and re-raises a `sqlite3.DatabaseError` inside `corrupt_store_as_status`, using the same `with corrupt_store_as_status(...): raise` pattern this router already uses for `StateDbReplacedError`. Malformed-image errors become the shared 503 corrupt-store payload. Every other database error is re-raised unchanged. The helper and the profile path lookup only run on the exception path, so the happy path does no extra work.

A side effect on `/timeline` and `/messages/around`: a damaged `sessions` b-tree also returned 500 there, because `_timeline_session_id` has no classifier. It now returns the same 503. `/messages` is unchanged in that case, since `_resolve_session_id` already returns its own 503.

## Related Issue

No upstream issue. Adapted from detail-app[bot]'s fix in kvnloo/hermes-agent#28 (credited with a `Co-authored-by` trailer). Rebuilt on current main to reuse `corrupt_store_as_status` instead of a second hand-written 503, and extended to the two sibling transcript endpoints. Tests cut to two contract tests and moved to `tests/hermes_cli/`.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `hermes_cli/web_routers/sessions.py`:
  - new `_read_transcript(profile, fn)` next to `_with_db`: a read-only `_with_db` call off the event loop, with `sqlite3.DatabaseError` re-raised inside `corrupt_store_as_status(_session_db_path_for_profile(profile))`.
  - `get_session_messages`, `get_session_timeline` and `get_session_messages_around` call `_read_transcript` instead of `asyncio.to_thread(_with_db, ..., read_only=True)`.
- `tests/hermes_cli/test_session_detail_malformed_db.py`: two tests.
  - A real `state.db` with the `messages` root page zeroed, driven through the mounted app with `TestClient`, parametrized over `/messages`, `/timeline` and `/messages/around?row_id=1`. All three now return 503 with the `hermes doctor` guidance. On `main` all three return 500.
  - A non-corruption `DatabaseError` from the transcript read still propagates and is not relabelled.

## How to Test

Branch: `ready/fork-28-messages-btree-corrupt-503-v2` (one commit).

1. `scripts/run_tests.sh tests/hermes_cli/test_session_detail_malformed_db.py -q`
   - On `main` (330d9d6df9), with only the tests applied: **3 failed, 10 passed**. Each parametrized case fails with `AssertionError: Internal Server Error — assert 500 == 503`. With `raise_server_exceptions=True` all three raise `sqlite3.DatabaseError: database disk image is malformed`.
   - With the fix: **13 passed**. Re-run after rebasing on `main` ffc74885c5: **13 passed**.
   - Negative control 1 (the helper's `with corrupt_store_as_status(...): raise` replaced by a bare `raise`): the three parametrized cases fail again with `assert 500 == 503`.
   - Negative control 2 (the helper turns every `DatabaseError` into a 503): `test_messages_read_non_corruption_error_is_not_relabelled` fails with an unexpected `HTTPException: 503`.
2. Adjacent: `scripts/run_tests.sh tests/hermes_cli/test_session_detail_malformed_db.py tests/hermes_cli/test_session_message_page_owner.py tests/hermes_cli/test_session_messages_inline_images.py tests/hermes_cli/test_history_commentary_display.py tests/hermes_cli/test_session_timeline.py tests/hermes_cli/test_web_analytics_corrupt_store.py tests/e2e/core/dashboard/test_dashboard_sessions.py -q` → **7 files, 52 passed, 0 failed**. I also ran the session tests in `tests/hermes_cli/test_web_server.py` (`-k "session and not update and not restart and not spawn and not launch"`) → **37 passed, 0 failed**.
3. Manual check with the `sessions` root page zeroed instead: `/timeline` and `/messages/around` return 500 on `main` and the `state_db_corrupt` 503 with the fix. `/messages` returns `_resolve_session_id`'s 503 on both.
4. `ruff check` on both touched files passes.

Not tested: the full suite, the rest of `test_web_server.py`, and how the Desktop transcript and timeline views render the dict-shaped `detail`. The resolve-step 503 on `/messages` still returns `_resolve_session_id`'s string detail, so clients see a string or a dict depending on which b-tree is damaged.

Not covered here: `/export` sends its first chunk before it reads messages, so its status code cannot change.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted and adjacent files listed above were run, not the full suite.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A. This is pure-Python exception routing with no OS calls.
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
