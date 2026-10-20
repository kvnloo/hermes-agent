import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-stale-session-events-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  if (isolated.splash === undefined) {
    delete process.env.HERMES_TUI_SPLASH
  } else {
    process.env.HERMES_TUI_SPLASH = isolated.splash
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('gateway events after a session switch', () => {
  it('never creates a turn, completes a tool, or closes the new owner from a stale session', async () => {
    const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
    acknowledgeFrames(tern)
    const gw = new GatewayClient()
    const requests = vi.spyOn(gw, 'request').mockImplementation(async method => {
      if (method === 'session.resume') {
        return {
          messages: [{ role: 'user', text: 'new prompt' }, { role: 'assistant', text: 'saved reply' }],
          running: false,
          session_id: 'new-session',
          status: 'idle',
          stored_session_id: 'new-stored'
        }
      }

      if (method === 'session.close' || method === 'complete.slash') {
        return { items: [] }
      }

      if (method === 'config.get') {
        return { value: null }
      }

      throw new Error(`Unexpected fixture RPC: ${method}`)
    })
    const app = new App(tern, gw, 'test')
    app.sid = 'old-session'
    const running = app.run()

    const rejectOldTurn = () => {
      const entries = JSON.stringify(app.transcript.entries)
      const revision = app.transcript.rev
      const live = app.transcript.live
      const busy = app.busy

      gw.emit('event', { payload: {}, session_id: 'old-session', type: 'message.start' })
      gw.emit('event', { payload: { text: 'stale answer' }, session_id: 'old-session', type: 'message.delta' })
      gw.emit('event', {
        payload: { name: 'terminal', result: { exit_code: 0, output: 'phantom success' }, tool_id: 'stale-tool' },
        session_id: 'old-session',
        type: 'tool.complete'
      })
      gw.emit('event', { payload: { status: 'completed', text: 'stale final' }, session_id: 'old-session', type: 'message.complete' })

      expect(app.transcript.rev).toBe(revision)
      expect(JSON.stringify(app.transcript.entries)).toBe(entries)
      expect(app.transcript.live).toBe(live)
      expect(app.busy).toBe(busy)
    }

    try {
      await app.resume('new-stored')
      expect(app.sid).toBe('new-session')
      expect(app.busy).toBeNull()
      expect(app.transcript.entries.some(entry => entry.kind === 'turn')).toBe(true)

      // The old session must not create a ghost turn while the new one is idle.
      rejectOldTurn()
      expect(app.transcript.live).toBeUndefined()

      gw.emit('event', { payload: {}, session_id: 'new-session', type: 'message.start' })
      gw.emit('event', { payload: { text: 'new-' }, session_id: 'new-session', type: 'message.delta' })
      expect(app.transcript.live).toBeDefined()
      expect(app.busy).not.toBeNull()

      // Nor can a late old-session completion finish the new active turn.
      rejectOldTurn()
      gw.emit('event', { payload: { text: 'owner' }, session_id: 'new-session', type: 'message.delta' })
      gw.emit('event', { payload: { status: 'completed' }, session_id: 'new-session', type: 'message.complete' })

      const turn = app.transcript.entries.findLast(entry => entry.kind === 'turn')

      if (turn?.kind !== 'turn') {
        throw new Error('Expected the current session to complete its own turn')
      }

      expect(turn.status).toBe('done')
      expect(turn.blocks.filter(block => block.kind === 'text').map(block => block.text)).toEqual(['new-owner'])
      expect(turn.blocks.some(block => block.kind === 'tool')).toBe(false)
      expect(app.busy).toBeNull()
    } finally {
      app.quit()
      await running
      requests.mockRestore()
    }
  })
})
