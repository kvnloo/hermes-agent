import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import React, { useState } from 'react'
import { expect, it, vi } from 'vitest'

import { resetOverlayState } from '../app/overlayStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { useInputHandlers } from '../app/useInputHandlers.js'

class FakeInput extends EventEmitter {
  chunks: string[] = []
  isRaw = false
  isTTY = true
  readableLength = 0
  ref = vi.fn()
  unref = vi.fn()
  setEncoding = vi.fn()
  setRawMode = vi.fn()

  read() {
    const next = this.chunks.shift() ?? null
    this.readableLength = this.chunks.length
    return next
  }

  send(data: string) {
    this.chunks.push(data)
    this.readableLength = this.chunks.length
    this.emit('readable')
  }
}

it('does not erase a newly typed draft when the queued-steer RPC settles', async () => {
  resetUiState()
  resetOverlayState()
  patchUiState({ sid: 'owner', busy: true })

  const stdin = new FakeInput()
  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 24, isTTY: false })
  const sys = vi.fn()
  const clearIn = vi.fn(() => setDraft(''))
  let settle!: (accepted: boolean) => void
  const steerQueue = vi.fn(() => new Promise<boolean>(resolve => { settle = resolve }))
  let setDraft: (next: string) => void = () => { throw new Error('composer not mounted') }
  let renderedDraft = ''
  const emptyBuf: string[] = []
  const emptyTokens: [] = []

  function Harness() {
    const [input, update] = useState('queued row')
    setDraft = update
    renderedDraft = input
    useInputHandlers({
      actions: { sys, countPrompts: () => 0 },
      composer: {
        actions: { clearIn, queueDraft: () => 'queued row', steerQueue },
        refs: {},
        state: { completions: [], input, inputBuf: emptyBuf, queueEditIdx: 0, tokens: emptyTokens }
      },
      gateway: { gw: { isCanonical: true } },
      terminal: { hasSelection: false, stdout },
      voice: { recordKey: 'ctrl+b' },
      wheelStep: 3
    } as any)

    return null
  }

  const instance = renderSync(<Harness />, { stdin: stdin as any, stdout: stdout as any, exitOnCtrlC: false, patchConsole: false })

  try {
    await expect.poll(() => stdin.listenerCount('readable')).toBeGreaterThan(0)
    stdin.send('\x13') // Ctrl+S
    await expect.poll(() => steerQueue.mock.calls.length).toBe(1)
    expect(steerQueue).toHaveBeenCalledWith(0)

    setDraft('new draft written during the RPC')
    await expect.poll(() => renderedDraft).toBe('new draft written during the RPC')
    settle(true)
    await expect.poll(() => sys.mock.calls.length).toBe(1)

    expect(clearIn).not.toHaveBeenCalled()
    expect(renderedDraft).toBe('new draft written during the RPC')
  } finally {
    instance.unmount()
    resetUiState()
    resetOverlayState()
  }
})
