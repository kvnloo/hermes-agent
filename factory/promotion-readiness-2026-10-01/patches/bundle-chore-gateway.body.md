## What does this PR do?

Removes three groups of gateway-side symbols that have no production caller on current `main`. Their only references were their own tests.

- **`gateway/run.py::_start_cron_ticker`**: the DEPRECATED shim kept when the `CronScheduler` provider landed (#48275). `start_gateway()` now runs `cron_provider.start` on a `SupervisedTickerThread` inside `_start_gateway_start_cron_and_housekeeping`. Nothing imports the shim any more, including `hermes_cli/debug.py`, which was the caller it was originally kept for.
- **`gateway/shutdown_forensics.py::context_as_json`**: production renders the shutdown snapshot only through `format_context_for_log`. The JSON serializer is never called.
- **`gateway/platforms/yuanbao_proto.py`**: `PB_MSG_TYPES`, `BIZ_SERVICES`, `encode_conn_msg`, `decode_biz_msg`. These are unused tables and thin wrappers. `encode_conn_msg_full` / `decode_conn_msg` (both still used) cover the same encoding byte-for-byte.

There is one test-quality fix in the same files. The three "cron must not start after an aborted startup" guards (four test cases; `test_start_gateway_classifies_startup_signal_exit` is parametrized) in `tests/gateway/test_startup_restart_race.py` patched `_start_cron_ticker`, which `start_gateway()` never calls, so their `cron_started is False` assertions could not fail. They now patch the real seam, `_start_gateway_start_cron_and_housekeeping`.

## Related Issue

No upstream issue. Supersedes my earlier PRs #127352 (`_start_cron_ticker`) and #127353 (`context_as_json`), which I closed to combine them with the yuanbao cleanup. The changes were first proposed in my fork as kvnloo/hermes-agent#284, kvnloo/hermes-agent#285 and kvnloo/hermes-agent#115 (rebuilt on current main as kvnloo/hermes-agent#298).

Overlap with open PRs: #67198 (arimu1, open since 2026-07-18) adds `test_start_cron_ticker_shim_forwards_kwargs_to_inprocess_provider`, whose docstring keeps the shim for `hermes_cli/debug.py`. That caller no longer exists on `main`. If this lands, that one test should be dropped. #67198's other three tests target `InProcessCronScheduler` and are unaffected. #77735 moves the shim and `_start_gateway_housekeeping` into a new `gateway/housekeeping.py`. It is based on a much older `run.py` and would need to drop the shim if this lands. #8367, #18763, #26734, #39577 and #54351 edit the pre-provider `_start_cron_ticker` and are stale against `main`. #112508 (salvaged and merged as #113075) and #59929 mention `context_as_json` only in tests; neither adds a production caller. No open PR references the four yuanbao names. #29077 and #115424 touch the yuanbao modules but use none of them.

## Type of Change

- [x] ♻️ Refactor (no behavior change)

## Changes Made

- `gateway/run.py`: delete `_start_cron_ticker` (7 lines).
- `tests/cron/test_scheduler_provider.py`: drop `test_ticker_calls_tick_at_least_once_then_stops`. It drove the shim, and `test_inprocess_provider_ticks_and_stops` already asserts the same tick(`sync=False`)-then-stop contract on `InProcessCronScheduler` directly. The module docstring now names the real entry points.
- `tests/gateway/test_startup_restart_race.py`: repoint the three cron-start guards (four test cases; `test_start_gateway_classifies_startup_signal_exit` is parametrized) from `gateway.run._start_cron_ticker` to `gateway.run._start_gateway_start_cron_and_housekeeping`.
- `website/i18n/zh-Hans/.../developer-guide/cron-internals.md`: the Gateway integration paragraph still named `_start_cron_ticker`. It now follows the English page (provider resolved via `resolve_cron_scheduler()`, built-in `InProcessCronScheduler` ticks every 60 s).
- `gateway/shutdown_forensics.py`: delete `context_as_json` and its now-unused `json` import.
- `tests/gateway/test_shutdown_forensics.py`: drop the serializer unit test. The #112459 argv-canary regression now asserts the canary is absent from `repr(ctx)`, which covers the whole snapshot, instead of going through the dead serializer.
- `gateway/platforms/yuanbao_proto.py`: delete `PB_MSG_TYPES`, `BIZ_SERVICES`, `encode_conn_msg`, `decode_biz_msg`.
- `tests/gateway/test_yuanbao_proto.py`: call `encode_conn_msg_full` / `decode_conn_msg` directly. The fixed-bytes protocol assertions are unchanged. `test_yuanbao_integration.py` no longer touches the proto helpers on `main`, so it needs no edit. The older fork variant (kvnloo/hermes-agent#115) rewrote it, and that hunk is intentionally not carried.

## How to Test

1. Reference check: on the branch, `git grep -n -w` for `_start_cron_ticker`, `context_as_json`, `PB_MSG_TYPES`, `BIZ_SERVICES`, `encode_conn_msg`, `decode_biz_msg` returns nothing. On `main` the only hits are the definitions, their tests, three test monkeypatch strings, and the zh-Hans doc line. That covers definitions, imports, `__all__`, tests, monkeypatch/`patch()` strings, getattr/string dispatch, `plugins/`, `optional-skills/`, `website/` and `scripts/`. None of the names are in `tests/compat/old_updater_surface.json` (`bare`, `guarded_only` or `unresolved_dynamic`).
2. `scripts/run_tests.sh tests/cron/test_scheduler_provider.py tests/gateway/test_startup_restart_race.py tests/gateway/test_cron_profile_gate.py tests/gateway/test_cron_ticks_every_profile.py tests/gateway/test_shutdown_forensics.py tests/gateway/test_planned_stop_watcher.py tests/gateway/test_launchd_exit_timeout_drain_cap.py tests/gateway/test_yuanbao_proto.py tests/gateway/test_yuanbao_integration.py tests/gateway/test_yuanbao_pipeline.py tests/gateway/test_yuanbao_forwarded_heartbeat.py tests/gateway/test_yuanbao_shutdown.py tests/test_old_updater_compat_surface.py -q`: 715 passed, 0 failed, 1 skipped (macOS-only). On `main` the same files give 717 passed. The difference is the two deleted tests for deleted helpers.
3. Repointed guard is live: with `start_gateway()`'s aborted-startup early returns temporarily forced off, all four guarded cases fail at the cron-start call (`TypeError: cannot unpack non-iterable NoneType object` from the patched seam). They pass again once restored.
4. `repr(ctx)` assertion is live: making `_proc_summary` temporarily store the child's argv under a new key fails `test_snapshot_and_log_line_identify_process_without_argv` on the `repr(ctx)` half, while the log-line half still passes.
5. `python -c "import gateway.run, gateway.shutdown_forensics, gateway.platforms.yuanbao_proto, gateway.platforms.yuanbao, cron.scheduler_provider"` imports cleanly. `ruff check` is clean on the touched files. `check-windows-footguns.py` reports only the two pre-existing `encoding='utf-8'` reads in `test_shutdown_forensics.py`, which are identical on `main`.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate. Overlap notes are in Related Issue.
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not done: I ran only the targeted files listed above via `scripts/run_tests.sh`.
- [ ] I've added tests for my changes. N/A: removal-only change, no new tests. The three existing cron-start guards are repointed so they can fail.
- [x] I've tested on my platform: Linux (CachyOS, Python 3.11)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A (zh-Hans cron-internals line)
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Tested on `main` @ `f8489405600c9a7d9d2f307dace086f18d7173ba`.

```
=== Summary: 13 files, 715 tests passed, 0 failed, 1 skipped (100% complete) in 58.5s (20 workers) ===
```

Branch base is `f8489405`. `main` @ `aeff051a` has not changed any of the eight touched files since then, so the branch merges cleanly, and the step-1 grep still finds nothing in the merged result: on `aeff051a` every hit is in one of those eight files, and the branch removes them all. Tests were not re-run on that SHA.
