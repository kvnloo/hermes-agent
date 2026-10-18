import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { EvalCell, EvalView } from '@hermes/shared/gateway-events'
import { Session, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { evalOutputParts } from '../eval.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-eval-cells-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])

const cell = (id: string, output: string, extra: Partial<EvalCell> = {}): EvalCell => ({
  id, code: `# ${id}\nprint('literal')`, language: 'python', output, status: 'done', ...extra
})

async function withApp(check: (app: App, send: (type: string, payload: unknown) => void, nodes: () => Promise<Tree[]>, click: (target: Tree) => Promise<void>) => Promise<void>) {
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'complete.slash') { return { items: [] } }
    throw new Error(`Unexpected RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'eval-session'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => { latest = View.from(view); render(view) }
  const send = (type: string, payload: unknown) => gw.emit('event', { type, session_id: app.sid, payload })

  try {
    await check(app, send, async () => {
      app.changed()
      await rendered(); await rendered()

      return flatten(latest?.regions.find(region => region?.id === 'main')?.children ?? [])
    }, async target => {
      const action = surface.dispatch({ act: 'click', ev: 'action', id: target.id, raw: {}, sf: surface.id })

      if (!action) { throw new Error('Missing SDK disclosure action') }
      await action()
    })
  } finally {
    app.quit(); await running

    if (previousSplash === undefined) { delete process.env.HERMES_TUI_SPLASH }
    else { process.env.HERMES_TUI_SPLASH = previousSplash }
  }
}

function finish(send: (type: string, payload: unknown) => void, cells?: EvalCell[], extra: Record<string, unknown> = {}, id = 'call') {
  send('tool.start', { name: 'execute_code', tool_id: id, args: { code: '# original\nprint(1)' } })
  send('tool.complete', { name: 'execute_code', tool_id: id, result: {
    output: cells?.map(c => c.output ?? '').join('') ?? 'plain\ntext\n',
    ...(cells ? { eval_display: { version: 1, cells }, eval_revision: 10 } : {}), ...extra
  } })
}

const outputs = (nodes: Tree[]) => nodes.filter(n => n.props.role === 'omp.run.output').map(n => n.props.text).join('')
const statuses = (nodes: Tree[]) => nodes.filter(n => n.props.role === 'omp.tool.eval.status')

// This suite mounts the real App + SDK and drives gateway events, as settings.test.ts does.
describe('ordered eval cells', () => {
  it('renders explicit cells and mixed printed views in exact stdout order without changing the result', async () => {
    await withApp(async (app, send, nodes) => {
      const text = 'before\n{"a":1}\nbetween\n# Heading\na | b\n1 | 2\nafter\n'

      const views: EvalView[] = [
        { id: 'json', kind: 'json', start: text.indexOf('{'), printed: '{"a":1}\n' },
        { id: 'md', kind: 'markdown', start: text.indexOf('#'), printed: '# Heading\n' },
        { id: 'table', kind: 'table', start: text.indexOf('a |'), printed: 'a | b\n1 | 2\n', columns: ['a', 'b'], rows: [['1', '2']] }
      ]

      finish(send, [cell('one', text, { views }), cell('two', 'second\n')])
      const painted = await nodes()
      expect(painted.filter(n => n.props.role === 'omp.run').map(n => n.props.key)).toEqual(['one', 'two'])
      expect(painted.filter(n => ['omp.run.output', 'omp.tool.eval.json', 'omp.tool.eval.markdown', 'omp.tool.eval.table'].includes(String(n.props.role))).map(n => n.kind)).toEqual(['code', 'code', 'code', 'md', 'table', 'code', 'code'])
      const turn = app.transcript.entries.find(e => e.kind === 'turn')
      const call = turn?.blocks.find(b => b.kind === 'tool')?.call
      expect(call?.id).toBe('call')
      expect((call?.result as { output: string }).output).toBe(text + 'second\n')
    })
  })

  it('keeps nested running/failed work outside output folds and retains event IDs', async () => {
    await withApp(async (app, send, nodes, click) => {
      send('tool.start', { name: 'execute_code', tool_id: 'call' })

      const runningCell = cell('live', Array.from({ length: 20 }, (_, i) => `line ${i}\n`).join(''), { status: 'running', events: [
        { id: 'parent', tool: 'terminal', status: 'running' },
        { id: 'nested', parent_id: 'parent', tool: 'read', status: 'error' }
      ] })

      send('eval.update', { tool_id: 'call', revision: 1, cell: runningCell })
      const painted = await nodes()
      expect(statuses(painted)).toHaveLength(2)
      const parent = painted.find(n => n.props.key === 'parent')
      expect(flatten(parent?.children ?? []).some(n => n.props.key === 'nested')).toBe(true)
      expect(outputs(painted)).not.toContain('line 19')
      expect(painted.find(n => n.props.role === 'omp.run.state')?.props.spans).toEqual([{ s: 'pending', t: 'running' }])
      expect(app.transcript.live?.blocks).toHaveLength(1)
      const toggle = painted.find(n => n.props.role === 'omp.run.toggle')

      if (!toggle) { throw new Error('Missing output disclosure') }
      await click(toggle)
      const expanded = await nodes()
      expect(outputs(expanded)).toContain('line 19')
      expect(statuses(expanded)).toHaveLength(2)
    })
  })

  it('never manufactures cells or typed views from arbitrary stdout without metadata', async () => {
    await withApp(async (_app, send, nodes) => {
      finish(send, undefined, { output: '{"a":1}\n# Not a cell\n┌ table ┐\n' })
      const painted = await nodes()
      expect(painted.filter(n => n.props.role === 'omp.run')).toHaveLength(1)
      expect(painted.some(n => n.kind === 'md' || n.kind === 'table')).toBe(false)
      expect(outputs(painted)).toBe('{"a":1}\n# Not a cell\n┌ table ┐\n')
    })
  })

  it('skips unmatched, overlapping, malformed and capture-truncated view spans', async () => {
    await withApp(async (_app, send, nodes) => {
      finish(send, [cell('clipped', 'lost\n{"a":1}\n', { views: [
        { id: 'missing', kind: 'json', start: 0, printed: '{"a":1}\n' }
      ] })], { output: '[tool result truncated]\n{"a":1}\n', stdout_truncated: true })
      const painted = await nodes()
      expect(outputs(painted)).toBe('[tool result truncated]\n{"a":1}\n')
      expect(painted.some(n => n.props.role === 'omp.tool.eval.json')).toBe(false)
      expect(evalOutputParts('xx', [{ id: 'bad', kind: 'markdown', start: 0, printed: 'missing' }])).toEqual([{ kind: 'text', key: 'text-0', text: 'xx' }])
    })
  })

  it('keeps valid spans while skipping malformed, unmatched and overlapping view entries', async () => {
    await withApp(async (_app, send, nodes) => {
      finish(send, [cell('safe', 'before\n{}\nafter\n', { views: [
        { id: 'wrong', kind: 'markdown', start: 0, printed: 'not present' },
        { id: 'valid', kind: 'json', start: 7, printed: '{}\n' },
        { id: 'overlap', kind: 'markdown', start: 8, printed: '}\n' }
      ] })])
      const painted = await nodes()
      expect(painted.filter(n => n.props.role === 'omp.tool.eval.json')).toHaveLength(1)
      expect(painted.some(n => n.props.role === 'omp.tool.eval.markdown')).toBe(false)
      expect(outputs(painted)).toBe('before\nafter\n')
    })
  })

  it('rejects malformed optional metadata and leaves literal output unchanged', async () => {
    await withApp(async (_app, send, nodes) => {
      finish(send, undefined, { output: 'literal\n', eval_display: { version: 1, cells: [{ id: 'bad', code: 123, status: 'done' }] } })
      expect(outputs(await nodes())).toBe('literal\n')
    })
  })

  it('replaces only the addressed occurrence and handles Unicode code-point offsets', () => {
    const output = '😀\n{}\n{}\n'
    const parts = evalOutputParts(output, [{ id: 'second', kind: 'json', start: 5, printed: '{}\n' }])
    expect(parts).toEqual([{ kind: 'text', key: 'text-0', text: '😀\n{}\n' }, { kind: 'view', key: 'second', view: { id: 'second', kind: 'json', start: 5, printed: '{}\n' } }])
  })

  it.each(['error', 'timeout', 'background'] as const)('keeps the %s outcome and errors visible', async status => {
    await withApp(async (_app, send, nodes) => {
      finish(send, [cell('outcome', 'retained\n', { status, error: status === 'background' ? undefined : 'real failure' })], { status })
      const painted = await nodes()
      expect(painted.find(n => n.kind === 'tool')?.props.status).toBe(status)
      expect(painted.find(n => n.props.role === 'omp.run.state')?.props.spans).toEqual([{ s: status === 'error' ? 'error' : status === 'timeout' ? 'warning' : 'pending', t: status }])

      if (status !== 'background') { expect(painted.some(n => n.props.role === 'omp.tool.error')).toBe(true) }
    })
  })

  it('applies late exact-call events to retained turns, rejects stale replay and running regressions', async () => {
    await withApp(async (app, send, nodes) => {
      finish(send, [cell('old', 'old\n')])
      send('message.complete', { status: 'completed' })
      send('message.start', {})
      send('eval.update', { tool_id: 'call', revision: 11, cell: cell('old', 'old\n', { events: [{ id: 'last', tool: 'terminal', status: 'done' }] }) })
      send('eval.update', { tool_id: 'call', revision: 1, cell: cell('old', '', { status: 'running' }) })
      send('eval.update', { tool_id: 'call', revision: 12, cell: cell('old', '', { status: 'running' }) })
      send('eval.update', { tool_id: 'foreign', revision: 100, cell: cell('foreign', 'bad') })
      send('tool.complete', { tool_id: 'call', name: 'execute_code', result: { output: 'old\n', eval_revision: 10, eval_display: { version: 1, cells: [cell('old', 'old\n')] } } })
      expect(statuses(await nodes())).toHaveLength(1)
      expect(app.transcript.live?.blocks).toHaveLength(0)
    })
  })

  it('sanitizes displayed structured cells only after matching their literal printed spans', async () => {
    await withApp(async (app, send, nodes) => {
      const printed = '# Saved\x1b[31m\x07\n'
      const output = `before\x07\n${printed}after\x07\n`
      finish(send, [cell('sanitized', output, { views: [{ id: 'safe-view', kind: 'markdown', start: 8, printed }] })])
      const painted = await nodes()
      expect(painted.find(n => n.props.role === 'omp.tool.eval.markdown')?.props.text).toBe('# Saved\n')
      expect(outputs(painted)).toBe('before\\u0007\nafter\\u0007\n')
      const turn = app.transcript.entries.find(entry => entry.kind === 'turn')
      const tool = turn?.kind === 'turn' ? turn.blocks.find(block => block.kind === 'tool') : undefined
      expect(tool?.call.eval?.cells[0]?.output).toBe(output)
    })
  })

  it('uses the same typed rendering for resumed result JSON and persisted display metadata', async () => {
    await withApp(async (app, _send, nodes) => {
      const data = cell('resumed-cell', '# Saved\n', { views: [{ id: 'saved-view', kind: 'markdown', start: 0, printed: '# Saved\n' }] })
      app.transcript.load([{ role: 'tool', tool_call_id: 'saved-call', name: 'execute_code', content: JSON.stringify({ output: data.output }), display_metadata: { tool_result_metadata: { eval_display: { version: 1, cells: [data] } } } }])
      const painted = await nodes()
      const turn = app.transcript.entries.find(entry => entry.kind === 'turn')
      expect(turn?.kind === 'turn' && turn.blocks.find(block => block.kind === 'tool')?.call.id).toBe('saved-call')
      expect(painted.find(n => n.kind === 'tool')?.props.name).toBe('eval')
      expect(painted.find(n => n.props.role === 'omp.tool.eval.markdown')?.props.text).toBe('# Saved\n')
    })
  })
})

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }
  rmSync(isolated.home, { force: true, recursive: true })
})
