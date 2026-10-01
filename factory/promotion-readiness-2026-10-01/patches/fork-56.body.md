## What does this PR do?

A collapsed paste (`[[ … [N lines] … ]]`) is lost when you submit it while the agent is busy, or before the first session exists. The model gets the literal label instead of the pasted body. This is the deterministic loss point that the later reports on #99032 trace to the busy-input and pre-session queue paths.

**Why it happens.** The pasted body lives only in the composer's tokens, and `clearIn()` drops those tokens synchronously on submit. The idle path expands the paste before that happens, so it works. The other paths keep the display string and try to expand it later, after the tokens are gone:

- busy: `handleBusyInput(queueItem(full))`
- no session: `enqueue(full)`

What the model then receives, by `busy_input_mode`:

| mode | before | after |
|---|---|---|
| interrupt | label | expanded paste |
| steer | label | expanded paste |
| queue (on drain) | label | expanded paste |
| no session yet (on drain) | label | expanded paste |

**Execution boundary on drain.** `sendQueued` decided `!` and `{!...}` from `item.text`. For a `/queue` item, that is the *expanded* paste. So a `/queue [[ paste ]]` whose content started with `!` was shell-executed when it drained, and `{!...}` inside pasted content was interpolated. Storing expanded text for busy items would have extended that to every busy submit. Drain now makes those decisions the way a direct submit does:

- Whether an item is shell-executed (`!`) and which `{!...}` commands run are decided only from `display`, where the paste is still its label. A `!` the user typed (`/queue !cmd <paste>`) still runs with the paste expanded, as it does on main.
- Interpolation runs on the display. The paste is expanded into the result afterwards.

**Known limitation, pre-existing and unchanged.** The paste label includes an edge preview of the pasted text: the first 16 and last 28 characters. If a `{!...}` falls inside that preview, it is visible in the display, and both the direct and queued paths interpolate it. Fixing that belongs in the label builder, so it is out of scope here.

## Related Issue

Refs #99032. This fixes the busy-input paths (interrupt, steer, queue) and input queued before the first session exists. Not addressed here: the first-session race also reported on #99032, where a paste made before session.create returns loses its tokens to resetSession and the label stays in the composer. That needs a separate fix.

Follows #75565 (@austinpickett) and #74797 (@eloklam), which fixed the same loss on the idle and `/queue` paths. The `/queue` path here keeps #74797's display/text split (`queueItemFromSlash`) and the slash-argument paste resolution from #100837 (@OutThisLife). This PR covers the remaining busy and no-session paths. Root cause as traced in the later comments on #99032. For these paths the approach follows the repair @Khwan888 described there: each queued item keeps its display, its payload and a snapshot of its paste tokens through the drain, and typed syntax is judged separately from pasted content.

It is complementary to #99042, which handles a placeholder that is already orphaned when it is dispatched; that PR does not change the busy or queue paths. @kokhlo, who has claimed #99032, keeps the orphaned-placeholder guard in #99042.

Overlap with open PRs:
- #123756 changes the guard condition on the Ctrl+K line just above the one this PR touches, so whichever lands second needs a trivial rebase. Its test may also need to expect `sendQueued`.
- #129525 (mine) changes `useQueue.ts` imports, again a trivial rebase.
- #99042 changes the return type of `expandTokens`, so the `expandTokens(...)` expander passed here would need its `.expanded` adapter.
- #74689 touches `useQueue.ts`/`useSubmission.ts` for queue session scoping; different defect, may need a rebase.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔒 Security fix
- [ ] 📝 Documentation update
- [ ] ✅ Tests (adding or improving test coverage)
- [ ] ♻️ Refactor (no behavior change)
- [ ] 🎯 New skill (bundled or hub)

## Changes Made

