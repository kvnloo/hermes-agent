## What does this PR do?

`agent/turn_usage.py` adds ` cache=R/P (pct)` to the per-call `API call #N` log line only when the provider read something from cache. When a response has no usage at all, it logs `in=? out=? total=? … usage=unavailable`. All three readers of that line in `evals/postmortem/` require `cache=`, so every full miss disappears:

- `forensics/logcalls.py` leaves misses out of coverage and out of the hit ratio, which then reads too high. Its plateau and non-advancing figures can't see a miss either.
- `live_ab/cache_prefix_live.py` and `live_ab/cache_prefix_wire.py` leave misses out of their per-call rows, and `cache_prefix_live` also leaves them out of its per-arm hit %.

A model switch or a cache expiry produces exactly these misses, so the per-call cache report looks healthiest in the cases it is meant to investigate.

This PR:

- makes `cache=` optional, so a line without it counts as a zero-hit call;
- parses the `usage=unavailable` line and reports it on its own;
- reads `cache_state=` when the line has one.

So the parser already handles the line shape from #121135, where `cache_state=no_field` stays out of the ratio instead of reading as a miss. It also accepts the trailing `ttfb=` that #119713 adds.

Round trip on `main`: the real `record_response_usage`, writing through the real `agent.log` format, logged five responses (hit, miss, cold write, no cache field, no usage). The old regex matches 1 of the 5 lines and the new one matches all 5.

**One behaviour change.** On today's line (before #121135), a call where the provider reported zero cache reads and a call on a route that reports no cache counter at all are logged the same way: no `cache=`. In the round trip above, the miss line and the no-cache-field line are identical apart from the call number and `id=`. This parser counts both as zero-hit calls. Those calls used to be dropped. Now they count toward coverage and pull `cache_hit_ratio_overall` down, so a route that never reports cache telemetry shows up as 0% hit instead of being invisible.

