## What does this PR do?

The TUI weather widget (`ui-tui/src/sdk/apps/weather.tsx`) starts `fetchReport()` without waiting for it, and `updateWidget()` is scoped to the app id (one ambient entry per `appId`), so it cannot tell one launch from the next. If you relaunch `/weather Rome` while `/weather Paris` is still in flight, the older request can settle last:

- **Late success:** the Paris report is painted on the card while `state.location` is already `Rome`.
- **Late failure:** a Paris timeout or error flips Rome's ready card to an error card.

This PR stamps each `load()` with a module-level epoch, and only the latest load may settle the widget. Both call sites, `init` and the `r` refresh reducer, go through `load()`, so both are covered. The fix stays inside the app; there is no SDK/`host.tsx` change.

## Related Issue

No upstream issue. Downstream origin: kvnloo/hermes-agent#66. That branch was written against the old wttr.in client and carried unrelated files. This PR rebuilds it on the current Open-Meteo client from #112193.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `ui-tui/src/sdk/apps/weather.tsx`: adds the `loadEpoch` guard and one `settle()` helper used by both the resolve and the reject branch.
- `ui-tui/src/__tests__/weatherApp.test.ts`: adds two relaunch-race tests on the Open-Meteo flow. Geocoding answers immediately, and each launch's forecast is held so the older launch can settle last:
  1. A stale forecast resolving last does not replace the newer launch.
  2. A stale forecast failure does not flip the newer launch to error.

## How to Test

From `ui-tui`:

1. `npx vitest run src/__tests__/weatherApp.test.ts`
   - On `main` without the fix, both new tests fail. Test 1 gets `"area": "Paris, France"` under `location: 'Rome'`. Test 2 gets `"kind": "error"` where `"ready"` was expected.
   - With the fix, 7/7 pass.
   - Negative control: changing the guard to `if (true)` makes both tests fail again.
2. `npx vitest run src/__tests__/userWidgets.test.ts src/__tests__/weatherApp.test.ts src/__tests__/widgetGridComponent.test.tsx src/__tests__/widgetSdk.test.ts`: 4 files, 23 tests pass.
3. `npm run typecheck`, plus `eslint` and `prettier --check` on both files: clean.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: TUI-only TypeScript change. The targeted vitest runs above pass.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), vitest

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Not tested: a manual TTY smoke against live Open-Meteo. The race is covered with mocked `fetch` only.
