import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { DictationPayload } from '@hermes/shared/gateway-events'
import type { TspEvent } from '@stencil-hq/tern'
import { KeyDecoder, Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { actionForKey } from '../actions.js'
import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-hold-gate-'))
  const previous = { home: process.env.HERMES_HOME, splash: process.env.HERMES_TUI_SPLASH }
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = 'off'

  return { home, previous }
})

const tick = () => new Promise<void>(resolve => setImmediate(resolve))
interface Call {
  method: string
  params: Record<string, unknown>
}
interface Fixture {
  app: App
  calls: Call[]
  press(bytes: string): Promise<void>
  event(payload: Partial<DictationPayload>, session?: string): Promise<void>
  role(name: string): NonNullable<View['regions'][number]>['children'][number] | undefined
  click(name: string): Promise<void>
  send(text: string): Promise<void>
  host(event: Record<string, unknown>): Promise<void>
  exit(): Promise<void>
}

async function withApp(
  run: (fixture: Fixture) => Promise<void>,
  start?: Promise<unknown>,
  stop?: () => Promise<unknown>
) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
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

  surface.render = next => {
    view = View.from(next)
    render(next)
  }

  const flush = async () => {
    await tick()
    await tick()
    await tick()
  }

  const nodes = () => {
    const all: NonNullable<View['regions'][number]>['children'][number][] = []

    const visit = (node: (typeof all)[number]) => {
      all.push(node)
      node.children.forEach(visit)
    }

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
      app,
      calls,
      role,
      host: async event => {
        input.emit('data', `\x1b_tsp;e;${JSON.stringify(event)}\x1b\\`)
        await flush()
      },
      exit: async () => {
        gw.emit('exit', 0)
        await flush()
      },
      press: async bytes => {
        input.emit('data', bytes)
        await flush()
      },
      event: async (payload, session = 'session-1') => {
        const id = calls.find(c => c.method === 'voice.dictate.start')?.params.capture_id
        gw.emit('event', {
          type: 'voice.dictation',
          session_id: session,
          payload: { capture_id: id, state: 'recording', ...payload }
        })
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
  for (const [key, value] of Object.entries({
    HERMES_HOME: isolated.previous.home,
    HERMES_TUI_SPLASH: isolated.previous.splash
  })) {
    if (value === undefined) {
      delete process.env[key]
    } else {
      process.env[key] = value
    }
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('push-to-talk capability gate', () => {
  it('demonstrates installed SDK cannot distinguish press, repeat and release', () => {
    const decoder = new KeyDecoder()
    const decoded = [1, 2, 3].map(phase => decoder.feed(Buffer.from(`\x1b[32;1:${phase}u`)))
    // This is a runtime SDK limitation, not a made-up host capability flag.
    expect(decoded[0]).toEqual([{ name: 'space', text: ' ', shift: false, alt: false, ctrl: false, meta: false }])
    expect(decoded[1]).toEqual(decoded[0])
    expect(decoded[2]).toEqual(decoded[0])
  })

  it('keeps unsupported hold mode out of the dock; explicit shortcut explains it without opening audio', async () => {
    await withApp(async ({ app, calls, role, press }) => {
      expect(role('omp.composer.mic.hold-unavailable')).toBeUndefined()
      await press('\x1b[32;4u')
      expect(
        app.transcript.entries.filter(entry => entry.kind === 'notice' && entry.text.includes('key-down/key-up'))
      ).toHaveLength(1)
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
      expect(role('omp.composer.mic')).toBeTruthy()
    })
  })

  it('preserves short Space taps and repeated spaces without inferring a hold', async () => {
    await withApp(async ({ app, calls, press }) => {
      app.composer.set('leftRIGHT', 4)
      await press(' ')
      expect(app.composer.text).toBe('left RIGHT')
      await press('    ')
      expect(app.composer.text).toBe('left     RIGHT')
      expect(app.composer.cursor).toBe(9)
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
    })
  })

  it('never steals plain Vim motion/jump characters or IME committed text', async () => {
    await withApp(async ({ app, calls, press }) => {
      await press('f j  日本語')
      expect(app.composer.text).toBe('f j  日本語')
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
      const context = { composerEmpty: false, busy: false, queued: false, overlayOpen: false, completionOpen: false }

      for (const name of ['space', 'f', 'j']) {
        expect(
          actionForKey(
            { name, text: name === 'space' ? ' ' : name, ctrl: false, alt: false, shift: false, meta: false },
            context
          )
        ).toBeUndefined()
      }
    })
  })

  it('keeps completion ownership and does not arm a hold behind its menu', async () => {
    await withApp(async ({ app, press, role, calls }) => {
      await press('/sett')
      await vi.waitFor(() => expect(role('omp.autocomplete')).toBeTruthy())
      const context = { composerEmpty: false, busy: false, queued: false, overlayOpen: false, completionOpen: true }
      expect(actionForKey({ name: 'space', ctrl: false, alt: true, shift: true, meta: false }, context)).toBeUndefined()
      await press(' ')
      expect(app.composer.text).toBe('/sett ')
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
    })
  })

  it('does not simulate release on visibility/focus loss or invent an activation', async () => {
    await withApp(async ({ app, calls, press, host }) => {
      await press(' ')
      await host({ ev: 'visible', sf: 'hermes', visible: false })
      await host({ ev: 'focus', sf: 'hermes', id: 'another-field' })
      await host({ ev: 'visible', sf: 'hermes', visible: true })
      expect(app.dictation.blocked).toBe(false)
      expect(app.composer.text).toBe(' ')
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
    })
  })

  it('fallback cancellation waits for startup and does not turn late final text into a send', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async ({ app, calls, press, event }) => {
      app.composer.set('draft ')
      await press('\x1bv')
      await press('\x1b[27u')
      expect(calls.some(c => c.method === 'voice.dictate.stop')).toBe(false)
      gate.resolve({})
      await tick()
      await tick()
      expect(calls.at(-1)).toMatchObject({
        method: 'voice.dictate.stop',
        params: { session_id: 'session-1', cancel: true }
      })
      await event({ state: 'idle', final: true, text: 'late speech' })
      expect(app.composer.text).toBe('draft ')
      expect(calls.some(c => c.method === 'prompt.submit')).toBe(false)
    }, gate.promise)
  })

  it('fallback finishes only the exact capture, inserts one final and remains review-only', async () => {
    await withApp(async ({ app, calls, press, click, event, role }) => {
      app.composer.set('before  after', 7)
      await press('\x1bv')
      await event({ state: 'recording', text: 'partial' })
      expect(role('omp.composer.mic.partial')?.props.text).toBe('partial')
      await click('omp.composer.mic')
      const start = calls.find(c => c.method === 'voice.dictate.start')!
      expect(calls.at(-1)?.params).toMatchObject({
        capture_id: start.params.capture_id,
        session_id: 'session-1',
        cancel: false
      })
      await event({ state: 'idle', final: true, text: 'speech' })
      expect(app.composer.text).toBe('before speech after')
      expect(calls.some(c => c.method === 'prompt.submit')).toBe(false)
      app.composer.undo()
      expect(app.composer.text).toBe('before  after')
    })
  })

  it('discards retired captures on disconnect without committing a late final', async () => {
    await withApp(async ({ app, calls, press, event, exit }) => {
      app.composer.set('review first')
      await press('\x1bv')
      await event({ state: 'recording', text: 'partial' })
      await exit()
      await event({ state: 'idle', final: true, text: 'retired' })
      expect(app.dictation.blocked).toBe(false)
      expect(app.composer.text).toBe('review first')
      expect(calls.some(c => c.method === 'prompt.submit')).toBe(false)
    })
  })
})
