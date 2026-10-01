## What does this PR do?

Every mounted composer (the main chat bar and each session tile) runs `useComposerVoice` against the **same** per-renderer `CONVERSATION_LEASE`, and `apps/desktop/src/lib/tts-lease.ts` dedupes on a single module-level "last sent" value per lease. On `main` the conversation-lease acquire effect and the unmount cleanup are unconditional:

```ts
useEffect(() => {
  void syncTtsLease(CONVERSATION_LEASE, voiceConversationActive && !liveEngineActive)
}, [liveEngineActive, voiceConversationActive])

useEffect(() => () => void syncTtsLease(CONVERSATION_LEASE, false), [])
```

So when a session tile mounts (its first effect run sends `false`) or unmounts (cleanup sends `false`) while another composer's voice conversation holds the lease, the shared lease is released mid-conversation. With the last holder gone, the backend unloads resident local TTS models (piper/kittentts) once the keep-warm window passes (`tts.keep_warm_seconds`, default 60 s) without a re-acquire, unless another lease such as read-aloud is held. The owning composer never re-acquires mid-conversation, so a later spoken reply pays the cold load the lease exists to hide. The owner's own end-of-conversation release is then deduped away, since the last sent value is already `false`.

The fix adds an ownership ref, the same pattern this hook already uses for `ownsWakeIndicatorRef`. Only the composer that acquired the lease releases it, either when its conversation ends or when it unmounts. Ownership is tracked per composer instance, not gated on `target === 'main'`, because a tile can host its own voice conversation.

Known residual, out of scope: if two composers both run their own voice conversation at the same time, the first to end still releases the shared key. That would need a refcount, which this PR does not add.

## Related Issue

No upstream issue.

Found and first fixed by Detail's automated bug scan (detail-app[bot]) in kvnloo/hermes-agent#58. This PR keeps that ownership-ref approach, adapts it to the `liveEngineActive` gate main has added since, and replaces its replica-harness test with two tests that drive the real hook. Built on main at f8489405.

Related: #118037 (closed) added the backend keep-warm window (`tts.keep_warm_seconds`). It delays but does not prevent the unload described here, because the owning composer never re-acquires. This PR does not change backend lease timing.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/src/app/chat/composer/hooks/use-composer-voice.ts`: adds `ownsConversationLeaseRef` to guard the acquire/release effect and the unmount cleanup. It keeps `main`'s `voiceConversationActive && !liveEngineActive` condition, so a GPT-Live conversation still never takes the lease. The read-aloud lease effect mirrors the global `$autoSpeakReplies` atom and has no unmount release, so it is not affected.
- `apps/desktop/src/app/chat/composer/hooks/use-composer-voice-lease.test.tsx`: two behaviour tests that mount real `useComposerVoice` instances with the real `tts-lease` module; only the `setTtsLease` call in `@/hermes` is stubbed. The hook's other dependencies are mocked with a copy of the harness in `use-composer-voice-shortcuts.test.tsx`, without its `@/lib/tts-lease` mock.
  1. A tile mounts and unmounts while main's conversation is active. The wire stays `[[lease, true]]`, and main ending its conversation still sends `false`.
  2. When the owner (a tile in conversation) unmounts, it still releases the lease.

## How to Test

From `apps/desktop`:

1. `npx vitest run src/app/chat/composer/hooks/use-composer-voice-lease.test.tsx`
   - On `main` without the fix, test 1 fails: `expected [[lease,true],[lease,false]] to deeply equal [[lease,true]]`. The tile released main's lease.
   - Test 2 passes on main too; it pins the owner's release so the fix can't simply drop the cleanup.
   - With the fix, 2/2 pass.
   - Negative controls: changing the `else if (ownsConversationLeaseRef.current)` branch to a plain `else` makes test 1 fail again. Making the unmount cleanup unconditional also makes test 1 fail.
2. `npx vitest run src/app/chat/composer/hooks src/lib/tts-lease.test.ts`: 33 files, 207 tests pass.
3. `npm run typecheck`, plus `eslint` and `prettier --check` on both files: clean.

All runs above were on f8489405. The branch merges cleanly into current main; not re-run on the merged tree.

## Checklist

### Code

- [x] I've read the [Contributing Guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md)
- [x] My commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`fix(scope):`, `feat(scope):`, etc.)
- [x] I searched for [existing PRs](https://github.com/NousResearch/hermes-agent/pulls) to make sure this isn't a duplicate
- [x] My PR contains **only** changes related to this fix/feature (no unrelated commits)
- [ ] I've run `pytest tests/ -q` and all tests pass. N/A: renderer-only change. The targeted vitest runs above pass.
- [x] I've added tests for my changes (required for bug fixes, strongly encouraged for features)
- [x] I've tested on my platform: Linux (CachyOS), jsdom/vitest

### Documentation & Housekeeping

- [x] I've updated relevant documentation (README, `docs/`, docstrings) — or N/A
- [x] I've updated `cli-config.yaml.example` if I added/changed config keys — or N/A
- [x] I've updated `CONTRIBUTING.md` or `AGENTS.md` if I changed architecture or workflows — or N/A
- [x] I've considered cross-platform impact (Windows, macOS) per the [compatibility guide](https://github.com/NousResearch/hermes-agent/blob/main/CONTRIBUTING.md#cross-platform-compatibility) — or N/A
- [x] I've updated tool descriptions/schemas if I changed tool behavior — or N/A

## Screenshots / Logs

Not tested: a live Electron + local TTS run (piper/kittentts) on this branch.
