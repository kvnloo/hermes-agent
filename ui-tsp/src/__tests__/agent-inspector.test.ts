import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { JobSnapshot, SubagentEventPayload } from '@hermes/shared/gateway-events'
import type { Surface, TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-agent-inspector-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

async function rendered() {
  for (let i = 0; i < 5; i++) {
    await new Promise<void>(resolve => setImmediate(resolve))
  }
}

type NativeNode = NonNullable<View['regions'][number]>['children'][number]

interface Harness {
  app: App
  surface: Surface
  nodes(region?: number): NativeNode[]
  inspector(): NativeNode[]
  event(type: string, payload: Record<string, unknown>): Promise<void>
  agent(type: string, extra?: Partial<SubagentEventPayload>): Promise<void>
  delegate(callId: string, delegationId: string): Promise<void>
  click(node: NativeNode | undefined): Promise<void>
  press(bytes: string): Promise<void>
  requests: string[]
  focus: ReturnType<typeof vi.spyOn>
  scroll: ReturnType<typeof vi.spyOn>
}

async function withApp(run: (h: Harness) => Promise<void>, jobs: JobSnapshot[] = []) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const requests: string[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    requests.push(method)

    const handlers: Record<string, () => unknown> = {
      'complete.slash': () => ({ items: [] }),
      'jobs.list': () => ({ jobs }),
      'jobs.tail': () => ({ available: true, job_id: (params as { job_id: string }).job_id, text: '', truncated: false })
    }

    if (!handlers[method]) {
      throw new Error(`Unexpected inspector RPC: ${method}`)
    }

    return handlers[method]()
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface: Surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }
  const focus = vi.spyOn(surface, 'focus')
  const scroll = vi.spyOn(surface, 'scroll')
  const collect = (children: readonly NativeNode[]): NativeNode[] => children.flatMap(node => [node, ...collect(node.children)])

  const nodes = (region?: number) => region === undefined
    ? view.regions.flatMap(region => region ? collect(region.children) : [])
    : collect(view.regions[region]?.children ?? [])

  const event = async (type: string, payload: Record<string, unknown>) => {
    gw.emit('event', { payload, session_id: app.sid, type })
    await rendered()
  }

  try {
    await rendered()
    await run({
      app, surface, nodes, requests, focus, scroll, event,
      inspector: () => {
        const sheet = nodes(2).find(node => node.props.role === 'omp.overlay.agent-inspector')
        expect(sheet, 'the clicked agent must open its inspector').toBeDefined()

        return collect(sheet!.children)
      },
      agent: (type, extra = {}) => event(type, {
        delegation_id: 'delegation-a', goal: 'Audit alpha', model: 'model-alpha', task_count: 2, task_index: 0, ...extra
      }),
      delegate: async (callId, delegationId) => {
        await event('tool.start', { args: { tasks: [{ goal: 'Audit alpha' }, { goal: 'Audit beta' }] }, name: 'delegate_task', tool_id: callId })
        await event('tool.complete', { name: 'delegate_task', result: { delegation_id: delegationId, status: 'dispatched' }, tool_id: callId })
      },
      click: async node => {
        expect(node, 'native clickable node must exist').toBeDefined()
        const action = surface.dispatch({ act: 'click', ev: 'action', id: node!.id, raw: {}, sf: 'hermes' })
        expect(action, 'native node must have an action handler').toBeDefined()
        await action!()
        await rendered()
      },
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

const text = (nodes: NativeNode[]) => JSON.stringify(nodes.map(node => node.props))
const agentRow = (h: Harness, callId = 'call-a', id = 'task-0') => h.nodes(0).find(node => node.kind === 'agent' && node.id.includes(`.${callId}.`) && node.props.key === id)

async function seed(h: Harness) {
  await h.delegate('call-a', 'delegation-a')
  await h.agent('subagent.start')
  await h.agent('subagent.tool', { api_calls: 3, input_tokens: 100, output_tokens: 20, tool_count: 1, tool_name: 'read', tool_preview: 'alpha.ts' })
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

describe('read-only subagent inspector', () => {
  it('opens the clicked delegation/task identity and excludes other agents and delegations', async () => {
    await withApp(async h => {
      await seed(h)
      await h.agent('subagent.tool', { goal: 'Audit beta', task_index: 1, tool_name: 'bash', tool_preview: 'foreign-beta' })
      await h.delegate('call-b', 'delegation-b')
      await h.agent('subagent.tool', { delegation_id: 'delegation-b', tool_name: 'edit', tool_preview: 'foreign-delegation' })
      await h.click(agentRow(h))
      const content = text(h.inspector())
      expect(content).toContain('Audit alpha')
      expect(content).toContain('Model: model-alpha')
      expect(content).toContain('Status: running')
      expect(content).toContain('3 requests · 120 tokens · 1 tools')
      expect(content).toContain('alpha.ts')
      expect(content).not.toContain('foreign-beta')
      expect(content).not.toContain('foreign-delegation')
      await h.agent('subagent.progress', { task_index: 1, text: 'later foreign note' })
      expect(text(h.inspector())).not.toContain('later foreign note')
      expect(h.requests.some(method => method === 'subagent.interrupt' || method === 'prompt.submit')).toBe(false)
    })
  })

  it('shows two additional tool events and notes live without reopening or fetching', async () => {
    await withApp(async h => {
      await seed(h)
      await h.click(agentRow(h))
      const sheet = h.app.overlays.at(-1)
      const requests = [...h.requests]
      await h.agent('subagent.tool', { tool_count: 2, tool_name: 'bash', tool_preview: 'npm test' })
      await h.agent('subagent.tool', { tool_count: 3, tool_name: 'edit', tool_preview: 'fix alpha.ts' })
      await h.agent('subagent.progress', { text: 'Verified alpha' })
      expect(h.inspector().filter(node => node.props.role === 'omp.agent.tool')).toHaveLength(3)
      expect(text(h.inspector())).toContain('npm test')
      expect(text(h.inspector())).toContain('fix alpha.ts')
      expect(text(h.inspector())).toContain('Verified alpha')
      expect(h.app.overlays.at(-1)).toBe(sheet)
      expect(h.requests).toEqual(requests)
    })
  })

  it('restores the exact draft/cursor and composer focus on Escape or Close without scrolling main', async () => {
    await withApp(async h => {
      await seed(h)
      h.app.composer.set('unsent 🐈 draft\nsecond line', 7)
      h.app.changed()
      await rendered()
      const mainIds = h.nodes(0).map(node => node.id)
      const input = h.nodes(1).find(node => node.kind === 'editor')!
      const draft = { cursor: h.app.composer.cursor, text: h.app.composer.text }

      for (const close of ['escape', 'click']) {
        await h.click(agentRow(h))
        expect(h.focus).toHaveBeenLastCalledWith(null)
        await h.press('ignored\x1b[13u')
        // Late native composer edits/submissions must not mutate a read-only visit.
        await h.surface.dispatch({ ev: 'edit', id: input.id, raw: {}, sf: 'hermes', text: 'stale edit', cursor: 0 } as TspEvent)?.()
        await h.surface.dispatch({ ev: 'send', id: input.id, raw: {}, sf: 'hermes', text: 'stale send' } as TspEvent)?.()
        await h.press('\x1b[6~')
        expect(h.scroll).toHaveBeenLastCalledWith(expect.stringMatching(/^layer\.agent-inspector:.*\.body\.activity$/), 'page-down')

        if (close === 'escape') {
          await h.press('\x1b[27u')
        } else {
          await h.click(h.inspector().find(node => node.props.key === 'close'))
        }

        expect(h.app.composer.text).toBe(draft.text)
        expect(h.app.composer.cursor).toBe(draft.cursor)
        expect(h.focus).toHaveBeenLastCalledWith(input.id)
        expect(h.nodes(0).map(node => node.id)).toEqual(mainIds)
      }

      expect(h.scroll.mock.calls.every(([id]: [unknown]) => String(id).startsWith('layer.agent-inspector:'))).toBe(true)
      expect(h.requests).not.toContain('prompt.submit')
    })
  })

  it.each(['completed', 'failed', 'interrupted'] as const)('survives completion and shows final %s status and summary', async status => {
    await withApp(async h => {
      await seed(h)
      await h.click(agentRow(h))
      const sheet = h.app.overlays.at(-1)
      await h.event('message.complete', { status: 'completed' })
      await h.agent('subagent.complete', { api_calls: 5, duration_seconds: 12, status, summary: 'Final audit result', tool_count: 4 })
      expect(h.app.overlays.at(-1)).toBe(sheet)
      expect(text(h.inspector())).toContain(`Status: ${{ completed: 'done', failed: 'failed', interrupted: 'cancelled' }[status]}`)
      expect(text(h.inspector())).toContain('Final audit result')
      expect(text(h.inspector())).toContain('5 requests · 120 tokens · 4 tools')
      expect(text(h.inspector())).toContain('12s')
      expect(text(h.inspector())).toContain('alpha.ts')
    })
  })

  it.each(['activate', 'button'] as const)('opens a known subagent from jobs %s and Close goes directly back to composer', async mode => {
    const jobs: JobSnapshot[] = [{ id: 'child-alpha', kind: 'subagent', owner_session_id: 'session-1', started: 123, state: 'running', title: 'Audit alpha' }]
    await withApp(async h => {
      await h.delegate('call-a', 'delegation-a')
      await h.agent('subagent.start', { subagent_id: 'child-alpha' })
      h.app.composer.set('jobs draft', 3)
      h.app.jobs.show()
      await rendered()
      const list = h.nodes(2).find(node => node.props.role === 'omp.jobs.list')!

      if (mode === 'activate') {
        await h.surface.dispatch({ ev: 'activate', id: list.id, item: `${list.id}.child-alpha`, raw: {}, sf: 'hermes' })?.()
      } else {
        await h.click(h.nodes(2).find(node => node.props.key === 'inspect'))
      }

      await rendered()
      expect(text(h.inspector())).toContain('child-alpha')
      expect(text(h.inspector())).not.toContain('Cancel job')
      await h.press('\x1b[27u')
      expect(h.app.overlays).toHaveLength(0)
      expect(h.app.composer.text).toBe('jobs draft')
      expect(h.app.composer.cursor).toBe(3)
    }, jobs)
  })
})
