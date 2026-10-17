import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-steer-action-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const altEnter = '\x1b[13;3u'
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

interface Options {
  mode?: string
  steer?(): Promise<{ status: 'queued' | 'rejected'; text: string }>
}

async function withApp(options: Options, run: (fixture: {
  app: App
  gw: GatewayClient
  surface: Surface
  calls: { method: string; params: unknown }[]
  press(bytes: string): Promise<void>
  busy(): Promise<void>
}) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const calls: { method: string; params: unknown }[] = []
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'setup.status') {
      return { provider_configured: true }
    }

    if (method === 'session.create') {
      return { session_id: 'session-1' }
    }

    if (method === 'config.get') {
      expect(params).toMatchObject({ key: 'busy', session_id: 'session-1' })

      return { value: options.mode ?? 'queue' }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'jobs.list') {
      return { jobs: [] }
    }

    calls.push({ method, params })

    if (method === 'session.steer') {
      return options.steer ? options.steer() : { status: 'queued', text: 'Use the smaller scope' }
    }

    if (method === 'request.answer') {
      return { status: 'ok' }
    }

    if (method === 'prompt.submit') {
      return { status: 'accepted' }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  await app.newSession()
  await rendered()
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
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
    await run({ app, gw, surface, calls, press, busy: async () => {
      gw.emit('event', { type: 'message.start', session_id: app.sid, payload: {} })
      await rendered()
      await rendered()
    } })
  } finally {
    app.quit()
    await running
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

describe('explicit busy steer vs follow-up', () => {
  it('steers once with Alt+Enter, clears the draft, and marks steering inside the current turn', async () => {
    await withApp({}, async ({ app, surface, calls, press, busy }) => {
      await busy()
      const turn = app.transcript.live
      app.composer.set('Use the smaller scope')
      await press(altEnter)
      expect(calls).toEqual([{ method: 'session.steer', params: { session_id: 'session-1', text: 'Use the smaller scope' } }])
      expect(app.composer.text).toBe('')
      expect(app.queue).toEqual([])
      expect(app.transcript.live).toBe(turn)
      expect(turn?.blocks).toContainEqual(expect.objectContaining({ kind: 'steering', text: 'Use the smaller scope' }))
      expect(nodes(surface).some(n => n.props.role === 'omp.steering')).toBe(true)
      expect(nodes(surface).some(n => n.props.text === 'Steering')).toBe(true)
    })
  })

  it('keeps busy Enter queued and displays both intents', async () => {
    await withApp({}, async ({ app, surface, calls, press, busy }) => {
      await busy()
      app.composer.set('Next task')
      await press('\r')
      expect(app.queue).toEqual(['Next task'])
      expect(app.composer.text).toBe('')
      expect(calls).toEqual([])
      expect(nodes(surface).find(n => n.props.role === 'omp.composer.hint')?.props.text).toContain('Enter queue · Alt+Enter steer')
    })
  })

  it('preserves idle Alt+Enter as a newline at the caret', async () => {
    await withApp({}, async ({ app, calls, press }) => {
      app.composer.set('draft', 2)
      await press(altEnter)
      expect(app.composer.text).toBe('dr\naft')
      expect(app.composer.cursor).toBe(3)
      expect(app.queue).toEqual([])
      expect(calls).toEqual([])
    })
  })

  it('retains draft and caret and shows a notice when steering fails', async () => {
    await withApp({ steer: async () => { throw new Error('No steering window') } }, async ({ app, calls, press, busy }) => {
      await busy()
      app.composer.set('Keep this draft', 4)
      await press(altEnter)
      expect(calls).toHaveLength(1)
      expect(app.composer.text).toBe('Keep this draft')
      expect(app.composer.cursor).toBe(4)
      expect(app.queue).toEqual([])
      expect(app.busy).not.toBeNull()
      expect(app.transcript.entries).toContainEqual(expect.objectContaining({ kind: 'notice', text: expect.stringContaining('No steering window') }))
      expect(app.transcript.live?.blocks).toEqual([])
    })
  })

  it('retains rejected steering instead of silently queuing a different intent', async () => {
    await withApp({ steer: async () => ({ status: 'rejected', text: 'Keep this draft' }) }, async ({ app, press, busy }) => {
      await busy()
      app.composer.set('Keep this draft')
      await press(altEnter)
      expect(app.composer.text).toBe('Keep this draft')
      expect(app.queue).toEqual([])
      expect(app.transcript.entries).toContainEqual(expect.objectContaining({ kind: 'notice', text: expect.stringContaining('rejected') }))
    })
  })

  it('swaps Enter and Alt+Enter, including the hint, for busy=steer', async () => {
    await withApp({ mode: 'steer' }, async ({ app, surface, calls, press, busy }) => {
      await busy()
      app.composer.set('Use the smaller scope')
      await press('\r')
      expect(calls).toEqual([{ method: 'session.steer', params: { session_id: 'session-1', text: 'Use the smaller scope' } }])
      app.composer.set('Later task')
      await press(altEnter)
      expect(app.queue).toEqual(['Later task'])
      expect(calls).toHaveLength(1)
      expect(nodes(surface).find(n => n.props.role === 'omp.composer.hint')?.props.text).toContain('Enter steer · Alt+Enter queue')
    })
  })

  it('honors busy=steer for native Send too', async () => {
    await withApp({ mode: 'steer' }, async ({ app, surface, calls, busy }) => {
      await busy()
      await surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'Use the smaller scope' })?.()
      await rendered()
      await rendered()
      expect(calls[0]?.method).toBe('session.steer')
      expect(app.composer.text).toBe('')
      expect(app.queue).toEqual([])
    })
  })

  it('coalesces repeated steering while preserving newer edits after acceptance', async () => {
    const gate = Promise.withResolvers<{ status: 'queued'; text: string }>()
    await withApp({ steer: () => gate.promise }, async ({ app, calls, press, busy }) => {
      await busy()
      app.composer.set('Original correction')
      await press(altEnter)
      await press(altEnter)
      app.composer.set('New draft')
      gate.resolve({ status: 'queued', text: 'Original correction' })
      await rendered()
      await rendered()
      expect(calls).toHaveLength(1)
      expect(app.composer.text).toBe('New draft')
      expect(app.transcript.live?.blocks).toContainEqual(expect.objectContaining({ kind: 'steering', text: 'Original correction' }))
    })
  })

  it('keeps delayed acceptance attached to its original turn after completion', async () => {
    const gate = Promise.withResolvers<{ status: 'queued'; text: string }>()
    await withApp({ steer: () => gate.promise }, async ({ app, gw, press, busy }) => {
      await busy()
      const turn = app.transcript.live
      app.composer.set('Original correction')
      await press(altEnter)
      gw.emit('event', { type: 'message.complete', session_id: app.sid, payload: {} })
      await busy()
      gate.resolve({ status: 'queued', text: 'Original correction' })
      await rendered()
      expect(turn?.blocks).toContainEqual(expect.objectContaining({ kind: 'steering' }))
      expect(app.transcript.live?.blocks).toEqual([])
    })
  })

  it('leaves busy=interrupt as explicit queue/steer, never an implicit interrupt', async () => {
    await withApp({ mode: 'interrupt' }, async ({ app, calls, press, busy }) => {
      await busy()
      app.composer.set('Follow-up')
      await press('\r')
      expect(app.queue).toEqual(['Follow-up'])
      app.composer.set('Correction')
      await press(altEnter)
      expect(calls).toEqual([{ method: 'session.steer', params: { session_id: 'session-1', text: 'Correction' } }])
    })
  })

  it('does not submit whitespace-only steering', async () => {
    await withApp({}, async ({ app, calls, press, busy }) => {
      await busy()
      app.composer.set('  ')
      await press(altEnter)
      expect(calls).toEqual([])
      expect(app.queue).toEqual([])
      expect(app.composer.text).toBe('  ')
    })
  })

  it('does not apply a delayed steering reply to a different session or its draft', async () => {
    const gate = Promise.withResolvers<{ status: 'queued'; text: string }>()
    await withApp({ steer: () => gate.promise }, async ({ app, press, busy }) => {
      await busy()
      app.composer.set('Old session correction')
      await press(altEnter)
      app.sid = 'session-2'
      app.transcript.clear()
      app.composer.set('New session draft')
      gate.resolve({ status: 'queued', text: 'Old session correction' })
      await rendered()
      expect(app.composer.text).toBe('New session draft')
      expect(app.transcript.entries).toEqual([])
    })
  })

  it.each(['queue', 'steer'])('keeps plain Enter deny-and-steer for approvals with busy=%s', async mode => {
    await withApp({ mode }, async ({ app, gw, calls, press, busy }) => {
      await busy()
      gw.emit('request', { id: 'approval-1', method: 'approval', params: { session_id: app.sid, command: 'rm fixture', request_id: 'request-1' }, respond: vi.fn(), fail: vi.fn() })
      app.composer.set('Use the smaller scope')
      await press('\r')
      expect(calls).toEqual([
        { method: 'request.answer', params: { id: 'approval-1', result: { choice: 'deny' } } },
        { method: 'prompt.submit', params: { session_id: 'session-1', text: 'Use the smaller scope' } }
      ])
      expect(app.composer.text).toBe('')
      expect(app.queue).toEqual([])
    })
  })

  it('does not redirect approval-owned text through session.steer', async () => {
    await withApp({ mode: 'steer' }, async ({ app, gw, calls, press, busy }) => {
      await busy()
      const respond = vi.fn()
      gw.emit('request', { id: 'approval-1', method: 'approval', params: { session_id: app.sid, command: 'rm fixture', request_id: 'request-1' }, respond, fail: vi.fn() })
      app.composer.set('Use the smaller scope')
      await press(altEnter)
      expect(respond).not.toHaveBeenCalled()
      expect(calls).toEqual([
        { method: 'request.answer', params: { id: 'approval-1', result: { choice: 'deny' } } },
        { method: 'prompt.submit', params: { session_id: 'session-1', text: 'Use the smaller scope' } }
      ])
      expect(app.queue).toEqual([])
    })
  })
})
