import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, type MockInstance, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'
import { confirmOverlay } from '../overlays/prompts.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-deny-steer-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const views = new WeakMap<Surface, View>()

function nodes(surface: Surface) {
  const pending = views.get(surface)?.regions.flatMap(region => region?.children ?? []) ?? []
  const all = [...pending]

  while (pending.length) {
    const node = pending.shift()!
    pending.push(...node.children)
    all.push(...node.children)
  }

  return all
}

function action(surface: Surface, role: string, key: string) {
  const target = nodes(surface).find(n => n.props.role === role && n.props.key === key)

  if (!target) {
    throw new Error(`Missing native action: ${role}/${key}`)
  }

  const handler = surface.dispatch({ act: 'click', ev: 'action', id: target.id, raw: {}, sf: 'hermes' })

  if (!handler) {
    throw new Error('Native action has no handler')
  }

  return handler
}

interface Fixture {
  app: App
  gw: GatewayClient
  surface: Surface
  calls: unknown[]
  focus: MockInstance<Surface['focus']>
  press(bytes: string): Promise<void>
  send(text: string): Promise<void>
  request(id: string, params?: Record<string, unknown>, respond?: () => void | Promise<void>): ServerRequest
}

async function withApp(run: (fixture: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )

  if (!(await connecting)) {
    throw new Error('The unit SDK peer did not connect')
  }

  const calls: unknown[] = []
  const responses = new Map<string, () => void | Promise<void>>()
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'request.answer') {
      const p = params as { id: string; result: Record<string, unknown> }
      expect(p.result).toEqual({ choice: 'deny' })
      calls.push({ id: p.id, result: p.result })
      await responses.get(p.id)?.()

      return { status: 'ok' }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'settings.get') {
      return { fields: {}, profile: 'fixture' }
    }

    if (method === 'prompt.submit' || method === 'session.interrupt') {
      calls.push({ method, params })

      return { status: 'accepted' }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const focus = vi.spyOn(surface, 'focus')
  const render = surface.render.bind(surface)

  surface.render = view => {
    views.set(surface, View.from(view))
    render(view)
  }

  const press = async (bytes: string) => {
    input.emit('data', bytes)
    await rendered()
    await rendered()
  }

  try {
    await run({
      app,
      gw,
      surface,
      calls,
      focus,
      press,
      send: async text => {
        await rendered()
        await surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text })?.()
        await rendered()
        await rendered()
      },
      request: (id, params = {}, respond) => {
        const req: ServerRequest = {
          id,
          method: 'approval',
          params: {
            command: 'printf fixture',
            request_id: `approval-${id}`,
            session_id: app.sid ?? undefined,
            ...params
          },
          fail: () => {
            throw new Error('Unexpected server-request failure')
          },
          respond: result => {
            calls.push({ id, result })

            return respond?.()
          }
        }

        if (respond) {
          responses.set(id, respond)
        }

        gw.emit('request', req)

        return req
      }
    })
  } finally {
    app.quit()
    await running
  }
}

