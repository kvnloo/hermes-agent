## What does this PR do?

Docs-only. Each statement below is wrong on current `main`; every correction cites the source that contradicts it. No behaviour changes.

### docs(agents): include hermes-serve* and hermes-dashboard* in restart-per-kind fleet scope

- **Was:** hermes_cli/AGENTS.md:156-158 — "every `hermes-gateway*` unit / `ai.hermes.gateway*` LaunchAgent ... drain-first (SIGUSR1)"
- **Source on main:** hermes_cli/update_cmd_fleet.py:797-812 `_is_hermes_gateway_unit()` accepts hermes-gateway*, hermes-serve*, hermes-dashboard* (#125297); :837-847 `_service_unit_supports_graceful_sigusr1_restart()` is gateway-only ('SIGUSR1 would just kill hermes-serve* ... blunt restart'); update_restart_recovery.py:67 `_SERVE_UNIT_PATTERNS = ("hermes-serve*", "hermes-dashboard*")`.
- **Now:** The bullet names all three unit families and limits the SIGUSR1 drain to gateway units.
- hermes-serve* was missing when the line was written (c500dc6d99, #120140); hermes-dashboard* joined the pass in 3e4fb34778 (#125314).

### docs: drop stale claim that inventoryless markers can't auto-clear

- **Was:** website/docs/getting-started/updating.md:314 — "Legacy markers without an inventory, and malformed or unsupported inventories, cannot be automatically cleared by startup or catch-up reconciliation." The same page contradicts this at :282: "...an older updater that never recorded them): once every live gateway runs the current checkout, the obligation is retired".
- **Source on main:** hermes_cli/update_cmd_fleet.py:380-456 `_marker_only_restart_obsolete()`: docstring and code discharge an inventory-less marker (`owed is None`) when every live row is current (#115638, #125952, gatewayless path #118742); :424 'an inventoried obligation without its SHA can never be proven' stays pending.
- **Now:** The sentence is narrowed to malformed/unsupported inventories and inventories recorded without their target commit.
- Drift introduced by #116710 (d6ef05e275 changed the code; its docs commit 5d17001947 added the :282 paragraph but left :314).

### docs(desktop): note publisher-signed macOS installs aren't replaced by a locally signed rebuild

- **Was:** website/docs/getting-started/updating.md:141 — "On macOS the rebuilt bundle is then copied (with `ditto`, signature intact) over a stale `/Applications/Hermes.app` ..." (no exception for publisher-signed installs)
- **Source on main:** hermes_cli/main_desktop.py:608-636 `_macos_signing_downgrade_error()` (#123748); :1218-1223 `_install_rebuilt_macos_bundles()` appends '<app> not refreshed: <reason>' and skips the swap.
- **Now:** One sentence added: a publisher-signed install is kept, not replaced by a locally signed rebuild or one with a different Team ID or bundle identifier, and the update reports why.
- Drift introduced by c06b3080b6 (#127225).

### docs: cover serve-ticker branch in cron status guidance

- **Was:** website/docs/user-guide/multi-profile-gateways.md:576 — "When no gateway owns the host role, `cron status` tells you to start the **one** host gateway ..."
- **Source on main:** hermes_cli/cron.py:507-531 `cron_status()`: when neither the lock nor the multiplexer serves the profile, `in_process_ticker` = fresh heartbeat + live writer; prints 'Scheduler host: an in-process ticker (hermes serve / Desktop backend) ticking profile ...' (:530) instead of the start-gateway advice.
- **Now:** The sentence covers the in-process ticker branch.
- Drift introduced by fc15ec8fe3 (#126156).

No other copies of these passages exist; the zh-Hans updating.md has neither the Desktop-rebuild nor the marker-settlement text, and there is no zh-Hans multi-profile-gateways.md.

## Related Issue

Replaces my closed PRs #127357, #127358 and #127361, combined into one PR together with the macOS signing note. No issue tracks these doc drifts; the docs now match the code changes made for #125297, #115638, #123748 and #121881.

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [x] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `hermes_cli/AGENTS.md`: restart-per-kind names `hermes-serve*` / `hermes-dashboard*` units; SIGUSR1 drain limited to gateway units.
- `website/docs/getting-started/updating.md`: Desktop rebuild step notes that publisher-signed installs are kept.
- `website/docs/getting-started/updating.md`: marker-settlement sentence narrowed to malformed/unsupported or SHA-less inventories.
- `website/docs/user-guide/multi-profile-gateways.md`: `cron status` guidance covers the in-process serve/Desktop ticker branch.

## How to Test

1. For each item above, read the cited source lines on `main`; the old text contradicts them, the new text matches.
2. Targeted tests on Linux (CachyOS). This branch changes no Python relative to `main`.
   - `tests/hermes_cli/test_desktop_install_after_update.py` (item 3): passes on this branch.
   - `tests/hermes_cli/test_cron_satellite_diagnostics.py` (item 4): passes on this branch.
   - Item 1 is pinned on `main` by `tests/hermes_cli/test_update_fleet_restart_timeout.py` (`test_hermes_dashboard_units_are_included`, `TestGracefulSigusr1Eligibility`); not run for this PR.
   - `tests/hermes_cli/test_update_fleet_restart_pending.py`, which holds the inventory-less marker tests behind item 2, could not run cleanly in my environment: 7 failures reproduce identically on `main` because the test venv belongs to another checkout and `hermes update` re-execs into it. This PR changes no Python.
   - Not tested on macOS; the signing tests stub `codesign`.
3. The Python steps of `.github/workflows/docs-site-checks.yml` pass on this branch: `python3 website/scripts/extract-skills.py && python3 website/scripts/generate-skill-docs.py && git diff --exit-code -- website/docs website/sidebars.ts website/i18n` (clean) and `python3 website/scripts/check_doc_links.py` (OK).
4. Not run: `npm run lint:diagrams` and `npm run build:fast`; the changed lines add no diagrams or MDX-sensitive syntax.

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

Line numbers cited above are as of `main` f848940560 (unchanged on aeff051a18).
