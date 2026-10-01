## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs(skills): correct clarify call shape and multi-select claims

- **Was:** optional-skills/creative/pixel-art/SKILL.md:50 and :70 — "clarify(\n    question=..., choices=[...])" (mirrored at website creative-pixel-art.md:65, :85); optional-skills/migration/openclaw-migration/SKILL.md:88-93 — "- one choice at a time" / "It does **not** support true multi-select checkboxes in a single prompt." (mirrored in website and zh-Hans migration-openclaw-migration.md)
- **Source on main:** tools/clarify_tool.py:16 _SHAPE, :50-55 _normalize_questions() rejects anything but a non-empty questions list; schema property multi_select (:175); CLI renders multi_select checkboxes (hermes_cli/cli_modal_mixin.py:929-930, cli_tui_mixin.py:474-506).
- **Check:** Probe on main: clarify_tool(question=..., choices=...) -> TypeError unexpected keyword 'question'; questions missing -> 'questions must be a non-empty array. Pass questions=[{question, choices?, multi_select?}] ...'.
- **Now:** New shape validates: _normalize_questions([{question, choices}]) ok; two questions with multi_select -> ok. tests/tools/test_clarify_tool.py, skills docs contract/page tests, website generator test: 44 passed.
- **Mirrors:** English per-skill pages regenerated with website/scripts/generate-skill-docs.py (exactly the two pages changed; generator re-run is clean). zh-Hans openclaw page is a hand translation the generator does not rewrite: the same two lines removed by hand and its retry hint now names the `questions` array like the English source.
- Drift introduced by 5eea87882a (#127760).

## Related Issue

No upstream issue; found by doc-drift review against current `main`.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `optional-skills/creative/pixel-art/SKILL.md`
- `optional-skills/migration/openclaw-migration/SKILL.md`
- `website/docs/user-guide/skills/optional/creative/creative-pixel-art.md`
- `website/docs/user-guide/skills/optional/migration/migration-openclaw-migration.md`
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/skills/optional/migration/migration-openclaw-migration.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: tests/tools/test_clarify_tool.py tests/skills/test_skill_docs_contract.py tests/skills/test_skill_pages_match_shipped_skills.py tests/website/test_generate_skill_docs.py -> 44 passed.
3. Docs CI equivalent: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run here: the Docusaurus build (`npm run build:fast`); added lines contain no MDX-sensitive `{}`/raw tags outside code.

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

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-skills` @ 104ffb375732, 5 files changed, 17 insertions(+), 26 deletions(-).
