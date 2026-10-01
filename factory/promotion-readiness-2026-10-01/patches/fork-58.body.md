## What does this PR do?

Every mounted composer (the main chat bar and each session tile) runs `useComposerVoice` against the **same** per-renderer `CONVERSATION_LEASE`, and `apps/desktop/src/lib/tts-lease.ts` dedupes on a single module-level "last sent" value per lease. On `main` the conversation-lease acquire effect and the unmount cleanup are unconditional:

```ts
useEffect(() => {
  void syncTtsLease(CONVERSATION_LEASE, voiceConversationActive && !liveEngineActive)
}, [liveEngineActive, voiceConversationActive])

useEffect(() => () => void syncTtsLease(CONVERSATION_LEASE, false), [])
```

So when a session tile mounts (its first effect run sends `false`) or unmounts (cleanup sends `false`) while another composer's voice conversation holds the lease, the shared lease is released mid-conversation. The backend then unloads resident local TTS models (piper/kittentts), so the next spoken reply pays the cold model load the lease exists to hide. The owner's own end-of-conversation release is then deduped away, since the last sent value is already `false`.

The fix adds an ownership ref, the same pattern this hook already uses for `ownsWakeIndicatorRef`. Only the composer that acquired the lease releases it, either when its conversation ends or when it unmounts. Tiles still own the lease fully when they host their own voice conversation. The gate is not `target === 'main'`.

## Related Issue

No upstream issue. Downstream origin: kvnloo/hermes-agent#58, rebuilt on current `main` without the unrelated files that were in that comparison.

Related but distinct: #118037 (wake-only conversations release the lease right after warm-up; backend hysteresis). This PR does not change backend lease timing.

## Type of Change

- [x] 🐛 Bug fix (non-breaking change that fixes an issue)

## Changes Made

- `apps/desktop/src/app/chat/composer/hooks/use-composer-voice.ts`: adds `ownsConversationLeaseRef` to guard the acquire/release effect and the unmount cleanup. It keeps `main`'s `voiceConversationActive && !liveEngineActive` condition, so a GPT-Live conversation still never takes the lease.
- `apps/desktop/src/app/chat/composer/hooks/use-composer-voice-lease.test.tsx`: two behaviour tests that mount **real** `useComposerVoice` instances against the **real** `tts-lease` module. Only the `setTtsLease` wire call is stubbed. The mock harness is the one `use-composer-voice-shortcuts.test.tsx` already uses.
  1. A tile mounts and unmounts while main's conversation is active. The wire stays `[[lease, true]]`, and main ending its conversation still sends `false`.
  2. When the owner (a tile in conversation) unmounts, it still releases the lease.

## How to Test

From `apps/desktop`:

1. `npx vitest run src/app/chat/composer/hooks/use-composer-voice-lease.test.tsx`
   - On `main` without the fix, test 1 fails: `expected [[lease,true],[lease,false]] to deeply equal [[lease,true]]`. The tile released main's lease.
   - With the fix, 2/2 pass.
   - Negative controls: changing the `else if (ownsConversationLeaseRef.current)` branch to a plain `else` makes test 1 fail again. Making the unmount cleanup unconditional also makes test 1 fail.
2. `npx vitest run src/app/chat/composer/hooks src/lib/tts-lease.test.ts`: 33 files, 207 tests pass.
3. `npm run typecheck`, plus `eslint` and `prettier --check` on both files: clean.

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

Not tested: a live Electron + local TTS run on this rebuild. The downstream origin reported an `agent.log` `[TTS] released 1 resident local model(s)` line at tile-open time without the fix, and none with it.

Known residual, out of scope: if two composers both run their own voice conversation at the same time, the first to end still releases the shared key. That would need a refcount, which this PR does not add.
