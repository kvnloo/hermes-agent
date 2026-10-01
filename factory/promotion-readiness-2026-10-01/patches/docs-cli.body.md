## What does this PR do?

Two CLI-reference corrections on `main` (tested at `f848940560`).

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `website/docs/reference/profile-commands.md:17-31` | The `hermes profile` subcommand table lists `list ... rename, export, import, install, update, info` | `hermes_cli/subcommands/profile.py:93-114` also registers `purge-identity` and `migrate-identity`, and both have their own sections further down the same page (`:259`, `:288`). Comparing the parser's `add_parser` names with the table on main: missing `['purge-identity', 'migrate-identity']`; after this change, none missing and none extra. Rows use the parsers' help strings. |
| 2 | `website/docs/getting-started/updating.md:310` | "Startup and gateway-status warnings, as well as update catch-up, check for a live successor on the current checkout" | Only update catch-up does (`_pending_fleet_restart_needed`, `hermes_cli/update_cmd_fleet.py:475-491`; used by `update_completion.py:219`). The startup warning (`main.py:3636-3640` → `_warn_pending_fleet_restart_on_startup` → `_update_owes_fleet_restart`, `update_cmd_fleet.py:494-515`, docstring "Hold a completed restart to the code it pulled, not a later checkout HEAD") first accepts successors at the SHA the receipt's completed restart phase pulled, in state `current` or `stale` (`_receipt_restart_phase_completed`, `:464-472`), so a later `git pull` that moves the checkout does not raise the warning again. `hermes gateway status` gets the same startup check. |

Docs only; no behaviour change.

## Related Issue

No upstream issue. Open #22128 touches another part of `updating.md`.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `website/docs/reference/profile-commands.md`: add `migrate-identity` and `purge-identity` rows after `rename` (matching section order).
- `website/docs/getting-started/updating.md`: catch-up checks the current checkout; startup / gateway-status warnings also accept successors at the completed restart's pulled SHA.

The zh-Hans `profile-commands.md` is an older translation: it has neither identity section (nor the `describe` row), so adding table rows there would point at sections that don't exist; leaving it to the zh-Hans refresh. The zh-Hans `updating.md` has no receipt paragraph.

## How to Test

1. Parser vs table: `python3 -c "import re;s=open('hermes_cli/subcommands/profile.py').read();d=open('website/docs/reference/profile-commands.md').read().split('## \`hermes profile list\`')[0];p=re.findall(r'profile_subparsers\.add_parser\(\s*\"([a-z-]+)\"',s);r=re.findall(r'^\| \`([a-z-]+)\` \|',d,re.M);print([x for x in p if x not in r])"` → `[]` (on main: `['purge-identity', 'migrate-identity']`).
2. Read `_update_owes_fleet_restart` vs `_pending_fleet_restart_needed` in `hermes_cli/update_cmd_fleet.py`.
3. `python3 website/scripts/check_doc_links.py` → OK.

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
