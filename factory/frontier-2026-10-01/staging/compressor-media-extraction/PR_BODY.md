## What does this PR do?

Moves the image/media cluster of `agent/context_compressor.py` (5,753 lines on `main`) into a new sibling, `agent/context_compressor_media.py`. The code moves unchanged. No behaviour changes.

This is the media slice of #80636 by andrexibiza, rebuilt on current `main`. #80636 was cut in August from a 6,883-line pin. It stacks four slices (text utils, skill prune, budget, media) and keeps the old names importable through a re-export seam. It no longer applies to `main`: `git merge-tree` reports a conflict in `agent/context_compressor.py` for the whole PR and for its media commit alone. Its new module also carries the August versions of functions that have changed since. For example, `_strip_historical_media` has no `spared` argument there. The media code has also grown since then (tool-image retirement inside the protected tail, the send-path `evict_stale_outbound_tool_images`, the `_multimodal` envelope). The sibling skill-prune slice, #80628, was closed as stale on 2026-09-02. AGENTS.md also now rules out re-export shims for internal moves. So this PR keeps that PR's module name and topic cut, drops the seam, and points callers at the new module. Andrex is credited as co-author on the commit. The name follows the `<stem>_<topic>` pattern that `agent/context_compressor_summary.py` already uses on `main`. Micro-compaction was already moved out separately, to `agent/micro_compaction.py`.

The same media commit is also in four PRs that stack on #80636: #80645, #80644, #81074 and #81181. Each carries it unchanged, so each also adds `agent/context_compressor_media.py`. If this PR lands, that commit is obsolete in all five, and each would drop it when rebased (otherwise the new file conflicts as add/add). The rest of those PRs is untouched here.

The other three slices of #80636 are not included here.

What moved (16 top-level statements, in their original order, with their comments):

- compaction-time image retirement: `_strip_historical_media`, `_retire_stale_tool_result_images`, `_MAX_KEEP_TOOL_IMAGES`
- send-path eviction: `evict_stale_outbound_tool_images`, `_image_payload`
- shared helpers: `_IMAGE_PART_TYPES`, `_is_image_part`, `_content_has_images`, `_tool_content_has_images`, `_tool_result_parts`, `_replace_image_parts`, `_strip_images_from_content`, `_strip_images_from_tool_msg`, `_rewritten`
- summarizer labels: `_summary_part_text`, `_image_part_label`

What stays in the facade: the content-text helpers (`_part_text`, `_content_text_for_contains`, `_append_text_to_content`, …). They are text utilities, not media, and `conversation_compression.py` imports one of them from the facade.

## Related Issue

Refs #78645. This PR covers only the media slice of #80636 (the same commit is in #80645, #80644, #81074 and #81181).

## Type of Change

- [x] ♻️ Refactor (no behavior change)

## Changes Made

- `agent/context_compressor_media.py` (new, 243 lines): the 16 moved statements, byte-for-byte, under a short module docstring. It imports `typing`, `agent.image_eviction_policy.outbound_image_retire_count` and `agent.turn_context.drop_stale_api_content`. It never imports the facade.
- `agent/context_compressor.py` (5,753 → 5,531 lines): the moved statements are removed. The facade imports from the sibling only the six names it still calls itself (`_is_image_part`, `_retire_stale_tool_result_images`, `_rewritten`, `_strip_historical_media`, `_strip_images_from_tool_msg`, `_summary_part_text`). The `outbound_image_retire_count` import is dropped because only moved code used it.
- `agent/turn_request_assembly.py` and `agent/chat_completion_helpers.py`: their function-local import of `evict_stale_outbound_tool_images` now names the sibling.
- `agent/image_eviction_policy.py` and `tests/agent/test_image_eviction_policy.py`: docstrings that named `context_compressor.evict_stale_outbound_tool_images` now name the sibling.
- `tests/agent/test_compressor_historical_media.py`, `test_compressor_stale_tool_images.py`, `test_outbound_stale_vision.py`, `test_protected_tail_pressure.py`: they import the moved names from the sibling. `ContextCompressor` and the other facade names still come from the facade.

No test is added or removed. No monkeypatch or `patch()` target in the tree names a moved symbol, so no patch seam changes.

## How to Test