afterAll(() => {
  for (const [key, value] of [
    ['HERMES_HOME', isolated.previous],
    ['HERMES_TUI_SPLASH', isolated.splash]
  ]) {
    if (value === undefined) {
      delete process.env[key!]
    } else {
      process.env[key!] = value
    }
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('non-blocking approvals with deny-and-steer', () => {
  it('renders denial steering before the answer it caused after message settlement', async () => {
    await withApp(async ({ app, request, send, surface }) => {
      app.transcript.start(1)
      app.transcript.text('Earlier work')
      app.busy = { label: 'Waiting', since: {}, startedAt: 1 }
      request('chronology')
      await send('Do not delete it; reply denied safely.')
      app.transcript.text('denied safely.')
      app.transcript.complete({ text: 'denied safely.', status: 'complete' })
      app.changed()
      await rendered()
      await rendered()
      const texts = nodes(surface).filter(n => n.kind === 'md').map(n => n.props.text)
      expect(texts.indexOf('Do not delete it; reply denied safely.')).toBeLessThan(texts.indexOf('denied safely.'))
      expect(texts.filter(text => text === 'Do not delete it; reply denied safely.')).toHaveLength(1)
    })
  })

  it('allows once with 1 on an empty draft, answering the exact request in the dock', async () => {
    await withApp(async ({ app, request, press, surface, calls, focus }) => {
      request('first')
      await rendered()
      const dock = views.get(surface)?.regions.find(region => region?.id === 'dock')
      const prompt = dock?.children.find(n => n.props.role === 'omp.editor.ask.approval')
      const composer = dock?.children.find(n => n.props.role === 'omp.editor')
      expect(prompt).toBeDefined()
      expect(dock!.children.indexOf(prompt!)).toBeLessThan(dock!.children.indexOf(composer!))
      expect(views.get(surface)?.regions.find(region => region?.id === 'layer')?.children).toEqual([])
      await press('1')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'once' } }])
      expect(app.composer.text).toBe('')
      expect(focus).not.toHaveBeenCalled()
    })
  })

  it('types into the composer, then denies and submits in order exactly once with Enter', async () => {
    await withApp(async ({ app, request, press, calls, focus }) => {
      app.busy = { label: 'Waiting for approval', since: {}, startedAt: Date.now() }
      request('first')
      await press('use rg instead')
      expect(app.composer.text).toBe('use rg instead')
      expect(calls).toEqual([])
      await press('\r')
      expect(calls).toEqual([
        { id: 'first', result: { choice: 'deny' } },
        { method: 'prompt.submit', params: { session_id: 'session-1', text: 'use rg instead', image_paths: [] } }
      ])
      expect(app.queue).toEqual([])
      expect(app.composer.text).toBe('')
      expect(focus).not.toHaveBeenCalled()
    })
  })

  it('keeps the draft and shows a notice when the deny response rejects; submits nothing', async () => {
    await withApp(async ({ app, request, press, surface, calls }) => {
      request('first', {}, async () => {
        throw new Error('deny failed')
      })
      await press('use rg instead')
      await press('\r')
      expect(app.composer.text).toBe('use rg instead')
      expect(app.overlays).toHaveLength(1)
      expect(calls).toEqual([{ id: 'first', result: { choice: 'deny' } }])
      expect(nodes(surface).some(n => JSON.stringify(n.props).includes('deny failed'))).toBe(true)
    })
  })

  it('drops stale response handlers after a same-id request replacement', async () => {
    await withApp(async ({ request, surface, calls }) => {
      request('same', { command: 'old command' })
      await rendered()
      const stale = action(surface, 'omp.btn', 'deny')
      request('same', { command: 'new command' })
      await rendered()
      await stale()
      expect(calls).toEqual([])
      await action(surface, 'omp.btn', 'deny')()
      expect(calls).toEqual([{ id: 'same', result: { choice: 'deny' } }])
    })
  })

  it('denies on Escape with an empty draft without ever taking composer focus', async () => {
    await withApp(async ({ app, request, press, calls, focus }) => {
      request('first')
      await press('\x1b[27u')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'deny' } }])
      expect(app.overlays).toEqual([])
      expect(focus).not.toHaveBeenCalled()
    })
  })

  it('queues a second request behind the first and shows 1 more', async () => {
    await withApp(async ({ request, press, calls, surface }) => {
      request('first', { command: 'first command' })
      request('second', { command: 'second command' })
      await rendered()
      expect(nodes(surface).find(n => n.props.role === 'omp.editor.ask.approval.queued')?.props.text).toBe('1 more')
      expect(nodes(surface).filter(n => n.props.role === 'omp.editor.ask.approval')).toHaveLength(1)
      await press('1')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'once' } }])
      expect(nodes(surface).some(n => n.props.text === 'second command')).toBe(true)
      await press('4')
      expect(calls[1]).toEqual({ id: 'second', result: { choice: 'deny' } })
    })
  })

  it('keeps digits, arrows, modified Enter and Escape with a nonempty composer', async () => {
    await withApp(async ({ app, request, press, calls }) => {
      request('first')
      await press('n1234y')
      await press('\x1b[A\x1b[B')
      await press('\x1b[27u')
      await press('\x1b[13;2u')
      expect(app.composer.text).toBe('n1234y\n')
      expect(calls).toEqual([])
    })
  })

  it('uses arrow/Enter selection and retains policy filters for numeric choices', async () => {
    await withApp(async ({ request, press, calls, surface }) => {
      request('first', { smart_denied: true, allow_session: false, allow_permanent: false })
      await rendered()
      expect(nodes(surface).filter(n => n.props.role === 'omp.ask.option')).toHaveLength(2)
      await press('3') // No third offered option: do not type or invent an approval.
      expect(calls).toEqual([])
      await press('\x1b[B\r')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'deny' } }])
      request('second', { choices: ['once', 'session', 'always', 'deny'], allow_session: false })
      await press('2')
      expect(calls[1]).toEqual({ id: 'second', result: { choice: 'always' } })
    })
  })

  it('native send uses the same ordered transaction and coalesces repeated submits while deny is pending', async () => {
    await withApp(async ({ request, send, app, calls }) => {
      const gate = Promise.withResolvers<void>()
      request('first', {}, () => gate.promise)
      await send('use rg instead')
      await send('use rg instead')
      expect(app.composer.text).toBe('use rg instead')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'deny' } }])
      gate.resolve()
      await rendered()
      await rendered()
      expect(calls).toEqual([
        { id: 'first', result: { choice: 'deny' } },
        { method: 'prompt.submit', params: { session_id: 'session-1', text: 'use rg instead', image_paths: [] } }
      ])
    })
  })

  it('retains atomic native send text on a failed denial RPC', async () => {
    await withApp(async ({ request, send, app, calls }) => {
      request('first', {}, () => {
        throw new Error('transport gone')
      })
      await send('use rg instead')
      expect(app.composer.text).toBe('use rg instead')
      expect(calls).toHaveLength(1)
    })
  })

  it('does not steer after cancellation or replacement while an async deny is in flight', async () => {
    await withApp(async ({ request, send, app, gw, calls }) => {
      const gate = Promise.withResolvers<void>()
      request('first', {}, () => gate.promise)
      await send('use rg instead')
      gw.emit('event', { type: 'request.cancel', session_id: 'session-1', payload: { id: 'first' } })
      request('second')
      gate.resolve()
      await rendered()
      expect(calls).toEqual([{ id: 'first', result: { choice: 'deny' } }])
      expect(app.composer.text).toBe('use rg instead')
      expect(app.overlays.map(o => o.key)).toEqual(['prompt:second'])
    })
  })

  it('drops native Send captured for a replaced request instead of denying its successor', async () => {
    await withApp(async ({ request, surface, calls }) => {
      request('same', { command: 'old command' })
      await rendered()
      const stale = surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'use rg instead' })
      expect(stale).toBeDefined()
      request('same', { command: 'new command' })
      await rendered()
      await stale?.()
      expect(calls).toEqual([])
    })
  })

  it('never turns a pre-approval native Send into a denial of a new request', async () => {
    await withApp(async ({ app, request, surface, calls }) => {
      app.changed()
      await rendered()
      const stale = surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'earlier draft' })
      expect(stale).toBeDefined()
      request('new')
      await stale?.()
      expect(calls).toEqual([])
    })
  })

  it('does not send when the gateway reports that the exact denial request expired', async () => {
    await withApp(async ({ app, gw, request, send, surface }) => {
      request('first')
      vi.mocked(gw.request).mockResolvedValueOnce({ status: 'expired' })
      await send('use rg instead')
      expect(gw.request).toHaveBeenCalledWith('request.answer', { id: 'first', result: { choice: 'deny' } })
      expect(gw.request).not.toHaveBeenCalledWith('prompt.submit', expect.anything())
      expect(app.composer.text).toBe('use rg instead')
      expect(nodes(surface).some(n => JSON.stringify(n.props).includes('no longer pending'))).toBe(true)
    })
  })

  it('withdraws queued approvals and cannot answer their cancelled generations', async () => {
    await withApp(async ({ app, gw, request, press, calls }) => {
      request('first')
      request('second')
      gw.emit('event', {
        type: 'approval.cancelled',
        session_id: 'session-1',
        payload: { request_ids: ['approval-second'] }
      })
      await press('1')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'once' } }])
      expect(app.overlays).toEqual([])
    })
  })

  it('preserves edits made while waiting for denial and does not steer across a backend exit', async () => {
    await withApp(async ({ app, gw, request, send, press, calls }) => {
      const gate = Promise.withResolvers<void>()
      request('first', {}, () => gate.promise)
      await send('use rg instead')
      await press(' please')
      gw.emit('exit', 1)
      gate.resolve()
      await rendered()
      expect(app.composer.text).toBe('use rg instead please')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'deny' } }])
      expect(app.overlays).toEqual([])
    })
  })

  it('floating modals retain key and native callback ownership over a dock approval', async () => {
    await withApp(async ({ app, request, surface, press, calls }) => {
      request('first')
      await rendered()
      const stale = action(surface, 'omp.btn', 'deny')
      app.open(confirmOverlay(app, { title: 'Confirm fixture', detail: '', confirm: 'Yes', onConfirm() {} }))
      await rendered()
      await stale()
      await press('1')
      expect(calls).toEqual([])
      await press('\x1b[27u')
      await press('1')
      expect(calls).toEqual([{ id: 'first', result: { choice: 'once' } }])
    })
  })
})
