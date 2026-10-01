## What does this PR do?

Removes the stale "Hermes autodetection is planned" guidance from the computer-use page and brings the zh-Hans screenshot-eviction bullet in line with the code on `main` (checked against `main` at `f848940560`; the cited lines are unchanged on current `main`).

| # | Doc on main | What it says | Evidence |
|---|---|---|---|
| 1 | `website/docs/user-guide/features/computer-use.md:92-95`, `:296-302`, `:697-700` | "Hermes autodetection is a planned cua-driver follow-up, so currently point Hermes at `~/.cua-driver/skills/cua-driver` or symlink it" (three places) | The same page's "Going deeper" section already says "The command links the pack into `~/.hermes/skills/cua-driver` (Hermes is one of the agents `cua-driver skills status` reports)" (`:274-275`). So do `website/docs/reference/cli-commands.md:1711-1712` ("`cua-driver skills install` detects Hermes and links Cua's skill pack into the Hermes skills directory automatically") and the bundled `skills/autonomous-ai-agents/computer-use/SKILL.md:336-340`. Upstream cua shipped it: `libs/cua-driver/rust/CHANGELOG.md` in trycua/cua lists "skills: autodetect Hermes (NousResearch/hermes-agent) at ~/.hermes/skills (trycua/cua#1963)" and "honor HERMES_HOME for skill links (trycua/cua#3291)". The page contradicts itself today. |
| 2 | `website/i18n/zh-Hans/.../user-guide/features/computer-use.md:102` | "截图淘汰 — Anthropic 适配器在上下文中仅保留最近 3 张截图" (the Anthropic adapter keeps only the last 3 screenshots) | Eviction is provider-independent and limit-triggered: `agent/image_eviction_policy.py:26-28` (`OUTBOUND_IMAGE_LIMIT = 20`, `OUTBOUND_IMAGE_BUDGET_BYTES = 24_000_000`, `IMAGE_EVICTION_BATCH = 8`), applied by `_evict_old_screenshots` (`agent/anthropic_message_convert.py:605-635`) and, for every provider, `evict_stale_outbound_tool_images` (`agent/context_compressor.py:1510`). The English page (`computer-use.md:397-403`) already describes this; the zh-Hans bullet now translates it. |

Docs only; no behaviour change.

## Related Issue

No upstream issue.

Overlaps open #90538 (@injaneity), which fixes the same three English passages, plus the "Going deeper" passage, `SKILL.md`, the generated skill page and the installer messages. Since then, 42602bd12a on `main` has rewritten the "Going deeper" passage and `SKILL.md`, so #90538's hunks for those no longer match `main`. This PR carries only the three passages that are still stale, plus the zh-Hans eviction bullet, which #90538 does not touch. If you'd rather land #90538 after a rebase, I'll drop the English hunks here and keep the zh-Hans fix. Thanks to @injaneity for spotting the English drift first.

Open #121112 edits a different section of `computer-use.md` (minimized Windows support); #97447/#106376/#80722 touch the generated skill page, which already carries the correct text on `main`. The pack filenames in the edited "cua-driver skill pack" bullet (`WEB_APPS.md`) are out of scope here; see #119301 / #119303.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `website/docs/user-guide/features/computer-use.md`: the three "planned / point at / symlink" passages now say `cua-driver skills install` links the pack into `~/.hermes/skills/cua-driver`.
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/features/computer-use.md`: screenshot-eviction bullet translated from the current English text.

The generated skill page (`website/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-computer-use.md`) already matches the corrected `SKILL.md`, so it needs no change. The zh-Hans page has no cua-driver skill-pack passage.

## How to Test

1. `git grep -n -i "autodetection is\|planned follow-up\|\.cua-driver/skills\|最近 3 张" -- website/ skills/` returns nothing after this change (on `main` it returns six lines: the three English passages and the zh-Hans bullet).
2. `python3 website/scripts/check_doc_links.py` → `OK: no route-style links in hand-authored docs.`

Not run: Docusaurus build or rendered preview of either page (prose-only edits inside existing paragraphs and a bullet; no new links or MDX).

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs only; not run.
- [ ] I've added tests for my changes. N/A, docs only.
- [x] I've tested on my platform: Linux (CachyOS): ran the grep and link check above only

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
