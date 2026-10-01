<!-- PR title: fix(desktop): keep a stale no-owner tile recovery from latching a live session read-only -->

## What does this PR do?

Fixes a race in the Desktop no-owner tile recovery (#94724) that can leave a session tile stuck read-only after the session has been proven routable.

`resumeTile` dispatches the resume through `resumeWithStoredTranscriptFallback`. When the owner gate fails closed, the helper awaits a cross-backend stored read and then latches the stored id read-only. If a second `resumeTile` for the same stored id resumes live while that read is still in flight (for example, the single-match owner backfill stamped the row in the meantime), the stale recovery still resolves last and:

1. **Sets the global read-only latch over the live outcome.** The live resume's `clearStoredTranscriptReadOnly` ran while the latch was not set yet, so it cleared nothing.
2. **Repaints the tile read-only and repoints the stored → runtime binding** onto the synthetic `read-only:<id>`. On every later open, the warm path reuses that binding, so the tile stays read-only and `submitToSession` refuses sends.

The main pane already drops its own superseded resumes with `isCurrentResume()`; the helper-backed tile path had no equivalent.

Fix (two small guards, one per effect):

- `read-only-transcript.ts`: each successful live resume bumps a per-stored-id generation, including when the clear is a no-op. The recovery captures the generation before its stored read and latches only if the generation has not moved. This also covers other callers of the helper, such as the session-rpc-dispatcher path proposed in #102690.
- `use-session-tile-delegate.ts`: `resumeTile` bumps a per-stored-id epoch on entry. A **read-only** outcome from a superseded call returns the current binding without painting or rebinding. Live outcomes are unchanged.

Not covered: the main-pane recovery in `apps/desktop/src/app/session/hooks/use-session-actions/index.ts` sets the latch with `markStoredTranscriptReadOnly` directly, so a main-pane no-owner recovery that resolves after a tile live resume for the same id can still latch it.

## Related Issue

Refs #94724 (the no-owner read-only recovery introduced in #96110)

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [ ] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `apps/desktop/src/store/read-only-transcript.ts`: adds a per-stored-id live-resume generation. `clearStoredTranscriptReadOnly` bumps it, and `resumeWithStoredTranscriptFallback` skips `markStoredTranscriptReadOnly` when the generation moved during the stored read.
- `apps/desktop/src/app/contrib/hooks/use-session-tile-delegate.ts`: adds a per-stored-id `resumeTile` epoch. A stale read-only outcome returns the current binding without calling `updateSessionState`.
- `apps/desktop/src/app/contrib/hooks/use-session-tile-delegate.test.ts`: adds two tests. The first is the race: call A parks on a deferred stored read, call B resumes live, then A resolves. The tile must stay bound to the live runtime, get no `read-only:*` paint, and stay unlatched. The second is a regression guard: a lone no-owner recovery still opens the tile read-only. The commit also extends the file-level `@/hermes` mock with a `fetchStoredTranscriptAcrossBackends` stub and a rejecting `getSession`, so the race test controls the cross-backend stored read and the unowned row's owner stays unresolvable. That mock applies to every suite in the file.

## How to Test

From `apps/desktop`. Steps 1–4 were run with this change on main at `f848940560`.

1. `npx vitest run --project ui src/app/contrib/hooks/use-session-tile-delegate.test.ts src/store/read-only-transcript.test.ts`: all pass.
2. Red run on main without the fix (production files reverted, tests kept): the race test fails with `expected 'read-only:stored-race' to be 'runtime-live'`. The lone-recovery regression guard passes, as intended.
3. Negative controls: disabling only the tile epoch guard fails the same assertion. Disabling only the helper generation guard fails the latch assertion (`expected true to be false`). Each guard is independently required.
4. Adjacent: `npx vitest run --project ui src/app/contrib/hooks/ src/app/contrib/session-rpc-dispatcher.test.ts src/app/chat/session-tile src/store/read-only-transcript.test.ts src/store/session-owner-resolution.test.ts`: all pass.
5. `eslint` and `prettier --check` are clean on the three changed files. `tsc -p . --noEmit` is clean apart from one missing `tests/fixtures/*.json` import, which comes from my sparse checkout and not from this change. The full `npm run typecheck`, `npm run lint` and the full UI/electron suites were not run. Not reproduced or verified in a running Desktop (Electron) app; the race was exercised only in the vitest/jsdom harness.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (N/A, desktop-only TypeScript change; targeted vitest runs listed above)
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), vitest jsdom

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Race test on main without the fix (production files reverted, tests kept):

```
AssertionError: expected 'read-only:stored-race' to be 'runtime-live' // Object.is equality
 FAIL  |ui| use-session-tile-delegate.test.ts > useSessionTileDelegate resumeTile no-owner recovery race (#94724) > a stale recovery that resolves after a live resume leaves the tile live
```
