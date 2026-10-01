## What does this PR do?

Docs-only, no behaviour change. `clarify` takes a single argument, `questions=[{question, choices?, multi_select?}]` (`tools/clarify_tool.py:16`, `:50-55`, schema `:175`). The registry handler passes only `args["questions"]` to the tool (`tools/clarify_tool.py:192`), so a payload with `question`/`choices` at the top level fails with `questions must be a non-empty array. Pass questions=[{question, choices?, multi_select?}]; a single question is a one-entry array.` Two optional skills still teach that rejected shape or limits that no longer exist:

- **pixel-art**: both examples call `clarify(question=..., choices=[...])` (`optional-skills/creative/pixel-art/SKILL.md:50`, `:70`). An agent that copies them fails on its first call.
- **openclaw-migration**:
  - It says the CLI's `clarify` handles "one choice at a time" and "does **not** support true multi-select checkboxes in a single prompt" (`optional-skills/migration/openclaw-migration/SKILL.md:89`, `:93`). Both claims are wrong. One call takes up to 5 questions (`tools/clarify_tool.py:9`), and the CLI renders `multi_select` questions as checkbox rows (`hermes_cli/cli_modal_mixin.py:929-930`, `hermes_cli/cli_tui_mixin.py:474-506`).
  - It introduces its examples as "these exact `clarify` payload shapes" and then lists bare `{"question":...,"choices":[...]}` objects (`:159-165`). Those are the top-level shape the tool rejects.
  - It lists its per-question rules under "For every `clarify` call: always include a non-empty `question`" (`:95`), which also points at a top-level `question`.

The pixel-art examples and the zh-Hans retry hint went stale with #127760. That PR made `questions=[...]` the only accepted shape but updated only the English openclaw retry hint (`:105`). The single-choice and no-multi-select lines are older: clarify has supported `multi_select` since 3e2f91f6b3 and multi-question calls since bd8b658a63.

## Related Issue

No upstream issue. The Detail doc-drift bot first flagged and drafted this on my fork (kvnloo/hermes-agent#307); it is credited as co-author. This version also fixes the openclaw example and rules wording and mirrors every edit into the zh-Hans page.

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
- `optional-skills/migration/openclaw-migration/SKILL.md`:
  - Removed the "one choice at a time" and "does not support true multi-select checkboxes" lines.
  - "For every `clarify` call:" now reads "For every entry in the `clarify` `questions` array:".
  - "Use these exact `clarify` payload shapes as the default pattern:" now reads "Use these exact `questions` entries as the default pattern:". The entries themselves are unchanged.
  - Added one sentence: "Independent decisions can share one `clarify` call as separate `questions` entries." This matches the tool description (`tools/clarify_tool.py:135-138`). The decision flow is unchanged, still valid, and still fits the 4-choice cap. The workspace-path follow-up stays a separate call because it depends on an earlier answer.
- `website/docs/user-guide/skills/optional/creative/creative-pixel-art.md` and `website/docs/user-guide/skills/optional/migration/migration-openclaw-migration.md`: regenerated with `website/scripts/generate-skill-docs.py`. No other generated page changes.
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/skills/optional/migration/migration-openclaw-migration.md`: this page is translated by hand and the generator does not rewrite it, so I made the same edits by hand (`:107`, `:111`, `:113`, `:133`, `:177`). Its retry hint (`:123`) now names the `questions` array, as the English text has done since #127760.

## How to Test

1. Read the cited lines on `main`:
   - Accepted shape: `tools/clarify_tool.py:16`, `:50-55`, `:175`, `:192`.
   - Batching guidance: `:135-138`.
   - Multi-select rendering: `hermes_cli/cli_modal_mixin.py:929-930`, `hermes_cli/cli_tui_mixin.py:474-506`.

   The removed or reworded text contradicts these lines. The new examples and wording match the schema.
2. Shape check against the real handler. The tool rejects both a bare openclaw example entry and the old pixel-art keyword form (`questions must be a non-empty array...`). It accepts the same entry inside `{"questions": [...]}`, and it accepts four independent entries in one call:
   ```python
   from tools.registry import registry
   h = registry._tools["clarify"].handler
   cb = lambda qs: {"answers": {q["qid"]: "x" for q in qs}, "outcome": "submitted"}
   entry = {"question": "Your existing SOUL.md conflicts ...", "choices": ["keep existing", "overwrite with backup", "review first"]}
   h(entry, callback=cb)                  # error: questions must be a non-empty array
   h({"questions": [entry]}, callback=cb) # responses: [...], outcome: submitted
   ```
3. Sanity checks, run on Linux against this branch: `tests/tools/test_clarify_tool.py tests/skills/test_skill_docs_contract.py tests/skills/test_skill_pages_match_shipped_skills.py tests/website/test_generate_skill_docs.py` gives 44 passed. These cover the tool's shape and check that the generated mirrors stay in sync. No test asserts the doc text.
4. Docs checks: after `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py`, `git diff --exit-code -- website/docs website/sidebars.ts website/i18n` is clean. `python3 website/scripts/check_doc_links.py` reports OK.
5. Not run: `npm run lint:diagrams` and `npm run build:fast`, because the website dependencies are not installed locally. Outside code fences and inline code, the added lines contain no `{}` or raw tags.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Only the targeted files listed above were run; this is a docs-only change.
- [ ] I've added tests for my changes. N/A: documentation only.
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Branch `ready/docs2-skills-v2`: one commit on `main` 330d9d6df9. All cited source lines were checked against that commit.
