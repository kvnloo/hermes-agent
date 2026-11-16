import { PassThrough } from 'node:stream'

import { renderSync, Text } from '@hermes/ink'
import { type OutMessage, Surface, type WireNode } from '@stencil-hq/tern'
import React from 'react'
import { afterAll, expect, it, vi } from 'vitest'

import { patchOverlayState, resetOverlayState } from '../app/overlayStore.js'
import { getUiState, patchUiState, resetUiState } from '../app/uiStore.js'
import { useComposerState } from '../app/useComposerState.js'
import { useSubmission } from '../app/useSubmission.js'
import type { GatewayClient } from '../gatewayClient.js'
import { load as loadHistory } from '../lib/history.js'
import { TernComposer } from '../tern/composer.js'
import { useTernComposer } from '../tern/useTernComposer.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-seam-bridge-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(async () => {
  const { rmSync } = await import('node:fs')

  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }
  rmSync(isolated.home, { force: true, recursive: true })
})

it('bridges buffered input, native edits and send to real history + durable prompt dispatch', async () => {
  resetUiState()
  resetOverlayState()
  patchUiState({ sid: 'session-a', busy: false, gatewayConnected: true })
  const request = vi.fn(async (method: string, _params?: Record<string, unknown>) => method === 'prompt.submit' ? { status: 'queued' } : {})
  const gw = { isCanonical: true, request } as unknown as GatewayClient
  const sys = vi.fn()
  const messages: OutMessage[] = []
  const surface = new Surface({ credits: () => 8, dropped() {}, send: frame => messages.push(frame) }, 'bridge', {})
  const tern = new TernComposer(surface)
  let composer!: ReturnType<typeof useComposerState>

  function Harness() {
    const submitRef = React.useRef<(value: string) => void>(() => {})
    const slashRef = React.useRef(vi.fn())
    composer = useComposerState({ gw, submitRef, sys })

    const submission = useSubmission({ appendMessage: vi.fn(), composerActions: composer.actions, composerRefs: composer.refs,
      composerState: composer.state, gw, setLastUserMsg: vi.fn(), slashRef, submitRef, sys })

    useTernComposer(tern, composer.refs, composer.actions, submission.dispatchSubmission)

    return <Text>{composer.state.input}</Text>
  }

  const input = Object.assign(new PassThrough(), { isTTY: false })
  const output = Object.assign(new PassThrough(), { isTTY: false, columns: 80, rows: 24 })
  output.resume()
  const ink = renderSync(<Harness />, { stdin: input as unknown as NodeJS.ReadStream, stdout: output as unknown as NodeJS.WriteStream, patchConsole: false })

  const editor = () => {
    const find = (node: WireNode): string | undefined => node.k === 'editor' ? node.id : node.c?.map(find).find(Boolean)

    for (const frame of messages.toReversed()) {
      if (frame.verb === 'f') {
        for (const op of frame.body.ops) {
          const found = op[0] === 'add' ? find(op[4]) : undefined

          if (found) { return found }
        }
      }
    }

    return ''
  }

  try {
    composer.actions.setInputBuf(['first buffered line'])
    composer.actions.setInput('last 😀')
    await vi.waitFor(() => expect(editor()).not.toBe(''))
    await vi.waitFor(() => expect(JSON.stringify(messages)).toContain('first buffered line'))
    expect(composer.refs.readDraft().text).toBe('first buffered line\nlast 😀')
    const id = editor()
    patchOverlayState({ sessions: true })
    surface.dispatch({ ev: 'send', id, sf: 'bridge', text: 'must not reach runtime', raw: {} })?.()
    expect(request.mock.calls.some(([method]) => method === 'prompt.submit')).toBe(false)
    patchOverlayState({ sessions: false })
    await vi.waitFor(() => expect(editor()).not.toBe(id))
    const current = editor()
    const pending = surface.dispatch({ ev: 'send', id: current, sf: 'bridge', text: 'first buffered line\nlast 😀', raw: {} })!
    pending()
    pending()
    await vi.waitFor(() => expect(request.mock.calls.filter(([method]) => method === 'prompt.submit')).toHaveLength(1))
    const call = request.mock.calls.find(([method]) => method === 'prompt.submit')!
    expect(call[1]).toMatchObject({ session_id: 'session-a', text: 'first buffered line\nlast 😀' })
    expect(loadHistory()).toContain('first buffered line\nlast 😀')
    expect(composer.refs.readDraft().text).toBe('')
    expect(getUiState().busy).toBe(true)
  } finally {
    tern.close()
    ink.unmount()
    input.destroy()
    output.destroy()
    resetUiState()
    resetOverlayState()
  }
})
