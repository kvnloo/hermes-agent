import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { DictationPayload } from '@hermes/shared/gateway-events'
import type { TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-dictation-'))
  const previous = { home: process.env.HERMES_HOME, splash: process.env.HERMES_TUI_SPLASH }
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = 'off'

  return { home, previous }
})

const tick = () => new Promise<void>(resolve => setImmediate(resolve))
interface Call { method: string; params: Record<string, unknown> }
interface Fixture {
  app: App
  calls: Call[]
  press(bytes: string): Promise<void>
  event(payload: Partial<DictationPayload>, session?: string): Promise<void>
  role(name: string): NonNullable<View['regions'][number]>['children'][number] | undefined
  click(name: string): Promise<void>
  send(text: string): Promise<void>
}

async function withApp(run: (fixture: Fixture) => Promise<void>, start?: Promise<unknown>, stop?: () => Promise<unknown>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const calls: Call[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    const p = params as Record<string, unknown>
    calls.push({ method, params: p })

    if (method === 'voice.dictate.start') {
      await start
    }

    if (method === 'voice.dictate.stop') {
      await stop?.()
    }

    return { capture_id: p?.capture_id, items: [], jobs: [] }
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view: View | undefined
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }

  const flush = async () => { await tick(); await tick(); await tick() }

  const nodes = () => {
    const all: NonNullable<View['regions'][number]>['children'][number][] = []

    const visit = (node: (typeof all)[number]) => { all.push(node); node.children.forEach(visit) }
    view?.regions.forEach(region => region?.children.forEach(visit))

    return all
  }

  const role = (name: string) => nodes().find(node => node.props.role === name)

  const dispatch = async (event: TspEvent) => {
    const handler = surface.dispatch(event)
    expect(handler).toBeTruthy()
    await handler!()
    await flush()
  }

  try {
    app.changed()
    await flush()
    await run({
      app, calls, role,
      press: async bytes => { input.emit('data', bytes); await flush() },
      event: async (payload, session = 'session-1') => {
        const id = calls.find(c => c.method === 'voice.dictate.start')?.params.capture_id
        gw.emit('event', { type: 'voice.dictation', session_id: session, payload: { capture_id: id, state: 'recording', ...payload } })
        await flush()
      },
      click: async name => {
        const node = role(name)
        expect(node).toBeTruthy()
        await dispatch({ act: 'click', ev: 'action', id: node!.id, raw: {}, sf: 'hermes' })
      },
      send: text => dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text } as TspEvent)
    })
  } finally {
    app.quit()
    await running
  }
}

