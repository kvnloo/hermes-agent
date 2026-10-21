import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Node, Session, type Surface, type TspEvent, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

// Production's bundle loader imports PNG bytes; Vite's asset loader does not.
vi.mock('../../assets/logo.png', async () => {
  const { readFileSync } = await import('node:fs')

  return { default: readFileSync(new URL('../../assets/logo.png', import.meta.url)) }
})

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-orb-'))
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

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))

async function withApp(
  run: (fixture: {
    app: App
    gw: GatewayClient
    surface: Surface
    latest: () => View | undefined
    event: (event: TspEvent) => Promise<void>
  }) => Promise<void>
) {
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, features: ['blobs'], r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  await connecting
  const gw = new GatewayClient()
  const app = new App(tern, gw, 'test')
  app.sid = 'shown'
  app.todoHud.adopt('shown')
  const running = app.run()
  const surface = tern.surfaces[0]!
  const original = surface.render.bind(surface)
  let last: View | undefined
  vi.spyOn(surface, 'render').mockImplementation(view => {
    last = View.from(view)
    original(view)
    surface.acknowledge(surface.seq)
  })
  // Keep native immediates real so the app's coalesced render can settle.
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'setTimeout', 'clearTimeout'] })

  try {
    app.changed()
    await rendered()
    await run({
      app, gw, surface, latest: () => last,
      event: async event => {
        input.emit('data', `\x1b_tsp;e;${JSON.stringify(event)}\x1b\\`)
        await rendered()
        await rendered()
      }
    })
  } finally {
    app.quit()
    vi.useRealTimers()
    await running
    vi.restoreAllMocks()

    if (previousSplash === undefined) {
      delete process.env.HERMES_TUI_SPLASH
    } else {
      process.env.HERMES_TUI_SPLASH = previousSplash
    }
  }
}

function orb(view: View | undefined) {
  const dock = view?.regions.find(region => region?.id === 'dock')
  const composer = dock?.children.find(node => node.props.role === 'omp.editor')
  const line = composer?.children.find(node => node.props.role === 'omp.composer.line')

  return line?.children.find(node => node.props.role === 'hermes.agent.orb')
}

describe('activity orb in the parity dock', () => {
  it('keeps the todo HUD and notices beside the orb, without idle or foreign-session animation', async () => {
    await withApp(async ({ gw, surface, latest }) => {
      expect(orb(latest())?.props.alt).toBe('Hermes agent: idle')
      expect(vi.getTimerCount()).toBe(0)
      gw.emit('event', { type: 'message.start', session_id: 'other' })
      gw.emit('event', { type: 'voice.status', session_id: 'other', payload: { state: 'listening' } })
      await rendered()
      expect(vi.getTimerCount()).toBe(0)
      gw.emit('event', { type: 'message.start', session_id: 'shown' })
      gw.emit('event', { type: 'reasoning.delta', session_id: 'shown', payload: { text: 'Reason' } })
      gw.emit('event', {
        type: 'todo.updated', session_id: 'shown',
        payload: { todos: [{ id: 'a', content: 'Work', status: 'in_progress' }] }
      })
      gw.emit('event', {
        type: 'notification.show', session_id: 'shown',
        payload: { key: 'n', text: 'Attention', kind: 'sticky', level: 'warn' }
      })
      await rendered()
      expect(orb(latest())?.props.alt).toBe('Hermes agent: thinking')
      const dock = latest()?.regions.find(region => region?.id === 'dock')
      expect(dock?.children.some(node => node.kind === 'checklist')).toBe(true)
      expect(dock?.children.some(node => node.props.role === 'omp.dispatches')).toBe(true)
      expect(vi.getTimerCount()).toBe(1)
      const send = vi.spyOn(surface, 'send')
      vi.advanceTimersByTime(200)
      expect(send).toHaveBeenCalled()
      gw.emit('event', { type: 'message.complete', session_id: 'shown', payload: { status: 'complete' } })
      await rendered()
      expect(orb(latest())?.props.alt).toBe('Hermes agent: idle')
      expect(vi.getTimerCount()).toBe(0)
      send.mockClear()
      vi.advanceTimersByTime(10_000)
      expect(send).not.toHaveBeenCalled()
    })
  })

  it('shares pane-wide visibility with completion notices and never resumes an idle orb', async () => {
    await withApp(async ({ gw, event, latest }) => {
      gw.emit('event', { type: 'message.start', session_id: 'shown' })
      await rendered()
      await event({ ev: 'visible', visible: false, raw: {} })
      expect(vi.getTimerCount()).toBe(0)
      gw.emit('event', { type: 'message.complete', session_id: 'shown', payload: { status: 'complete' } })
      await rendered()
      expect(orb(latest())?.props.alt).toBe('Hermes agent: idle')
      expect(vi.getTimerCount()).toBe(0)
      await event({ ev: 'resize', sf: 'hermes', visible: true, cols: 80, raw: {} })

      const notes = latest()?.regions.find(region => region?.id === 'dock')?.children
        .find(node => node.props.role === 'omp.dispatches')

      expect(notes?.children[0]?.children.find(node => node.props.role === 'omp.dispatch.message')?.props.text)
        .toBe('A Hermes turn finished while this pane was hidden.')
      // Only the notice expiry is live, not an idle animation loop.
      expect(vi.getTimerCount()).toBe(1)
    })
  })

  it('cancels timers on native visibility, Reduce Motion, modal sheets and gone events', async () => {
    await withApp(async ({ app, gw, surface, event }) => {
      gw.emit('event', { type: 'message.start', session_id: 'shown' })
      await rendered()
      expect(vi.getTimerCount()).toBe(1)
      const send = vi.spyOn(surface, 'send')
      await event({ ev: 'visible', sf: 'hermes', visible: false, raw: {} })
      expect(vi.getTimerCount()).toBe(0)
      send.mockClear()
      vi.advanceTimersByTime(1_000)
      expect(send).not.toHaveBeenCalled()
      await event({ ev: 'resize', sf: 'hermes', cols: 80, visible: true, raw: {} })
      expect(vi.getTimerCount()).toBe(1)
      await event({ ev: 'motion', reduce: true, raw: {} })
      expect(vi.getTimerCount()).toBe(0)
      send.mockClear()
      vi.advanceTimersByTime(1_000)
      expect(send).not.toHaveBeenCalled()
      await event({ ev: 'motion', reduce: false, raw: {} })
      expect(vi.getTimerCount()).toBe(1)
      const sheet = { key: 'test-sheet', modal: true, node: () => new Node('text', { text: 'Sheet' }), onKey: () => false }
      app.open(sheet)
      await rendered()
      expect(vi.getTimerCount()).toBe(0)
      app.close(sheet)
      await rendered()
      expect(vi.getTimerCount()).toBe(1)
      await event({ ev: 'gone', ids: ['hermes'], raw: {} })
      expect(vi.getTimerCount()).toBe(0)
      send.mockClear()
      vi.advanceTimersByTime(1_000)
      expect(send).not.toHaveBeenCalled()
    })
  })
})
