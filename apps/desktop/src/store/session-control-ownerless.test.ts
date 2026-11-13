import { afterEach, expect, it, vi } from 'vitest'

import { $gateway, setPrimaryGateway, setPrimaryGatewayConnection } from './gateway'
import { $profiles } from './profile'
import { isSessionGone, resetBackgroundPollingGuard } from './runtime-gone'
import { $sessionControlBySession, clearAllSessionControl, refreshSessionControl } from './session-control'
import { clearAllSessionStates, recordSessionEventScope, setSessionOwnerProbe } from './session-states'

afterEach(() => {
  setSessionOwnerProbe(null)
  clearAllSessionControl()
  clearAllSessionStates()
  resetBackgroundPollingGuard()
  $profiles.set([])
  $gateway.set(null as never)
  setPrimaryGateway(null)
  setPrimaryGatewayConnection(null)
})

it('does not publish an ownerless control error or retire a runtime that can rebind (#107502)', async () => {
  const runtimeId = 'rt-ownerless-107502'
  const primaryRequest = vi.fn(async (_method: string, _params: unknown) => ({
    control: { goal: null, heartbeat: null, loop: null, revision: 'rebound', updated_at: 0 }
  }))
  const primary = { onEvent: () => () => undefined, request: primaryRequest, state: 'open' }

  setPrimaryGateway(primary as never, 'default')
  setPrimaryGatewayConnection({ connectionId: 'local' })
  $gateway.set(primary as never)
  $profiles.set([{ name: 'default' }, { name: 'developer' }] as never)
  setSessionOwnerProbe(async () => undefined)

  // After a backend lifecycle event no owner rung or profile probe names the
  // runtime. No request may be sent to the ambient gateway by guesswork.
  await refreshSessionControl(runtimeId, { background: true })
  expect($sessionControlBySession.get()[runtimeId]).toMatchObject({
    capability: 'unknown',
    error: null,
    loading: false,
    snapshot: null
  })
  expect(primaryRequest).not.toHaveBeenCalled()
  expect(isSessionGone(runtimeId)).toBe(false)

  // The very same runtime is still alive; once an exact event scope arrives,
  // a foreground hydration must retry and show the control snapshot.
  recordSessionEventScope({ connectionId: 'local', profile: 'default', session_id: runtimeId })
  await refreshSessionControl(runtimeId)
  expect(primaryRequest).toHaveBeenCalledTimes(1)
  expect(primaryRequest.mock.calls[0]?.slice(0, 2)).toEqual(['session.control.read', { session_id: runtimeId }])
  expect($sessionControlBySession.get()[runtimeId]).toMatchObject({
    capability: 'supported',
    error: null,
    loading: false,
    snapshot: { revision: 'rebound' }
  })
})
