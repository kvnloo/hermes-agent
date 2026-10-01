import { PassThrough } from 'node:stream'

import { renderSync, Text } from '@hermes/ink'
import React from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { turnController } from '../app/turnController.js'
import { patchTurnState, resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { useLongRunToolCharms } from '../app/useLongRunToolCharms.js'

const T0 = 1_800_000_000_000
const unmounts: Array<() => void> = []
let ticks: number[]
let charms: number[]

const Harness = () => {
  useLongRunToolCharms()

  return <Text>charms</Text>
}

const runTool = (ageMs: number) => {
  patchUiState({ busy: true })
  patchTurnState({ tools: [{ id: 'tool-1', name: 'terminal', startedAt: T0 - ageMs }] })

  const view = renderSync(<Harness />, {
    patchConsole: false,
    stdin: new PassThrough() as unknown as NodeJS.ReadStream,
    stdout: Object.assign(new PassThrough(), { columns: 80, rows: 24 }) as unknown as NodeJS.WriteStream
  })

  unmounts.push(() => {
    view.unmount()
    view.cleanup()
  })
}

beforeEach(() => {
  vi.useFakeTimers({ now: T0 })
  resetUiState()
  resetTurnState()
  ticks = []
  charms = []

  const fakeSetInterval = globalThis.setInterval

  vi.spyOn(globalThis, 'setInterval').mockImplementation(((fn: () => void, ms?: number) =>
    fakeSetInterval(() => {
      if (ms === 1000) {
        ticks.push(Date.now() - T0)
      }

      fn()
    }, ms)) as typeof setInterval)
  vi.spyOn(turnController, 'pushActivity').mockImplementation(() => void charms.push(Date.now() - T0))
})

afterEach(() => {
  while (unmounts.length) {
    unmounts.pop()!()
  }

  vi.restoreAllMocks()
  vi.useRealTimers()
  resetUiState()
  resetTurnState()
})

it('sleeps until a tool is old enough to charm, then charms on the same schedule', async () => {
  runTool(0)
  await vi.advanceTimersByTimeAsync(20_000)

  expect(ticks.filter(at => at < 8_000)).toEqual([])
  expect(charms).toEqual([8_000, 18_000])
})

it('still charms when the wake lands a millisecond before the tool is due', async () => {
  runTool(2_000)
  await vi.advanceTimersByTimeAsync(5_999)
  // Node may fire a timer ~1 ms before Date.now() reaches its target.
  vi.setSystemTime(Date.now() - 1)
  await vi.advanceTimersByTimeAsync(30_000)

  expect(charms).toHaveLength(2)
})
