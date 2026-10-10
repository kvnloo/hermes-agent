import { act, cleanup, render } from '@testing-library/react'
import { useEffect, useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// `useComposerVoice` is mounted by every composer in the window — the main
// chat bar and each session tile — and each instance drives the SAME
// per-renderer `CONVERSATION_LEASE` (one key shared by all instances, with the
// dedupe/serialization state held at module scope in `tts-lease.ts`). Before
// the ownership token, a tile that mounted or unmounted while the main
// composer held an active voice conversation emitted a stray
// `syncTtsLease(CONVERSATION_LEASE, false)` that released the shared lease
// mid-conversation, and the owner's own end-of-conversation release then
// short-circuited because `sent` was already `false`.
//
// This test mounts two instances of a harness that replicates the exact two
// conversation-lease effects (acquire/flip + unmount cleanup) guarded by the
// ownership token from `use-composer-voice.ts`, driven through
// `@testing-library/react` so React's real passive-effect scheduler orders,
// flushes, and cleans up the effects. Both instances share the real
// `tts-lease.ts` module state — that shared surface is what the bug lives on,
// which is why a cross-composer test is meaningful (a single instance can
// never reproduce it).

const setTtsLease = vi.fn(async (_lease: string, _active: boolean) => ({ ok: true }))

vi.mock('@/hermes', () => ({
  setTtsLease: (lease: string, active: boolean) => setTtsLease(lease, active)
}))

import { CONVERSATION_LEASE, resetTtsLeasesForTests, syncTtsLease } from './tts-lease'

// A faithful replica of the conversation-lease wiring in `useComposerVoice`:
// the acquire effect + the unmount cleanup, guarded by an ownership-token ref
// so a composer that never acquired the lease cannot release the shared one
// another composer still holds. Keep this in sync with the two effects in
// `apps/desktop/src/app/chat/composer/hooks/use-composer-voice.ts`.
function ComposerVoiceLeaseStub({ active }: { active: boolean }) {
  const ownsRef = useRef(false)

  // eslint-disable-next-line no-restricted-syntax -- mirrors useComposerVoice's ownership token
  useEffect(() => {
    if (active) {
      ownsRef.current = true
      void syncTtsLease(CONVERSATION_LEASE, true)
    } else if (ownsRef.current) {
      ownsRef.current = false
      void syncTtsLease(CONVERSATION_LEASE, false)
    }
  }, [active])

  useEffect(
    () => () => {
      if (ownsRef.current) {
        void syncTtsLease(CONVERSATION_LEASE, false)
      }
    },
    []
  )

  return null
}

function App({
  mainActive,
  showTile,
  tileActive = false
}: {
  mainActive: boolean
  showTile: boolean
  tileActive?: boolean
}) {
  return (
    <>
      <ComposerVoiceLeaseStub active={mainActive} key="main" />
      {showTile && <ComposerVoiceLeaseStub active={tileActive} key="tile" />}
    </>
  )
}

// The wire call inside `syncTtsLease` is deferred behind a microtask (it runs in
// a `.then` so a fast on→off→on can be coalesced before the request goes out).
// `render`/`rerender`/`unmount` flush the passive effects themselves via `act`,
// but the queued microtask needs one more microtask turn to land on the wire —
// so every interaction is followed by a single `await Promise.resolve()` flush,
// matching the idiom used by `tts-lease.test.ts`.
async function flush() {
  await act(async () => {
    await Promise.resolve()
  })
}

describe('conversation lease — cross-composer ownership', () => {
  beforeEach(() => {
    resetTtsLeasesForTests()
    setTtsLease.mockReset()
    setTtsLease.mockImplementation(async () => ({ ok: true }))
  })

  afterEach(() => {
    cleanup()
    resetTtsLeasesForTests()
  })

  it('a tile mounting mid-conversation does not release the main composer\'s lease', async () => {
    const view = render(<App mainActive={false} showTile={false} />)
    await flush()

    // Main flips its conversation on → acquires the shared lease.
    view.rerender(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // A session tile mounts while the main is still in conversation. The tile
    // never acquired the lease, so it must NOT send a stray release.
    view.rerender(<App mainActive={true} showTile={true} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
  })

  it('a tile unmounting mid-conversation does not release the main composer\'s lease', async () => {
    const view = render(<App mainActive={false} showTile={true} />)
    await flush()
    expect(setTtsLease).not.toHaveBeenCalled()

    // Main turns its conversation on while the (idle) tile is already mounted.
    view.rerender(<App mainActive={true} showTile={true} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // Closing the session tile unmounts its subtree. The tile never held the
    // lease, so its unmount cleanup must NOT release what the main still owns.
    view.rerender(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
  })

  it('the lease stays held after tile interference — no spurious release, no self-heal churn', async () => {
    const view = render(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // Tile mounts then unmounts while the main holds the conversation.
    view.rerender(<App mainActive={true} showTile={true} />)
    await flush()
    view.rerender(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // A no-op rerender of the owner (its `voiceConversationActive` did not
    // change) produces no reacquire and no release — `sent` was never
    // corrupted, so there is nothing to self-heal from.
    view.rerender(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
    expect(setTtsLease).toHaveBeenCalledTimes(1)
  })

  it('a tile mounting in the same React commit as the owner\'s first acquire does not suppress the acquire', async () => {
    // Both children mount in one render — the same-commit "latest intent wins"
    // race: with the buggy effects the tile's `false` overwrote `sent` before
    // the acquire's microtask fired, suppressing it entirely. With the
    // ownership token the tile (active=false, never owned) takes no action.
    const view = render(<App mainActive={true} showTile={true} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    view.unmount()
    await flush()
    // The owner's unmount cleanup releases what the owner acquired.
    expect(setTtsLease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  })

  it('the owner ending its conversation after tile interference still releases the lease', async () => {
    const view = render(<App mainActive={true} showTile={true} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // Tile unmounts mid-conversation — no stray release.
    view.rerender(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // The owner ends its conversation. Because the token was never released
    // by a non-owner, `sent` is still `true`, so the owner's `true → false`
    // release goes out instead of short-circuiting on a stale `false`.
    view.rerender(<App mainActive={false} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  })

  it('an unmounting owner releases its own lease, and a non-owning tile does not', async () => {
    const view = render(<App mainActive={true} showTile={true} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // Closing the tile tab first: the tile never owned the lease, so its
    // unmount cleanup is a no-op.
    view.rerender(<App mainActive={true} showTile={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // The owner unmounts while its conversation is still active: its cleanup
    // releases the lease it acquired so the backend can unload the engine.
    view.unmount()
    await flush()
    expect(setTtsLease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  })

  it('a tile that starts its own voice conversation still acquires and releases the lease', async () => {
    // The fix must not regress tile voice conversations: a tile is a first-class
    // host (toggle/hotkey/controls are unguarded by `target`), so gating the
    // lease to the main composer would leave every tile reply a cold start.
    // The tile is the sole active composer here — it must own the full cycle.
    const view = render(<App mainActive={false} showTile={true} tileActive={false} />)
    await flush()
    expect(setTtsLease).not.toHaveBeenCalled()

    view.rerender(<App mainActive={false} showTile={true} tileActive={true} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    view.rerender(<App mainActive={false} showTile={true} tileActive={false} />)
    await flush()
    expect(setTtsLease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  })

  it('an idle composer mounting and unmounting never touches the wire', async () => {
    // A tile that opens and closes without ever entering a voice conversation
    // must be invisible to the backend: never an acquire, never a release.
    const view = render(<App mainActive={false} showTile={true} tileActive={false} />)
    await flush()
    expect(setTtsLease).not.toHaveBeenCalled()

    view.rerender(<App mainActive={false} showTile={false} tileActive={false} />)
    await flush()
    expect(setTtsLease).not.toHaveBeenCalled()
  })
})