afterAll(() => {
  for (const [key, value] of Object.entries({ HERMES_HOME: isolated.previous.home, HERMES_TUI_SPLASH: isolated.previous.splash })) {
    if (value === undefined) { delete process.env[key] } else { process.env[key] = value }
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('native composer dictation', () => {
  it('never records on launch, focus, edits or unrelated events', async () => {
    await withApp(async ({ calls, app, event, role }) => {
      app.composer.set('draft')
      app.changed()
      await event({ final: true, state: 'idle', text: 'unsolicited' })
      expect(calls.filter(c => c.method.startsWith('voice.'))).toEqual([])
      expect(app.composer.text).toBe('draft')
      expect(role('omp.composer.mic')).toBeTruthy()
    })
  })

  it('toggle starts, partials render live, final inserts at the caret without submitting', async () => {
    await withApp(async ({ app, calls, press, event, role, click }) => {
      app.composer.set('before after', 7)
      await press('\x1bv')
      expect(calls.filter(c => c.method === 'voice.dictate.start')).toHaveLength(1)
      expect(role('omp.composer.mic.starting')).toBeTruthy()
      await event({ state: 'recording', text: 'hello', final: false })
      expect(role('omp.composer.mic.partial')?.props.text).toBe('hello')
      expect(app.composer.text).toBe('before after')
      await click('omp.composer.mic')
      expect(calls.at(-1)).toMatchObject({ method: 'voice.dictate.stop', params: { cancel: false } })
      expect(role('omp.composer.mic.transcribing')).toBeTruthy()
      await event({ state: 'idle', final: true, text: 'hello ' })
      expect(app.composer.text).toBe('before hello after')
      expect(app.composer.cursor).toBe(13)
      expect(calls.some(c => c.method === 'prompt.submit')).toBe(false)
      app.composer.undo()
      expect(app.composer.text).toBe('before after')
    })
  })

  it('blocks Enter, alternate send, native Send and click Send with a visible reason', async () => {
    await withApp(async ({ app, calls, press, event, send, role }) => {
      app.composer.set('keep me')
      await press('\x1bv')

      for (const state of ['starting', 'recording', 'transcribing'] as const) {
        await event({ state })
        expect(role('omp.composer.send.disabled')?.props.text).toContain('dictation active')
        expect(role('omp.composer.send')).toBeUndefined()
        await press('\r')
        await send('atomic native draft')
        app.submitAlternate()
        expect(app.composer.text).toBe('keep me')
        expect(app.queue).toEqual([])
      }

      expect(calls.some(c => ['prompt.submit', 'session.steer'].includes(c.method))).toBe(false)
    })
  })

  it('Escape cancels and discards hypotheses without changing the draft or caret', async () => {
    await withApp(async ({ app, calls, press, event }) => {
      app.composer.set('draft stays', 4)
      await press('\x1bv')
      await event({ text: 'not committed' })
      await press('\x1b[27u')
      expect(calls.at(-1)).toMatchObject({ method: 'voice.dictate.stop', params: { cancel: true, session_id: 'session-1' } })
      await event({ state: 'idle', final: true, text: 'late result' })
      expect(app.composer.text).toBe('draft stays')
      expect(app.composer.cursor).toBe(4)
      expect(app.dictation.state).toBe('idle')
    })
  })

  it('serializes cancellation behind a pending start, ignoring intermediate events', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async ({ calls, press, event, app }) => {
      await press('\x1bv')
      await press('\x1b[27u')
      expect(calls.filter(c => c.method === 'voice.dictate.stop')).toHaveLength(0)
      await event({ state: 'idle', final: true, text: 'cancelled' })
      expect(app.composer.text).toBe('')
      gate.resolve({})
      await tick(); await tick()
      expect(calls.at(-1)).toMatchObject({ method: 'voice.dictate.stop', params: { cancel: true } })
    }, gate.promise)
  })

  it('ignores foreign session/capture events and duplicate finals', async () => {
    await withApp(async ({ app, press, event }) => {
      await press('\x1bv')
      await event({ final: true, state: 'idle', text: 'foreign' }, 'other-session')
      await event({ capture_id: 'old-capture', final: true, state: 'idle', text: 'stale' })
      expect(app.composer.text).toBe('')
      await event({ final: true, state: 'idle', text: 'once' })
      await event({ final: true, state: 'idle', text: 'once' })
      expect(app.composer.text).toBe('once')
    })
  })

  it('retains ownership and Send gating when cancellation fails, allowing an explicit retry', async () => {
    let attempts = 0
    await withApp(async ({ app, press, event, send, role }) => {
      app.composer.set('keep draft')
      await press('\x1bv')
      await event({ state: 'recording' })
      await press('\x1b[27u')
      expect(app.dictation.state).toBe('error')
      expect(app.dictation.blocked).toBe(true)
      expect(role('omp.composer.send.disabled')).toBeTruthy()
      await send('not allowed')
      expect(app.composer.text).toBe('keep draft')
      await press('\x1b[27u')
      expect(app.dictation.state).toBe('idle')
      expect(app.composer.text).toBe('keep draft')
    }, undefined, async () => {
      if (++attempts === 1) { throw new Error('transport unavailable') }
    })
  })

  it('shows a rejected start without assuming capture succeeded or retrying implicitly', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async ({ app, calls, press, role }) => {
      await press('\x1bv')
      gate.reject(new Error('microphone busy'))
      await tick(); await tick(); await tick()
      expect(app.dictation.state).toBe('error')
      expect(app.dictation.blocked).toBe(false)
      expect(role('omp.composer.mic.error')).toBeTruthy()
      expect(calls.filter(c => c.method === 'voice.dictate.start')).toHaveLength(1)
    }, gate.promise)
  })

  it('shows backend errors and permits an explicit retry, never auto-restarting', async () => {
    await withApp(async ({ app, calls, click, event, role }) => {
      await click('omp.composer.mic')
      await event({ state: 'error', error: 'Microphone permission denied' })
      expect(role('omp.composer.mic.error')).toBeTruthy()
      expect(app.dictation.label).toContain('permission denied')
      expect(calls.filter(c => c.method === 'voice.dictate.start')).toHaveLength(1)
      await click('omp.composer.mic')
      expect(calls.filter(c => c.method === 'voice.dictate.start')).toHaveLength(2)
    })
  })
})
