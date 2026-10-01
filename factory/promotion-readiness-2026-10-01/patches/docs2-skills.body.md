## What does this PR do?

Docs-only, no behaviour change. `clarify` accepts one argument, `questions=[{question, choices?, multi_select?}]` (`tools/clarify_tool.py:16`, `:50-55`, schema `:175`), and the registry handler passes only `args["questions"]` to the tool (`tools/clarify_tool.py:192`). The pixel-art skill's two examples still use the old top-level form `clarify(question=..., choices=[...])` (`optional-skills/creative/pixel-art/SKILL.md:50`, `:70`), so an agent that copies them fails on the first call with the tool error `questions must be a non-empty array. Pass questions=[{question, choices?, multi_select?}]; a single question is a one-entry array.`

The openclaw-migration skill says the CLI's `clarify` is limited to "one choice at a time" and "does **not** support true multi-select checkboxes in a single prompt" (`optional-skills/migration/openclaw-migration/SKILL.md:89` and `:93`). Both are false. One call takes up to 5 questions (`tools/clarify_tool.py:9`), and the CLI renders `multi_select` questions as checkbox rows (`hermes_cli/cli_modal_mixin.py:929-930`, `hermes_cli/cli_tui_mixin.py:474-506`).

The pixel-art examples and the zh-Hans retry hint went stale with #127760, which made `questions=[...]` the only accepted shape and updated only the English openclaw retry hint. The openclaw single-choice and no-multi-select lines are older: clarify has supported `multi_select` since 3e2f91f6b3 and multi-question calls since bd8b658a63.

## Related Issue

No upstream issue. Originally flagged and drafted by the Detail doc-drift bot on my fork (kvnloo/hermes-agent#307). This version adds the zh-Hans mirror.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `optional-skills/creative/pixel-art/SKILL.md`: both `clarify` examples now use `clarify(questions=[{...}])`.
- `optional-skills/migration/openclaw-migration/SKILL.md`: removed the "one choice at a time" and "does not support true multi-select checkboxes" lines.
- `website/docs/user-guide/skills/optional/creative/creative-pixel-art.md` and `website/docs/user-guide/skills/optional/migration/migration-openclaw-migration.md`: regenerated with `website/scripts/generate-skill-docs.py`. Only these two pages change.
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/skills/optional/migration/migration-openclaw-migration.md`: this page is hand-translated and the generator does not rewrite it, so I removed the same two lines by hand. Its retry hint now names the `questions` array, which the English text has done since #127760.

## How to Test

1. Read the cited lines on `main`. For the accepted shape: `tools/clarify_tool.py:16`, `:50-55`, `:175`, `:192`. For multi-select rendering: `hermes_cli/cli_modal_mixin.py:929-930`, `hermes_cli/cli_tui_mixin.py:474-506`. The removed text contradicts these lines and the new examples match the schema.
2. Sanity checks, run on Linux against this branch: `tests/tools/test_clarify_tool.py tests/skills/test_skill_docs_contract.py tests/skills/test_skill_pages_match_shipped_skills.py tests/website/test_generate_skill_docs.py` -> 44 passed. These cover the tool's shape and check that the mirrors stay in sync. No test asserts the doc text.
3. Docs checks run: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py` leaves `website/docs`, `website/sidebars.ts` and `website/i18n` unchanged, and `python3 website/scripts/check_doc_links.py` is OK.
4. Not run: `npm run lint:diagrams` and `npm run build:fast`, because the website dependencies are not installed locally. Outside code fences and inline code, the added lines contain no `{}` or raw tags.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass — targeted files only (listed above); docs-only change
- [ ] I've added tests for my changes — N/A, documentation only
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Cited source lines verified on `main` aeff051a18; merges cleanly.
