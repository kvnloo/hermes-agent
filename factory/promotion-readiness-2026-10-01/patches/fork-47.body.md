## What does this PR do?

`parse_rate_limit_headers()` defaults an absent `x-ratelimit-remaining-<tag>` header to `0`. Zero is also the genuine "exhausted" signal, so a response that carries `x-ratelimit-limit-<tag>` without the matching `remaining` header is recorded as 100% used:

- The CLI `/usage` shows a fabricated `100.0%  800/800 used  (0 left, …)` bar and a `⚠ requests/min at 100%` warning. The gateway `/usage` shows `RPM: 0/800`. Both tell the user they are rate-limited when the provider never said so.
- The same `RateLimitState` is the `last_known_state` that `is_genuine_nous_rate_limit()` consults on a later 429. If the prior response sent `limit` + `reset` (≥ 60 s) but no `remaining`, a bare upstream-capacity 429 is classified as a genuine account limit and trips the cross-session Nous breaker.

The 429-header path in `nous_rate_guard._parse_buckets_from_headers()` already parses `remaining` with a `None` default. This PR makes the tracker do the same: an absent or unparseable `remaining` gives a "no data" bucket (`limit=0`), which is how a missing `limit` is already shown. `RateLimitState.has_data` now also requires at least one window with a limit. A state with no complete window therefore counts as no data: the gateway `/usage` leaves out the Rate Limits line instead of printing it empty, and the CLI `/usage` leaves out the rate-limit block. A `remaining` of `0` that is actually present still reports exhaustion.

## Related Issue

No upstream issue. Found by Detail and first fixed in the fork as kvnloo/hermes-agent#47 (detail-app[bot]). This is a rebuild of that fix on current main, where bucket construction has moved to a `_BUCKET_TAGS` comprehension. It keeps the same approach: a missing `remaining` gives a no-data bucket, and `has_data` requires a usable window. Searched open/closed PRs and issues for `x-ratelimit-remaining`, `rate_limit_tracker` and `parse_rate_limit_headers`. Open PRs that touch `agent/rate_limit_tracker.py` (#40460 `_fmt_count` negative guard, #128670 Anthropic unified headers, #78167 proactive throttle) do not change how a missing `remaining` is handled. #78167 adds a proactive throttle on exhausted buckets. With the current `0` default, that throttle would also fire on these limit-only buckets.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `agent/rate_limit_tracker.py`: per-bucket parsing moves to `_parse_bucket()`. An absent or unparseable `remaining` returns an empty (no-data) bucket instead of `remaining=0`. `RateLimitState.has_data` requires `captured_at > 0` and at least one bucket with `limit > 0`.
- `tests/agent/test_rate_limit_tracker.py`: one test. A limit-only response is not 100% used and `has_data` is false, while a present `remaining: 0` still renders 100% with the warning.
- `tests/agent/test_nous_rate_guard.py`: one test. A last-known state built from `limit` + `reset` with no `remaining` does not make a bare 429 genuine.

## How to Test

1. `scripts/run_tests.sh tests/agent/test_rate_limit_tracker.py tests/agent/test_nous_rate_guard.py -q`
2. Without the production change, both new tests fail: `assert 100.0 == 0.0` (usage_pct of the limit-only bucket) and `assert True is False` (`is_genuine_nous_rate_limit` trips on the partial last-known state).
3. Reverting only the `None` default for `remaining` brings back both failures. Reverting only the `has_data` change fails the tracker test on `assert not state.has_data`.

Adjacent suites pass with the change: `tests/gateway/test_usage_command.py`, `tests/hermes_cli/test_cli_status_bar.py`, `tests/agent/test_credits_cold_start.py`, `tests/agent/test_nous_welcome_client_contract.py`, `tests/agent/test_welcome_error_identity.py`, `tests/agent/test_welcome_tier_recovery.py` (139 tests in total across the 8 files). `ruff check` is clean on the touched files.

Runs were on main f848940. Main has since moved ahead with no changes to the touched files, and the branch merges cleanly. Not tested: the full `pytest tests/` suite, and a live provider response with partial headers. The behaviour is covered only by the two unit tests above.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (targeted files only, listed above)
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A
