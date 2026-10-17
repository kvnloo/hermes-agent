import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { AgentControlResult, AgentHubRow, AgentTranscriptResult, JobSnapshot } from '@hermes/shared/gateway-events'
import type { Surface, TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { openAgentInspector } from '../overlays/agent-inspector.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-agent-hub-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

type NativeNode = NonNullable<View['regions'][number]>['children'][number]
interface Fixture {
  agents: AgentHubRow[]
  jobs?: JobSnapshot[]
  page?(params: unknown): Promise<AgentTranscriptResult>
  control?(method: string): Promise<AgentControlResult>
}

const row = (extra: Partial<AgentHubRow> = {}): AgentHubRow => ({
  actions: { send: true, stop: true, transcript: true }, child_session_id: 'child-session',
  goal: 'Inspect alpha', id: 'child-session', parent_id: 'root', status: 'running', subagent_id: 'sa-alpha', ...extra
})

const flush = async () => {
  for (let i = 0; i < 8; i++) {
    await new Promise<void>(resolve => setImmediate(resolve))
  }
}

interface Harness {
  app: App
  gw: GatewayClient
  surface: Surface
  nodes(): NativeNode[]
  click(key: string): Promise<void>
  edit(text: string): Promise<void>
  select(id: string): Promise<void>
  event(type: string, session?: string): Promise<void>
  press(bytes: string): Promise<void>
  calls: { method: string; params: unknown }[]
}

async function withApp(fixture: Fixture, run: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const handshake = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await handshake).toBe(true)
  const gw = new GatewayClient()
  const calls: Harness['calls'] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    const handlers: Record<string, () => unknown> = {
      'complete.slash': () => ({ items: [] }),
      'jobs.list': () => ({ jobs: fixture.jobs ?? [] }),
      'subagent.hub': () => ({ agents: structuredClone(fixture.agents) }),
      'subagent.message': () => fixture.control?.(method) ?? { status: 'queued' },
      'subagent.stop': () => fixture.control?.(method) ?? { status: 'cancel_requested' },
      'subagent.transcript': () => fixture.page?.(params) ?? { available: true, child_session_id: 'child-session', messages: [{ content: 'Full stored reply', role: 'assistant' }], next_offset: null }
    }

    if (!handlers[method]) {
      throw new Error(`Unexpected hub RPC: ${method}`)
    }

    return handlers[method]()
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }
  const collect = (nodes: readonly NativeNode[]): NativeNode[] => nodes.flatMap(node => [node, ...collect(node.children)])
  const nodes = () => view.regions.flatMap(region => region ? collect(region.children) : [])

  const dispatch = async (event: TspEvent) => {
    const action = surface.dispatch(event)
    expect(action).toBeDefined()
    await action!()
    await flush()
  }

  try {
    await flush()
    await run({
      app, gw, surface, nodes, calls,
      click: async key => {
        const node = nodes().find(node => node.props.key === key && node.id.startsWith('layer.'))
        expect(node, `native ${key} action exists`).toBeDefined()
        await dispatch({ act: 'click', ev: 'action', id: node!.id, raw: {}, sf: 'hermes' })
      },
      edit: async text => {
        const node = nodes().find(node => node.props.role === 'omp.agent.input')!
        await dispatch({ cursor: text.length, ev: 'edit', from: 0, to: String(node.props.text).length, len: String(node.props.text).length, id: node.id, raw: {}, sf: 'hermes', text } as TspEvent)
      },
      select: async id => {
        const node = nodes().find(node => node.props.role === 'omp.agents.roster')!
        await dispatch({ ev: 'select', id: node.id, item: `${node.id}.${id}`, raw: {}, sf: 'hermes' })
      },
      event: async (type, session = 'session-1') => {
        gw.emit('event', { payload: {}, session_id: session, type })
        await flush()
      },
      press: async bytes => { input.emit('data', bytes); await flush() }
    })
  } finally {
    app.quit()
    await running
  }
}

const content = (h: Harness) => JSON.stringify(h.nodes().map(node => node.props))

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

