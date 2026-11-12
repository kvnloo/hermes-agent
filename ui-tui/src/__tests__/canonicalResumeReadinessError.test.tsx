import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import React from 'react'
import { expect, it, vi } from 'vitest'

import { getUiState, patchUiState, resetUiState } from '../app/uiStore.js'
import { useSessionLifecycle } from '../app/useSessionLifecycle.js'

it('recovers when the setup probe fails after a canonical resume error', async () => {
  resetUiState()
  patchUiState({ sid: 'existing', status: 'ready' })
  const sys = vi.fn()
  const request = vi.fn(async (method: string) => {
    if (method === 'session.resume') {
      throw new Error('storage_unavailable')
    }

    if (method === 'setup.status') {
      throw new Error('readiness check still in progress; retrying next tick')
    }

    throw new Error(`unexpected request: ${method}`)
  })
  let lifecycle!: ReturnType<typeof useSessionLifecycle>

  function Harness() {
    lifecycle = useSessionLifecycle({
      colsRef: { current: 80 },
      composerActions: { setComposerTokens: vi.fn() },
      gw: { isCanonical: true, request },
      panel: vi.fn(),
      rpc: request,
      scrollRef: { current: null },
      setHistoryItems: vi.fn(),
      setLastUserMsg: vi.fn(),
      setSessionStartedAt: vi.fn(),
      setStickyPrompt: vi.fn(),
      setVoiceProcessing: vi.fn(),
      setVoiceRecording: vi.fn(),
      sys
    } as any)

    return null
  }

  const stream = () => Object.assign(new PassThrough(), { columns: 80, isTTY: false, rows: 24 })
  const instance = renderSync(React.createElement(Harness), {
    patchConsole: false,
    stderr: stream() as unknown as NodeJS.WriteStream,
    stdin: stream() as unknown as NodeJS.ReadStream,
    stdout: stream() as unknown as NodeJS.WriteStream
  })

  try {
    await expect(lifecycle.resumeById('stored')).resolves.toBeUndefined()
    expect(getUiState().status).toBe('ready')
    expect(getUiState().sid).toBe('existing')
    expect(sys).toHaveBeenCalledWith('error: storage_unavailable')
    expect(sys).toHaveBeenCalledWith('error: readiness check still in progress; retrying next tick')
    expect(request.mock.calls.map(([method]) => method)).toEqual(['session.resume', 'setup.status'])
  } finally {
    instance.unmount()
    resetUiState()
  }
})
