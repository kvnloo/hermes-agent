## What does this PR do?

`adoptedRunningTurn` marks a turn this window resumed onto mid-run, for example when leaving HUD mode, opening a pop-out mid-turn, or opening a subagent watch window. The window never received that turn's prompt row, so the settle path has to hydrate stored history.

Only the normal `message.complete` branch of `completeAssistantMessage` consumes the flag. If the adopted turn ends any other way, the flag stays `true`:

- Stop (`cancelRun` plus the interrupted late-complete early return)
- an `error` frame (`failAssistantMessage`)
- a `running=false` heartbeat settle

The stale flag then carries into the next turn this window submits itself. That turn's final is non-empty, so the `#95514` empty-complete guard passes and the stale flag alone makes `shouldHydrate` true. The result is a redundant `hydrateFromStoredSession` (a REST transcript fetch plus reconcile) over a reply that is already on screen.

This PR clears the flag where this window starts a turn itself:

- the submit optimistic seed (`seedOptimistic` in `use-prompt-actions/submit.ts`)
- the restore/edit/regenerate optimistic arms (`applyRewindOptimistic` / `applyReloadOptimistic` in `rewind.ts`)

Two places are left alone on purpose:

- **`message.start`.** A subagent watch window resumes with `running=true`, which sets the flag. `tui_gateway`'s `_mirror_subagent_to_child` then sends a synthetic `message.start` into that window for the same adopted turn, and that turn still needs its hydrate to show the child's goal/prompt row. Watch windows have no composer, so clearing at submit cannot affect them.
- **Settle paths.** A heartbeat can arrive before an adopted turn's reordered `message.complete` (#119569).

Known remainder: a turn started by the backend rather than this window (a queue drain from another window, a goal follow-up) can still inherit a leaked flag. That only hydrates a turn whose prompt this window did not write, which is acceptable.

## Related Issue

There is no upstream issue for this. #127911 / #127939 are related but different: they cover duplicate cards when hydrating an interrupted turn itself. This PR covers a stale adoption flag on a *later* turn.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/src/app/session/hooks/use-prompt-actions/submit.ts`: the optimistic seed sets `adoptedRunningTurn: false`.
- `apps/desktop/src/app/session/hooks/use-prompt-actions/rewind.ts`: `applyReloadOptimistic` and `applyRewindOptimistic` set `adoptedRunningTurn: false`.
- Tests:
  - `use-prompt-actions/index.test.tsx`: a fresh submit clears a leaked flag. The test Harness gains an optional `seedAdoptedRunningTurn` prop.
  - `use-prompt-actions/rewind.test.ts`: both rewind/reload arms clear a leaked flag.
  - `use-message-stream/session-info-side-effects.test.tsx`: an adopted watch turn that receives `message.start` (the child-mirror case) still hydrates on settle. This guard passes on `main` and with the fix, and fails if the flag is instead cleared at `message.start`.

## How to Test

1. `cd apps/desktop && npx vitest run src/app/session/hooks/use-prompt-actions/index.test.tsx src/app/session/hooks/use-prompt-actions/rewind.test.ts src/app/session/hooks/use-message-stream/session-info-side-effects.test.tsx`
   - **On `main` (tests only):** 2 failed / 194 passed. `index.test.tsx:2163` reports `expected false to be true` (`seeds.every(s => s.adoptedRunningTurn === false)`). `rewind.test.ts:691` reports `expected true to be false`. The child-mirror guard passes.
   - **With the fix:** 196 / 196 pass.
   - **Negative control:** with each new line changed to `adoptedRunningTurn: state.adoptedRunningTurn`, both new tests fail again.
   - **Alternative rejected:** clearing the flag at `message.start` instead makes the child-mirror guard fail (`expected "vi.fn()" to be called with arguments: [ 3, null, 'session-active' ]`).
2. **Adjacent suites:** `npx vitest run src/app/session/hooks/use-message-stream/ src/app/session/hooks/use-session-actions.test.tsx src/app/session/hooks/use-prompt-actions/ src/app/chat/` gives 228 files passed.
3. **Typecheck:** the renderer (`tsc -p .`), e2e and builder-config legs are clean. The electron leg has one error that also occurs on unmodified `main`, in an untouched test: `electron/channel-build-version.test.ts(321,22) TS2307 ... bundle-smoke-metadata.mjs`.
4. **Lint/format:** eslint and prettier are clean on the touched files. The one remaining eslint warning, `react-hooks/exhaustive-deps` on the test Harness `useEffect`, also appears on `main`.

Not tested: a live Electron adopt → Stop → next-submit run. The leak path comes from reading the code.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: this is a desktop TypeScript change only; the targeted vitest suites above pass.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (vitest/jsdom only)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
