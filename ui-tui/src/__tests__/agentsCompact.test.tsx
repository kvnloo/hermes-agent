import { PassThrough } from 'node:stream'

import { Box, forceRedraw, renderSync, Text } from '@hermes/ink'
import React, { Profiler } from 'react'
import stripAnsi from 'strip-ansi'
import { expect, it, vi } from 'vitest'

import { renderToScreen } from '../../packages/hermes-ink/src/ink/render-to-screen.js'
import { cellAtIndex } from '../../packages/hermes-ink/src/ink/screen.js'
import { $agentDockCollapsed, applyAgentSnapshot } from '../app/agentRoster.js'
import { getInputSelection } from '../app/inputSelectionStore.js'
import { applyProcessSnapshot } from '../app/processRoster.js'
import { resetTurnState } from '../app/turnStore.js'
import { getUiState, patchUiState, resetUiState } from '../app/uiStore.js'
import { AgentsOverlay } from '../components/agentsOverlay.js'
import { AgentsPanelView, LiveAgentsPanel } from '../components/agentsPanel.js'
import { TextInput } from '../components/textInput.js'
import type { GatewayClient } from '../gatewayClient.js'
import { messages } from '../i18n/runtime.js'
import { buildAgentRows } from '../lib/agentRows.js'
import { DEFAULT_THEME } from '../theme.js'

it('keeps collapsed live chrome to one row without losing count or restore controls', () => {
  const rows = buildAgentRows([], [{ delegation_id: 'work', status: 'running', goal: 'Review the boundary' }], 1000)

  for (const cols of [78, 98]) {
    const view = renderToScreen(<AgentsPanelView collapsed cols={cols} {...rows} t={DEFAULT_THEME} />, cols)
    expect(view.height).toBe(1)
    const text = Array.from({ length: cols }, (_, i) => cellAtIndex(view.screen, i).char).join('')
    expect(text).toContain(messages().hubs.agentsPanel.liveAgents(rows.running))
    expect(text).toContain(messages().hubs.agentsPanel.collapsedHint.trim())
    expect(renderToScreen(<AgentsPanelView cols={cols} {...rows} t={DEFAULT_THEME} />, cols).height).toBeGreaterThan(
      view.height
    )
  }
})

it('opens the selected live transcript on Enter while details remain independently accessible', async () => {
  patchUiState({ sid: 'owner' })
  applyAgentSnapshot('owner', {
    subagents: [{ subagent_id: 'child', goal: 'Inspect ownership', status: 'running' }],
    delegations: []
  })

  const request = vi.fn(async (method: string) =>
    method === 'subagent.tail' ? { available: true, text: 'CHILD_TOOL_OUTPUT', truncated: false } : {}
  )

  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 20, isTTY: false })
  const stdin = Object.assign(new PassThrough(), { isTTY: true, setRawMode: () => {}, ref: () => {}, unref: () => {} })
  let output = ''
  stdout.on('data', chunk => {
    output += stripAnsi(chunk.toString())
  })

  const view = renderSync(
    <Box height={20}>
      <AgentsOverlay gw={{ request } as unknown as GatewayClient} onClose={() => {}} t={DEFAULT_THEME} />
    </Box>,
    {
      stdout: stdout as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream,
      patchConsole: false
    }
  )

  try {
    await vi.waitFor(() => expect(output).toContain('Inspect ownership'))
    stdin.write('\r')
    await vi.waitFor(() =>
      expect(request).toHaveBeenCalledWith('subagent.tail', { session_id: 'owner', subagent_id: 'child' })
    )
    await vi.waitFor(() => expect(output).toContain('CHILD_TOOL_OUTPUT'))
    output = ''
    stdin.write('d')
    await vi.waitFor(() => expect(output).toContain('Inspect ownership'))
    expect(output).not.toContain('CHILD_TOOL_OUTPUT')
    output = ''
    stdin.write('t')
    await vi.waitFor(() => expect(output).toContain('CHILD_TOOL_OUTPUT'))
    const cursorSnapshotRef = { current: null }
    const onChange = vi.fn()
    view.rerender(<TextInput cursorSnapshotRef={cursorSnapshotRef} onChange={onChange} value="draft" />)
    await vi.waitFor(() => expect(getInputSelection()?.value).toBe('draft'))
    stdin.write('\x1b[D')
    await vi.waitFor(() => expect(getInputSelection()?.start).toBe(4))
    view.rerender(<Box />)
    view.rerender(<TextInput cursorSnapshotRef={cursorSnapshotRef} onChange={onChange} value="draft" />)
    await vi.waitFor(() => expect(getInputSelection()?.start).toBe(4))
    stdin.write('!')
    await vi.waitFor(() => expect(onChange).toHaveBeenCalledWith('draf!t'))
  } finally {
    view.unmount()
    view.cleanup()
    applyAgentSnapshot(null)
    resetUiState()
  }
})

