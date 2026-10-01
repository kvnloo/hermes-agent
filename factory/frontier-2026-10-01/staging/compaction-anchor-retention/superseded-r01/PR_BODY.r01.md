## What does this PR do?

The lean anchor index (`_build_anchor_index`) is the compressor's LLM-free safety net for exact identifiers. The Jev scorecard (`evals/compaction/results/SCORECARD-2026-09-19-jev.md`) traced the summary's misses to identifiers in assistant text: delegation ids, config keys and exact error strings. It called them "a summariser-retention target (anchor index / identifier capture)". None of those three classes matches a row in `_ANCHOR_PATTERNS` today, so the index drops them no matter how much budget is left.

This PR adds three rows:

| row | captures | stays out |
|---|---|---|
| `task ids` | `sa-2-7318d0ba` (delegate_tool), `t_4f9c2a1e` (kanban) | 8-hex fragments inside other words |
| `dotted keys` | `plugins.stream_reasoning_deltas`, `compression.tail_mode`, `hermes_cli.dashboard_auth` | `config.yaml`, `context_compressor.py`, `api.openai.com`, `e.g.`, because the last segment must be snake_case |
| `error messages` | `GraphQL: Pull Request has merge conflicts (mergePullRequest)`, ``Blocked: `git checkout` would rewrite …``, `fatal: …`, `error TS2741: …` | `TypeError: …` and other exception names, which the existing `errors` row already covers |

The rows go after the existing ones. Every existing section keeps its exact line under the shared 7,000-char budget, and the new sections only use what is left. There is no prompt, cadence, budget or config change. Scope is local-compressor routes in lean tail mode only: legacy mode doesn't build the index, and native compaction summaries are opaque.

**Where the classes come from.** The 90 gold answers committed in `SCORECARD-2026-08-15.md` include 49 identifiers. Written in plain text, 24 of the 49 match a current row; 31 match with these rows. The 7 new matches are:
- 5 error lines (sweep, gui, acp transcripts)
- 1 subagent id (gui)
- 1 config key (prmerge)

This only checks that the gold strings match a row. It does not measure recall. I haven't run the recall exam because it needs the aux model; the commands are below if you want numbers before merging.

**Relationship to #117462.** That PR changes the same function: it harvests tool-call arguments, puts cheap ids first, truncates per section instead of `break`ing, and adds session ids, todo ids and more path extensions. It covers different classes in the same table, and the two PRs compose: with both applied, both test files pass (5 + 2). Whichever lands second needs a small rebase of the table. I'm happy to rebase this onto #117462 with the rows in its cheap-first order, or to fold it into that PR instead.

One limitation on current main: the loop `break`s at the first section that doesn't fit. So in dense regions, rows appended at the end only get budget that `files` and `errors` left over. #117462's per-section truncation is what lets them through there.

## Related Issue

Refs #116246 (scorecard), #87326 (lean tail and recall exam), #117462 (same function, complementary)

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `agent/context_compressor.py`: three rows appended to `_ANCHOR_PATTERNS` (+5 lines).
- `tests/agent/test_context_compressor_anchor_index.py`: two tests.
  - The new classes are captured verbatim from assistant text.
  - File names, hosts and `e.g` are not caught as dotted keys; each new section respects its cap; sections stay inside `_LEAN_ANCHOR_BUDGET_CHARS`.

## How to Test

1. `scripts/run_tests.sh tests/agent/test_context_compressor_anchor_index.py` gives 2 passed. On main it gives 2 failed (`AssertionError: 'sa-2-7318d0ba' missing from anchor index`, `assert 'compression.tail_mode' in ''`). Removing any one of the three rows turns the tests red again.
2. Neighbouring files give 365 passed on main and on this branch (plus the 2 new tests):
   - `tests/agent/test_context_compressor.py`
   - `test_lean_single_aux_call.py`
   - `test_compression_rotation_state.py`
   - `test_context_compressor_summary_continuity.py`
   - `test_compaction_redaction_boundaries.py`
   - `test_native_compaction_summary_retention.py`
3. `python evals/compaction/test_region_scoping.py` gives ALL PASS, and `python evals/token_accounting/replay_gates.py` gives 11/11 PASS. Both match main.
4. Optional recall exam (not run; uses `auxiliary.compression`). Use the same transcript, and copy the cached `questions-*.json` into each out dir so both checkouts answer the same bank. Run 3 reps per transcript from main and from this branch:
   `python evals/compaction/runner.py --transcript <lineage.json> --policies current+recovery --questions 30 --out <dir>`

Other checks I ran:
- On a seeded synthetic region of about 443K chars, building the index takes about 0.03 s with or without the new rows.
- In 720 synthetic regions, the index never exceeded the 7,000-char section budget (max about 1.8K tokens including the heading).
- On `website/docs` + `AGENTS.md` (7.8M chars), `task ids` matched only 2 distinct doc examples.
- About 30% of distinct `dotted keys` values are `DEFAULT_CONFIG` keys, and the rest are dotted API names like `ctx.register_hook`. That's why the label is "dotted keys".

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

On main (tests only):

```
FAILED tests/agent/test_context_compressor_anchor_index.py::test_anchor_index_keeps_task_ids_config_keys_and_error_messages_verbatim
FAILED tests/agent/test_context_compressor_anchor_index.py::test_new_anchor_classes_stay_exact_and_bounded
2 failed
```

With the rows: `2 passed` (3 runs).

Written with AI assistance (Claude Code). I reviewed the diff and ran the checks above.
