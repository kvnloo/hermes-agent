import { useEffect, useRef } from 'react'

import { LONG_RUN_CHARMS } from '../content/charms.js'
import { pick, toolTrailLabel } from '../lib/text.js'
import type { ActiveTool } from '../types.js'

import { turnController } from './turnController.js'
import { useTurnSelector } from './turnStore.js'
import { getUiState } from './uiStore.js'

export const LONG_RUN_CHARM_DELAY_MS = 8_000
export const LONG_RUN_CHARM_INTERVAL_MS = 10_000
export const LONG_RUN_CHARM_TICK_MS = 1_000
export const MAX_CHARMS_PER_TOOL = 2

interface Slot {
  count: number
  lastAt: number
}

/** Pure arming plan for the long-run tool-charm clock (#111986 PR3 / #99773).
 *
 * Charms cannot fire until a live tool is ≥ DELAY_MS old, so a 1s interval
 * while every tool is still young is idle churn. Defer with one timeout until
 * the earliest eligibility, then tick at 1s.
 */
export type LongRunCharmArmPlan =
  | { kind: 'idle' }
  | { kind: 'deferred'; waitMs: number }
  | { kind: 'interval'; periodMs: typeof LONG_RUN_CHARM_TICK_MS }

export const longRunCharmArmPlan = (
  busy: boolean,
  tools: readonly Pick<ActiveTool, 'startedAt'>[],
  nowMs: number
): LongRunCharmArmPlan => {
  if (!busy || tools.length === 0) {
    return { kind: 'idle' }
  }

  let soonestWait: number | null = null

  for (const tool of tools) {
    if (!tool.startedAt) {
      continue
    }

    const age = nowMs - tool.startedAt

    if (age >= LONG_RUN_CHARM_DELAY_MS) {
      return { kind: 'interval', periodMs: LONG_RUN_CHARM_TICK_MS }
    }

    const wait = LONG_RUN_CHARM_DELAY_MS - age

    if (soonestWait === null || wait < soonestWait) {
      soonestWait = wait
    }
  }

  if (soonestWait === null) {
    return { kind: 'idle' }
  }

  return { kind: 'deferred', waitMs: Math.max(0, soonestWait) }
}

/** True iff the 1s charm clock should be armed right now (eligible tools exist). */
export const shouldArmLongRunCharmClock = (
  busy: boolean,
  tools: readonly Pick<ActiveTool, 'startedAt'>[],
  nowMs: number
): boolean => longRunCharmArmPlan(busy, tools, nowMs).kind === 'interval'

export function useLongRunToolCharms() {
  const tools = useTurnSelector(state => state.tools)
  const slots = useRef(new Map<string, Slot>())

  useEffect(() => {
    const busy = getUiState().busy
    const plan = longRunCharmArmPlan(busy, tools, Date.now())

    if (plan.kind === 'idle') {
      slots.current.clear()

      return
    }

    const tick = () => {
      if (!getUiState().busy) {
        slots.current.clear()

        return
      }

      const now = Date.now()
      const liveIds = new Set(tools.map(t => t.id))

      for (const key of Array.from(slots.current.keys())) {
        if (!liveIds.has(key)) {
          slots.current.delete(key)
        }
      }

      for (const tool of tools) {
        if (!tool.startedAt || now - tool.startedAt < LONG_RUN_CHARM_DELAY_MS) {
          continue
        }

        const slot = slots.current.get(tool.id) ?? { count: 0, lastAt: 0 }

        if (slot.count >= MAX_CHARMS_PER_TOOL || now - slot.lastAt < LONG_RUN_CHARM_INTERVAL_MS) {
          continue
        }

        slots.current.set(tool.id, { count: slot.count + 1, lastAt: now })
        turnController.pushActivity(
          `${pick(LONG_RUN_CHARMS)} (${toolTrailLabel(tool.name)} · ${Math.round((now - tool.startedAt) / 1000)}s)`
        )
      }
    }

    if (plan.kind === 'deferred') {
      // One-shot wake when the soonest tool crosses DELAY_MS. Re-check the
      // plan at fire time so a cleared busy/tools mid-wait does not promote.
      let intervalId: ReturnType<typeof setInterval> | undefined

      const timeoutId = setTimeout(() => {
        const next = longRunCharmArmPlan(getUiState().busy, tools, Date.now())

        if (next.kind !== 'interval') {
          return
        }

        tick()
        intervalId = setInterval(tick, LONG_RUN_CHARM_TICK_MS)
      }, plan.waitMs)

      return () => {
        clearTimeout(timeoutId)

        if (intervalId !== undefined) {
          clearInterval(intervalId)
        }
      }
    }

    tick()
    const id = setInterval(tick, plan.periodMs)

    return () => clearInterval(id)
  }, [tools])
}