it('keeps the mounted dock asleep for status churn while following its theme, rosters and session', async () => {
  // Leave React/Ink scheduling real; this contract is independent of clock ticks.
  vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
  vi.setSystemTime(1_000_000)
  resetTurnState()
  resetUiState()
  $agentDockCollapsed.set(false)
  patchUiState({ sid: 'dock-owner' })
  const child = { subagent_id: 'fixture-agent', goal: 'fixtureagent', status: 'running', started_at: 995 }

  const process = {
    session_id: 'fixture-process',
    command: 'fixtureprocess',
    status: 'running',
    uptime_seconds: 5,
    output_preview: 'ready'
  }

  applyAgentSnapshot('dock-owner', { subagents: [child], delegations: [] })
  applyProcessSnapshot('dock-owner', [process])
  const stdout = Object.assign(new PassThrough(), { columns: 120, rows: 40, isTTY: true })
  const stdin = Object.assign(new PassThrough(), { isTTY: false })
  let output = ''
  stdout.on('data', chunk => {
    output += String(chunk)
  })
  const commits = vi.fn()

  const view = renderSync(
    <Box flexDirection="column" height={12}>
      <Profiler id="dock-consumer" onRender={commits}>
        <LiveAgentsPanel cols={100} />
      </Profiler>
      <Text>ROSTER_CONTROL</Text>
    </Box>,
    {
      patchConsole: false,
      stdout: stdout as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream
    }
  )

  const settle = async () => {
    await new Promise<void>(resolve => setImmediate(resolve))
    await new Promise<void>(resolve => setImmediate(resolve))
  }

  const frame = async () => {
    await settle()
    output = ''
    expect(forceRedraw(stdout as unknown as NodeJS.WriteStream)).toBe(true)
    const text = stripAnsi(output)
    expect(text).toContain('ROSTER_CONTROL')

    return text
  }

  try {
    const initial = await frame()
    expect(initial).toContain('fixtureagent')
    expect(initial).toContain('fixtureprocess')
    expect(commits).toHaveBeenCalled()
    commits.mockClear()

    for (let i = 0; i < 20; i++) {
      patchUiState({ status: `streaming-${i}` })
    }

    await settle()
    expect(commits).not.toHaveBeenCalled()

    patchUiState({ theme: { ...getUiState().theme } })
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    expect(await frame()).toContain('fixtureagent')
    commits.mockClear()

    applyAgentSnapshot('dock-owner', { subagents: [{ ...child, goal: 'changedagent' }], delegations: [] })
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    expect(await frame()).toContain('changedagent')
    commits.mockClear()

    applyProcessSnapshot('dock-owner', [{ ...process, command: 'changedprocess', output_preview: 'progress' }])
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    const updated = await frame()
    expect(updated).toContain('changedagent')
    expect(updated).toContain('changedprocess')
    commits.mockClear()

    patchUiState({ sid: 'other-session' })
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    const away = await frame()
    expect(away).not.toContain('changedagent')
    expect(away).not.toContain('changedprocess')
    commits.mockClear()

    patchUiState({ sid: 'dock-owner' })
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    const returned = await frame()
    expect(returned).toContain('changedagent')
    expect(returned).toContain('changedprocess')
    expect(Date.now()).toBe(1_000_000)
  } finally {
    view.unmount()
    view.cleanup()
    applyAgentSnapshot(null)
    applyProcessSnapshot(null)
    $agentDockCollapsed.set(false)
    resetTurnState()
    resetUiState()
    vi.useRealTimers()
  }
})
