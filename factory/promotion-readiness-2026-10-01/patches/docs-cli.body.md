## What does this PR do?

Two doc-accuracy fixes, checked against current `main` (`aeff051a18`): the `hermes profile` reference table is missing two registered subcommands, and the update guide says all receipt checks use the current checkout when only update catch-up does.

| # | Doc on main | What it says | What the code does |
|---|---|---|---|
| 1 | `website/docs/reference/profile-commands.md:17-31` | The `hermes profile` subcommand table lists `list ... rename, export, import, install, update, info` | `hermes_cli/subcommands/profile.py:93-114` also registers `purge-identity` and `migrate-identity`. Both already have their own sections further down the same page (`:259`, `:288`). |
| 2 | `website/docs/getting-started/updating.md:310` | "Startup and gateway-status warnings, as well as update catch-up, check for a live successor on the current checkout" | Only update catch-up does (`_pending_fleet_restart_needed`). The startup warning (`_update_owes_fleet_restart`) first accepts successors at the SHA the receipt's completed restart phase pulled. |

Detail for row 2, all in `hermes_cli/update_cmd_fleet.py` unless noted:

- Update catch-up (`update_completion.py:219`) calls `_pending_fleet_restart_needed` (`:475-491`), which checks only the current checkout SHA.
- The startup warning (`main.py:3639-3643` → `_warn_pending_fleet_restart_on_startup` → `_update_owes_fleet_restart`, `:494-515`, docstring "Hold a completed restart to the code it pulled, not a later checkout HEAD") first accepts successors in state `current` or `stale` at the SHA the completed restart phase pulled (`_receipt_restart_phase_completed`, `:464-472`). A later `git pull` that moves the checkout therefore does not raise the warning again. `hermes gateway status` gets the same startup check.

Docs only; no behaviour change.

## Related Issue

No upstream issue. Found by Detail and carried in my fork as kvnloo/hermes-agent#89 and kvnloo/hermes-agent#97, rebuilt on main. Main had reworded the `updating.md` paragraph since then, and this PR also adds the `purge-identity` row next to `migrate-identity` (the fork PR added only `migrate-identity`).

Open PR #22128 also edits `updating.md`, but only the messaging-platform and manual-update sections (around lines 107-134). No overlap with this change.

## Type of Change

- [x] 📝 Documentation update

## Changes Made

- `website/docs/reference/profile-commands.md`: add `migrate-identity` and `purge-identity` rows after `rename`, matching the order of their sections on the page. The row text is each parser's help string.
- `website/docs/getting-started/updating.md`: say that update catch-up checks the current checkout, and that startup and gateway-status warnings also accept successors on the code the receipt's completed restart phase pulled.

The zh-Hans `profile-commands.md` is an older translation: it has neither identity section (nor the `describe` row), so adding table rows there would point at sections that don't exist; leaving it to the zh-Hans refresh. The zh-Hans `updating.md` has no receipt paragraph.

## How to Test

1. Parser vs table, from the repo root:

   ```bash
   python3 - <<'EOF'
   import re
   src = open("hermes_cli/subcommands/profile.py").read()
   doc = open("website/docs/reference/profile-commands.md").read().split("## `hermes profile list`")[0]
   parsers = re.findall(r'profile_subparsers\.add_parser\(\s*"([a-z-]+)"', src)
   rows = re.findall(r"^\| `([a-z-]+)` \|", doc, re.M)
   print("missing:", [p for p in parsers if p not in rows], "extra:", [r for r in rows if r not in parsers])
   EOF
   ```

   This branch: `missing: [] extra: []`. On main: `missing: ['purge-identity', 'migrate-identity'] extra: []`.
2. Read `_update_owes_fleet_restart` vs `_pending_fleet_restart_needed` in `hermes_cli/update_cmd_fleet.py`.
3. `python3 website/scripts/check_doc_links.py` → OK.

Ran steps 1 and 3 on Linux (CachyOS) against this branch, and step 1 against main for the before result. Not run: the Docusaurus site build and `pytest` (docs-only change).

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. Docs only; not run.
- [ ] I've added tests for my changes. N/A, docs only.
- [x] I've tested on my platform: Linux (CachyOS), How to Test steps 1 and 3

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
