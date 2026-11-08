import { act, cleanup, render, waitFor } from '@testing-library/react'
import { useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type * as HermesModule from '@/hermes'
import { textPart } from '@/lib/chat-messages'
import { createClientSessionState } from '@/lib/chat-runtime'
import { $sessionTiles, publishSessionState } from '@/store/session-states'

vi.mock('@/hermes', async importOriginal => {
  const actual = await importOriginal<typeof HermesModule>()

  return {
    ...actual,
    getLatestSessionMessages: vi.fn(async () => ({ messages: [], session_id: 'stored-1' }))
  }
})

type ChannelListener = (event: MessageEvent) => void

class FakeBroadcastChannel {
  static instances = new Map<string, Set<FakeBroadcastChannel>>()

  name: string
  private listeners = new Set<ChannelListener>()

  constructor(name: string) {
    this.name = name
    const group = FakeBroadcastChannel.instances.get(name) ?? new Set()
    group.add(this)
    FakeBroadcastChannel.instances.set(name, group)
  }

  postMessage(data: unknown) {
    const group = FakeBroadcastChannel.instances.get(this.name)

    if (!group) {
      return
    }

    for (const channel of group) {
      if (channel === this) {
        continue
      }

      for (const listener of channel.listeners) {
        listener({ data } as MessageEvent)
      }
    }
  }

  addEventListener(_type: string, listener: ChannelListener) {
    this.listeners.add(listener)
  }

  removeEventListener(_type: string, listener: ChannelListener) {
    this.listeners.delete(listener)
  }
}

const STORED = 'stored-peer-sync'
const RUNTIME = 'rt-peer-sync'

describe('useTranscriptPeerSync (#65047)', () => {
  beforeEach(() => {
    FakeBroadcastChannel.instances.clear()
    vi.stubGlobal('BroadcastChannel', FakeBroadcastChannel)
    vi.resetModules()
    $sessionTiles.set([])
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.resetModules()
    $sessionTiles.set([])
  })

  it('re-pulls the transcript when a peer finishes a turn on the viewed session', async () => {
    const local = createClientSessionState(STORED, [
      { id: 'u1', role: 'user', parts: [textPart('a')] },
      { id: 'a1', role: 'assistant', parts: [textPart('b')] }
    ])

    publishSessionState(RUNTIME, local)

    const { getLatestSessionMessages } = await import('@/hermes')
    vi.mocked(getLatestSessionMessages).mockResolvedValue({
      session_id: STORED,
      messages: [
        { content: 'a', role: 'user', timestamp: 1 },
        { content: 'b', role: 'assistant', timestamp: 2 },
        { content: 'c', role: 'user', timestamp: 3 },
        { content: 'd', role: 'assistant', timestamp: 4 }
      ]
    })

    const { useTranscriptPeerSync } = await import('./use-transcript-peer-sync')
    const seeds: unknown[] = []

    function Harness() {
      const activeSessionIdRef = useRef<string | null>(RUNTIME)
      const busyRef = useRef(false)
      const selectedStoredSessionIdRef = useRef<string | null>(STORED)

      useTranscriptPeerSync({
        activeSessionIdRef,
        busyRef,
        selectedStoredSessionIdRef,
        updateSessionState: (sessionId, updater, storedSessionId) => {
          const next = updater(local)
          seeds.push({ sessionId, storedSessionId, messages: next.messages })

          return next
        }
      })

      return null
    }

    await act(async () => {
      render(<Harness />)
    })

    const peer = new FakeBroadcastChannel('hermes:transcript')

    await act(async () => {
      peer.postMessage({ messageCount: 4, sessionId: STORED })
    })

    expect(getLatestSessionMessages).toHaveBeenCalledWith(STORED, undefined)
    expect(seeds.at(-1)).toEqual(
      expect.objectContaining({
        sessionId: RUNTIME,
        storedSessionId: STORED
      })
    )
    expect((seeds.at(-1) as { messages: unknown[] }).messages).toHaveLength(4)
  })

  it('ignores a peer ping for a session this window is not viewing', async () => {
    const { getLatestSessionMessages } = await import('@/hermes')
    vi.mocked(getLatestSessionMessages).mockClear()
    const { useTranscriptPeerSync } = await import('./use-transcript-peer-sync')

    function Harness() {
      const activeSessionIdRef = useRef<string | null>(RUNTIME)
      const busyRef = useRef(false)
      const selectedStoredSessionIdRef = useRef<string | null>(STORED)

      useTranscriptPeerSync({
        activeSessionIdRef,
        busyRef,
        selectedStoredSessionIdRef,
        updateSessionState: (sessionId, updater) => updater(createClientSessionState(STORED))
      })

      return null
    }

    await act(async () => {
      render(<Harness />)
    })

    const peer = new FakeBroadcastChannel('hermes:transcript')

    await act(async () => {
      peer.postMessage({ sessionId: 'some-other-chat', messageCount: 9 })
    })

    expect(getLatestSessionMessages).not.toHaveBeenCalled()
  })

  it('keeps the newer peer refresh when an earlier fetch finishes last', async () => {
    const local = createClientSessionState(STORED, [{ id: 'u1', role: 'user', parts: [textPart('a')] }])
    publishSessionState(RUNTIME, local)

    let resolveFirst: (value: { messages: Array<{ content: string; role: string; timestamp: number }>; session_id: string }) => void
    let resolveSecond: (value: { messages: Array<{ content: string; role: string; timestamp: number }>; session_id: string }) => void
    const first = new Promise<{ messages: Array<{ content: string; role: string; timestamp: number }>; session_id: string }>(
      resolve => (resolveFirst = resolve)
    )
    const second = new Promise<{ messages: Array<{ content: string; role: string; timestamp: number }>; session_id: string }>(
      resolve => (resolveSecond = resolve)
    )
    const { getLatestSessionMessages } = await import('@/hermes')
    vi.mocked(getLatestSessionMessages).mockReturnValueOnce(first as never).mockReturnValueOnce(second as never)
    const { useTranscriptPeerSync } = await import('./use-transcript-peer-sync')
    const seeds: unknown[] = []

    function Harness() {
      const activeSessionIdRef = useRef<string | null>(RUNTIME)
      const busyRef = useRef(false)
      const selectedStoredSessionIdRef = useRef<string | null>(STORED)

      useTranscriptPeerSync({
        activeSessionIdRef,
        busyRef,
        selectedStoredSessionIdRef,
        updateSessionState: (sessionId, updater, storedSessionId) => {
          const next = updater(local)
          seeds.push({ sessionId, storedSessionId, messages: next.messages })

          return next
        }
      })

      return null
    }

    await act(async () => {
      render(<Harness />)
    })

    const peer = new FakeBroadcastChannel('hermes:transcript')

    await act(async () => {
      peer.postMessage({ messageCount: 2, sessionId: STORED })
      peer.postMessage({ messageCount: 4, sessionId: STORED })
    })
    await waitFor(() => expect(getLatestSessionMessages).toHaveBeenCalledTimes(2))

    await act(async () => {
      resolveSecond!({
        session_id: STORED,
        messages: [
          { content: 'a', role: 'user', timestamp: 1 },
          { content: 'b', role: 'assistant', timestamp: 2 },
          { content: 'c', role: 'user', timestamp: 3 },
          { content: 'd', role: 'assistant', timestamp: 4 }
        ]
      })
    })
    await waitFor(() => expect(seeds).toHaveLength(1))

    await act(async () => {
      resolveFirst!({
        session_id: STORED,
        messages: [
          { content: 'a', role: 'user', timestamp: 1 },
          { content: 'b', role: 'assistant', timestamp: 2 }
        ]
      })
    })

    expect(seeds).toHaveLength(1)
    expect((seeds[0] as { messages: unknown[] }).messages).toHaveLength(4)
  })

  it('does not let a delayed older peer refresh overwrite a newer tile transcript', async () => {
    const tileRuntime = 'rt-peer-tile'
    const local = createClientSessionState(STORED, [{ id: 'u1', role: 'user', parts: [textPart('a')] }])
    publishSessionState(RUNTIME, local)
    publishSessionState(tileRuntime, local)
    $sessionTiles.set([{ storedSessionId: STORED, runtimeId: tileRuntime }])

    const older = {
      session_id: STORED,
      messages: [
        { content: 'a', role: 'user', timestamp: 1 },
        { content: 'b', role: 'assistant', timestamp: 2 }
      ]
    }
    const newer = {
      session_id: STORED,
      messages: [
        ...older.messages,
        { content: 'c', role: 'user', timestamp: 3 },
        { content: 'd', role: 'assistant', timestamp: 4 }
      ]
    }

    let releaseOlderActive!: (value: typeof older) => void
    const olderActive = new Promise<typeof older>(resolve => {
      releaseOlderActive = resolve
    })
    const { getLatestSessionMessages } = await import('@/hermes')
    vi.mocked(getLatestSessionMessages).mockReset()
    vi.mocked(getLatestSessionMessages)
      .mockReturnValueOnce(olderActive as never)
      .mockResolvedValueOnce(newer as never)
      .mockResolvedValueOnce(newer as never)
      .mockResolvedValueOnce(older as never)

    const { useTranscriptPeerSync } = await import('./use-transcript-peer-sync')
    const published: Array<{ sessionId: string; count: number }> = []

    function Harness() {
      const activeSessionIdRef = useRef<string | null>(RUNTIME)
      const busyRef = useRef(false)
      const selectedStoredSessionIdRef = useRef<string | null>(STORED)

      useTranscriptPeerSync({
        activeSessionIdRef,
        busyRef,
        selectedStoredSessionIdRef,
        updateSessionState: (sessionId, updater) => {
          const next = updater(local)
          published.push({ sessionId, count: next.messages.length })

          return next
        }
      })

      return null
    }

    await act(async () => {
      render(<Harness />)
    })

    const peer = new FakeBroadcastChannel('hermes:transcript')

    await act(async () => {
      peer.postMessage({ messageCount: 2, sessionId: STORED })
    })
    await waitFor(() => expect(getLatestSessionMessages).toHaveBeenCalledTimes(1))

    await act(async () => {
      peer.postMessage({ messageCount: 4, sessionId: STORED })
    })
    await waitFor(() => expect(published.filter(row => row.sessionId === tileRuntime)).toHaveLength(1))

    // The older event's active read completes only after the newer event has
    // already published its tile. It must not mint a newer tile generation.
    await act(async () => {
      releaseOlderActive(older)
      await new Promise<void>(resolve => setTimeout(resolve, 0))
    })

    expect(getLatestSessionMessages).toHaveBeenCalledTimes(3)
    expect(published.filter(row => row.sessionId === tileRuntime)).toEqual([{ sessionId: tileRuntime, count: 4 }])
  })
})
