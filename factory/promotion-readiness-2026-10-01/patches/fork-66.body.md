## What does this PR do?

The TUI weather widget can show a stale result after a relaunch. `load()` (`ui-tui/src/sdk/apps/weather.tsx:229-238` on main) starts `fetchReport()` without waiting for it, and `updateWidget()` in `ui-tui/src/sdk/host.tsx` (lines 84-102) matches the ambient entry by `appId` only, so it cannot tell one launch from the next. If you relaunch `/weather Rome` while `/weather Paris` is still in flight, the older request can settle last:

- **Late success:** the Paris report is painted on the card while `state.location` is already `Rome`.
- **Late failure:** a Paris timeout or error flips Rome's ready card to an error card.

This PR stamps each `load()` with a module-level epoch, and only the latest load may settle the widget. Every fetch goes through `load()` (called from `init` and from the `r` branch of `reduce`), so the guard covers both paths. The fix stays inside the app; there is no SDK/`host.tsx` change.

Weather is the only built-in app that calls `updateWidget()` (checked with `git grep` on main), so no other built-in app has this race. User widgets can also call it through `sdk.updateWidget`; this PR does not change that API, so they are not covered here.

## Related Issue

No upstream issue. The race and the per-launch epoch fix were first proposed by the Detail bot in kvnloo/hermes-agent#66, written against the old wttr.in client. This PR rebuilds that fix on the current Open-Meteo client from #112193, with new tests.

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
4. Not tested: running the TUI against live Open-Meteo. The race is exercised only with a mocked `fetch`.

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

N/A
