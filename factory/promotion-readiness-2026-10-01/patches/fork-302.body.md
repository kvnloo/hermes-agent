## What does this PR do?

**User cost.** With the live-agents dock collapsed (Ctrl+R / F7), `LiveAgentsPanel` still runs its 1 s `setNow` clock for as long as any subagent is live. The collapsed line (`▸ N live agents · <first activity> · …`) never shows agent elapsed, so each tick re-renders the dock and costs a full Ink frame with nothing new to show. The status rule's own 1 s clocks still run when visible, so this removes the dock's extra wakeup and dock re-render, not every idle repaint.

**Mechanism.** `ui-tui/src/components/agentsPanel.tsx:156` on main, `ticking = live || processRows.length > 0`, ignores `collapsed`.

**Measured** (real `LiveAgentsPanel` with fake timers, one running subagent, 10 s window, React `Profiler` commits / Ink `onFrame` count):

| state | `main` | this PR |
|---|---|---|
| collapsed, agents only | 10 commits / 10 frames | **0 / 0** |
| expanded | 10 / 10 | 10 / 10 (unchanged) |

**Fix.** The clock only drops its agent half while the dock is collapsed: `ticking = processRows.length > 0 || (live && !collapsed)`. Process rows keep the clock in both states. A finished process shows `exit N · Ns ago` in the collapsed line and leaves the dock after `PROCESS_RETAIN_SECONDS`, and both of those depend on `now`. When the clock re-arms it re-seeds `now`, the same thing `FaceTicker` / `SessionDuration` / `IdleSince` do when the status rule is uncovered. Expanding after a collapse therefore shows the current elapsed time, not the value from when the dock folded.

This is a rebuild of #127466, which I closed before it was reviewed. The old version also stopped the clock for process rows while collapsed. Its collapsed line then stuck at `exit 0 · 5s ago`, and a finished process could not age out while the dock stayed collapsed. The second test below catches that.

## Related Issue

Refs #111986 (truthful motion / no hidden timer churn), Refs #99773. Supersedes #127466 (closed, unmerged).

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue). This is a perf fix with no visible change.

## Changes Made

- `ui-tui/src/components/agentsPanel.tsx`: the dock clock arms for process rows, or for live agents while expanded. It re-seeds `now` on (re)arm.
- `ui-tui/src/__tests__/agentDockCollapsedClock.test.tsx`: two behaviour tests through the real `LiveAgentsPanel`:
  1. Collapsed with a live agent: 0 commits and 0 Ink frames over 10 s. Expanding paints the live elapsed (`22s`, not the stale `12s`), and the clock then keeps ticking (`23s`).
  2. Collapsed with a finished process: `Ns ago` keeps counting, and the row ages out after `PROCESS_RETAIN_SECONDS`.

## How to Test

1. `cd ui-tui && npx vitest run src/__tests__/agentDockCollapsedClock.test.tsx`
2. On `main`, test 1 fails with `expected [ 10, 10 ] to deeply equal [ +0, +0 ]`. With this change both tests pass.
   Test 2 passes on `main` by design. It pins the process-row ageing that #127466 broke, and it fails under that rule (negative control 2).
3. Negative controls (each fails exactly one test):
   - Drop `&& !collapsed`: test 1 fails with `[10, 10]`.
   - Use the #127466 rule `!collapsed && (live || processRows.length > 0)`: test 2 fails, frozen at `exit 0 · 5s ago`.
   - Drop the re-seed: test 1 fails, showing `probe auth 12s` after expand.
4. Manual check (not run): start a long `delegate_task` (optionally with `HERMES_TUI_FPS=1`), press Ctrl+R to collapse the dock, wait a few seconds, then press Ctrl+R again. The elapsed time shown is current, not the value from when it collapsed.

Results on `main` @ f8489405600c (Linux, Node 26):
`ui-tui/` is unchanged on current `main` (aeff051a18), and the branch merges cleanly.
- New test: 2/2 passed, and 5/5 repeat runs plus a shuffled run were green.
- Adjacent: `agentsDock`, `agentsCompact`, `processDock`, `agentsHydration`, `agentRoster`, `agentControls`, `subagentTree`, `appChromeBlockedTimers` (8 files), plus the new test file: 9 files, 76/76 passed.
- `npm run typecheck` clean. eslint and prettier clean on the touched files.
- Merge-tested (git merge-tree) against my open TUI PRs #129524, #129525, #129526 and #129556: all clean. #129526 edits the `theme` line in the same component, in a different hunk. On a combined tree that also contains #129526 and #129556, this test, their tests and typecheck pass.

Not tested: the full `npm test` vitest suite (only the 9 files above ran), the manual Ctrl+R check in a live TUI, and frame rate or CPU of the full app in a real terminal. The numbers above come from the isolated dock.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: this change is TUI-only. I ran the targeted vitest files and typecheck instead.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), Node 26

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Test 1 on `main`:

```
AssertionError: expected [ 10, 10 ] to deeply equal [ +0, +0 ]
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