- `ui-tui/src/app/useSubmission.ts`
  - Busy and no-session submits queue `submission.text` (expanded), keep `full` (label) as `display`, and carry an expander built from the submit-time tokens. The `/queue` slash path carries `expandPasteTokens(...)`, so its image labels stay as labels, as they do today.
  - `sendQueued(item)`:
    - gates `!` on `item.display` and runs the expanded `item.text`;
    - gates `{!...}` on `item.display`, interpolates the display, then applies `item.expand`;
    - passes the display to `send`, so the transcript keeps the label.
  - The interrupt branch of `handleBusyInput` sends `item.text` with `item.display` as the bubble.
  - Double-Enter drains through `sendQueued(item)` instead of `dispatchSubmission(text)`, which treated queued text as fresh composer input and re-ran slash, `!` and interpolation parsing over pasted bytes.
  - Behaviour change: a manual drain (double-Enter or Ctrl+K) now goes through the same `sendQueued` path as the automatic drain effect in `useMainApp`. One visible effect: a queued item whose text looks like a slash command (`/queue /help`) used to run as a slash command when drained manually. It is now sent as a prompt, the same as the automatic drain always sent it.
- `ui-tui/src/hooks/useQueue.ts`
  - `QueueItem` gains an optional `expand`.
  - `queueItem`, `enqueue` and `takeQueueItem` carry `expand` through.
  - `dequeue()` returns the `QueueItem`, not just `.text`.
- `ui-tui/src/app/useInputHandlers.ts`, `useMainApp.ts`, `interfaces.ts`: Ctrl+K drains through `actions.sendQueued`; the types follow.
- `ui-tui/src/__tests__/queuedPasteSubmission.test.tsx` (new)
  - Mounts the real `useSubmission` and `useQueue` against a fake gateway.
  - `clearIn` drops the tokens, as the composer does.
  - Uses real `pasteTokenLabel` labels.
  - Asserts the exact `prompt.submit` / `session.steer` text, the shell commands run, and the transcript.
- `ui-tui/src/__tests__/queueScopeRenderer.test.tsx`: follows the `dequeue()` return type.

## How to Test

1. Setup in a fresh clone: `npm ci` from the repository root, then `cd ui-tui && npm run build:ink`. Then run `npx vitest run src/__tests__/queuedPasteSubmission.test.tsx`.
   - With this change: 6 passed.
   - Same file on `main` at f848940560 (this branch's base): 6 failed. Examples:
     - interrupt, steer and queue modes and no-session: `expected ["review this: [[ line one line two line three line four line five [5 lines] ]]"] to deeply equal ["review this: line one\nline two…"]`.
     - `/queue` with a paste that starts with `!`: `expected [ 'echo pwned\nz\nz\nz\nz\nz\nend' ] to deeply equal []`. The pasted command was shell-executed.
   - With the branch merged onto `main` at 298a01c79b: 6 passed. That `main` without the change: 6 failed.
2. Negative controls. Reverting each key line makes the suite fail again:
   - interpolate `item.text` instead of the display: `expected [ 'date', 'touch /tmp/pwned' ] to deeply equal [ 'date' ]`;
   - gate `!` on `item.text`;
   - queue `full` on the busy path;
   - `enqueue(full)` on the no-session path;
   - drop `display` from the interrupt `send`.
3. Not run: the full ui-tui suite (`npm test`) and `npm run check`. What did run:
   - On the branch: the new file plus 17 adjacent test files in `src/__tests__/` (18 files): `attachments`, `createGatewayEventHandler`, `gatewayClientKillLatch`, `inputSelectionClipboard`, `libTextI18n`, `moaProgressActivity`, `orchestratorPromptSession`, `platform`, `queueScopeRenderer`, `queueSubmission`, `startupLatency`, `startupLatencyDashboard`, `submissionCore`, `useInputHandlers`, `useQueue`, `useSubmission`, `voiceSubmitModeRenderer`: 228 passed.
   - Merged onto `main` at 298a01c79b: the same 17 adjacent files plus `useComposerState` and `composerHighlights`: 239 passed.
   - Not tested: a live TUI session against a real gateway. The tests drive the real hooks with a fake gateway.
4. `npm run typecheck` is clean on the branch and on the merge with 298a01c79b. eslint and prettier are clean on the touched files.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: TypeScript-only change. Only the targeted vitest files and the typecheck above were run.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), vitest 4.1.10 (targeted ui-tui tests only)

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

N/A
