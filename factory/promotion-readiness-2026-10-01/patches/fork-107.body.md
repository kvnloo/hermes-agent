## What does this PR do?

Tool call ids are not unique across turns: llama.cpp emits one constant id, and Hermes' own deterministic ids repeat. When a turn's `tool.complete` is lost (degraded websocket, reconnect), settle seals that tool part with `completedAt` and no `result`. `toolCallOwnerMessageId` treats any part without a `result` as the owner. So when a later turn sends `tool.start` with the same id, the event is routed back onto the old sealed row. `upsertToolPart`'s unseal branch then writes the new call's command over the old turn's row, and the live turn shows no tool row at all.

The fix makes the owner lookup depend on the event phase:

- **`complete` event:** still reconciles with a sealed-no-result part wherever that part is. This is the late result arriving after settle (#113035), and it is unchanged.
- **`running` event:** re-arms a sealed-no-result part only while that part's turn is still in flight. The owning bubble must be `pending` or `interim`, and no settled reply may have landed after it.

The `interim` flag alone is not enough evidence. A bubble sealed by interim commentary keeps `interim: true` after its turn settles into a later bubble. The session-wide `interimBoundaryPending` flag is also not used, because a later turn can set it.

Trade-off: an id alone cannot tell a reused id from a late running event for the old call. Once the old turn has settled, a running event with that id (for example a replayed `tool.start`) now opens its own row instead of re-arming the sealed one. The completion lookup is unchanged.

## Related Issue

Refs #113035. Follows #113123, which excluded parts that already have a `result`, and #128009, which handles a reused id within the same message. This PR covers the case those leave open: a part sealed without a result, from an earlier turn.

Builds on kvnloo/hermes-agent#107 by detail-app[bot], which found this case and proposed the phase-aware lookup and the plain-settle guard test. Its per-row `pending || interim` gate leaves the interim-sealed shape (b) open, so this version adds the settled-reply boundary.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/src/lib/chat-messages/tool-parts.ts`: `toolCallOwnerMessageId(messages, payload, phase)`. A running-phase event skips a sealed-no-result candidate unless its bubble is pending or interim and no settled assistant reply (`!pending && !interim && completedAt`) is newer than it.
- `apps/desktop/src/app/session/hooks/use-message-stream/index.ts`: `upsertToolCall` passes its `phase` to the lookup.
- `apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/tools.ts`: the `tool.complete` production probe passes `'complete'`, so its behaviour is unchanged.
- `apps/desktop/src/app/session/hooks/use-message-stream/late-tool-events.test.tsx` gets two new tests:
  - A three-way `it.each` test: a reused id after a lost completion gets its own row when the prior turn (a) settled on its own bubble, (b) sealed the call behind interim commentary and then settled, or (c) settled, with the later turn opening with interim commentary.
  - A test that a late completion still attaches to a part sealed by a plain turn settle.

## How to Test

1. `cd apps/desktop && npx vitest run --project ui src/app/session/hooks/use-message-stream/late-tool-events.test.tsx` gives 7/7 passing.
2. On the base commit (f8489405) without the fix, all three reuse shapes fail with `expected [ { messageIndex: +0, …(1) } ] to have a length of 2 but got 1`. The old row is overwritten and the new turn has no row. The plain-settle late-completion test passes on the base; it guards the phase split.
3. Negative controls, each applied to the fix on its own:
   - Dropping the settled-reply check (so `pending || interim` alone counts as in flight): shape (b) fails.
   - Removing the running-phase check entirely: all three shapes fail.
   - Applying the check to both phases: the plain-settle late-completion test fails.
4. Neighbouring tests: `src/app/session/hooks/use-message-stream` (all files), `src/lib/chat-messages*`, `src/lib/tool-run-continuity.test.ts` and `src/components/assistant-ui/tool/inline-edit-persistence.test.tsx` give 63 files, 442 tests passing. `tsc -p . --noEmit` is clean. eslint and prettier are clean on the changed files.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: desktop TypeScript only. The targeted vitest suites above pass.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), vitest jsdom project `ui`

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A (docstring updated)
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

All runs above were on base f8489405. The branch merges cleanly onto current main but was not re-run there.

Not tested: the electron typecheck projects (no electron files changed), and an Electron run against a live gateway with a dropped websocket. The tests drive the real `useMessageStream` event handler through the shared test harness.
