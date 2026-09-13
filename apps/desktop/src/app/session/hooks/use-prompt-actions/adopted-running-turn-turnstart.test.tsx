import { act, cleanup, render, waitFor } from '@testing-library/react'
import type { MutableRefObject } from 'react'
import { useEffect, useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { textPart } from '@/lib/chat-messages'
import { createClientSessionState } from '@/lib/chat-runtime'
import { setSessions } from '@/store/session'
import type { SessionInfo } from '@/types/hermes'

import { applyReloadOptimistic, applyRewindOptimistic, planReload } from './rewind'
import { clearSingleFlightSessionResumeState } from './single-flight-resume'

import { usePromptActions } from '.'

const RUNTIME_SESSION_ID = 'rt-abc123'

function sessionInfo(overrides: Partial<SessionInfo> = {}): SessionInfo {
  return {
    ended_at: null,
    id: RUNTIME_SESSION_ID,
    input_tokens: 0,
    is_active: true,
    last_active: 0,
    message_count: 3,
    model: null,
    output_tokens: 0,
    preview: null,
    source: null,
    started_at: 0,
    title: 'Old title',
    tool_call_count: 0,
    ...overrides
  }
}

vi.mock('@/hermes', () => ({
  getProfiles: vi.fn(async () => ({ profiles: [] })),
  getSession: vi.fn(),
  PROMPT_SUBMIT_REQUEST_TIMEOUT_MS: 1_800_000,
  setApiRequestProfile: vi.fn(),
  transcribeAudio: vi.fn()
}))

vi.mock('@/store/gateway', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  requestGatewayForAgent: vi.fn()
}))

interface HarnessHandle {
  cancelRun: () => Promise<void>
  submitText: (text: string) => Promise<boolean>
}

function Harness({
  initialState,
  onReady,
  refreshSessions,
  requestGateway
}: {
  initialState: Record<string, unknown>
  onReady: (handle: HarnessHandle) => void
  refreshSessions: () => Promise<void>
  requestGateway: <T>(method: string, params?: Record<string, unknown>) => Promise<T>
}) {
  const activeSessionIdRef = useRef<string | null>(RUNTIME_SESSION_ID)
  const selectedStoredSessionIdRef: MutableRefObject<string | null> = { current: RUNTIME_SESSION_ID }
  const busyRef = { current: false }

  // Keep a mutable ref seeded with the full initial state (including
  // adoptedRunningTurn) so the first updateSessionState reads a stale flag.
  const stateRef = useRef({ ...initialState } as never)

  const actions = usePromptActions({
    activeSessionId: RUNTIME_SESSION_ID,
    activeSessionIdRef,
    branchCurrentSession: async () => true,
    busyRef,
    createBackendSessionForSend: async () => RUNTIME_SESSION_ID,
    getRoutedStoredSessionId: () => null,
    getRuntimeIdForStoredSession: () => null,
    getRouteToken: () => 'token',
    handleSkinCommand: () => '',
    openMemoryGraph: () => undefined,
    refreshSessions,
    requestGateway,
    resumeStoredSession: () => undefined,
    runtimeIdByStoredSessionIdRef: { current: new Map([[RUNTIME_SESSION_ID, RUNTIME_SESSION_ID]]) },
    selectedStoredSessionIdRef,
    startFreshSessionDraft: () => undefined,
    sttEnabled: false,
    updateSessionState: (_sessionId, updater) => {
      const next = updater(stateRef.current) as unknown as Record<string, unknown>
      stateRef.current = next as never

      return next as never
    }
  })

  useEffect(() => {
    onReady({
      cancelRun: (...args: Parameters<typeof actions.cancelRun>) =>
        act(async () => actions.cancelRun(...args)) as Promise<void>,
      submitText: (...args: Parameters<typeof actions.submitText>) =>
        act(async () => actions.submitText(...args)) as Promise<boolean>
    })
  }, [actions.cancelRun, actions.submitText, onReady])

  return null
}

