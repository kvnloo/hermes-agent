import { PassThrough } from 'node:stream'

import { Box, renderSync, Text } from '@hermes/ink'
import React, { Profiler } from 'react'
import stripAnsi from 'strip-ansi'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { $agentDockCollapsed, applyAgentSnapshot } from '../app/agentRoster.js'
import { applyProcessSnapshot, PROCESS_RETAIN_SECONDS } from '../app/processRoster.js'
import { resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { LiveAgentsPanel } from '../components/agentsPanel.js'

const T0 = 1_800_000_000_000
const unmounts: Array<() => void> = []

// React flushes passive effects on a real macrotask while Ink's frame throttle
// runs on the faked clock, so step in small slices to let both settle.
const settle = async () => {
  for (let i = 0; i < 5; i += 1) {
    await vi.advanceTimersByTimeAsync(10)
  }
}

const mountDock = () => {
  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 30 })
  const frames: string[] = []
  let commits = 0
  let inkFrames = 0
  stdout.on('data', chunk => frames.push(stripAnsi(chunk.toString())))

  const view = renderSync(
    <Box flexDirection="column">
      <Text>[top]</Text>
      <Profiler id="dock" onRender={() => void (commits += 1)}>
        <LiveAgentsPanel cols={80} />
      </Profiler>
      <Text>[end]</Text>
    </Box>,
    {
      onFrame: () => void (inkFrames += 1),
      patchConsole: false,
      stdin: new PassThrough() as unknown as NodeJS.ReadStream,
      stdout: stdout as unknown as NodeJS.WriteStream
    }
  )

  unmounts.push(() => {
    view.unmount()
    view.cleanup()
  })

  return { commits: () => commits, inkFrames: () => inkFrames, last: () => frames.at(-1) ?? '' }
}

beforeEach(() => {
  vi.useFakeTimers({ now: T0 })
  resetUiState()
  resetTurnState()
  patchUiState({ sid: 'sess-dock' })
  $agentDockCollapsed.set(false)
  applyAgentSnapshot(null)
  applyProcessSnapshot(null)
})

afterEach(() => {
  while (unmounts.length) {
    unmounts.pop()!()
  }

  vi.useRealTimers()
  $agentDockCollapsed.set(false)
  applyAgentSnapshot(null)
  applyProcessSnapshot(null)
  resetUiState()
  resetTurnState()
})

it('stops repainting agent elapsed while the dock is collapsed and expands to the live value', async () => {
  applyAgentSnapshot('sess-dock', {
    delegations: [],
    subagents: [
      { goal: 'probe auth', started_at: T0 / 1000 - 12, status: 'running', subagent_id: 'child-1', tool_count: 1 }
    ]
  })
  $agentDockCollapsed.set(true)

  const dock = mountDock()
  await settle()
  expect(dock.last()).toContain('▸ 1 live agents')

  const [commits, frames] = [dock.commits(), dock.inkFrames()]
  await vi.advanceTimersByTimeAsync(10_000)

  // The collapsed summary carries no agent elapsed, so nothing re-renders.
  expect([dock.commits() - commits, dock.inkFrames() - frames]).toEqual([0, 0])

  $agentDockCollapsed.set(false)
  await settle()
  expect(dock.last()).toContain('probe auth 22s')

  await vi.advanceTimersByTimeAsync(1_000)
  expect(dock.last()).toContain('probe auth 23s')
})

it('keeps ageing finished processes out while the dock is collapsed', async () => {
  applyProcessSnapshot('sess-dock', [
    {
      command: 'pytest tests/',
      completion_reason: 'exited',
      exit_code: 0,
      exited_at: T0 / 1000 - 5,
      session_id: 'proc-1',
      status: 'exited',
      uptime_seconds: 17
    }
  ])
  $agentDockCollapsed.set(true)

  const dock = mountDock()
  await vi.advanceTimersByTimeAsync(3_000)
  expect(dock.last()).toContain('exit 0 · 8s ago')

  await vi.advanceTimersByTimeAsync(PROCESS_RETAIN_SECONDS * 1000)
  expect(dock.last()).not.toContain('pytest')
  expect(dock.last()).not.toContain('exit 0')
})
