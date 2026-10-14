// Independent mounted retention evidence for PR #129524.
import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { applyAgentSnapshot } from '../app/agentRoster.js'
import { resetDelegationState } from '../app/delegationStore.js'
import { applyProcessSnapshot, $processSnapshot, type ProcessEntry } from '../app/processRoster.js'
import { clearSpawnHistory, $spawnHistory } from '../app/spawnHistoryStore.js'
import { resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { AgentsOverlay } from '../components/agentsOverlay.js'
import type { GatewayClient } from '../gatewayClient.js'
import { DEFAULT_THEME } from '../theme.js'

const SID = 'overlay-retention-fixture'
const T0 = 1_800_000_000_000
const cleanup: Array<() => void> = []
const intervals = new Map<ReturnType<typeof setInterval>, number>()
const scheduled: number[] = []
// Real Ink also owns a 2s raw-input watchdog. Observe the overlay's 1s timer
// without pretending that the renderer's unrelated watchdog should stop.
const overlayTimerCount = () => [...intervals.values()].filter(ms => ms === 1000).length
const timerDelays = () => [...intervals.values()].sort((a, b) => a - b)

function mountOverlay() {
  const stdout = Object.assign(new PassThrough(), { columns: 140, rows: 40, isTTY: false })
  const stdin = Object.assign(new PassThrough(), {
    isTTY: true, setRawMode: () => {}, ref: () => {}, unref: () => {}
  })
  const stderr = new PassThrough()
  let pending = ''
  let lastFrame = ''
  let frameCount = 0
  stdout.on('data', chunk => { pending += chunk.toString() })
  const request = vi.fn(async (method: string, params: unknown) => {
    if (method !== 'delegation.status' || JSON.stringify(params) !== '{}') {
      throw new Error(`Unexpected transport call: ${method}`)
    }
    return { paused: false }
  })
  const instance = renderSync(
    <AgentsOverlay gw={{ request } as unknown as GatewayClient} onClose={() => {}} t={DEFAULT_THEME} />,
    {
      stdout: stdout as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stderr: stderr as unknown as NodeJS.WriteStream,
      patchConsole: false,
      onFrame: () => {
        if (pending) {
          lastFrame = stripAnsi(pending)
          pending = ''
          frameCount++
        }
      }
    }
  )
  cleanup.push(() => {
    instance.unmount()
    instance.cleanup()
    stdout.destroy()
    stdin.destroy()
    stderr.destroy()
  })
  return { frame: () => lastFrame, frames: () => frameCount, request }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(T0)
  intervals.clear()
  scheduled.length = 0
  const fakeSet = globalThis.setInterval
  const fakeClear = globalThis.clearInterval
  vi.spyOn(globalThis, 'setInterval').mockImplementation((callback, delay, ...args) => {
    const id = fakeSet(callback, delay, ...args)
    intervals.set(id, Number(delay))
    scheduled.push(Number(delay))
    return id
  })
  vi.spyOn(globalThis, 'clearInterval').mockImplementation(id => {
    intervals.delete(id as ReturnType<typeof setInterval>)
    return fakeClear(id)
  })
  resetTurnState()
  resetUiState()
  resetDelegationState()
  clearSpawnHistory()
  patchUiState({ sid: SID })
  applyAgentSnapshot(SID)
  applyProcessSnapshot(SID, [])
})

afterEach(() => {
  cleanup.splice(0).forEach(fn => fn())
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('mounted AgentsOverlay retention clock', () => {
  it.each([
    ['done', 0, null],
    ['failed', 1, null],
    ['killed', null, 'killed'],
    ['lost', null, 'lost']
  ] as const)('ages %s rows through 60 seconds, removes them at 61, and stops ticking', async (status, exitCode, reason) => {
    const command = `retention-${status}-sentinel`
    const process: ProcessEntry = {
      session_id: command, command, status: 'exited', exit_code: exitCode,
      completion_reason: reason, exited_at: T0 / 1000 - 59, uptime_seconds: 70
    }
    applyProcessSnapshot(SID, [process])
    const originalSnapshot = $processSnapshot.get()
    const view = mountOverlay()
    await expect.poll(view.frame).toContain(`${59}s ago`)
    expect(view.frame()).toContain(command)
    await expect.poll(() => view.request.mock.calls.length).toBe(1)

    await vi.advanceTimersByTimeAsync(1000)
    await expect.poll(view.frame).toContain('60s ago')
    expect(view.frame()).toContain(command)
    expect($processSnapshot.get()).toBe(originalSnapshot)
    expect(overlayTimerCount()).toBe(1)
    expect(timerDelays()).toEqual([1000, 2000])

    await vi.advanceTimersByTimeAsync(1000)
    await expect.poll(view.frame).not.toContain(command)
    expect(view.frame()).not.toContain('61s ago')
    await expect.poll(() => overlayTimerCount()).toBe(0)
    expect($processSnapshot.get()).toBe(originalSnapshot)
    const stoppedFrames = view.frames()
    await vi.advanceTimersByTimeAsync(120_000)
    expect(view.frames()).toBe(stoppedFrames)
    expect(overlayTimerCount()).toBe(0)
    expect(timerDelays()).toEqual([2000])
    expect(view.request.mock.calls).toEqual([['delegation.status', {}]])
    console.log(JSON.stringify({ case: status, boundary60: 'visible', boundary61: 'absent', intervalAfterExpiry: 0, snapshotUnchanged: true }))
  })

  it('keeps running process rows visible and ticking beyond the retention horizon', async () => {
    applyProcessSnapshot(SID, [{ session_id: 'running-control', command: 'running-control-sentinel', status: 'running', uptime_seconds: 10 }])
    const view = mountOverlay()
    await expect.poll(view.frame).toContain('running-control-sentinel')
    await expect.poll(() => overlayTimerCount()).toBe(1)
    const before = view.frames()
    await vi.advanceTimersByTimeAsync(61_000)
    await expect.poll(() => view.frames()).toBeGreaterThan(before)
    expect(view.frame()).toContain('running-control-sentinel')
    expect(overlayTimerCount()).toBe(1)
    expect(timerDelays()).toEqual([1000, 2000])
    expect(view.request.mock.calls).toEqual([['delegation.status', {}]])
  })

  it('keeps a static archived replay without process rows timer-free', async () => {
    $spawnHistory.set([{
      id: 'static-history', label: 'static-replay-sentinel', sessionId: SID,
      startedAt: T0 - 10_000, finishedAt: T0,
      subagents: [{ id: 'archived-agent', goal: 'static-replay-sentinel', status: 'completed', depth: 0, index: 0, taskCount: 1, tools: [], notes: [], thinking: [], durationSeconds: 10, startedAt: T0 - 10_000 }]
    }])
    const view = mountOverlay()
    await expect.poll(view.frame).toContain('static-replay-sentinel')
    await expect.poll(() => view.request.mock.calls.length).toBe(1)
    expect(overlayTimerCount()).toBe(0)
    expect(timerDelays()).toEqual([2000])
    await vi.advanceTimersByTimeAsync(120_000)
    expect(view.frame()).toContain('static-replay-sentinel')
    expect(overlayTimerCount()).toBe(0)
    expect(scheduled.filter(ms => ms === 1000)).toEqual([])
    expect(timerDelays()).toEqual([2000])
    expect(view.request.mock.calls).toEqual([['delegation.status', {}]])
  })
})
