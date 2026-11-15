import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { en } from '@/i18n/en'
import { createClientSessionState } from '@/lib/chat-runtime'
import { $activeGatewayProfile } from '@/store/profile'
import { $connection, $sessions } from '@/store/session'
import { $sessionStates } from '@/store/session-states'

import { adoptPreparedSubmission, ENTRY_PREFIX, preparedSubmissionKey, readPreparedSubmission, removePreparedSubmission, writePreparedSubmission } from './prepared-submissions'
import { storedJournal } from './prepared-submissions-test-utils'
import type { SubmissionDestination } from './submission-destination'
import { useSubmitPrompt } from './submit'
import type { GatewayRequest } from './utils'

vi.mock('@/store/gateway', async original => ({
  ...(await original<Record<string, unknown>>()),
  retainGatewayForSessionTurn: vi.fn(async () => () => undefined)
}))

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal('hermesDesktop', undefined)
  $sessions.set([])
  $sessionStates.set({})
  $connection.set(null)
  $activeGatewayProfile.set('default')

  const actual = Storage.prototype.setItem
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(function (key, value) {
    if (key.startsWith(ENTRY_PREFIX)) {
      throw new DOMException('Storage quota exceeded', 'QuotaExceededError')
    }

    return actual.call(this, key, value)
  })
  vi.spyOn(console, 'warn').mockImplementation(() => undefined)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  localStorage.clear()
})

it('keeps a quota-refused browser journal entry adoptable until its admission is retired', async () => {
  const destination = { scopeKey: 'webapp::default' } as SubmissionDestination
  const key = preparedSubmissionKey('stored', destination, 'caption', [])
  const entry = {
    id: 'send-1',
    owner: { connectionId: 'local', profile: 'default' },
    text: 'caption',
    attachments: [],
    params: { submission_id: 'send-1' }
  }

  await expect(writePreparedSubmission(key, entry)).resolves.toBeUndefined()
  expect(storedJournal()).toEqual({})
  expect(await readPreparedSubmission(key)).toEqual(entry)
  expect((await adoptPreparedSubmission(key, 'send-1'))?.entry).toEqual(entry)
  await removePreparedSubmission(key, 'send-1')
  expect(await readPreparedSubmission(key)).toBeUndefined()
})

it('still reaches prompt.submit when the browser refuses the pre-send journal write', async () => {
  let state = createClientSessionState()
  const requestGateway = vi.fn(async (method: string, params?: Record<string, unknown>) => {
    if (method === 'prompt.submit') {
      return { admission_id: params?.submission_id, session_id: 'runtime-a', status: 'started' } as never
    }

    return {} as never
  })

  const deps = {
    activeSessionIdRef: { current: 'runtime-a' as string | null },
    selectedStoredSessionIdRef: { current: 'stored-a' as string | null },
    busyRef: { current: false },
    copy: en.desktop,
    createBackendSessionForSend: vi.fn(async () => null),
    getRoutedStoredSessionId: () => null,
    getRuntimeIdForStoredSession: () => 'runtime-a',
    getRouteToken: () => 'same-route',
    requestGateway: requestGateway as GatewayRequest,
    runtimeIdByStoredSessionIdRef: { current: new Map([['stored-a', 'runtime-a']]) },
    resumeStoredSession: vi.fn(),
    syncAttachmentsForSubmit: vi.fn(async (sessionId: string) => ({ sessionId, attachments: [] })),
    updateSessionState: vi.fn((_sid: string, updater: (s: typeof state) => typeof state) => {
      state = updater(state)

      return state
    })
  }

  const { result } = renderHook(() => useSubmitPrompt(deps as never))
  await act(async () => {
    expect(await result.current('send with a full browser origin')).toBe(true)
  })

  expect(requestGateway.mock.calls.filter(([method]) => method === 'prompt.submit')).toHaveLength(1)
  expect(state.messages.some(message => message.role === 'user')).toBe(true)
  expect(storedJournal()).toEqual({})
  expect(console.warn).toHaveBeenCalledWith('[prepared-submission-unstored]', expect.any(DOMException))
})