beforeEach(() => {
  clearSingleFlightSessionResumeState()
  setSessions(() => [sessionInfo()])
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('T2d: cancelRun clears a stale adoptedRunningTurn', () => {
  it('sets adoptedRunningTurn to false when cancelling a turn that had the flag set', async () => {
    const states: Record<string, unknown>[] = []
    let cancelHandle: (() => Promise<void>) | null = null

    function CapturingHarness() {
      const activeSessionIdRef = useRef<string | null>(RUNTIME_SESSION_ID)
      const selectedStoredSessionIdRef: MutableRefObject<string | null> = { current: RUNTIME_SESSION_ID }
      const busyRef = { current: true }

      const stateRef = useRef({
        ...createClientSessionState(null, [
          { id: 'u1', role: 'user', parts: [textPart('hi')] },
          { id: 'a1', role: 'assistant', parts: [textPart('partial')], pending: true }
        ]),
        busy: true,
        streamId: 'a1',
        interrupted: false,
        adoptedRunningTurn: true
      } as never)

      const actions = usePromptActions({
        activeSessionId: RUNTIME_SESSION_ID,
        activeSessionIdRef,
        branchCurrentSession: async () => true,
        busyRef,
        createBackendSessionForSend: async () => RUNTIME_SESSION_ID,
        getRoutedStoredSessionId: () => null,
        getRuntimeIdForStoredSession: () => null,
        getRouteToken: () => 'token',
        handleSkinCommand: () => '',
        openMemoryGraph: () => undefined,
        refreshSessions: async () => undefined,
        requestGateway: vi.fn(async () => ({}) as never),
        resumeStoredSession: () => undefined,
        runtimeIdByStoredSessionIdRef: { current: new Map([[RUNTIME_SESSION_ID, RUNTIME_SESSION_ID]]) },
        selectedStoredSessionIdRef,
        startFreshSessionDraft: () => undefined,
        sttEnabled: false,
        updateSessionState: (_sessionId, updater) => {
          const next = updater(stateRef.current) as unknown as Record<string, unknown>
          stateRef.current = next as never
          states.push(next)

          return next as never
        }
      })

      useEffect(() => {
        cancelHandle = () => act(async () => actions.cancelRun()) as Promise<void>
      }, [actions.cancelRun])

      return null
    }

    render(<CapturingHarness />)
    await waitFor(() => expect(cancelHandle).not.toBeNull())
    await cancelHandle!()

    expect(states.at(-1)).toMatchObject({
      adoptedRunningTurn: false,
      interrupted: true,
      busy: false,
      streamId: null
    })

    cleanup()
  })
})

describe('T3b: seedOptimistic (submit) clears adoptedRunningTurn', () => {
  it('sets adoptedRunningTurn to false when submitting a new prompt', async () => {
    const states: Record<string, unknown>[] = []
    let submitHandle: ((text: string) => Promise<boolean>) | null = null

    function SubmitHarness() {
      const activeSessionIdRef = useRef<string | null>(RUNTIME_SESSION_ID)
      const selectedStoredSessionIdRef: MutableRefObject<string | null> = { current: RUNTIME_SESSION_ID }
      const busyRef = { current: false }

      const stateRef = useRef({
        ...createClientSessionState(RUNTIME_SESSION_ID, [{ id: 'u1', role: 'user', parts: [textPart('first')] }]),
        awaitingResponse: true,
        busy: true,
        interrupted: false,
        adoptedRunningTurn: true
      } as never)

      const actions = usePromptActions({
        activeSessionId: RUNTIME_SESSION_ID,
        activeSessionIdRef,
        branchCurrentSession: async () => true,
        busyRef,
        createBackendSessionForSend: async () => RUNTIME_SESSION_ID,
        getRoutedStoredSessionId: () => RUNTIME_SESSION_ID,
        getRuntimeIdForStoredSession: () => RUNTIME_SESSION_ID,
        getRouteToken: () => 'token',
        handleSkinCommand: () => '',
        openMemoryGraph: () => undefined,
        refreshSessions: async () => undefined,
        requestGateway: vi.fn(async () => ({}) as never),
        resumeStoredSession: () => undefined,
        runtimeIdByStoredSessionIdRef: { current: new Map([[RUNTIME_SESSION_ID, RUNTIME_SESSION_ID]]) },
        selectedStoredSessionIdRef,
        startFreshSessionDraft: () => undefined,
        sttEnabled: false,
        updateSessionState: (_sessionId, updater) => {
          const next = updater(stateRef.current) as unknown as Record<string, unknown>
          stateRef.current = next as never
          states.push(next)

          return next as never
        }
      })

      useEffect(() => {
        submitHandle = (text: string) => act(async () => actions.submitText(text)) as Promise<boolean>
      }, [actions.submitText])

      return null
    }

    render(<SubmitHarness />)
    await waitFor(() => expect(submitHandle).not.toBeNull())

    await submitHandle!('hello world')

    // seedOptimistic is the first state update from submit.
    expect(states[0]).toMatchObject({
      adoptedRunningTurn: false,
      interrupted: false,
      busy: true,
      awaitingResponse: true
    })

    cleanup()
  })
})

describe('T3c: applyReloadOptimistic clears adoptedRunningTurn', () => {
  it('sets adoptedRunningTurn to false on regenerate', () => {
    const state = {
      ...createClientSessionState(null, [
        { id: 'u1', role: 'user', parts: [textPart('prompt')], rowId: 10 },
        { id: 'a1', role: 'assistant', parts: [textPart('reply')] }
      ]),
      adoptedRunningTurn: true
    }

    const plan = planReload(state.messages, null)
    expect(plan).not.toBeNull()

    const next = applyReloadOptimistic(state, plan!)
    expect(next.adoptedRunningTurn).toBe(false)
    expect(next.busy).toBe(true)
    expect(next.turnLive).toBe(false)
  })
})

describe('T3d: applyRewindOptimistic clears adoptedRunningTurn', () => {
  it('sets adoptedRunningTurn to false on restore/edit', () => {
    const state = {
      ...createClientSessionState(null, [
        { id: 'u1', role: 'user', parts: [textPart('prompt')] },
        { id: 'a1', role: 'assistant', parts: [textPart('reply')] }
      ]),
      adoptedRunningTurn: true
    }

    const next = applyRewindOptimistic(state, 0)
    expect(next.adoptedRunningTurn).toBe(false)
    expect(next.busy).toBe(true)
    expect(next.turnLive).toBe(false)
  })
})
