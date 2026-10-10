import type { GatewayEventName } from '@hermes/shared'
import { QueryClient } from '@tanstack/react-query'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { type ChatMessage, textPart, toChatMessages } from '@/lib/chat-messages'
import { $messages, setActiveSessionId, setMessages } from '@/store/session'
import { $sessionStates } from '@/store/session-states'

import { usePromptActions } from '../use-prompt-actions'
import { planReload, rebindSurvivorRowIds } from '../use-prompt-actions/rewind'
import { isFailedUserTurn, visibleUserMessageIndices } from '../use-prompt-actions/utils'
import { useSessionStateCache } from '../use-session-state-cache'

import { useMessageStream } from './index'

const SID = 'admitted-error-runtime'
const STORED = 'admitted-error-stored'
const PROMPT = 'Keep this admitted prompt on its original turn.'
const noop = async () => undefined

function mount() {
  const calls: Array<{ method: string; params?: Record<string, unknown> }> = []
  let acknowledge: ((result: { user_row_id: number }) => void) | undefined

  const accepted = new Promise<{ user_row_id: number }>(resolve => {
    acknowledge = resolve
  })

  const rpc = async <T,>(method: string, params?: Record<string, unknown>): Promise<T> => {
    calls.push({ method, params })

    return (
      method === 'prompt.submit' && calls.filter(call => call.method === method).length === 1
        ? await accepted
        : { status: 'started' }
    ) as T
  }

  const queryClient = new QueryClient()

  const hook = renderHook(() => {
    const busyRef = useRef(false)

    const cache = useSessionStateCache({
      activeSessionId: SID,
      selectedStoredSessionId: STORED,
      busyRef,
      setAwaitingResponse: () => undefined,
      setBusy: value => {
        busyRef.current = value
      },
      setMessages
    })

    const stream = useMessageStream({
      activeSessionIdRef: cache.activeSessionIdRef,
      sessionStateByRuntimeIdRef: cache.sessionStateByRuntimeIdRef,
      updateSessionState: cache.updateSessionState,
      queryClient,
      hydrateFromStoredSession: noop,
      refreshHermesConfig: noop,
      refreshSessions: noop
    })

    const actions = usePromptActions({
      activeSessionId: SID,
      activeSessionIdRef: cache.activeSessionIdRef,
      branchCurrentSession: async () => true,
      busyRef,
      createBackendSessionForSend: async () => SID,
      getRoutedStoredSessionId: () => STORED,
      getRuntimeIdForStoredSession: () => SID,
      getRouteToken: () => 'admitted-error-route',
      handleSkinCommand: () => '',
      openMemoryGraph: () => undefined,
      refreshSessions: noop,
      requestGateway: rpc,
      resumeStoredSession: noop,
      runtimeIdByStoredSessionIdRef: cache.runtimeIdByStoredSessionIdRef,
      selectedStoredSessionIdRef: cache.selectedStoredSessionIdRef,
      startFreshSessionDraft: () => undefined,
      sttEnabled: false,
      updateSessionState: cache.updateSessionState
    })

    return { actions, cache, stream }
  })

  act(() => hook.result.current.cache.ensureSessionState(SID, STORED))

  return {
    acknowledge: (rowId: number) => acknowledge!({ user_row_id: rowId }),
    calls,
    hook,
    state: () => hook.result.current.cache.sessionStateByRuntimeIdRef.current.get(SID)!,
    send: (type: GatewayEventName, payload: Record<string, unknown> = {}) =>
      act(() => hook.result.current.stream.handleGatewayEvent({ type, payload, session_id: SID }))
  }
}

beforeEach(() => {
  setActiveSessionId(SID)
  setMessages([])
  $sessionStates.set({})
})

afterEach(() => {
  cleanup()
  setActiveSessionId(null)
  setMessages([])
  $sessionStates.set({})
  vi.restoreAllMocks()
})

describe('provider failure retains acknowledged user admission', () => {
  it.each([
    ['before', false],
    ['after', false],
    ['before', true],
    ['after', true]
  ] as const)('retries the durable row (ACK=%s error, stopped=%s)', async (order, stopped) => {
    const lane = mount()
    let submitted: Promise<boolean>

    act(() => {
      submitted = lane.hook.result.current.actions.submitText(PROMPT, { attachments: [] })
    })
    await waitFor(() => expect(lane.calls.some(call => call.method === 'prompt.submit')).toBe(true))

    if (order === 'before') {
      await act(async () => {
        lane.acknowledge(13)
        expect(await submitted).toBe(true)
      })
    }

    lane.send('message.start')

    if (stopped) {
      await act(async () => lane.hook.result.current.actions.cancelRun())
    }

    lane.send('message.complete', { status: 'error', error: 'Connection error.', text: 'Connection error.' })

    if (order === 'after') {
      await act(async () => {
        lane.acknowledge(13)
        expect(await submitted).toBe(true)
      })
    }

    const failed = lane.state().messages.find(message => message.error)
    expect(Boolean(failed)).toBe(!stopped)
    expect(lane.state().messages.find(message => message.role === 'user')).toMatchObject({ rowId: 13 })
    expect($messages.get()).toEqual(lane.state().messages)

    const retryTarget = failed?.id ?? lane.state().messages.find(message => message.role === 'user')!.id

    await act(async () => lane.hook.result.current.actions.reloadFromMessage(retryTarget))

    const submits = lane.calls.filter(call => call.method === 'prompt.submit')
    expect(submits).toHaveLength(2)
    expect(submits[1].params).toMatchObject({ text: PROMPT, truncate_before_row_id: 13, confirm_truncate: true })
  })

  it('keeps a persisted provider-error turn in the backend user-ordinal space after replay', () => {
    const messages = toChatMessages([
      { id: 13, role: 'user', content: PROMPT },
      {
        id: 14,
        role: 'system',
        content: 'The provider could not finish this turn.',
        display_kind: 'failed_turn',
        display_metadata: {
          error: 'Connection error.',
          error_surface: { layer: 'provider', code: 'connection_error', retryable: true }
        }
      },
      { id: 15, role: 'user', content: 'A newer submitted prompt.' }
    ])

    expect(messages[1]).toMatchObject({ role: 'assistant', error: 'Connection error.' })
    const rebound = rebindSurvivorRowIds(messages, [113, 115])

    expect(rebound[0].rowId).toBe(113)
    expect(rebound[3].rowId).toBe(115)
    expect(visibleUserMessageIndices(messages)).toEqual([0, 3])
  })

  it.each([undefined, 0, -1, 1.5, Number.NaN, Number.MAX_SAFE_INTEGER + 1])(
    'keeps an unadmitted failed turn as a plain resubmit (rowId=%s)',
    rowId => {
      const messages: ChatMessage[] = [
        { id: 'unadmitted-user', role: 'user', parts: [textPart(PROMPT)], rowId },
        { id: 'submit-error', role: 'assistant', parts: [], error: 'The submit was refused.' }
      ]

      expect(isFailedUserTurn(messages, 0)).toBe(true)
      expect(visibleUserMessageIndices(messages)).toEqual([])
      expect(planReload(messages, 'submit-error')).toMatchObject({
        text: PROMPT,
        truncateMessageId: undefined,
        truncateOrdinal: undefined,
        truncateRowId: undefined
      })
    }
  )
})
