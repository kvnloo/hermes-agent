import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'
import { HostLifecycle } from '../host-lifecycle.js'
import { openSettings } from '../overlays/settings.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-host-lifecycle-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const painted = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

const active = '\x1b]9;4;3\x07'
const paused = '\x1b]9;4;4\x07'
const clear = '\x1b]9;4;0;\x07'

interface Fixture {
  app: App
  gw: GatewayClient
  surface: Surface
  progress: string[]
  notifications: string[]
  calls: { method: string; params: unknown }[]
  sendable(): unknown
  send(text: string): Promise<void>
  press(bytes: string): Promise<void>
  event(type: string, payload?: Record<string, unknown>, sid?: string): Promise<void>
  approval(id: string): ServerRequest
}

async function withApp(run: (h: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const progress: string[] = []
  const notifications: string[] = []

  const stdout = vi.spyOn(process.stdout, 'write').mockImplementation(chunk => {
    if (typeof chunk === 'string' && chunk.startsWith('\x1b]9;4;')) {
      progress.push(chunk)
    }

    if (typeof chunk === 'string' && chunk.includes(']777;notify;')) {
      notifications.push(chunk)
    }

    return true
  })

  const gw = new GatewayClient()
  const calls: Fixture['calls'] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    switch (method) {
      case 'complete.slash': return { items: [] }

      case 'settings.get': return { fields: {}, profile: 'fixture' }

      case 'prompt.submit': return { status: 'accepted' }

      case 'session.interrupt': return { status: 'ok' }

      default: throw new Error(`Unexpected fixture RPC: ${method}`)
    }
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'shown'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let last: View | undefined

  surface.render = view => {
    last = View.from(view)
    render(view)
  }

  app.changed()
  await painted()

  try {
    await run({
      app, gw, surface, calls, progress, notifications,
      sendable: () => {
        const pending = last?.regions.flatMap(region => region?.children ?? []) ?? []

        while (pending.length) {
          const node = pending.shift()!

          if (node.id === INPUT_ID) {
            return node.props.sendable
          }

          pending.push(...node.children)
        }

        throw new Error('Composer did not render')
      },
      send: async text => {
        const handler = surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text })
        expect(handler).toBeDefined()
        await handler!()
        await painted()
      },
      press: async bytes => {
        input.emit('data', bytes)
        await painted()
      },
      event: async (type, payload = {}, sid = 'shown') => {
        gw.emit('event', { type, payload, session_id: sid })
        await painted()
      },
      approval: id => {
        const request: ServerRequest = {
          id, method: 'approval', params: { session_id: app.sid ?? undefined, request_id: id, command: 'true' },
          respond() {}, fail() { throw new Error('Unsupported fixture prompt') }
        }

        gw.emit('request', request)

        return request
      }
    })
  } finally {
    app.quit()
    await running
    stdout.mockRestore()
    vi.restoreAllMocks()
  }
}

