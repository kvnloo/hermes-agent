## What does this PR do?

`probeGatewayWebSocket` (`apps/desktop/electron/gateway-ws-probe.ts`) backs the desktop "Test remote" action and the boot probes. It arms two timers:

- a **connect timer** (`connectTimeoutMs`, 10 s by default) that fails the probe if the socket never opens;
- a **grace timer** (`readyGraceMs`, 750 ms by default), armed in `onOpen`, that catches a post-handshake credential rejection (open, then immediate close).

`onOpen` arms the grace timer but leaves the connect timer running. If the upgrade lands in the last `readyGraceMs` of the connect budget (9.25–10 s with the defaults), the connect timer fires first. The probe then resolves `{ ok: false }` with a "Timed out after ...ms waiting for the WebSocket to open" reason, for a socket that opened and stayed open. The renderer's real dial (`apps/shared/src/json-rpc-gateway.ts`) already clears its connect timer on open, so the probe and the real connection can disagree.

The fix calls the existing `clearTimers()` in `onOpen`, before the grace timer is armed. After a successful upgrade, only the grace window, a frame, an error or a close can settle the probe.

Credit: the bug and the original fix were found by Detail's automated bug finder (detail-app[bot]). This PR rebuilds that fix on current `main` with the existing `clearTimers()` helper and keeps its regression test.

## Related Issue

No upstream issue or PR found. Searched PRs and issues for `gateway-ws-probe`, `probeGatewayWebSocket`, `connectTimer` and "probe grace window". #41570 (closed) only changed the grace length.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/electron/gateway-ws-probe.ts`: `onOpen` calls `clearTimers()` before it arms the grace timer (one line plus a comment).
- `apps/desktop/electron/gateway-ws-probe.test.ts`: new test `probe resolves ok when the socket opens late in the connect budget and stays open`. It uses `readyGraceMs` (200) > `connectTimeoutMs` (50), so the grace deadline falls after the connect deadline. It emits `open` and asserts `{ ok: true }`.

## How to Test

1. `cd apps/desktop && npx vitest run --project electron electron/gateway-ws-probe.test.ts`
2. On unpatched `main` the new test fails with `Received { ok: false, reason: 'Timed out after 50ms waiting for the WebSocket to open.' }`.
3. With the patch, 19/19 pass. With only the `clearTimers()` line commented out, the new test fails again with the same reason.
4. Adjacent: `electron/gateway-ws-probe.test.ts`, `connection-config.test.ts`, `connection-config-apply.test.ts`, `backend-probes.test.ts`, `backend-probes-runtime.test.ts` and `backend-connection-state.test.ts` give 169 passed. `tsc -p tsconfig.electron.json --noEmit`, `eslint` and `prettier --check` on both files are clean.

Not tested: the same race in the `keepWaitingWhile` path (spawned backend), where the checkpoint keeps rescheduling after open and can reach the hard cap during the grace window. The same line fixes it, but no test covers it. I also did not run a live "Test remote" against a real gateway.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
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
