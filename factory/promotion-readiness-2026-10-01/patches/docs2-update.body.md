## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs(agents): include hermes-serve* and hermes-dashboard* in restart-per-kind fleet scope

- **Was:** hermes_cli/AGENTS.md:156-158 — "every `hermes-gateway*` unit / `ai.hermes.gateway*` LaunchAgent ... drain-first (SIGUSR1)"
- **Source on main:** hermes_cli/update_cmd_fleet.py:797-812 _is_hermes_gateway_unit() accepts hermes-gateway*, hermes-serve*, hermes-dashboard* (#125297); :837-847 _service_unit_supports_graceful_sigusr1_restart() is gateway-only ('SIGUSR1 would just kill hermes-serve* ... blunt restart'); update_restart_recovery.py:67 _SERVE_UNIT_PATTERNS = ("hermes-serve*", "hermes-dashboard*").
- **Check:** AGENTS.md enumerates only gateway units for a pass that restarts three families.
- **Now:** Bullet enumerates all three families and scopes SIGUSR1 to gateway units. tests/hermes_cli/test_update_stale_dashboard.py passes on main.
- **Mirrors:** No other copy (website cli-internals.md only names the stage list).
- Drift introduced by 3e4fb34778 (#125314).

### docs: drop stale claim that inventoryless markers can't auto-clear

- **Was:** website/docs/getting-started/updating.md:314 — "Legacy markers without an inventory, and malformed or unsupported inventories, cannot be automatically cleared by startup or catch-up reconciliation." (contradicted by the same page at :282: "...an older updater that never recorded them): once every live gateway runs the current checkout, the obligation is retired")
- **Source on main:** hermes_cli/update_cmd_fleet.py:380-456 _marker_only_restart_obsolete(): docstring and code discharge an inventory-less marker (owed is None) when every live row is current (#115638, #125952, gatewayless path #118742); :424 'an inventoried obligation without its SHA can never be proven' stays pending.
- **Check:** Doc line contradicts both the code and the page's own earlier paragraph.
- **Now:** Sentence narrowed to malformed/unsupported inventories and inventories recorded without their target commit.
- **Mirrors:** website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/getting-started/updating.md has no marker-settlement section — nothing to mirror.
- Drift introduced by 05c5cbf190 (#126179).

### docs(desktop): note publisher-signed macOS installs aren't replaced by a locally signed rebuild

- **Was:** website/docs/getting-started/updating.md:141 — "On macOS the rebuilt bundle is then copied (with `ditto`, signature intact) over a stale `/Applications/Hermes.app` ..." (no exception for publisher-signed installs)
- **Source on main:** hermes_cli/main_desktop.py:608-636 _macos_signing_downgrade_error() (#123748); :1218-1223 _install_rebuilt_macos_bundles() appends '<app> not refreshed: <reason>' and skips the swap.
- **Check:** Doc implies unconditional replacement.
- **Now:** Sentence added. tests/hermes_cli/test_desktop_install_after_update.py passes on main.
- **Mirrors:** website/i18n/zh-Hans/docusaurus-plugin-content-docs/current/getting-started/updating.md has no Desktop-rebuild phase text — nothing to mirror.
- Drift introduced by c06b3080b6 (#127225).

### docs: cover serve-ticker branch in cron status guidance

- **Was:** website/docs/user-guide/multi-profile-gateways.md:576 — "When no gateway owns the host role, `cron status` tells you to start the **one** host gateway ..."
- **Source on main:** hermes_cli/cron.py:507-531 cron_status(): when neither the lock nor the multiplexer serves the profile, in_process_ticker = fresh heartbeat + live writer; prints 'Scheduler host: an in-process ticker (hermes serve / Desktop backend) ticking profile ...' (:530) instead of the start-gateway advice.
- **Check:** Doc describes only the start-gateway branch.
- **Now:** Sentence covers the in-process ticker branch. tests/hermes_cli/test_cron_satellite_diagnostics.py passes on main.
- **Mirrors:** No zh-Hans multi-profile-gateways.md.
- Drift introduced by fc15ec8fe3 (#126156).

## Related Issue

Supersedes our own parked docs PRs #127357, #127358, #127361 (closed to keep the review queue short); no open issue tracks these drifts.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `hermes_cli/AGENTS.md`
- `website/docs/getting-started/updating.md`
- `website/docs/user-guide/multi-profile-gateways.md`

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Behaviour the docs describe, run on this branch: tests/hermes_cli/test_update_stale_dashboard.py tests/hermes_cli/test_desktop_install_after_update.py tests/hermes_cli/test_cron_satellite_diagnostics.py tests/tui_gateway/test_bot_mode_silence_delivery.py pass; tests/hermes_cli/test_update_fleet_restart_pending.py has 7 environment failures identical on main (the shared venv belongs to /workspace/hermes-home/hermes-agent, so cmd_update's retarget_to_owning_install() re-execs there and argparse exits 2) — the bundle changes no Python. Overall 105 passed / 7 failed (pre-existing, env) / 4 skipped.
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

Verified on `main` f848940560; merges cleanly onto eb8d21f482. Branch `ready/docs2-update` @ ec60a9f5a730, 3 files changed, 6 insertions(+), 5 deletions(-).
