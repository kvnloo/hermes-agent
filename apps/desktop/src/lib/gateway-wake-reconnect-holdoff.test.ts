import { describe, expect, it } from 'vitest'

import {
  decideTrailingWakeForcedReconnect,
  decideWakeForcedReconnect,
  WAKE_RECONNECT_HOLDOFF_MS
} from './gateway-wake-reconnect-holdoff'

describe('decideWakeForcedReconnect (leading + coalesced trailing)', () => {
  it('forces immediately on the first wake', () => {
    const decision = decideWakeForcedReconnect({
      now: 1_000,
      lastForcedAt: null,
      trailingPending: false
    })

    expect(decision).toEqual({
      kind: 'force-now',
      nextLastForcedAt: 1_000,
      cancelTrailing: true
    })
  })

  it('arms exactly one trailing force for a second wake inside the holdoff', () => {
    const decision = decideWakeForcedReconnect({
      now: 1_000 + 1_000,
      lastForcedAt: 1_000,
      trailingPending: false
    })

    expect(decision).toEqual({
      kind: 'nudge-only',
      scheduleTrailing: true,
      trailingDueAt: 1_000 + WAKE_RECONNECT_HOLDOFF_MS
    })
  })

  it('does not enqueue a second trailing force when one is already pending', () => {
    const decision = decideWakeForcedReconnect({
      now: 1_000 + 2_000,
      lastForcedAt: 1_000,
      trailingPending: true
    })

    expect(decision).toEqual({
      kind: 'nudge-only',
      scheduleTrailing: false,
      trailingDueAt: 1_000 + WAKE_RECONNECT_HOLDOFF_MS
    })
  })

  it('ten wakes during holdoff produce at most one leading force and one trailing schedule', () => {
    let lastForcedAt: number | null = null
    let trailingPending = false
    let immediateForces = 0
    let trailingSchedules = 0

    for (let i = 0; i < 10; i += 1) {
      const now = 5_000 + i * 200
      const decision = decideWakeForcedReconnect({ now, lastForcedAt, trailingPending })

      if (decision.kind === 'force-now') {
        immediateForces += 1
        lastForcedAt = decision.nextLastForcedAt
        trailingPending = false
      } else if (decision.scheduleTrailing) {
        trailingSchedules += 1
        trailingPending = true
      }
    }

    expect(immediateForces).toBe(1)
    expect(trailingSchedules).toBe(1)
    expect(trailingPending).toBe(true)

    // Holdoff expires → exactly one trailing forced recovery.
    const trailing = decideTrailingWakeForcedReconnect(lastForcedAt + WAKE_RECONNECT_HOLDOFF_MS)

    expect(trailing.kind).toBe('force-now')
    expect(trailing.nextLastForcedAt).toBe(lastForcedAt + WAKE_RECONNECT_HOLDOFF_MS)
  })

  it('deterministic half-open scenario: leading force, mid-holdoff wake arms trailing, expiry forces once', () => {
    // t=0 online → immediate forced probe
    const t0 = decideWakeForcedReconnect({ now: 0, lastForcedAt: null, trailingPending: false })

    expect(t0.kind).toBe('force-now')
    const lastForcedAt = t0.kind === 'force-now' ? t0.nextLastForcedAt : 0

    // t=1s transport becomes half-open; second online inside holdoff
    const t1 = decideWakeForcedReconnect({
      now: 1_000,
      lastForcedAt,
      trailingPending: false
    })

    expect(t1).toEqual({
      kind: 'nudge-only',
      scheduleTrailing: true,
      trailingDueAt: WAKE_RECONNECT_HOLDOFF_MS
    })

    // t=15s holdoff expires → trailing forced recovery (half-open not stranded)
    const t15 = decideTrailingWakeForcedReconnect(WAKE_RECONNECT_HOLDOFF_MS)

    expect(t15).toEqual({
      kind: 'force-now',
      nextLastForcedAt: WAKE_RECONNECT_HOLDOFF_MS,
      cancelTrailing: true
    })
  })

  it('forces again once the holdoff has fully elapsed', () => {
    const decision = decideWakeForcedReconnect({
      now: 1_000 + WAKE_RECONNECT_HOLDOFF_MS,
      lastForcedAt: 1_000,
      trailingPending: true
    })

    expect(decision).toEqual({
      kind: 'force-now',
      nextLastForcedAt: 1_000 + WAKE_RECONNECT_HOLDOFF_MS,
      cancelTrailing: true
    })
  })
})
