import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-tern-retry-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

async function withTurn(retryable: boolean, check: (app: App, calls: unknown) => void) {
  const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
  const gw = new GatewayClient()
  const calls = vi.spyOn(gw, 'request').mockResolvedValue({} as never)
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  const running = app.run()

  try {
    const surface = tern.surfaces[0]!
    const send = surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'retry me' })
    expect(send).toBeTypeOf('function')
    send!()
    expect(calls).toHaveBeenCalledWith('prompt.submit', { session_id: 'session-1', text: 'retry me' })
    gw.emit('event', {
      type: 'message.complete',
      session_id: 'session-1',
      payload: { error: 'Transient failure', error_surface: { layer: 'provider', code: 'transient', retryable }, status: 'error' }
    })
    check(app, calls)
  } finally {
    app.quit()
    await running
    calls.mockRestore()
  }
}

describe('native retry action', () => {
  it('replays a confirmed retryable text-only prompt exactly once', async () => {
    await withTurn(true, (app, calls) => {
      const failed = app.transcript.entries.findLast(e => e.kind === 'turn')
      expect(failed?.kind).toBe('turn')
      const id = failed!.id
      expect(app.canRetry(id)).toBe(true)
      app.retryFailed(id)
      expect(calls).toHaveBeenCalledTimes(2)
      expect(calls).toHaveBeenLastCalledWith('prompt.submit', { session_id: 'session-1', text: 'retry me' })
      app.retryFailed(id)
      expect(calls).toHaveBeenCalledTimes(2)
    })
  })

  it('refuses nonretryable failures', async () => {
    await withTurn(false, (app, calls) => {
      const id = app.transcript.entries.findLast(e => e.kind === 'turn')!.id
      expect(app.canRetry(id)).toBe(false)
      app.retryFailed(id)
      expect(calls).toHaveBeenCalledTimes(1)
    })
  })

  it('refuses a stale session and queued prompt', async () => {
    await withTurn(true, (app, calls) => {
      const id = app.transcript.entries.findLast(e => e.kind === 'turn')!.id
      app.queue.push('next task')
      expect(app.canRetry(id)).toBe(false)
      app.queue = []
      app.sid = 'session-2'
      app.retryFailed(id)
      expect(calls).toHaveBeenCalledTimes(1)
    })
  })
})
