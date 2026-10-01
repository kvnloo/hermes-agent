## What does this PR do?

The lean anchor index (`_build_anchor_index`) is the compressor's LLM-free safety net for exact identifiers. The Jev scorecard (`evals/compaction/results/SCORECARD-2026-09-19-jev.md`) traced the summary's misses to identifiers in assistant text: delegation ids, config keys and exact error strings. It called them "a summariser-retention target (anchor index / identifier capture)". Delegation ids and config keys match no row in `_ANCHOR_PATTERNS` today, and exact error strings only match when they contain an exception name, so the index drops the rest no matter how much budget is left.

This PR adds three rows:

| row | captures | stays out |
|---|---|---|
| `task ids` | `sa-2-7318d0ba` (delegate_tool), `t_4f9c2a1e` (kanban) | hex fragments inside longer words |
| `dotted keys` | `plugins.stream_reasoning_deltas`, `compression.tail_mode`, `hermes_cli.dashboard_auth` | `config.yaml`, `context_compressor.py`, `api.openai.com`, `e.g.` (the last segment must be snake_case). Fragments such as `router.add_post` inside `self._app.router.add_post`: a match never starts right after `x.` |
| `error messages` | CLI error lines: `fatal: …`, `error: …`, `error TS2741: …`, gh's `GraphQL: Pull Request has merge conflicts (mergePullRequest)`. Hermes tool refusals: ``Blocked: `git checkout` would rewrite …`` | `TypeError: …` and other exception names, which the existing `errors` row already covers. Python annotations (`error: Exception)`) and log formats (`"error: %s"`): `fatal:`/`error:` only count where a line starts, after a quote or backtick, or after an escaped `\n` in JSON tool output. |

The rows go after the existing ones. Every existing section keeps its exact line under the shared 7,000-char budget, and the new sections only use what is left. There is no prompt, cadence, budget or config change. Scope is local-compressor routes in lean tail mode only: legacy mode doesn't build the index, and native compaction summaries are opaque.

**Where the classes come from.** The 90 gold answers committed in `SCORECARD-2026-08-15.md` include 49 identifiers. Written in plain text, 24 of the 49 match a current row; 31 match with these rows. The 7 new matches are:
- 5 error lines, which are only 2 distinct strings: the `Blocked:` git-guard refusal (3) and one gh merge-conflict error (2)
- 1 subagent id
- 1 config key

The rows were written after reading those golds, so this is an in-sample count, not a held-out result. It only checks that the gold strings match a row; it does not measure recall. The 09-19 scorecard asks to check the index's coverage on its prreview/sysprompt/sigsegv banks first. Those banks aren't committed, so that check wasn't run. The recall exam wasn't run either, because it needs the aux model; the commands are below if you want numbers before merging.

**Relationship to #117462.** That PR changes the same function: it harvests tool-call arguments, puts cheap ids first, truncates per section instead of `break`ing, and adds session ids, todo ids and more path extensions. It covers different classes in the same table. I offered these rows there as a fold-in first, appended after its last row so none of its lines change; this is the standalone version. With both applied, 7 of 7 tests in the two test files pass (its 5 and these 2). If #117462 lands first, this needs a small rebase of the table.

The cost of appending: the new sections only get the budget the existing ones leave, so in dense regions they get little or nothing. On main the loop also `break`s at the first section that doesn't fit, so a new section that overflows is dropped whole. #117462's per-section truncation keeps the first values of such a section, but the rows still come last there, so dense regions stay mostly out of reach.

`dotted keys` also misses config keys whose last part is one word, such as `terminal.backend` or `compression.enabled`. That's 270 of the 996 dotted key paths in `DEFAULT_CONFIG` (27%; 212 of 870 if you count only leaf settings). The snake_case rule that keeps file names and hosts out is what drops them.

## Related Issue

