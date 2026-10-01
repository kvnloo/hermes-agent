<!-- PR title: fix(desktop): keep a stale no-owner recovery from latching a live session read-only -->
<!-- branch: ready/fork-49-tile-stale-readonly-recovery-v2 -->

## What does this PR do?

Fixes a race in the Desktop no-owner read-only recovery (#94724). The race can leave a session read-only after it has been proven routable.

When the owner gate fails closed, both recovery paths await a stored read and then latch the stored id read-only: the tile path (`resumeTile` → `resumeWithStoredTranscriptFallback`) and the main pane (the `catch` in `resumeSession`). Suppose a live resume of the same stored id lands while that recovery is still pending, for example because the single-match owner backfill stamped the row in the meantime. The stale recovery still finishes last and:

1. **Sets the global read-only latch over the live outcome.** The live resume's `clearStoredTranscriptReadOnly` ran before the latch was set, so it cleared nothing. From then on, the main-pane submit refuses sends for that session.
2. **In a tile, repaints the session read-only and repoints the stored → runtime binding** onto the synthetic `read-only:<id>`. Every later open takes the warm path, which reuses that binding. The tile stays read-only and `submitToSession` refuses sends.

The main pane already drops its own superseded resumes with `isCurrentResume()`. The helper-backed tile path had no equivalent, and neither path noticed a live resume of the same id that the other path made (a tile vs. the main pane).

The fix uses one shared signal instead of bookkeeping in each path. Every successful live resume, from a tile or the main pane, calls `clearStoredTranscriptReadOnly`. That function now bumps a per-stored-id generation, even when the clear itself is a no-op. Each recovery takes a snapshot of the generation when its resume attempt starts, and backs off if the generation has moved:

- `resumeWithStoredTranscriptFallback` sets the latch only if the generation still matches the snapshot. The snapshot is an optional argument that defaults to call time. Other callers of the helper therefore get the guard without changes, for example the session-rpc-dispatcher path proposed in #102690.
- `resumeTile` takes its snapshot on entry, before the owner probe, and passes it to the helper. If a live resume has already bound the session, a read-only outcome returns that binding and paints nothing. If nothing is bound yet, it paints as before, so it never returns an unpainted `read-only:<id>`.
- `resumeSession` takes its snapshot on entry. The main-pane recovery still paints the history it read. It sets the latch and shows the "Opened read-only" toast only if the generation has not moved. Otherwise it returns with the history shown and no latch, and the next send resumes the session through the normal submit path.

Scope: some live re-resumes never call `clearStoredTranscriptReadOnly` on main, for example the session-not-found recovery inside submit and interrupt. They still don't bump the generation. This PR leaves them unchanged.

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

- `apps/desktop/src/store/read-only-transcript.ts`: adds a per-stored-id live-resume generation. `clearStoredTranscriptReadOnly` bumps it, and the new `liveResumeGeneration()` reads it. `resumeWithStoredTranscriptFallback` takes an optional `liveResumesAtStart` snapshot and skips `markStoredTranscriptReadOnly` when the generation has moved.
- `apps/desktop/src/app/contrib/hooks/use-session-tile-delegate.ts`: `resumeTile` takes the snapshot on entry and passes it to the helper. For a superseded read-only outcome, it returns the existing binding without calling `updateSessionState`.
- `apps/desktop/src/app/session/hooks/use-session-actions/index.ts`: `resumeSession` takes the snapshot on entry. The no-owner recovery calls `markStoredTranscriptReadOnly` and shows its toast only when the generation has not moved.
- `apps/desktop/src/app/contrib/hooks/use-session-tile-delegate.test.ts`: tile race test. Call A waits on a deferred cross-backend stored read, call B resumes live, then A's read resolves. The tile must stay bound to the live runtime, get no `read-only:*` paint, and stay unlatched. The file-level `@/hermes` mock gains a `fetchStoredTranscriptAcrossBackends` stub and a rejecting `getSession`. This lets the test control the stored read and keeps the unowned row's owner unresolvable. The mock applies to every suite in the file, and they all still pass.
- `apps/desktop/src/app/session/hooks/use-session-actions.test.tsx`: main-pane race test. The resume fails with `SessionOwnerResolutionError`, and the recovery waits on a deferred REST read. Meanwhile a tile-style live resume of the same id runs through `resumeWithStoredTranscriptFallback`, then the read resolves. The history must be painted and the id must stay unlatched.

## How to Test

Run from `apps/desktop`. All results below are on main at `895b506ec9`.

1. `npx vitest run --project ui src/app/contrib/hooks/use-session-tile-delegate.test.ts src/app/session/hooks/use-session-actions.test.tsx src/store/read-only-transcript.test.ts`: 168/168 pass.
2. Red run on main without the fix (the three production files reverted, tests kept): both new tests fail and everything else passes (2 failed, 166 passed).
   - Tile test: `expected 'read-only:stored-race' to be 'runtime-live'`.
   - Main-pane test: fails on the latch assertion (`expected true to be false`).
3. Negative controls, disabling one guard at a time:
   - Tile paint guard: the tile test fails with `expected 'read-only:stored-race' to be 'runtime-live'`.
   - Helper latch guard: the tile test fails on the latch (`expected true to be false`).
   - Main-pane latch guard: the main-pane test fails on the latch (`expected true to be false`).

   Each guard is required on its own.
4. Owner-probe window, checked with a throwaway test that is not committed: call A waits in its owner probe (`getSession`) instead of the stored read. This passes with the change. It fails on the latch when `resumeTile` does not pass its entry snapshot to the helper, and it fails on main. That is why the helper takes the snapshot argument.
5. Adjacent: `npx vitest run --project ui src/app/contrib/ src/app/chat/session-tile src/store/read-only-transcript.test.ts src/store/session-owner-resolution.test.ts src/lib/legacy-session-owner-backfill.test.ts src/app/session/hooks/`: 123 files, 1439 tests pass.
6. `npm run typecheck`:
   - `tsc -p . --noEmit`, the `tsconfig.e2e.json` step and the `electron-builder.config.cjs` step are clean.
   - The `tsconfig.electron.json` step reports one error in `electron/channel-build-version.test.ts`: it cannot find type declarations for `tests/install/e2e-assets/bundle-smoke-metadata.mjs`. Plain main reports the same error.
7. `eslint` and `prettier --check` on the five changed files are clean, apart from one `react-hooks/exhaustive-deps` warning in `use-session-actions/index.ts` that main already has.

Not run: the full `npm run lint` and the full UI/electron suites. Not reproduced in a running Desktop (Electron) app; both races were exercised only in the vitest/jsdom harness.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass (N/A: desktop-only TypeScript change; the targeted vitest runs are listed above)
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), vitest jsdom

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Both new tests on main without the fix (production files reverted, tests kept):

```
 FAIL  |ui| use-session-tile-delegate.test.ts > useSessionTileDelegate resumeTile no-owner recovery race (#94724) > a stale recovery that resolves after a live resume leaves the tile live
AssertionError: expected 'read-only:stored-race' to be 'runtime-live' // Object.is equality

 FAIL  |ui| use-session-actions.test.tsx > resumeSession failure recovery > does not latch a no-owner recovery read-only once a tile resumes the same id live (#94724)
AssertionError: expected true to be false // Object.is equality

 Test Files  2 failed | 1 passed (3)
      Tests  2 failed | 166 passed (168)
```
