## What does this PR do?

Corrects three Bot Mode / Bot Chat statements that no longer match the code on `main` (tested at `f848940560`).

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `website/docs/developer-guide/cron-internals.md:366` | "Without a mailbox owner it retains `hermes [-p <profile>] chat --in ~ -c "Bot Chat" --create-if-missing -Q --query-file <tmp>`" | `_deliver_to_bot_chat` (`cron/scheduler_delivery.py:772-950`) never passes the target profile with `-p`. It builds the child env with `served_profile_child_env(..., target_home=home)`, which sets `HERMES_HOME` to the resolved target (`tools/environments/local.py:409-411`), and appends `-p default` only when the target is the root home (`if home.parent.name != "profiles": argv += ["-p", "default"]`), then `chat --in ~ -c "Bot Chat" --create-if-missing -Q --query-file <tmp>`. |
| 2 | `website/i18n/zh-Hans/.../user-guide/bot-mode.md:125` | `Message from 🤖 <sender> (@<sender>):` | `tools/bot_mode_dm.py:243` stamps `f"Message from 🤖 {_display_name(...)} (@{_handle(me)}): "`, a display name plus a handle, which the English page already shows as `Message from 🤖 <friendly name> (@<handle>):` (`website/docs/user-guide/bot-mode.md:186`). |
| 3 | `website/docs/user-guide/bot-mode.md:356-357` and `website/i18n/zh-Hans/.../user-guide/bot-mode.md:213` | promoting while the old gateway is writable lets "both independent `state.db` stores" accept messages | Hosted-room state lives in the root `shared-state.db`, not the master `state.db` (`gateway/hosted_rooms.py:398-413` `default_db_path`; the docstring explains it is deliberately separate). `groups.promote` / `groups.demote` (`tui_gateway/methods_groups.py:506-519`) act on that store. |

Docs only; no behaviour change.

## Related Issue

No upstream issue. Searched open PRs/issues for `bot-chat`, `shared-state.db`, `Message from 🤖`: no overlap. (Our separate local-delivery-launcher correction for `bot-mode.md` is a different paragraph.)

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `website/docs/developer-guide/cron-internals.md`: the unowned CLI lane runs `hermes chat ...` with `HERMES_HOME` pinned to the target home (plus `-p default` for the root home).
- `website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/user-guide/bot-mode.md`: DM stamp placeholder now matches the English page; room store renamed to `shared-state.db`.
- `website/docs/user-guide/bot-mode.md`: room store renamed to `shared-state.db`.

The zh-Hans `cron-internals.md` has no Bot Chat paragraph, so it needs no change. The rest of the zh-Hans DM bullet is an older, shorter translation; this PR only fixes the placeholder and does not re-translate it.

## How to Test

1. Compare each quote with `main` and read the cited source.
2. `python3 website/scripts/check_doc_links.py` → `OK: no route-style links in hand-authored docs.`

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs only; not run.
- [ ] I've added tests for my changes. N/A, docs only.
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
