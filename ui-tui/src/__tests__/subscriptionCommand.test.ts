import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getOverlayState, resetOverlayState } from '../app/overlayStore.js'
import { subscriptionCommands } from '../app/slash/commands/subscription.js'
import { findSlashCommand } from '../app/slash/registry.js'
import type { SubscriptionStateResponse } from '../gatewayTypes.js'

vi.mock('../lib/openExternalUrl.js', () => ({
  openExternalUrl: vi.fn(() => true)
}))

const subscriptionCommand = subscriptionCommands.find(cmd => cmd.name === 'subscription')!

const loggedInState = (overrides: Partial<SubscriptionStateResponse> = {}): SubscriptionStateResponse => ({
  ok: true,
  logged_in: true,
  is_admin: true,
  can_change_plan: true,
  org_name: 'Acme',
  role: 'OWNER',
  current: null,
  portal_url: 'https://portal.nousresearch.com/billing',
  ...overrides
})

const guarded =
  <T>(fn: (r: T) => void) =>
  (r: null | T) => {
    if (r) {
      fn(r)
    }
  }

/** Build a ctx whose rpc routes by method name to a supplied map of results. */
const buildCtx = (results: Record<string, unknown>) => {
  const sys = vi.fn()
  const calls: Array<{ method: string; params: unknown }> = []

  const rpc = vi.fn((method: string, params: unknown) => {
    calls.push({ method, params })

    return Promise.resolve(results[method])
  })

  const ctx = {
    gateway: { rpc },
    guarded,
    guardedErr: vi.fn(),
    sid: 'sid-1',
    stale: () => false,
    transcript: { page: vi.fn(), panel: vi.fn(), sys }
  }

  const run = async (arg: string) => {
    subscriptionCommand.run(arg, ctx as any, 'subscription')
    await rpc.mock.results[0]?.value
    await Promise.resolve()
    await Promise.resolve()
  }

  return { calls, ctx, rpc, run, sys }
}

const printed = (sys: ReturnType<typeof vi.fn>) => sys.mock.calls.map(c => c[0]).join('\n')

describe('/subscription slash command', () => {
  beforeEach(() => {
    resetOverlayState()
  })

  it('fetches subscription.state and opens the overlay', async () => {
    const { run } = buildCtx({
      'subscription.state': loggedInState()
    })

    await run('')

    const overlay = getOverlayState().subscription

    expect(overlay).not.toBeNull()
    expect(overlay?.screen).toBe('overview')
  })

  it('shows portal-login sys line when not logged in', async () => {
    const { run, sys } = buildCtx({
      'subscription.state': loggedInState({ logged_in: false })
    })

    await run('')

    expect(printed(sys)).toContain('Not logged into Nous Portal')
    expect(getOverlayState().subscription).toBeNull()
  })

  it('/upgrade alias resolves to the same command', () => {
    expect(findSlashCommand('upgrade')).toBe(subscriptionCommand)
  })

  it('/subscription resolves to the same command', () => {
    expect(findSlashCommand('subscription')).toBe(subscriptionCommand)
  })
})

// requestRemoteSpending ctx: the step-up screen's "Allow Remote Spending" path
// (`subscriptionOverlay.tsx` → `StepUpScreen.enable()`). `ctx.gateway.rpc` never
// rejects — it catches every transport error and resolves to null (see
// useMainApp.ts). The ctx function must map that null to the transport-failure
// retry message instead of letting it fall through to a misleading
// "someone with billing permissions must approve it" default.
describe('/subscription requestRemoteSpending ctx', () => {
  beforeEach(() => {
    resetOverlayState()
  })

  /** Open the overlay, then return the overlay ctx + rpc mock for direct calls. */
  const openAndGrab = async (stepUpResult: unknown) => {
    const { rpc, run } = buildCtx({
      'subscription.state': loggedInState(),
      'billing.step_up': stepUpResult
    })

    // `run` awaits the subscription.state resolution + the guarded .then; after
    // it the overlay (with its ctx) is mounted in the store. The overlay ctx
    // captures this same rpc mock, so a later requestRemoteSpending() call
    // resolves to the billing.step_up entry above.
    await run('')

    const overlayCtx = getOverlayState().subscription?.ctx

    return { overlayCtx, rpc }
  }

  it('null (transport failure) → transport-failure retry message, granted:false', async () => {
    const { overlayCtx } = await openAndGrab(null)

    const res = await overlayCtx!.requestRemoteSpending()

    expect(res.granted).toBe(false)
    expect(res.message).toBe('Could not reach the billing service — check your connection, then retry.')
    expect(res.error).toBeUndefined()
  })

  it('granted response → granted:true, no transport-fallback message', async () => {
    const { overlayCtx } = await openAndGrab({ ok: true, granted: true })

    const res = await overlayCtx!.requestRemoteSpending()

    expect(res.granted).toBe(true)
    expect(res.message).toBeUndefined()
    expect(res.error).toBeUndefined()
  })
})
