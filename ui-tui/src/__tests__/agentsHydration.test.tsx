import { PassThrough } from 'node:stream'

import { Box, renderSync } from '@hermes/ink'
import React from 'react'
import stripAnsi from 'strip-ansi'
import { expect, it, vi } from 'vitest'

import { applyAgentSnapshot } from '../app/agentRoster.js'
import { $delegationState, resetDelegationState } from '../app/delegationStore.js'
import { applyProcessSnapshot } from '../app/processRoster.js'
import { clearSpawnHistory } from '../app/spawnHistoryStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { AgentsOverlay } from '../components/agentsOverlay.js'
import type { GatewayClient } from '../gatewayClient.js'
import { DEFAULT_THEME } from '../theme.js'

it('does not undo an acknowledged pause when opening status resolves late', async () => {
  resetDelegationState()
  let resolveStatus!: (value: unknown) => void

  const status = new Promise(resolve => {
    resolveStatus = resolve
  })

  const request = vi.fn(async (method: string) => (method === 'delegation.status' ? status : { paused: true }))
  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 16, isTTY: false })
  const stdin = Object.assign(new PassThrough(), { isTTY: true, setRawMode: () => {}, ref: () => {}, unref: () => {} })

  const view = renderSync(
    <Box height={16}>
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
    await vi.waitFor(() => expect(request).toHaveBeenCalledWith('delegation.status', {}))
    stdin.write('p')
    await vi.waitFor(() => expect($delegationState.get().paused).toBe(true))
    resolveStatus({ paused: false, max_spawn_depth: 4 })
    await status
    await new Promise(resolve => setTimeout(resolve, 50))
    expect($delegationState.get().paused).toBe(true)
  } finally {
    view.unmount()
    view.cleanup()
    resetDelegationState()
  }
})

it('shows the working process stop alternative instead of an unusable x shortcut', async () => {
  clearSpawnHistory()
  resetDelegationState()
  applyAgentSnapshot(null)
  patchUiState({ sid: 'owner' })
  applyProcessSnapshot('owner', [{ session_id: 'bg-1', command: 'sleep 600', status: 'running' }])

  const request = vi.fn(async () => ({ paused: false }))
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
    await vi.waitFor(() => expect(output).toContain('sleep 600'))
    expect(output).toContain('/stop')
    expect(output).not.toContain('x stop')

    output = ''
    applyAgentSnapshot('owner', {
      subagents: [{ subagent_id: 'child', goal: 'Inspect work', status: 'running' }],
      delegations: []
    })
    await vi.waitFor(() => expect(output).toContain('Inspect work'))
    expect(output).toContain('x stop')
  } finally {
    view.unmount()
    view.cleanup()
    applyProcessSnapshot(null)
    applyAgentSnapshot(null)
    clearSpawnHistory()
    resetDelegationState()
    resetUiState()
  }
})