That covers any route whose usage has no cache counter, because `normalize_usage` reads an absent field as 0. Examples are an OpenAI-compatible endpoint that leaves out `prompt_tokens_details`, and the Bedrock and native Gemini adapters, which write an absent cache count as an explicit 0 (see #121135's automated review). This is the conflation #84460 describes, now visible in the parser's output. Once a line carries `cache_state=no_field`, the parser leaves that call out of the ratio. For the Bedrock and Gemini paths, that also needs the adapter change suggested in that review.

## Related Issue

Refs #84460: the durable log line conflates a reported zero with missing telemetry.
Refs #121135, which adds `cache_state=` to the line. Its automated review notes that no parser reads the new states yet, because every reader requires `cache=`. This is that parser change.
Refs #119713, which appends `ttfb=` to the line.
The harness landed in #103756 (tracking issue #103563).

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `evals/postmortem/forensics/logcalls.py`
  - `_LINE`: the ` cache=R/P` group is optional, and `in=`/`out=`/`total=` also accept `?`.
  - `parse_logs` returns usage-less lines with `inp`/`out`/`hit` set to `None`, and records `cache_state` when the line has it.
  - `main()` keeps usage-less lines out of every token figure and out of the coverage fraction. `state.db`'s `api_call_count` does not count them either, because `record_response_usage` returns before it queues token counts.
  - Calls with `cache_state=no_field` stay out of the hit ratio, the buckets and the plateau pairs.
  - The `coverage` block gains `zero_hit`, `no_cache_field` and `usage_unavailable`, and the coverage print line shows them.
  - The docstring describes the optional fields. It does not mention the legacy-line ambiguity described above. I can add a sentence if you'd like it in the code.
- `evals/postmortem/live_ab/cache_prefix_live.py`, `evals/postmortem/live_ab/cache_prefix_wire.py`: the same regex with the `cache=` group optional. A row without it reads `cached=0`.
- `evals/postmortem/tests/test_postmortem_harness.py`: two tests on the existing synthetic `state.db`.
  - One uses the current line shapes: two hits, a miss and a usage-less line.
  - One uses the pending shapes: `cache_state=` with `cache_read=`/`cache_write=`, `ttfb=` after `upstream=`, a `no_field` call, and a usage-less line.

## How to Test

1. `scripts/run_tests.sh evals/postmortem/tests/test_postmortem_harness.py tests/agent/test_turn_usage_log_line.py -q` gives 8 passed (3 of 3 runs). With `main`'s `logcalls.py`, both new tests fail on the dropped lines: `assert 2 == 3` and `assert (2 == 4)` on `calls_found`.
2. Six of the changes in `logcalls.py` are pinned by a test. Reverting any one of these turns at least one test red:
   - the optional `cache=` group;
   - the `in=?` alternative;
   - the `no_field` filter;
   - the `cache_state` capture;
   - the ratio over calls with cache telemetry;
   - the plateau filter.

   No test pins the early-exit guard (`if not scored`), the coverage print line or the docstring. Reverting the guard to `if not calls` still passes every test. On input whose only calls are `cache_state=no_field`, the reverted guard would then divide by zero. As committed, the code prints a message and returns 1.
3. With #121135 and #119713:
   - Applied separately onto `main`, each merges cleanly with this branch (`git merge-tree`). The two of them conflict with each other in `agent/turn_usage.py`, which this PR does not touch.
   - On each merged tree, the real producer's five lines all parse with the new regex.
   - With #121135 applied, its `tests/agent/test_cache_log_states.py` plus `tests/agent/test_turn_usage_log_line.py` and the harness give 126 passed.
   - With #119713 applied, its `test_turn_usage_log_line.py` plus the harness give 10 passed.
4. Live probes: I pulled the exact regex out of each file with `ast` and replayed the same producer lines through it. The old regex reads 1 of the 4 usage-bearing rows, giving an arm hit of 40.0%. The new one reads 4 of 4: 40 cached of 400 input, or 10.0%. The probes don't read `cache_state=`, so the row with no cache field counts as 0 cached even when its line says `cache_state=no_field`. Leaving that row out, as `logcalls.py` does, would give 13.3% (40 of 300).
5. Synthetic `state.db` plus `agent.log` input, 420 calls:
   - When every call reads from cache, the `observed` and `modeled` blocks of `logcalls.json` are identical before and after the change.
   - With a model switch, three idle-gap misses per session and about 2% usage-less responses:

     | | coverage | hit ratio |
     |---|---|---|
     | old | 94.2% | 98.0% |
     | new | 100% | 93.1% (the corpus's true ratio) |

     These numbers depend on the miss rate I put into the synthetic data. They say nothing about any real run.

`evals/` is outside `testpaths`, so CI does not run the harness tests. I did not run the two live probes, because they make real provider calls.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate. Searches for `logcalls`, `cache_state` and `usage=unavailable` find no other open PR on these parsers. #121135 and #119713 change the line format but not its readers.
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not done: I ran only the targeted files above with `scripts/run_tests.sh`.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A. The `logcalls.py` docstring is updated. The README's reference output for the #102117 run was produced with the old regex and is left as a historical record.
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A. The new read uses `utf-8-sig`. `ruff check` and `scripts/check-windows-footguns.py --all` are clean. `--diff main` still lists four older `encoding="utf-8"` reads in the touched files, and this PR leaves them alone.
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

The coverage line on the synthetic input, before and after:

```
[logcalls] coverage 389/413 calls (94.2%) from 1 file(s)
[logcalls] coverage 413/413 calls (100.0%) from 1 file(s): 24 zero-hit, 0 without a cache field; 7 usage=unavailable not counted
```

```
=== Summary: 2 files, 8 tests passed, 0 failed (100% complete) ===
```

AI assistance: Claude Code wrote this change, its tests and this description, and ran the checks above locally. The commit sits on `main` @ `234badf401` and the checks ran there, except the early-exit check in step 2, which ran on `main` @ `aea969677c`. Step 1 and the merges and test counts in step 3 were re-run on `aea969677c`, and step 1 and the merges again on `main` @ `34f8ec3b40`, with the same results. Between `234badf401` and `34f8ec3b40`, no commit touches these files, `agent/turn_usage.py` or `hermes_logging.py`, and `agent/usage_pricing.py` changed only in its model alias table.
