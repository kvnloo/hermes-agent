import { EventEmitter } from 'node:events'
import { readFileSync, rmSync } from 'node:fs'

import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-reference-journey-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

interface EventStep {
  type: string
  payload: Record<string, unknown>
}

interface JourneyStep {
  id: string
  intent?: 'inspect' | 'send' | 'approval' | 'model-picker' | 'jobs' | 'visual-picker' | 'close-overlays'
  text?: string
  events?: EventStep[]
  expect: string
}

interface Journey {
  source: string
  evidence: string
  steps: JourneyStep[]
}

const journey = JSON.parse(readFileSync(new URL('./fixtures/journey.json', import.meta.url), 'utf8')) as Journey
const tick = () => new Promise<void>(resolve => setImmediate(resolve))
const painted = async () => { await tick(); await tick(); await tick() }

function tools(app: App) {
  return app.transcript.entries.flatMap(entry => entry.kind === 'turn'
    ? entry.blocks.flatMap(block => block.kind === 'tool' ? [block.call] : []) : [])
}

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

describe('RFC #510 14-step synthetic native journey', () => {
  it('replays the fixed stages in reference order without claiming a live Tern window', () => {
    expect(journey.source).toContain('#510')
    expect(journey.evidence).toContain('synthetic')
    expect(journey.steps.map(step => step.id)).toEqual([
      'fresh', 'prompt', 'thinking', 'read-search', 'write-edit', 'subagent',
      'queued-follow-up', 'approval', 'failure-recovery', 'completion',
      'model-picker', 'background-inspection', 'split-preview', 'back-to-chat'
    ])
    expect(new Set(journey.steps.map(step => step.id)).size).toBe(14)
  })

  it('drives App, owned gateway events and native overlays through all 14 stages', async () => {
    const input = new EventEmitter()
    const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
    const connecting = tern.handshake()
    input.emit('data', '\x1b_tsp;r;' + JSON.stringify({
      ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0'
    }) + '\x1b\\')
    expect(await connecting).toBe(true)

    const gw = new GatewayClient()
    const calls: { method: string; params: unknown }[] = []
    const request = vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
      calls.push({ method, params })
      if (method === 'prompt.submit') { return { status: 'accepted' } }
      if (method === 'complete.slash') { return { items: [] } }
      if (method === 'config.get') { return { value: 'queue' } }
      if (method === 'jobs.list') { return { jobs: [] } }
      if (method === 'model.options') {
        return {
          model: 'fixture-main', provider: 'fixture',
          providers: [{ slug: 'fixture', name: 'Fixture', authenticated: true, models: ['fixture-main', 'fixture-alt'] }]
        }
      }

      throw new Error('Unexpected synthetic journey RPC: ' + method)
    })
    const app = new App(tern, gw, 'test')
    app.sid = 'journey'
    app.info = { cwd: '/fixture', model: 'fixture-main', provider: 'fixture', branch: 'main' }
    acknowledgeFrames(tern)
    const running = app.run()
    const surface = tern.surfaces[0]!
    let current: View | undefined
    const render = surface.render.bind(surface)

    surface.render = next => {
      current = View.from(next)
      render(next)
    }

    const send = async (text: string) => {
      const action = surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text })
      expect(action).toBeTypeOf('function')
      await action?.()
      await painted()
    }
    const emit = async (event: EventStep) => {
      gw.emit('event', { type: event.type, session_id: 'journey', payload: event.payload })
      await painted()
    }
    const rows = () => current?.regions.flatMap(region => region?.children ?? []) ?? []
    const submitCount = () => calls.filter(call => call.method === 'prompt.submit').length

    try {
      await painted()

      for (const stage of journey.steps) {
        if (stage.intent === 'send') {
          await send(stage.text ?? '')
        } else if (stage.intent === 'approval') {
          const respond = vi.fn()
          gw.emit('request', {
            id: 'approval-journey', method: 'approval',
            params: { session_id: 'journey', request_id: 'approval-journey', command: 'printf fixture' },
            respond, fail: vi.fn()
          })
          await painted()
          expect(app.overlays.some(overlay => overlay.key.startsWith('prompt:'))).toBe(true)
          await emit({ type: 'approval.cancelled', payload: { request_ids: ['approval-journey'] } })
          expect(respond).not.toHaveBeenCalled()
          expect(app.overlays.some(overlay => overlay.key.startsWith('prompt:'))).toBe(false)
        } else if (stage.intent === 'model-picker') {
          // The queued follow-up receives a complete gateway lifecycle first.
          await emit({ type: 'message.start', payload: {} })
          await emit({ type: 'message.complete', payload: { status: 'complete', text: 'Follow-up completed.' } })
          app.composer.set('Unsent draft', 5)
          await app.slash('/model')
          await painted()
          expect(app.overlays.length).toBeGreaterThan(0)
          expect(calls.some(call => call.method === 'model.options')).toBe(true)
          expect(calls.some(call => call.method === 'config.set')).toBe(false)
          app.close(app.overlays.at(-1)!)
        } else if (stage.intent === 'jobs') {
          await app.slash('/jobs')
          await painted()
          expect(calls.some(call => call.method === 'jobs.list')).toBe(true)
        } else if (stage.intent === 'visual-picker') {
          // A fixture can inspect the picker; a real split needs Tern host receipts.
          await app.slash('/visual')
          await painted()
          expect(app.overlays.length).toBeGreaterThan(0)
          expect(calls.some(call => call.method === 'visual.publish')).toBe(false)
        } else if (stage.intent === 'close-overlays') {
          for (const overlay of [...app.overlays].reverse()) { app.close(overlay) }
          await painted()
        }

        for (const event of stage.events ?? []) { await emit(event) }

        switch (stage.id) {
          case 'fresh':
            expect(app.sid).toBe('journey')
            expect(app.busy).toBeNull()
            expect(rows().length).toBeGreaterThan(0)
            break
          case 'prompt':
            expect(submitCount()).toBe(1)
            expect(app.busy).not.toBeNull()
            expect(app.transcript.entries.some(entry => entry.kind === 'user' && entry.text === stage.text)).toBe(true)
            break
          case 'thinking':
            expect(app.transcript.live?.blocks.some(block => block.kind === 'thinking')).toBe(true)
            break
          case 'read-search':
            expect(tools(app).map(call => call.id)).toEqual(expect.arrayContaining(['read-1', 'search-1']))
            break
          case 'write-edit':
            expect(tools(app).map(call => call.id)).toEqual(expect.arrayContaining(['write-1', 'edit-1']))
            break
          case 'subagent':
            expect(tools(app).find(call => call.id === 'delegate-1')?.subagents?.[0]?.status).toBe('running')
            break
          case 'queued-follow-up':
            expect(app.queue).toEqual([stage.text])
            expect(submitCount()).toBe(1)
            break
          case 'failure-recovery':
            expect(tools(app).find(call => call.id === 'fail-1')?.result).toMatchObject({ exit_code: 2 })
            expect(tools(app).find(call => call.id === 'recover-1')?.result).toMatchObject({ exit_code: 0 })
            break
          case 'completion':
            expect(tools(app).find(call => call.id === 'delegate-1')?.subagents?.[0]?.status).toBe('done')
            expect(app.transcript.entries.some(entry => entry.kind === 'turn' && entry.status === 'done')).toBe(true)
            expect(submitCount()).toBe(2)
            break
          case 'background-inspection':
            expect(app.transcript.entries.some(entry => entry.kind === 'panel' && entry.text.includes('Background report'))).toBe(false)
            break
          case 'back-to-chat':
            expect(app.overlays).toHaveLength(0)
            expect(app.composer.text).toBe('Unsent draft')
            expect(app.composer.cursor).toBe(5)
            expect(submitCount()).toBe(2)
            break
        }
      }

      expect(journey.steps).toHaveLength(14)
    } finally {
      app.quit()
      await running
      request.mockRestore()
    }
  })
})
