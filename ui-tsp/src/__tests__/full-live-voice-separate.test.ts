import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { LiveVoicePayload } from '@hermes/shared/gateway-events'
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
  const home = mkdtempSync(join(tmpdir(), 'hermes-live-voice-'))
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
  event(payload: Partial<LiveVoicePayload>, session?: string): Promise<void>
  role(name: string): NonNullable<View['regions'][number]>['children'][number] | undefined
  click(name: string): Promise<void>
  send(text: string): Promise<void>
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

    if (method === 'voice.live.start') {
      await start
    }

    if (method === 'voice.live.control') {
      await stop?.()
    }

    return { live_id: p?.live_id, items: [], jobs: [] }
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
      press: async bytes => {
        input.emit('data', bytes)
        await flush()
      },
      event: async (payload, session = 'session-1') => {
        const id = calls.find(c => c.method === 'voice.live.start')?.params.live_id
        gw.emit('event', {
          type: 'voice.live',
          session_id: session,
          payload: { live_id: id, phase: 'listening', ...payload }
        })
        await flush()
      },
      click: async name => {
        const node = role(name)
        expect(node).toBeTruthy()
        expect(node!.kind).toBe('el')
        expect(node!.props.tag).toBe('button')
        expect(node!.props.text).toBeTruthy()
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

describe('separate opt-in live voice', () => {
  it('registers the opt-in chord separately from dictation', async () => {
    await withApp(async ({ press, role, calls }) => {
      await press('\x1b[118;4u')
      expect(role('omp.live.consent')).toBeTruthy()
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
    })
  })
  it('never opens audio on launch, editing or unsolicited events', async () => {
    await withApp(async ({ calls, app, event, role }) => {
      app.composer.set('private draft')
      await event({ phase: 'listening' })
      expect(calls.some(c => c.method.startsWith('voice.'))).toBe(false)
      expect(role('omp.live.toggle')).toBeTruthy()
    })
  })
  it('requires consent, supports cancel, and keeps Mic separate', async () => {
    await withApp(async ({ app, calls, click, role, press }) => {
      app.composer.set('keep draft')
      await click('omp.live.toggle')
      expect(role('omp.live.consent')).toBeTruthy()
      expect(calls.some(c => c.method.startsWith('voice.live'))).toBe(false)
      await click('omp.live.cancel')
      expect(role('omp.live.idle')).toBeTruthy()
      await click('omp.live.toggle')
      await click('omp.live.start')
      expect(calls.find(c => c.method === 'voice.live.start')?.params).toMatchObject({
        consent: true,
        session_id: 'session-1'
      })
      await press('\x1bv')
      expect(calls.some(c => c.method.startsWith('voice.dictate'))).toBe(false)
      expect(app.composer.text).toBe('keep draft')
    })
  })
  it('renders phase, mute, barge-in, assistant transcript and TTS completion', async () => {
    await withApp(async ({ calls, click, event, role, app }) => {
      await click('omp.live.toggle')
      await click('omp.live.start')

      for (const phase of ['listening', 'transcribing', 'thinking', 'speaking', 'interrupted'] as const) {
        await event({ phase })
        expect(role(`omp.live.${phase}`)).toBeTruthy()
      }

      await click('omp.live.mute')
      expect(calls.at(-1)).toMatchObject({ method: 'voice.live.control', params: { action: 'mute', muted: true } })
      await event({ phase: 'muted', muted: true })
      expect(role('omp.live.mute')?.props.text).toBe('Unmute')
      await click('omp.live.mute')
      expect(calls.at(-1)?.params.muted).toBe(false)
      await event({ phase: 'speaking', muted: false, assistant_text: 'Actual assistant reply' })
      expect(role('omp.live.assistant')?.props.text).toBe('Actual assistant reply')
      await click('omp.live.interrupt')
      expect(calls.at(-1)?.params.action).toBe('interrupt')
      await event({ phase: 'listening' })
      expect(app.liveVoice.phase).toBe('listening')
    })
  })
  it('blocks all draft Send paths without automatically submitting the draft', async () => {
    await withApp(async ({ app, calls, click, send, press, event, role }) => {
      app.composer.set('unsent draft', 3)
      await click('omp.live.toggle')
      await click('omp.live.start')
      await event({ phase: 'thinking', user_text: 'A spoken turn' })
      await send('native send')
      await press('\r')
      app.submitAlternate()
      expect(app.composer.text).toBe('unsent draft')
      expect(app.composer.cursor).toBe(3)
      expect(role('omp.composer.send.disabled')?.props.text).toContain('live voice')
      expect(calls.some(c => c.method === 'prompt.submit')).toBe(false)
    })
  })
  it('shows permission/start failure and requires explicit retry', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async ({ click, role, calls }) => {
      await click('omp.live.toggle')
      await click('omp.live.start')
      gate.reject(new Error('Microphone permission denied'))
      await tick()
      await tick()
      await tick()
      expect(role('omp.live.failure')?.props.text).toContain('permission denied')
      expect(calls.filter(c => c.method === 'voice.live.start')).toHaveLength(1)
    }, gate.promise)
  })
  it('keeps TTS/backend errors visible after audio release', async () => {
    await withApp(async ({ click, event, role, app }) => {
      await click('omp.live.toggle')
      await click('omp.live.start')
      await event({ phase: 'error', error: 'Configured TTS unavailable' })
      await event({ phase: 'idle' })
      expect(app.liveVoice.blocked).toBe(false)
      expect(role('omp.live.failure')?.props.text).toContain('Configured TTS unavailable')
    })
  })
  it('serializes stop behind startup; retains lease until idle', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async ({ click, calls, event, app, press }) => {
      await click('omp.live.toggle')
      await click('omp.live.start')
      await press('\x1b[27u')
      expect(calls.filter(c => c.method === 'voice.live.control')).toHaveLength(0)
      gate.resolve({})
      await tick()
      await tick()
      expect(calls.at(-1)?.params.action).toBe('stop')
      expect(app.liveVoice.blocked).toBe(true)
      await event({ phase: 'idle' })
      expect(app.liveVoice.blocked).toBe(false)
    }, gate.promise)
  })
  it('ignores foreign leases and releases old session on switch', async () => {
    await withApp(async ({ app, click, calls, event }) => {
      await click('omp.live.toggle')
      await click('omp.live.start')
      await event({ live_id: 'foreign', phase: 'speaking', assistant_text: 'wrong' })
      expect(app.liveVoice.assistant).toBe('')
      await app.resume('other-session')
      expect(calls.find(c => c.method === 'voice.live.control')?.params).toMatchObject({
        session_id: 'session-1',
        action: 'stop'
      })
      await event({ phase: 'idle' })
      expect(app.liveVoice.blocked).toBe(false)
    })
  })
})
