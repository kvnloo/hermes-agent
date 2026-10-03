import { act, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { createClientSessionState } from '@/lib/chat-runtime'

import { type MessageStreamHarness, renderMessageStream } from './test-harness'

// Verification tests for the adoptedRunningTurn lifecycle fix. Each test
// targets one behavioral guarantee from the test plan.

const SID = 'session-active'

let stream: MessageStreamHarness
let hydrateFromStoredSession: ReturnType<typeof vi.fn<() => Promise<void>>>

function mountStream() {
  hydrateFromStoredSession = vi.fn(async () => undefined)
  stream = renderMessageStream(SID, { hydrateFromStoredSession })
}

const start = () => act(() => stream.handleEvent({ payload: {}, session_id: SID, type: 'message.start' }))

const delta = (text: string) =>
  act(() => stream.handleEvent({ payload: { text }, session_id: SID, type: 'message.delta' }))

const complete = (text: string) =>
  act(() => stream.handleEvent({ payload: { text }, session_id: SID, type: 'message.complete' }))

const seedState = (extra: Partial<ReturnType<typeof createClientSessionState>>) => {
  const current = stream.states.get(SID) ?? createClientSessionState()
  stream.states.set(SID, { ...current, ...extra })
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('T2a: interrupted message.complete clears adoptedRunningTurn + interimBoundaryPending', () => {
  it('resets adoptedRunningTurn and interimBoundaryPending to false on the interrupted bail', async () => {
    mountStream()
    await start()
    await delta('partial')

    // Simulate a cancel that left interrupted=true, plus a leaked adoption flag.
    seedState({
      interrupted: true,
      adoptedRunningTurn: true,
      interimBoundaryPending: true,
      busy: false,
      streamId: null
    })

    await complete('late arrived full text')

    const state = stream.state()
    expect(state.adoptedRunningTurn).toBe(false)
    expect(state.interimBoundaryPending).toBe(false)
    expect(hydrateFromStoredSession).not.toHaveBeenCalled()
  })
})

describe('T2b: failAssistantMessage clears adoptedRunningTurn', () => {
  it('resets adoptedRunningTurn to false on an error frame', async () => {
    mountStream()
    await start()
    await delta('partial')

    seedState({ adoptedRunningTurn: true })

    // The `error` event triggers failAssistantMessage.
    act(() =>
      stream.handleEvent({ payload: { message: 'agent initialization failed' }, session_id: SID, type: 'error' })
    )

    const state = stream.state()
    expect(state.adoptedRunningTurn).toBe(false)
    expect(state.busy).toBe(false)
    expect(state.streamId).toBeNull()
  })
})

describe('T2c: session.info running=false clears adoptedRunningTurn on settle', () => {
  it('resets adoptedRunningTurn to false when a live turn settles via running=false', async () => {
    mountStream()
    await start()

    seedState({ adoptedRunningTurn: true })

    act(() => stream.handleEvent({ payload: { running: false }, session_id: SID, type: 'session.info' }))

    const state = stream.state()
    expect(state.adoptedRunningTurn).toBe(false)
    expect(state.busy).toBe(false)
    expect(state.turnLive).toBe(false)
  })
})

describe('T3a (extra): message.start clears adoptedRunningTurn', () => {
  it('sets adoptedRunningTurn to false immediately after message.start', async () => {
    mountStream()

    seedState({ adoptedRunningTurn: true, interrupted: false, busy: false })

    await start()

    const state = stream.state()
    expect(state.adoptedRunningTurn).toBe(false)
    expect(state.turnLive).toBe(true)
  })
})

describe('T4a: a legitimately adopted turn STILL hydrates on non-empty complete', () => {
  it('calls hydrateFromStoredSession when adoptedRunningTurn stays true (no message.start replay)', async () => {
    mountStream()

    // Real adoption: session.activate/resume with running=true sets the flag
    // and turnLive, but NEVER replays message.start. So message.start's clear
    // never runs, and the flag stays true into message.complete.
    seedState({
      adoptedRunningTurn: true,
      busy: true,
      awaitingResponse: true,
      turnLive: true,
      sawAssistantPayload: false
    })

    // NO message.start — the adoption path skips it.
    await delta('Adopted reply text.')
    await complete('Adopted reply text.')

    expect(hydrateFromStoredSession).toHaveBeenCalledWith(3, null, SID)
  })
})
