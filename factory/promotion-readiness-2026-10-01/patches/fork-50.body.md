## What does this PR do?

`CompressionConfig.save_over_limit` (`processing.save_over_limit` in the compression YAML) is loaded into the config, but nothing reads it. The example config that shipped with it (`datagen-config-examples/trajectory_compression.yaml`, removed in 0c0875b746) documented the flag as 'If true, save trajectories even if compression can't get under target'. When it is `false`, trajectories that are still over `target_max_tokens` after compression should stay out of the output. Instead, the write loop in `_process_directory_async` writes every outcome that is not a timeout. So `save_over_limit: false` still puts over-budget samples into the compressed dataset, while the summary report counts the same entries under "Still over limit".

The fix is one condition in the write loop. When `save_over_limit` is false, an outcome whose `metrics.still_over_limit` is true is skipped. With the default (`true`), output is unchanged. Timed-out entries are still dropped as before. Error-path entries keep the original trajectory with empty metrics, so they are still written as before (the filter cannot tell whether they are over budget). Every entry point (single file, sampled file, directory, `scripts/sample_and_compress.py`) goes through `process_directory`, so this is the only write site.

The defect was first identified by Detail's automated scan (detail-app[bot]) in kvnloo/hermes-agent#50; this is a smaller rebuild of that fix against current `main` (its extra counter and tests are not included).

## Related Issue

No existing issue. Searched PRs/issues for `save_over_limit`: open #103709 adds docs saying over-budget results are "handled by the existing `save_over_limit` setting" but does not change the write loop. This PR makes that statement true. Open #41512 / #40728 change how timeouts are handled in the same loop; this change is independent of them and compatible with both. Open #127966 rewrites this write loop into batched streaming writes; whichever of the two lands second needs to apply the same `save_over_limit` / `still_over_limit` condition at its write sites.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `trajectory_compressor.py` (`_process_directory_async`): the write filter also drops `still_over_limit` outcomes when `config.save_over_limit` is false.
- `tests/test_trajectory_compressor.py`: one parametrized test runs the real `process_directory` pipeline (with the file's existing `_make_compressor` stub tokenizer) on an over-limit trajectory that cannot be shrunk and an under-target trajectory, and asserts the summarizer is never called. With `save_over_limit=True` both are written; with `False` only the under-target one is.

## How to Test

1. `scripts/run_tests.sh tests/test_trajectory_compressor.py -q` -> 19 passed.
2. On `main` (the same as reverting the condition to `if outcome is not None:`), the `[False-written1]` case fails with `AssertionError: assert ['over', 'under'] == ['under']`; the `[True-written0]` control passes on both.

All six test files that reference `trajectory_compressor` pass with the change (60 tests): `tests/test_trajectory_compressor.py`, `tests/test_trajectory_compressor_async.py`, `tests/tools/test_config_null_guard.py`, `tests/hermes_cli/test_arcee_provider.py`, `tests/agent/test_env_loader_secret_sources.py`, `tests/agent/test_stream_drop_logging.py`. `ruff check` is clean.

Not tested: an end-to-end run with a real tokenizer and summarization model (the test uses the file's existing `_make_compressor` stub tokenizer and never reaches the summarizer); timeout combined with `save_over_limit: false` (timed-out `None` outcomes take the same path as before); the full `tests/` suite.

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