afterAll(() => {
  for (const [key, value] of [['HERMES_HOME', isolated.previous], ['HERMES_TUI_SPLASH', isolated.splash]]) {
    if (value === undefined) {
      delete process.env[key!]
    } else {
      process.env[key!] = value
    }
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('Carly admission and host lifecycle', () => {
  it('advertises false under a settings modal, retains the human draft, and accepts once closed', async () => {
    await withApp(async h => {
      h.app.composer.set('human draft', 3)
      openSettings(h.app)
      await painted()
      expect(h.sendable()).toBe(false)
      await h.send('host prompt must wait')
      expect(h.calls.some(c => c.method === 'prompt.submit')).toBe(false)
      expect(h.app.composer.text).toBe('human draft')
      expect(h.app.composer.cursor).toBe(3)
      h.app.close(h.app.overlays[0]!)
      await painted()
      expect(h.sendable()).toBe(true)
      await h.send('host prompt after admission')
      expect(h.calls.filter(c => c.method === 'prompt.submit')).toEqual([
        { method: 'prompt.submit', params: { session_id: 'shown', text: 'host prompt after admission', image_paths: [] } }
      ])
    })
  })

  it.each(['rewind', 'session', 'attachment', 'dictation'] as const)('shares the %s guard with the native send handler', async guard => {
    await withApp(async h => {
      h.app.composer.set('preserved')

      if (guard === 'rewind') {h.app.rewinding = { label: 'Rewinding', startedAt: Date.now(), since: {} }}

      if (guard === 'session') {h.app.sid = null}

      if (guard === 'attachment') {vi.spyOn(h.app.attachments, 'blocked', 'get').mockReturnValue(true)}

      if (guard === 'dictation') {h.app.dictation.state = 'recording'}
      h.app.changed()
      await painted()
      expect(h.sendable()).toBe(false)
      await h.send('must not be consumed')
      expect(h.app.composer.text).toBe('preserved')
      expect(h.calls.some(c => c.method === 'prompt.submit')).toBe(false)
    })
  })

  it('projects confirmed busy, tools, approval waiting and settled while hidden, deduping completion', async () => {
    await withApp(async h => {
      await h.event('message.start', {}, 'foreign')
      expect(h.progress).toEqual([])
      await h.event('message.start')
      await h.event('tool.start', { tool_id: 'tool', name: 'bash', args: { command: 'true' } })
      expect(h.progress).toEqual([active])
      h.approval('approve')
      await painted()
      expect(h.progress).toEqual([active, paused])
      // A dock approval still admits the existing deny-and-submit transaction.
      expect(h.sendable()).toBe(true)
      await h.event('request.cancel', { id: 'approve' })
      expect(h.progress).toEqual([active, paused, active])
      h.app.changed()
      await h.event('tool.complete', { tool_id: 'tool', name: 'bash', result: { exit_code: 0 } })
      await h.surface.dispatch({ ev: 'visible', sf: 'hermes', visible: false, raw: {} })?.()
      await h.event('message.complete', { status: 'complete', text: 'Done' })
      await h.event('message.complete', { status: 'complete', text: 'Done' })
      expect(h.progress).toEqual([active, paused, active, clear])
      expect(h.notifications).toHaveLength(2)
      expect(h.notifications[0]).toContain('Input required')
      expect(h.notifications[1]).toContain('Turn finished')
      expect(h.app.transcript.entries.some(e => e.kind === 'turn' && e.status === 'done')).toBe(true)
    })
  })

  it('keeps Ctrl+C draft-clearing semantics and offers an owned interrupt that preserves a nonempty draft', async () => {
    await withApp(async h => {
      await h.event('message.start')
      h.app.composer.set('human draft')
      await h.press('\x03')
      expect(h.app.composer.text).toBe('')
      expect(h.calls.some(c => c.method === 'session.interrupt')).toBe(false)
      h.app.composer.set('keep this draft')
      openSettings(h.app)
      await painted()
      await h.press('\x1b[120;6u')
      expect(h.app.composer.text).toBe('keep this draft')
      expect(h.calls.filter(c => c.method === 'session.interrupt')).toEqual([
        { method: 'session.interrupt', params: { session_id: 'shown' } }
      ])
      expect(h.progress).toEqual([active])
      await h.event('message.complete', { status: 'interrupted' })
      expect(h.progress).toEqual([active, clear])
    })
  })

  it('holds sends during session adoption and projects the confirmed resumed waiting state', async () => {
    await withApp(async h => {
      const result = Promise.withResolvers<unknown>()
      vi.mocked(h.gw.request).mockImplementationOnce(() => result.promise)
      const resuming = h.app.resume('stored')
      await painted()
      expect(h.sendable()).toBe(false)
      result.resolve({ session_id: 'resumed', running: true, status: 'waiting' })
      await resuming
      await painted()
      expect(h.progress).toEqual([paused])
      h.approval('resumed-approval')
      await painted()
      expect(h.progress).toEqual([paused])
      await h.event('request.cancel', { id: 'resumed-approval' }, 'resumed')
      expect(h.progress).toEqual([paused, active])
      await h.event('message.complete', { status: 'error' }, 'resumed')
      expect(h.progress).toEqual([paused, active, clear])
    })
  })

  it('never emits an idle edge between a completed turn and its queued send admission', async () => {
    await withApp(async h => {
      await h.event('message.start')
      await h.send('next queued message')
      expect(h.app.queue).toEqual(['next queued message'])
      const result = Promise.withResolvers<unknown>()
      vi.mocked(h.gw.request).mockImplementationOnce(() => result.promise)
      await h.event('message.complete', { status: 'complete' })
      expect(h.progress).toEqual([active])
      result.resolve({ status: 'streaming' })
      await painted()
      expect(h.progress).toEqual([active])
      await h.event('message.complete', { status: 'complete' })
      expect(h.progress).toEqual([active, clear])
    })
  })

  it('does not claim work until prompt admission is confirmed, or settle an interrupt before confirmation', async () => {
    await withApp(async h => {
      const result = Promise.withResolvers<unknown>()
      vi.mocked(h.gw.request).mockImplementationOnce(() => result.promise)
      await h.send('pending admission')
      expect(h.progress).toEqual([])
      result.resolve({ status: 'streaming' })
      await painted()
      expect(h.progress).toEqual([active])
      h.app.interrupt()
      expect(h.progress).toEqual([active])
      await h.event('message.complete', { status: 'interrupted' })
      expect(h.progress).toEqual([active, clear])
    })
  })

  it('projects confirmed session.close even while the replacement session is still hydrating', async () => {
    await withApp(async h => {
      await h.event('message.start')
      const closed = Promise.withResolvers<unknown>()
      const created = Promise.withResolvers<unknown>()
      vi.mocked(h.gw.request)
        .mockResolvedValueOnce({ provider_configured: true })
        .mockImplementationOnce(() => closed.promise)
        .mockImplementationOnce(() => created.promise)
      const switching = h.app.newSession()
      await painted()
      expect(h.sendable()).toBe(false)
      expect(h.progress).toEqual([active])
      closed.resolve({ status: 'closed' })
      await painted()
      expect(h.progress).toEqual([active, clear])
      expect(h.app.sid).toBeNull()
      created.resolve({ session_id: 'new' })
      await switching
      await painted()
      expect(h.progress).toEqual([active, clear])
      expect(h.sendable()).toBe(true)
    })
  })

  it('clears progress on backend death and exit, without duplicate attention', async () => {
    await withApp(async h => {
      await h.event('message.start')
      h.gw.emit('exit', 1)
      await painted()
      expect(h.progress).toEqual([active, clear])
      expect(h.sendable()).toBe(false)
      h.app.quit()
      expect(h.progress).toEqual([active, clear])
    })
  })

  it('projects a session boundary and suppresses repeated idle/close updates', () => {
    const writes: string[] = []
    const host = new HostLifecycle(text => writes.push(text))
    host.project({ sid: 'old', working: true, waiting: false })
    host.project({ sid: 'new', working: true, waiting: false })
    host.project({ sid: null, working: true, waiting: true })
    host.project({ sid: null, working: false, waiting: false })
    expect(writes).toEqual([active, clear, active, clear])
  })
})
