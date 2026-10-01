## What does this PR do?

Brings four Desktop user-guide statements in line with the app (checked by reading the source on `main` at `1ce2cfb7fa`). Line numbers below are at that commit.

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `website/docs/user-guide/desktop.md:57` | Timeline rail: "Hover it to pop open the list of prompts ... (It appears once the chat has a handful of turns.)" | `TimelineRail` wraps each marker in its own `Tip` tooltip with that prompt's preview (`apps/desktop/src/components/assistant-ui/thread/timeline-rail.tsx:166-191`); there is no popover list. `ActiveThreadTimeline` returns null only when `railEntries` is empty (`timeline.tsx:303-305`), and `deriveTimelineEntries` has no minimum count (`timeline-data.ts:46-69`). |
| 2 | `website/docs/user-guide/desktop.md:145` | Simple mode: "With more than one profile the profile rail stays" | The Simple policy is `profileRailVisible: context => context.profileCount > 1 \|\| context.connectionCount > 1` (`apps/desktop/src/store/interface-mode.ts:106-108`, comment: "multi-gateway installs still need the rail even when the active gateway has only one profile"). |
| 3 | `website/docs/user-guide/multi-connection-desktop.md:231-233` | Right-click on an at-rest square offers "Switch to, Color, Rename, Edit SOUL.md and Delete" | `RestSquare`'s menu starts with `ProfileLaunchMenuSection` (`apps/desktop/src/app/chat/sidebar/profile-switcher.tsx:1325`), which renders **Open in new window** when `canOpenNewWindow()` and **Set as default** (`profile-launch-menu.tsx:22-55`). |
| 4 | `website/docs/user-guide/desktop.md:470`, `multi-connection-desktop.md:61-65` and `:239-240` | desktop.md describes an "**Open on launch**" control with **Primary gateway** / **Last used** options; neither page mentions the default profile | The only launch control is the toggle "At startup, return to Sessions on the last-used gateway" (`apps/desktop/src/i18n/en.ts:1529-1530`, `connections-registry.tsx:917-920`); no "Open on launch" string exists. Startup selection follows `$defaultProfileRoute` first and only falls back to `launchMode` primary/last-used when no default is set (`apps/desktop/src/store/connections.ts:255-279`); Electron main connects that route at startup (`electron/main.ts:15000-15007`, `:15341`). The default's own description: "Used when Hermes opens and for new chats." (`apps/desktop/src/i18n/en.ts:3280`) |

Docs only; no behaviour change.

## Related Issue

No upstream issue. Supersedes my closed #127380, which made only the item 2 change.

Open PRs that edit these pages touch other lines: #126161 (the token bullet in the same Registered gateways list as item 4), #109472, #128498, #123026, #100753, #89790, #88794, #70777, #128505.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `website/docs/user-guide/desktop.md`: timeline rail tooltips, no turn threshold; Simple-mode rail with more than one profile or gateway; launch setting named as the real toggle, with default-profile precedence.
- `website/docs/user-guide/multi-connection-desktop.md`: at-rest square menu includes Open in new window / Set as default; both launch bullets note that a default profile takes precedence.

There are no zh-Hans copies of these pages.

## How to Test

1. For each row, compare the quoted doc line on `main` with the cited source. For item 1, `apps/desktop/src/components/assistant-ui/thread/timeline-idle.test.tsx:113-122` ("builds ticks without a separate popover") already asserts there is no popover list.
2. `git grep -n "Open on launch\|handful of turns\|pop open the list" -- website/` returns nothing after this change.
3. No links are added or changed; `python3 website/scripts/check_doc_links.py` still reports OK.

Not done: no Docusaurus build, and the Desktop app was not run. Each statement was checked against the cited source on main.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs only; not run.
- [ ] I've added tests for my changes. N/A, docs only.
- [ ] I've tested on my platform: Linux (CachyOS): link check only; Desktop app not launched.

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
