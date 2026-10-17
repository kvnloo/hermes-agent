import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { TranscriptMessage } from '@hermes/shared/gateway-events'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-resume-fidelity-'))
  const previous = process.env.HERMES_HOME
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, previousSplash }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  if (isolated.previousSplash === undefined) {
    delete process.env.HERMES_TUI_SPLASH
  } else {
    process.env.HERMES_TUI_SPLASH = isolated.previousSplash
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))

type RenderedNode = NonNullable<View['regions'][number]>['children'][number]

async function withApp(messages: TranscriptMessage[], check: (app: App, gw: GatewayClient, cards: () => RenderedNode[]) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  acknowledgeFrames(tern)
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const requests = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'session.resume') {
      return { session_id: 'resumed', messages, info: { stored_session_id: 'stored' } }
    }

    if (method === 'session.close' || method === 'complete.slash') {
      return { items: [] }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'initial'
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let view: View | undefined

  surface.render = value => {
    view = View.from(value)
    render(value)
  }

  const cards = () => {
    const found: RenderedNode[] = []

    const walk = (n: RenderedNode) => {
      if (n.kind === 'tool') {
        found.push(n)
      }

      for (const child of n.children) {
        walk(child)
      }
    }

    for (const region of view?.regions ?? []) {
      for (const child of region?.children ?? []) {
        walk(child)
      }
    }

    return found
  }

  try {
    await check(app, gw, cards)
  } finally {
    app.quit()
    await running
    requests.mockRestore()
  }
}

function shape(n: RenderedNode): unknown {
  return { kind: n.kind, props: n.props, children: n.children.map(shape) }
}

function byRole(n: RenderedNode, role: string): RenderedNode | undefined {
  if (n.props.role === role) {
    return n
  }

  for (const child of n.children) {
    const found = byRole(child, role)

    if (found) {
      return found
    }
  }

  return undefined
}

function tool(name: string, args: Record<string, unknown>, content?: unknown, extra: Partial<TranscriptMessage> = {}): TranscriptMessage {
  return { role: 'tool', tool_call_id: 'call', name, args, ...(content !== undefined ? { content } : {}), ...extra }
}

