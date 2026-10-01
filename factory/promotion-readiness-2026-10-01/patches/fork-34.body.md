## What does this PR do?

`probeGatewayWebSocket` (`apps/desktop/electron/gateway-ws-probe.ts`) backs the desktop "Test remote" action and the boot probes. It arms two timers:

- a **connect timer** (`connectTimeoutMs`, 10 s by default) that fails the probe if the socket never opens;
- a **grace timer** (`readyGraceMs`, 750 ms by default), armed in `onOpen`, that catches a post-handshake credential rejection (open, then immediate close).

`onOpen` arms the grace timer but leaves the connect timer running. If the upgrade lands in the last `readyGraceMs` of the connect budget (9.25–10 s with the defaults), the connect timer fires first. The probe then resolves `{ ok: false }` with a "Timed out after ...ms waiting for the WebSocket to open" reason, for a socket that opened and stayed open. The renderer's real dial (`apps/shared/src/json-rpc-gateway.ts`) already clears its connect timer on open, so the probe and the real connection can disagree.

The fix calls the existing `clearTimers()` in `onOpen`, before the grace timer is armed. After a successful upgrade, only the grace window, a frame, an error or a close can settle the probe.

The same line also covers the `keepWaitingWhile` path used when the desktop spawns its own backend. There the connect timer keeps re-arming as a checkpoint after open and can hit the `maxConnectWaitMs` hard cap during the grace window.

Credit: Detail's automated bug finder (detail-app[bot]) found this bug and wrote the original fix. This PR rebuilds that fix on current `main` with the existing `clearTimers()` helper and keeps its regression test. The commit carries a `Co-authored-by: detail-app[bot]` trailer.

## Related Issue

Overlaps #93186 (open, by @Finn763). Item 4 of that PR ("Connect timer disarmed on open") makes the same `onOpen` change in `gateway-ws-probe.ts` and adds an equivalent test, together with a larger boot-time RPC verification change. That PR reported the defect upstream first. This PR is a standalone version of only that hunk. If #93186 merges first, this PR is redundant and should be closed.

No upstream issue covers it. #41570 (closed) only changed the grace length.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/electron/gateway-ws-probe.ts`: `onOpen` calls `clearTimers()` before it arms the grace timer (one line plus a comment).
- `apps/desktop/electron/gateway-ws-probe.test.ts`: new test `probe resolves ok when the socket opens late in the connect budget and stays open`. It uses `readyGraceMs` (200) > `connectTimeoutMs` (50), so the grace deadline falls after the connect deadline. It emits `open` and asserts `{ ok: true }`.

## How to Test

1. Check out `ready/fork-34-ws-probe-connect-timer-v2` (one commit on `main` @ 330d9d6d), then run `cd apps/desktop && npx vitest run --project electron electron/gateway-ws-probe.test.ts`.
2. Apply only the test hunk to `main` and rerun step 1. The new test fails with `Received { ok: false, reason: 'Timed out after 50ms waiting for the WebSocket to open.' }` (1 failed, 18 passed).
3. With the patch, 19/19 pass. With only the `clearTimers()` line commented out, the new test fails again with the same reason.
4. Adjacent: `electron/gateway-ws-probe.test.ts`, `connection-config.test.ts`, `connection-config-apply.test.ts`, `backend-probes.test.ts`, `backend-probes-runtime.test.ts`, `backend-connection-state.test.ts` and `backend-ready.test.ts` give 7 files, 196 passed. `tsc -p tsconfig.electron.json --noEmit`, `eslint` and `prettier --check` on both files are clean.
5. `keepWaitingWhile` variant, checked with a local fake-timer case that is not part of this PR (`connectTimeoutMs` 30, `progressCheckIntervalMs` 5, `maxConnectWaitMs` 60, `readyGraceMs` 50, `keepWaitingWhile: () => true`, `open` at 55 ms). On `main` it resolves `Timed out after 60ms waiting for the WebSocket to open (backend still running at the 60ms cap).` With the patch it resolves `{ ok: true }`.

Not tested: a live "Test remote" or spawned-backend boot against a real gateway.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate (the overlap with #93186 is described above)
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: TypeScript-only change. I ran the targeted vitest files listed above.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)
