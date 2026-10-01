## What does this PR do?

In the bundled xlsx skill, `apply_cell()` (`skills/productivity/xlsx/scripts/xlsx_create.py`) first gives a hyperlink cell the built-in `Hyperlink` named style, whose font uses theme color 10 (the standard link blue). If the same spec also sets `bold`, `italic` or `font_size`, it then runs `cell.font = Font(**font_kw)`. That replaces the style's font with a bare `Font` that has no color, name or scheme. So `{"value": "Report", "hyperlink": "https://…", "bold": true}` produces a link that still works but renders in black. `font_color` is not affected, because there the requested color is applied directly.

The fix copies the cell's resolved font and sets only the requested attributes on the copy. The Hyperlink style keeps its color, `bold`/`italic`/`size` still apply, and an explicit `font_color` still wins. Plain styled cells now keep the default font face and size and change only the requested attributes. `copy.copy()` is used instead of the deprecated `StyleProxy.copy(**kw)`.

The bug was first flagged by the Detail automated scanner; this keeps its copy-then-set fix with a smaller regression test.

## Related Issue

No existing issue. Open PRs that touch `xlsx_create.py` (#89986 table headers, #89927 autofilter overlap, #106090 office-skill install) do not change font handling. #106090 wraps this file's openpyxl imports in try/except, so whichever lands second gets a small conflict there (drop `Font` from the re-indented `openpyxl.styles` import).

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `skills/productivity/xlsx/scripts/xlsx_create.py`: in `apply_cell`, font overrides are set on `copy.copy(cell.font)` instead of on a fresh `Font(**font_kw)`. Adds `import copy` and drops the now-unused `Font` import.
- `skills/productivity/xlsx/tests/test_xlsx_skill.py`: `test_hyperlink_font_overrides_keep_link_color` builds a plain link, a bold+italic+size link and a bold link with an explicit `font_color`, then reloads the workbook. It checks that the styled link keeps theme color 10 and its requested style, that `font_color` still overrides, and that the plain sibling is not bolded.

## How to Test

The skill tests need `openpyxl`, which is not a Hermes dependency, so they ran in a throwaway env: `uv run --no-project --with openpyxl==3.1.5 --with pytest python -m pytest skills/productivity/xlsx/tests/test_xlsx_skill.py -q`

1. Without the production change, the new test fails: `assert (None is not None)`. The bold/italic/size hyperlink font is `name=None … color=None … sz=14.0`.
2. With the change, the whole xlsx skill suite passes (13 passed).

`tests/skills/test_skill_document_contracts.py` passes (29 passed, 1 skipped). `ruff check` is clean on both files.

Not tested: how the link renders in Excel or LibreOffice. The color is checked by reloading the workbook with openpyxl.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (targeted files only, listed above)
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), openpyxl 3.1.5 (uv ephemeral env)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A