describe('resume tool-card fidelity', () => {
  it('renders the same failed bash card as live completion, including output tail and exit 2', async () => {
    const args = { command: 'npm test' }
    const result = { output: Array.from({ length: 20 }, (_, i) => `line ${i}`).join('\n'), exit_code: 2, duration_s: 1.25 }
    await withApp([tool('terminal', args, JSON.stringify(result))], async (app, gw, cards) => {
      // A late completion has no observed start; neither path may synthesize timing.
      gw.emit('event', { type: 'tool.complete', session_id: 'initial', payload: { tool_id: 'call', name: 'terminal', args, result } })
      gw.emit('event', { type: 'message.complete', session_id: 'initial', payload: { status: 'completed' } })
      await rendered()
      const live = cards()[0]!
      expect(live.props).toMatchObject({ name: 'bash', status: 'error', exit: 2 })
      expect(live.props.preview).toBeUndefined()
      expect(live.props.took).toBeUndefined()
      await app.resume('stored')
      await rendered()
      expect(cards()).toHaveLength(1)
      expect(shape(cards()[0]!)).toEqual(shape(live))
      expect(JSON.stringify(shape(cards()[0]!))).toContain('line 10\\nline 11')
      expect(JSON.stringify(shape(cards()[0]!))).toContain('truncated: showing last 10 lines')
    })
  })

  it('preserves real live run-box output and outcome on resume, but not observed-only timing', async () => {
    const args = { command: 'npm test' }
    const result = { output: Array.from({ length: 20 }, (_, i) => `line ${i}`).join('\n'), exit_code: 2 }

    await withApp([tool('terminal', args, result)], async (app, gw, cards) => {
      gw.emit('event', { type: 'tool.start', session_id: 'initial', payload: { tool_id: 'call', name: 'terminal', args } })
      gw.emit('event', { type: 'tool.complete', session_id: 'initial', payload: { tool_id: 'call', name: 'terminal', result } })
      gw.emit('event', { type: 'message.complete', session_id: 'initial', payload: { status: 'completed' } })
      await rendered()
      const live = cards()[0]!
      expect(live.props.took).toEqual(expect.any(Number))
      expect(live.props).toMatchObject({ status: 'error', exit: 2 })

      await app.resume('stored')
      await rendered()
      const resumed = cards()[0]!
      expect(resumed.props).toMatchObject({ status: live.props.status, exit: live.props.exit })
      expect(resumed.props.took).toBeUndefined()

      for (const role of ['omp.run.input', 'omp.run.output', 'omp.run.state']) {
        expect(shape(byRole(resumed, role)!)).toEqual(shape(byRole(live, role)!))
      }
    })
  })

  it('restores read paths and search matches without inventing duration', async () => {
    const messages = [
      tool('read_file', { path: 'src/main.ts' }, JSON.stringify({ content: '1|const answer = 42', total_lines: 1 }), { tool_call_id: 'read' }),
      tool('search_files', { path: 'src', pattern: 'answer' }, { total_count: 1, matches: [{ path: 'src/main.ts', line: 1, content: 'const answer = 42' }] }, { tool_call_id: 'search' })
    ]

    await withApp(messages, async (app, _gw, cards) => {
      await app.resume('stored')
      await rendered()
      expect(cards()).toHaveLength(2)
      expect(cards()[0]!.props).toMatchObject({ name: 'read', target: 'src/main.ts' })
      expect(cards()[0]!.props.took).toBeUndefined()
      expect(JSON.stringify(shape(cards()[1]!))).toContain('const answer = 42')
      expect(JSON.stringify(shape(cards()[1]!))).toContain('src/main.ts')
      expect(cards()[1]!.props.status).toBe('done')
    })
  })

  it.each(['terminal', 'execute_code'])('shows no result recorded rather than an empty success for %s', async name => {
    await withApp([tool(name, { command: 'lost command', code: 'lost code' })], async (app, _gw, cards) => {
      await app.resume('stored')
      await rendered()
      expect(cards()).toHaveLength(1)
      expect(cards()[0]!.props.note).toBe('no result recorded')
      expect(cards()[0]!.props.status).not.toBe('done')
      expect(cards()[0]!.props.took).toBeUndefined()
      expect(cards()[0]!.props.exit).toBeUndefined()
      const missing = JSON.stringify(shape(cards()[0]!))
      expect(missing).toContain('no result recorded')
      expect(missing).not.toContain('"t":"ok"')
      expect(missing).toContain('"tone":"muted"')
    })
  })

  it('restores interruption, persisted edit previews and final todo snapshots', async () => {
    await withApp([
      tool('terminal', {}, { exit_code: 130, output: 'partial\n[Command interrupted]' }, { tool_call_id: 'cancel' }),
      tool('patch', { path: 'src/main.ts' }, '{}', { tool_call_id: 'edit', display_metadata: { tool_result_metadata: { inline_diff: '@@ -1 +1 @@\n-old\n+new' } } }),
      tool('tool_call', { name: 'todo_list', arguments: { todos: [{ id: '1', content: 'Do work', status: 'pending' }] } }, JSON.stringify({ todos: [{ id: '1', content: 'Do work', status: 'completed' }] }), { tool_call_id: 'todo' })
    ], async (app, _gw, cards) => {
      await app.resume('stored')
      await rendered()
      expect(cards()[0]!.props.status).toBe('cancelled')
      expect(cards()[0]!.props.exit).toBeUndefined()
      expect(cards()[0]!.props.took).toBeUndefined()
      expect(JSON.stringify(shape(cards()[0]!))).toContain('cancelled')
      expect(JSON.stringify(shape(cards()[0]!))).not.toContain('after ')
      expect(JSON.stringify(shape(cards()[1]!))).toContain('+new')
      expect(JSON.stringify(shape(cards()[2]!))).toContain('"status":"done"')
    })
  })
})
