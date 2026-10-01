## What does this PR do?

Adds one opt-in shared-metrics counter, `hermes.memory.prefetch.count`, for the turn-start recall of the external memory provider.

`MemoryManager._prefetch_provider` makes the turn wait on the external provider for up to the prefetch timeout (8 s). It can exit five ways: context returned, nothing returned, the provider raised, the timeout hit, or the provider was skipped because its previous call is still running. None of these exits recorded anything. When a provider times out on most turns, the only sign is a log warning. In #124151 the author had to time Hindsight's recall endpoint by hand to find that the 8 s bound dropped prefetch on nearly every turn, and #120042 found the same thing in a production audit (18–27 s recalls, about 53 dropped prefetches in one day).

The counter sits beside `hermes.memory.op.count`, which the memory tool and provider tool calls already feed (25c1b008c8). It follows the same pattern: a builder in `shared_metrics_loop.py`, a contract entry, a schema def, and a row in the "what is collected" table.

| Dimension | Values |
|---|---|
| `provider` | a bundled memory plugin name, else `plugin` (the rule `memory.op.count` uses) |
| `outcome` | `success`, `empty`, `failed`, `timed_out`, `skipped` |
| `latency_bucket` | how long the turn waited on the provider, in the tool-call buckets `lt_100ms` … `gte_30s` |

The row is recorded on the caller's thread at each of these five exits. A stuck call that returns late therefore adds no second row, and the row lands in the profile that owns the turn. The call site passes the raw return value, and the builder decides between `success` and `empty` inside the recording guard, so the metric cannot raise into the prefetch path. The builtin branch is unchanged. The background review, curator and delegate children run with `skip_memory=True`, so they never prefetch and add no rows. The query and the recalled text are never recorded. Nothing is recorded unless `telemetry.shared_metrics.enabled` is on.

## Related Issue

No tracking issue. Related:

- #124151 raises the Hindsight prefetch bound after measuring it by hand, and #120042 raises the default bound to 12 s after a production audit. This counter would have shown the `timed_out` rate directly. Each of them merges cleanly with this PR. With either one applied, every test in `tests/hermes_cli/test_shared_metrics_loop.py` and `tests/agent/test_memory_provider.py` passes: 74 of 74 with #124151 and 72 of 72 with #120042. Under #124151's 20 s bound, a Hindsight timeout would land in `10s_to_30s`, as provider `plugin`, because Hindsight is not a bundled provider. That follows from the bucket and provider rules; I did not run that path.
- One open PR, #92118, conflicts with this one in `agent/memory_manager.py`. It rewrites the `if result and result.strip():` line right after the success/empty record call, and it lets a provider return a structured result. Keeping both sides' lines resolves the conflict. With both merged, a structured result would count as `empty` until the builder reads its `.context`. That is a one-line follow-up for whichever PR lands second.
- #125881 merges cleanly, but its memory-admission check runs right after the success/empty record call. With both merged, a recalled context that the check blocks would still be counted as `success`. I found this by reading the merged code and did not run it.

## Type of Change

- [x] ✨ New feature (non-breaking change that adds functionality)

## Changes Made

- `agent/memory_manager.py`: `_prefetch_provider` records one row at each of the five exits above. The return exit passes the raw result. The skip check now records outside `_external_prefetch_lock`, so no telemetry call runs while the lock is held. One case is not covered: if the prefetch thread cannot be started at all (`thread.start()` raises), the exception propagates as it does on `main` and no row is written.
- `hermes_cli/observability/shared_metrics_loop.py`: adds `memory_prefetch_fields` and `record_memory_prefetch`. A `success` whose returned value holds no text becomes `empty`.
- `hermes_cli/observability/shared_metrics_contract.py`: adds `MEMORY_PREFETCH_MARK` and `MEMORY_PREFETCH_METRIC`, the `MEMORY_PREFETCH_OUTCOMES` set, the dimension map entry and the mark-to-counter projection.
- `hermes_cli/observability/schemas/hermes.shared_metrics.v3.schema.json`: adds `memory_prefetch_counter` and references it from `metrics.items`.
- `website/docs/developer-guide/relay-shared-metrics.md`: adds a table row next to `hermes.memory.op.count`.
- `tests/hermes_cli/test_shared_metrics_loop.py`:
  - One new test drives all five exits through `MemoryManager.prefetch_all` and reads the rows back from the real store. It checks that the timed-out exit waited out the whole timeout and that every other exit returned sooner. The timeout is 2 s, so every wall-clock bound in the test is at least 2 s, as the timing-test rule in AGENTS.md asks. As a result the test takes about 2 s.
  - The existing collection-off test now also runs a prefetch and checks that no row appears.