describe('owned agent hub', () => {
  it('replaces /agents report with native roster, explicit flags, nested lineage and read-only full pages', async () => {
    const agents = [row(), row({ actions: { send: false, stop: false, transcript: true }, child_session_id: 'nested', goal: 'Nested child', id: 'nested', parent_id: 'sa-alpha' })]
    await withApp({ agents, page: async params => ({
      available: true, child_session_id: 'child-session',
      messages: [{ content: JSON.stringify(params).includes('"offset":50') ? 'second page tool result' : 'x'.repeat(20000), role: 'tool' }],
      next_offset: JSON.stringify(params).includes('"offset":50') ? null : 50
    }) }, async h => {
      h.app.composer.set('unsent parent draft', 4)
      await h.app.slash('/agents')
      await flush()
      expect(h.nodes().some(node => node.props.role === 'omp.overlay.agent-hub')).toBe(true)
      expect(content(h)).toContain('parent sa-alpha')
      expect(content(h)).toContain('x'.repeat(20000))
      expect(h.calls.some(call => call.method === 'slash.exec')).toBe(false)
      await h.click('next')
      expect(content(h)).toContain('second page tool result')
      expect(h.calls).toContainEqual({ method: 'subagent.transcript', params: { child_session_id: 'child-session', limit: 50, offset: 50, session_id: 'session-1' } })
      await h.press('\x03')
      expect(h.app.composer.text).toBe('unsent parent draft')
      await h.press('\x1b[27u')
      expect(h.app.overlays).toHaveLength(0)
      expect(h.app.composer.cursor).toBe(4)
      expect(h.calls.some(call => call.method === 'prompt.submit')).toBe(false)
    })
  })

  it('sends supported owned steering and preserves the child draft on rejection; stop is not terminal', async () => {
    const agents = [row()]
    let status: AgentControlResult['status'] = 'rejected'
    await withApp({ agents, control: async method => method === 'subagent.stop' ? { status: 'cancel_requested' } : { status } }, async h => {
      await h.app.slash('/agents')
      await flush()
      await h.edit('Change course')
      await h.click('send')
      expect(content(h)).toContain('Your draft was kept')
      expect(h.nodes().find(node => node.props.role === 'omp.agent.input')?.props.text).toBe('Change course')
      status = 'queued'
      await h.click('send')
      expect(h.calls).toContainEqual({ method: 'subagent.message', params: { child_session_id: 'child-session', session_id: 'session-1', subagent_id: 'sa-alpha', text: 'Change course' } })
      expect(content(h)).toContain('not yet delivered')
      expect(h.nodes().find(node => node.props.role === 'omp.agent.input')?.props.text).toBe('')
      await h.click('stop')
      expect(content(h)).toContain('waiting for terminal status')
      expect(content(h)).toContain('Status: running')
      agents[0] = row({ actions: { send: false, stop: false, transcript: true }, status: 'cancel_requested' })
      await h.event('subagent.progress')
      expect(content(h)).toContain('Status: cancel_requested')
      expect(h.nodes().some(node => node.props.key === 'stop')).toBe(false)
      agents[0] = row({ actions: { send: false, stop: false, transcript: true }, status: 'cancelled' })
      await h.event('subagent.complete')
      expect(content(h)).toContain('Status: cancelled')
    })
  })

  it.each(['idle', 'completed', 'unknown', 'foreign', 'advisor', 'aborted'])('honors backend flags for %s without inventing retry/revive', async status => {
    await withApp({ agents: [row({ actions: { send: false, stop: false, transcript: true }, status })] }, async h => {
      await h.app.slash('/agents')
      await flush()
      expect(content(h)).toContain(`Status: ${status}`)
      expect(h.nodes().some(node => node.id.startsWith('layer.') && (node.props.key === 'send' || node.props.key === 'stop'))).toBe(false)
      expect(content(h)).not.toMatch(/Retry in|Revive|Restart/)
      const calls = h.calls.length
      await h.event('subagent.progress', 'foreign-session')
      expect(h.calls).toHaveLength(calls)
    })
  })

  it('hydrates canonical inspector identity, refreshes streaming pages identically after completion and ignores stale visits', async () => {
    const agents = [row()]
    await withApp({ agents }, async h => {
      h.app.transcript.toolStart({ args: {}, name: 'delegate_task', tool_id: 'call' })
      h.app.transcript.subagent('subagent.start', { child_session_id: 'child-session', goal: 'Inspect alpha', subagent_id: 'sa-alpha', task_count: 1, task_index: 0 })
      openAgentInspector(h.app, { agentId: 'sa-alpha', callId: 'call' })
      await flush()
      expect(h.nodes().some(node => node.props.role === 'omp.overlay.agent-inspector')).toBe(true)
      const before = h.nodes().filter(node => node.props.key === 'content').map(node => node.props.text)
      agents[0] = row({ actions: { send: false, stop: false, transcript: true }, status: 'completed' })
      await h.event('subagent.complete')
      expect(h.nodes().filter(node => node.props.key === 'content').map(node => node.props.text)).toEqual(before)
      await h.click('close')
      const calls = h.calls.length
      await h.event('subagent.progress')
      expect(h.calls).toHaveLength(calls)
      expect(h.gw.listenerCount('event')).toBe(1)
    })
  })

  it('opens a gateway-known child from jobs without inferring authority from folded task rows', async () => {
    await withApp({ agents: [row()], jobs: [{ id: 'sa-alpha', kind: 'subagent', owner_session_id: 'session-1', started: 0, state: 'running', title: 'Inspect alpha', can_cancel: true }] }, async h => {
      h.app.composer.set('parent draft', 3)
      h.app.jobs.show()
      await flush()
      await h.click('inspect')
      expect(h.nodes().some(node => node.props.role === 'omp.overlay.agent-inspector')).toBe(true)
      expect(content(h)).toContain('Full stored reply')
      await h.click('close')
      expect(h.app.composer.text).toBe('parent draft')
      expect(h.app.composer.cursor).toBe(3)
    })
  })

  it('drops a delayed transcript after close or session replacement', async () => {
    const pending = Promise.withResolvers<AgentTranscriptResult>()
    await withApp({ agents: [row()], page: () => pending.promise }, async h => {
      await h.app.slash('/agents')
      await flush()
      await h.click('close')
      h.app.sid = 'replacement'
      pending.resolve({ available: true, child_session_id: 'child-session', messages: [{ role: 'assistant', content: 'STALE_PRIVATE_TRANSCRIPT' }], next_offset: null })
      await flush()
      expect(content(h)).not.toContain('STALE_PRIVATE_TRANSCRIPT')
      expect(h.app.overlays).toHaveLength(0)
      expect(h.calls.some(call => call.method === 'subagent.message')).toBe(false)
    })
  })

  it('shows stale exact selections as unavailable, never selects a different child', async () => {
    await withApp({ agents: [row()] }, async h => {
      const { openAgentHub } = await import('../overlays/agent-hub.js')
      openAgentHub(h.app, { subagentId: 'stale-id' })
      await flush()
      expect(content(h)).toContain('This agent is unavailable')
      expect(h.calls.some(call => call.method === 'subagent.transcript')).toBe(false)
      expect(h.nodes().some(node => node.id.startsWith('layer.') && node.props.key === 'send')).toBe(false)
    })
  })
})
