## What does this PR do?

`GET /api/sessions/{id}/messages` returns a bare `500 Internal Server Error` when `state.db` is corrupt in the `messages` b-tree but the `sessions` primary key is intact.

`_resolve_session_id` already turns a malformed store into the 503 "run `hermes doctor`" response, but only for the resolve step (ba7743b / #99529). With this partial-corruption shape, resolve succeeds and `db.get_messages(...)` is the first read to hit the damage. Its `sqlite3.DatabaseError` leaves `get_session_messages` unclassified, so FastAPI's default 500 replaces the repair guidance. `GET /api/sessions` already maps a malformed store to the `state_db_corrupt` 503 (#120274), and `corrupt_store_as_status` produces the same payload plus the store `path` (current shape from #121428).

The fix sends a `sqlite3.DatabaseError` from the transcript read through the existing `corrupt_store_as_status` helper, using the same `with corrupt_store_as_status(...): raise` pattern this router already uses for `StateDbReplacedError`. Malformed-image errors become the shared 503 corrupt-store payload. Every other database error is re-raised unchanged. The helper and the profile path lookup only run on the exception path, so the happy path does no extra work.

## Related Issue

No upstream issue. Adapted from detail-app[bot]'s fix in kvnloo/hermes-agent#28. Rebuilt on current main to reuse `corrupt_store_as_status` instead of a second hand-written 503. Tests cut to the two contract tests and moved to `tests/hermes_cli/`.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `hermes_cli/web_routers/sessions.py` (`get_session_messages`): catch `sqlite3.DatabaseError` around the `asyncio.to_thread(_with_db, ..., _read)` call and re-raise it inside `corrupt_store_as_status(_session_db_path_for_profile(profile))`.
- `tests/hermes_cli/test_session_detail_malformed_db.py`: two tests.
  - A real `state.db` with the `messages` root page zeroed, driven through the mounted app with `TestClient`, now returns 503 with the `hermes doctor` guidance. On `main` it returns 500.
  - A non-corruption `DatabaseError` from the transcript read still propagates and is not relabelled.

## How to Test

1. `scripts/run_tests.sh tests/hermes_cli/test_session_detail_malformed_db.py -q`
   - On `main` (f848940), with only the tests applied: **1 failed, 10 passed**. `AssertionError: Internal Server Error — assert 500 == 503`.
   - With the fix: **11 passed**.
   - Negative control (classification removed, bare `raise` kept): the same test fails again with `assert 500 == 503`.
2. Adjacent: `scripts/run_tests.sh tests/hermes_cli/test_session_detail_malformed_db.py tests/hermes_cli/test_session_message_page_owner.py tests/hermes_cli/test_session_messages_inline_images.py tests/hermes_cli/test_history_commentary_display.py tests/hermes_cli/test_session_timeline.py tests/hermes_cli/test_web_analytics_corrupt_store.py tests/hermes_cli/test_web_server.py tests/e2e/core/dashboard/test_dashboard_sessions.py -q` → **8 files, 242 passed, 0 failed**.
3. `ruff check` on both touched files passes.

Not tested: the full suite, and how the Desktop transcript view renders the dict-shaped `detail`. The resolve-step 503 on this endpoint still returns `_resolve_session_id`'s string detail, so clients see a string or a dict depending on which b-tree is damaged.

Not covered here: `/timeline` and `/messages/around` read the `messages` table the same way and still return 500 on this store. They resolve the id through `_timeline_session_id` (an exact-id `_read_one`), not `_resolve_session_id`, so they also lack the resolve-step 503. Wrapping them would change how they report a damaged `sessions` index as well, which needs its own tests, so I left them for a follow-up. `/export` sends its first chunk before reading messages, so its status code cannot change.

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