Refs #116246 (scorecard), #87326 (lean tail and recall exam), #117462 (same function, complementary)

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `agent/context_compressor.py`: three rows appended to `_ANCHOR_PATTERNS` (+10 lines with comments).
- `tests/agent/test_context_compressor_anchor_index.py`: two tests.
  - The new classes are captured verbatim from assistant text and from JSON terminal output, and an error value stops at the escaped newline.
  - File names, hosts, `e.g` and mid-name fragments are not caught as dotted keys. Annotations and `%s` log formats are not caught as error messages. Each new section respects its cap, and sections stay inside `_LEAN_ANCHOR_BUDGET_CHARS`.

## How to Test

1. `scripts/run_tests.sh tests/agent/test_context_compressor_anchor_index.py`: 2 of 2 tests pass (3 runs). On main both fail (`AssertionError: 'sa-2-7318d0ba' missing from anchor index`, `assert 'compression.tail_mode' in ''`). Removing any one of the three rows turns the tests red again. So does loosening the error row's line-start rule or its `%s` guard, or letting a dotted key start mid-name.
2. Neighbouring files: 365 of 365 tests pass on main and on this branch (the branch run adds the 2 new tests, which pass too):
   - `tests/agent/test_context_compressor.py`
   - `test_lean_single_aux_call.py`
   - `test_compression_rotation_state.py`
   - `test_context_compressor_summary_continuity.py`
   - `test_compaction_redaction_boundaries.py`
   - `test_native_compaction_summary_retention.py`
3. `python evals/compaction/test_region_scoping.py` gives ALL PASS. `python evals/token_accounting/replay_gates.py`: 11 of 11 gates pass, with the same results as main apart from the compressor file hash.
4. Optional recall exam (not run; uses `auxiliary.compression`). Use the same transcript, and copy the cached `questions-*.json` into each out dir so both checkouts answer the same bank. Run 3 reps per transcript from main and from this branch:
   `python evals/compaction/runner.py --transcript <lineage.json> --policies current+recovery --questions 30 --out <dir>`

Other checks:
- On a seeded synthetic region of about 443K chars, the three new patterns take about 0.045 s together. On main that region already hits the `break` before the new rows, so the build stays at about 0.03 s; on a region where every section fits, the rows add that time.
- On one tool message holding a 40K-char `a.a.a…` chain, the `dotted keys` row takes about 1 ms, and about 7 ms at 200K chars. Without the mid-name rule it took 6.2 s at 40K chars and grew quadratically. The whole index takes about 2.6 s on that input with or without the new rows; that time is the existing `files` row, which this PR doesn't change.
- In 180 seeded synthetic regions, this branch's index peaked at 7,190 chars including the heading, about 1.8K tokens at 4 chars per token. The loop can't go over the 7,000-char section budget by construction, so that part is not a finding.
- On `website/docs` + `AGENTS.md` (7.8M chars), `task ids` matched only 2 distinct doc examples. `error messages` matched 9 times: 7 quoted messages or message examples, 1 code example and 1 type annotation in a table (`error: str | None`).
- On `agent/*.py`, `error messages` matches 2 strings: one error-message template (`turn_tool_validation.py`) and one docstring line (`file_safety.py`). `Blocked:` counts anywhere in a line, not only at the start, so prose or a docstring that uses `Blocked: ` that way is caught too. An earlier version of the row, without the line-start rule and the `%s` guard, matched 80, nearly all annotations and log formats.
- About 30% of distinct `dotted keys` values in the docs are `DEFAULT_CONFIG` keys; the rest are dotted API names like `ctx.register_hook`. That's why the label is "dotted keys". On Python source the row mostly picks up attribute access (`self.base_url`, `agent.session_id`). In a region full of `read_file` output it can crowd out real config keys.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate (#117462 overlaps the function, not these classes; see above)
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

## Screenshots / Logs

On main (tests only), 0 of 2 tests pass:

```
FAILED tests/agent/test_context_compressor_anchor_index.py::test_anchor_index_keeps_task_ids_config_keys_and_error_messages_verbatim
FAILED tests/agent/test_context_compressor_anchor_index.py::test_new_anchor_classes_stay_exact_and_bounded
2 failed
```

With the rows, 2 of 2 tests pass (`2 passed`, 3 runs).

AI assistance: Claude Code (Claude Opus 5.5) wrote the change, the tests and this description, and ran the checks described above.