## How to Test

1. `scripts/run_tests.sh tests/hermes_cli/test_shared_metrics_loop.py -q`
2. To see it fail without the change, keep the test file and check out `main`'s versions of the five other files, then rerun step 1. `test_external_prefetch_records_each_exit_with_how_long_the_turn_waited` fails with `assert [] == [('honcho', 'success', 1), ...]`.
3. Neighbouring tests: `scripts/run_tests.sh tests/agent/test_memory_provider.py tests/agent/test_turn_context.py tests/hermes_cli/test_relay_shared_metrics.py tests/hermes_cli/test_relay_shared_metrics_runtime.py -q`

What I ran (Linux, Python 3.11 venv, nemo-relay 0.8.4):

- **Without the change:** 15 of the 16 tests in the file pass, and the new test fails.
- **With the change:** 16 of 16 pass, three runs in a row.
- **Reverting one piece at a time:** 10 of 10 single reverts make the new test fail, and the rest of the file still passes. The reverts were:
  - each of the four record calls;
  - the mark-to-counter projection;
  - the provider-name rule;
  - an outcome-name typo;
  - the `empty` rule;
  - a latency of 0;
  - a constant latency above the timeout.
- **Slow runner:** the new test still passes with every fake provider slowed by 1.5 s.
- **12 neighbouring test files:** 330 of 330 pass on `main`, and 331 of 331 pass with the change (the extra one is the new test).
- **Fake memory backend:** I also ran a local HTTP fake with delay, slow-past-timeout, hang, empty, HTTP 500 and connection-refused faults, through `_memory_turn_start_and_prefetch` and the real Relay binding. Results:
  - every turn wrote exactly one row with the expected outcome;
  - a hung provider gave one `timed_out` row (`1s_to_2s` at a 1 s timeout, `5s_to_10s` at the shipped 8 s), then `skipped` rows while it stayed stuck;
  - the context returned to the turn was byte-identical with and without the change;
  - a profile with collection off created no store at all.
- **Real bundled provider:** `holographic` with 20 turns gave 10 `success` and 10 `empty` rows under the provider label `holographic`.
- **Cost:** I ran a microbenchmark of `_prefetch_provider` alone on a shared host.
  - The change adds about 38 µs per call with collection off and about 111 µs with it on.
  - Over the same blocks, the A/A difference ranged from about −3 to +1 µs off and −3 to +11 µs on (5th to 95th percentile).
  - In a second run, swapping the record call for a no-op brought the off delta down to about 2 µs, so nearly all of the cost is the record call.
  - Measured alone, the record call costs about the same as the existing `record_execution_backend` call.
  - It runs once per turn per external provider, and the turn already waits 0.2 ms to 8 s on that provider.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (I ran the targeted files above, not the full suite)
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux x86_64, Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Not tested:

- Python 3.14 with nemo-relay 0.9, the runtime that ships shared metrics. My runs used Python 3.11 and nemo-relay 0.8.4.
- Hosted memory backends (Honcho, Hindsight, mem0, Supermemory) over a real network.
- Sending packages. All runs used `send: false`.
- Windows and macOS.

The holographic provider returns `""` when its own recall fails, so a failure there shows as `empty`, not `failed`. That is how the provider behaves; the metric reports what it returns.

The code, the tests, the test and benchmark runs, and this description were done with Claude Code (AI-assisted). I reviewed the diff and the test results.
