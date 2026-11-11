import { PassThrough } from 'node:stream'

import { renderSync, Text } from '@hermes/ink'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { patchTurnState, resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import {
  LONG_RUN_CHARM_DELAY_MS,
  LONG_RUN_CHARM_TICK_MS,
  longRunCharmArmPlan,
  shouldArmLongRunCharmClock,
  useLongRunToolCharms
} from '../app/useLongRunToolCharms.js'

type IntervalSpy = ReturnType<typeof vi.spyOn<typeof globalThis, 'setInterval'>>

const T0 = 1_800_000_000_000
const mounted: Array<() => void> = []

const Harness = () => {
  useLongRunToolCharms()

  return <Text>charm-harness</Text>
}

const oneSecondTimers = (spy: IntervalSpy) =>
  spy.mock.calls.filter(call => call[1] === LONG_RUN_CHARM_TICK_MS).length

const mountHarness = () => {
  const stdout = new PassThrough()
  const stdin = new PassThrough()
  const stderr = new PassThrough()
  Object.assign(stdout, { columns: 80, isTTY: false, rows: 24 })
  Object.assign(stdin, { isTTY: false })
  Object.assign(stderr, { isTTY: false })

  const instance = renderSync(<Harness />, {
    patchConsole: false,
    stderr: stderr as NodeJS.WriteStream,
    stdin: stdin as NodeJS.ReadStream,
    stdout: stdout as NodeJS.WriteStream
  })

  mounted.push(() => {
    instance.unmount()
    instance.cleanup()
  })
}

const seedYoungTool = (ageMs: number) => {
  patchUiState({ busy: true, sid: 'sess-charm' })
  patchTurnState({
    tools: [{ id: 't-young', name: 'run_terminal', startedAt: T0 - ageMs }]
  })
}

const seedEligibleTool = () => {
  patchUiState({ busy: true, sid: 'sess-charm' })
  patchTurnState({
    tools: [{ id: 't-old', name: 'run_terminal', startedAt: T0 - LONG_RUN_CHARM_DELAY_MS - 500 }]
  })
}

let intervalSpy: IntervalSpy
let nowSpy: ReturnType<typeof vi.spyOn<typeof Date, 'now'>>

beforeEach(() => {
  resetUiState()
  resetTurnState()
  nowSpy = vi.spyOn(Date, 'now').mockReturnValue(T0)
  intervalSpy = vi.spyOn(globalThis, 'setInterval')
})

afterEach(() => {
  while (mounted.length > 0) {
    mounted.pop()!()
  }

  intervalSpy.mockRestore()
  nowSpy.mockRestore()
  resetUiState()
  resetTurnState()
})

describe('longRunCharmArmPlan (pure)', () => {
  it('idles when not busy or no tools', () => {
    expect(longRunCharmArmPlan(false, [{ startedAt: T0 - 20_000 }], T0)).toEqual({ kind: 'idle' })
    expect(longRunCharmArmPlan(true, [], T0)).toEqual({ kind: 'idle' })
    expect(longRunCharmArmPlan(true, [{ startedAt: undefined }], T0)).toEqual({ kind: 'idle' })
  })

  it('defers until the soonest tool reaches DELAY_MS', () => {
    expect(longRunCharmArmPlan(true, [{ startedAt: T0 - 2_000 }], T0)).toEqual({
      kind: 'deferred',
      waitMs: LONG_RUN_CHARM_DELAY_MS - 2_000
    })
    expect(longRunCharmArmPlan(true, [{ startedAt: T0 - 1_000 }, { startedAt: T0 - 5_000 }], T0)).toEqual({
      kind: 'deferred',
      waitMs: LONG_RUN_CHARM_DELAY_MS - 5_000
    })
  })

  it('arms the 1s interval once any tool is eligible', () => {
    expect(longRunCharmArmPlan(true, [{ startedAt: T0 - LONG_RUN_CHARM_DELAY_MS }], T0)).toEqual({
      kind: 'interval',
      periodMs: LONG_RUN_CHARM_TICK_MS
    })
    expect(
      longRunCharmArmPlan(
        true,
        [{ startedAt: T0 - 1_000 }, { startedAt: T0 - LONG_RUN_CHARM_DELAY_MS - 1 }],
        T0
      )
    ).toEqual({ kind: 'interval', periodMs: LONG_RUN_CHARM_TICK_MS })
  })
})

describe('shouldArmLongRunCharmClock (pure)', () => {
  it('is true only for the interval plan', () => {
    expect(shouldArmLongRunCharmClock(true, [{ startedAt: T0 - 1_000 }], T0)).toBe(false)
    expect(shouldArmLongRunCharmClock(true, [{ startedAt: T0 - LONG_RUN_CHARM_DELAY_MS }], T0)).toBe(true)
    expect(shouldArmLongRunCharmClock(false, [{ startedAt: T0 - 20_000 }], T0)).toBe(false)
  })
})

describe('longRunCharmClockDefer (mounted)', () => {
  it('arms no 1s clock while all tools are younger than DELAY_MS', () => {
    seedYoungTool(3_000)
    mountHarness()

    expect(oneSecondTimers(intervalSpy)).toBe(0)
  })

  it('arms exactly one 1s clock when a tool is already eligible', () => {
    seedEligibleTool()
    mountHarness()

    expect(oneSecondTimers(intervalSpy)).toBe(1)
  })

  it('arms no 1s clock when idle / no tools', () => {
    patchUiState({ busy: false })
    patchTurnState({ tools: [] })
    mountHarness()

    expect(oneSecondTimers(intervalSpy)).toBe(0)
  })
})