1. Review the move: `git show --color-moved=plain HEAD`. Git marks 230 of the 243 deleted lines and 235 of the 264 added lines as moved. The other lines are the import edits, blank lines and the new module docstring.
2. No old-path references: `git grep -nE "context_compressor\.(_strip_historical_media|evict_stale_outbound_tool_images|_is_image_part|_tool_content_has_images)"` returns nothing. No `from agent.context_compressor import …` statement anywhere names a moved symbol, whether at module level or inside a function.
3. Targeted tests: `scripts/run_tests.sh tests/agent/test_compressor_historical_media.py tests/agent/test_compressor_stale_tool_images.py tests/agent/test_outbound_stale_vision.py tests/agent/test_protected_tail_pressure.py tests/agent/test_image_eviction_policy.py tests/agent/test_compressor_zero_user_guard.py -q`. On this branch, 57 of 57 tests pass. On `main`, with main's copies of these six files, the same 57 tests pass.
4. Wider suite: `scripts/run_tests.sh tests/agent/ tests/tools/ -q` on `main` and on this branch. The two trees give the same counts over 1,683 files: 20,111 tests pass, 16 fail, 131 are skipped and 8 error, and the failing and erroring tests are the same ones on both. All 16 failures and 8 setup/collection errors (7 in `test_plugin_guard.py`, 1 in `test_fal_sdk.py`) are pre-existing on `main` and unrelated to compression (relay plugins, LSP workspace, TTS/web keyless routing, plugin_guard install fixtures, fal_sdk import). One more file, `tests/agent/test_shell_hooks_tree_kill.py`, hit the 300 s per-file limit on both trees because I ran the two suites at the same time; run alone, it passes 6/6 on both. Per-file counts are identical.
5. `python -c "import agent.context_compressor_media"` works in a fresh interpreter and does not load the facade. `agent.context_compressor`, `agent.native_compaction`, `agent.turn_request_assembly` and `agent.chat_completion_helpers` all import cleanly. `ruff check` and `scripts/check-windows-footguns.py` are clean on all 10 touched files.

I also checked the following on a scratch copy; none of it is part of this PR:

- Sabotaging the moved `_strip_historical_media` fails `ContextCompressor.compress()` tests. Sabotaging the moved `evict_stale_outbound_tool_images` fails the iteration-summary tests and the conversation-loop tests (traceback through `turn_request_assembly.py:155`). So the facade and both send paths run the sibling's code.
- Every moved statement has identical source text and AST in its new home. Every other top-level statement in the facade has an identical AST, in the same order (194 compared). `agent/native_compaction.py` and its import of `is_compaction_summary_message` from the facade are untouched.
- Overlap with open PRs: on 2026-10-01 (listed between 11:15 and 11:45 CDT), 411 of the 33,677 open PRs changed `agent/context_compressor.py`.
  - I merge-tested only a sample of three outside #80636's stack. #129147 still merges cleanly. #118847 and #119347 already conflict with `main`, and this branch adds no new conflict hunk to either.
  - For the rest, I compared each PR's own before and after of the file, statement by statement, against `main`. This was not a merge test.
  - Five PRs change moved code, and their change would need to move to the new module: #90910, #106867, #107589 and #110103 (focused fixes), and #130634 (a 63-file feature PR).
  - #85481, #104914 and #130634 add facade calls to moved helpers that the facade would no longer import.
  - #104914, #107589 and #130634 add test imports of moved names from the old path, and those would then fail. #110103 and #120403 add old-path imports of `_summary_part_text` and `_rewritten`, which keep working because the facade still imports them.
  - Sixteen more are stale-base diffs of 619 to 3,000 files, with unrelated titles, that also touch moved statements. 13 of them already conflict with `main`.
  - #80636 and the four PRs stacked on it already conflict with `main` in `agent/context_compressor.py`. With this branch they also get the add/add conflict on `agent/context_compressor_media.py` described above.

Shape, from `evals/codebase_navigability/static_metrics.py`: one more module. The facade is still above 2,000 lines; this is one slice, not the whole split. The new module joins the largest import cycle (1,131 → 1,132 modules) through `agent.turn_context`, which owns `drop_stale_api_content`. The README predicts this for splits. The lookup simulations (`bench.py`, `lookup_sim.py`) show the moved definitions get cheaper to look up. Those numbers are simulated, so this PR does not rest on them.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate. #80636 covers this slice and is credited above. #80645, #80644, #81074 and #81181 stack on #80636 and carry the same media commit, so they also add `agent/context_compressor_media.py`. No other open PR adds it; I checked the file lists of all open PRs on 2026-10-01.
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Not done: I ran `tests/agent/` and `tests/tools/` through `scripts/run_tests.sh` on both trees (step 4).
- [ ] I've added tests for my changes. N/A: a pure move. The existing tests now import from the new module.
- [x] I've tested on my platform: Linux (CachyOS), Python 3.11

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A. Two docstrings repointed. No page under `website/docs`, `skills/` or any `AGENTS.md` names a moved symbol.
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Based on `main` @ `aea969677c60`. It merges cleanly onto `main` @ `44a1ce972450` (29 commits newer), and none of the touched files changed in between. Re-running the move script on `44a1ce972450` gives exactly the merged tree.

```
main @ aea969677c60:
=== Summary: 1683 files, 20111 tests passed, 16 failed, 131 skipped (100% complete) in 3537.3s (2 workers) ===
this branch:
=== Summary: 1683 files, 20111 tests passed, 16 failed, 131 skipped (100% complete) in 3541.4s (2 workers) ===
```

Not tested: Windows and macOS (pure move, no platform code), and the `hermes` CLI end to end.

AI assistance: prepared with Claude Code (Claude Opus 5.5). It made the move with a small AST-based script, ran the checks above and drafted this description.
