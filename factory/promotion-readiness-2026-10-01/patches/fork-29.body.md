## What does this PR do?

`adoptedRunningTurn` marks a turn this window resumed onto mid-run, for example when leaving HUD mode, opening a pop-out mid-turn, or opening a subagent watch window. The window never received that turn's prompt row, so the settle path has to hydrate stored history.

Only the normal `message.complete` branch of `completeAssistantMessage` (`apps/desktop/src/app/session/hooks/use-message-stream/index.ts`, where `shouldHydrate` ends in `state.adoptedRunningTurn || !state.sawAssistantPayload`) consumes the flag. If the adopted turn ends any other way, the flag stays `true`:

- Stop (`cancelRun` plus the interrupted late-complete early return)
- an `error` frame (`failAssistantMessage`)
- a `running=false` heartbeat settle

The stale flag then carries into the next turn this window submits itself. That turn's final is non-empty, so the #95514 empty-complete guard passes and the stale flag alone makes `shouldHydrate` true. The result is a redundant `hydrateFromStoredSession` (a REST transcript fetch plus reconcile) over a reply that is already on screen.

This PR clears the flag where this window seeds a turn optimistically:

- the submit optimistic seed (`seedOptimistic` in `use-prompt-actions/submit.ts`)
- the restore/edit/regenerate optimistic arms (`applyRewindOptimistic` / `applyReloadOptimistic` in `rewind.ts`)

Two places are left alone on purpose:

- **`message.start`.** A subagent watch window resumes with `running=true`, which sets the flag, and `tui_gateway`'s `_mirror_subagent_to_child` then sends a synthetic `message.start` for that same adopted turn, so clearing there would skip the hydrate that shows the child's goal/prompt row (watch windows have no composer, so clearing at submit cannot affect them).
- **Settle paths.** A heartbeat can arrive before an adopted turn's reordered `message.complete` (#119569).

Known remainder: a turn this window did not seed can still inherit a leaked flag. That covers backend-started turns (a queue drain from another window, a goal follow-up) and quick-entry sends (`submitToSession`). Those turns' prompts were not written in this window, so the extra hydrate is harmless.

The leak and these three clear sites were first proposed by an automated Detail fix on my fork (kvnloo/hermes-agent#29), credited with a `Co-authored-by` trailer. That version also cleared the flag at `message.start` and on every settle path; this PR drops those for the reasons above.

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

## How to Test

Branch `ready/fork-29-desktop-adopted-turn-stale-flag-v2` is one commit on `main` at 330d9d6. All commands run from `apps/desktop`.

1. `npx vitest run src/app/session/hooks/use-prompt-actions/index.test.tsx src/app/session/hooks/use-prompt-actions/rewind.test.ts`
   - **On 330d9d6 with only the test changes:** 2 failed / 182 passed. `index.test.tsx:2214` reports `expected false to be true` (`seeds.every(s => s.adoptedRunningTurn === false)`). `rewind.test.ts:691` reports `expected true to be false`.
   - **With the fix:** 184 / 184 pass.
   - **Negative control:** with each new line changed to `adoptedRunningTurn: state.adoptedRunningTurn`, both new tests fail again with the same assertions.
2. **Adjacent suites:** `npx vitest run src/app/session/hooks/use-message-stream/ src/app/session/hooks/use-session-actions.test.tsx src/app/session/hooks/use-prompt-actions/ src/app/chat/ src/app/contrib/` gives 258 files / 2292 tests passed.
3. **Typecheck:** every step of `npm run typecheck` is clean: `tsc -p .`, `tsc -p tsconfig.electron.json`, `tsc -p tsconfig.e2e.json` and the electron-builder config check.
4. **Lint/format:** eslint reports 0 errors and prettier is clean on the touched files. The one eslint warning, `react-hooks/exhaustive-deps` on the test Harness `useEffect`, is also on `main`.

Not tested: a live Electron adopt → Stop → next-submit run. The leak path comes from reading the code. Also not addressed: a submit or queue drain that lands between a `running=false` heartbeat settle and the adopted turn's late reordered `message.complete` (#119569). That race exists on main.

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
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
