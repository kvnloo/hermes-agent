import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { LspQueryResult, LspSymbol } from '@hermes/shared/gateway-events'
import { node, Session, type Surface, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { localCommand } from '../commands.js'
import { parseLspResult } from '../lsp-result.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-lsp-semantic-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME }
  else { process.env.HERMES_HOME = isolated.previous }

  rmSync(isolated.home, { force: true, recursive: true })
})

const tick = async () => { await new Promise<void>(resolve => setImmediate(resolve)); await new Promise<void>(resolve => setImmediate(resolve)) }
const descendants = (root: Tree): Tree[] => [root, ...root.children.flatMap(descendants)]
const byRole = (nodes: Tree[], role: string) => nodes.filter(node => node.props.role === role)
const base = { path: '/project/src/a.py', server: 'mock-semantic', position_encoding: 'utf-16' as const }
const span = { start: { line: 2, col: 3 }, end: { line: 4, col: 5 } }
const target = (path: string) => ({ path, range: span })
const symbol = (id: string, name: string, children: LspSymbol[] = []): LspSymbol => ({ id, name, kind: 5, location: target(base.path), selection: span, children })

interface Harness {
  app: App
  surface: Surface
  gw: GatewayClient
  nodes(): Tree[]
  show(result: unknown, replay?: boolean): Promise<Tree[]>
}

async function withApp(run: (h: Harness) => Promise<void>, reply?: () => Promise<unknown>, width = 80) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0', cols: width, rows: 28 })}\x1b\\`)

  if (!await connecting) { throw new Error('SDK fixture handshake failed') }
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'complete.slash') { return { items: [] } }

    if (method === 'lsp.query' && reply) { return reply() }
    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'lsp-fixture'
  app.info = { cwd: '/project', model: 'fixture', terminal_backend: 'local' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => { latest = View.from(view); render(view) }
  const nodes = () => latest?.regions.flatMap(region => region?.children.flatMap(descendants) ?? []) ?? []

  try {
    await run({ app, surface, gw, nodes, show: async (result, replay = false) => {
      if (replay) {
        app.transcript.load([{ role: 'tool', tool_call_id: 'lsp-1', name: 'lsp', args: { operation: 'symbols' }, content: JSON.stringify(result) }])
      } else {
        app.transcript.toolStart({ name: 'lsp', tool_id: 'lsp-1', args: { operation: 'symbols' } }, 1)
        app.transcript.toolComplete({ name: 'lsp', tool_id: 'lsp-1', result }, 2)
        app.transcript.complete({ status: 'complete', text: '' }, 3)
      }

      app.changed()
      await tick()

      return nodes()
    } })
  } finally { app.quit(); await running }
}

describe('native semantic LSP results', () => {
  it('groups cross-file references and preserves openable complete source ranges', async () => {
    await withApp(async h => {
      const nodes = await h.show({ lsp_result: { ...base, kind: 'references', locations: [target(base.path), target('/project/src/b.py'), target(base.path)] } })
      expect(byRole(nodes, 'omp.tool.references.file')).toHaveLength(2)
      expect(byRole(nodes, 'omp.tool.reference').map(node => node.props.href)).toEqual([
        'file:///project/src/a.py#L2-L4', 'file:///project/src/a.py#L2-L4', 'file:///project/src/b.py#L2-L4'
      ])
      expect(byRole(nodes, 'omp.tool.reference').every(node => node.props.text === '2:3–4:5')).toBe(true)
    })
  })

  it('keeps nested stable native symbol items through stored-result replay', async () => {
    const result: LspQueryResult = { lsp_result: { ...base, kind: 'symbols', symbols: [symbol('outer', 'Outer', [symbol('child', 'method')])] } }
    await withApp(async h => {
      const live = byRole(await h.show(result), 'omp.tool.symbols')[0]!
      const replayed = byRole(await h.show(result, true), 'omp.tool.symbols')[0]!
      expect(replayed.props.nodes).toEqual(live.props.nodes)
      expect(replayed.props.nodes).toMatchObject([{ id: 'outer', open: true, children: [{ id: 'child', label: [{ t: 'method', href: 'file:///project/src/a.py#L2-L4' }, {}] }] }])
    })
  })

  it.each(['references', 'symbols', 'hover'] as const)('distinguishes checked-empty %s from server failure and unavailability', async kind => {
    await withApp(async h => {
      const data = { references: { locations: [] }, symbols: { symbols: [] }, hover: { contents: [], range: null } }[kind]
      const empty = await h.show({ lsp_result: { ...base, kind, ...data } })
      expect(byRole(empty, 'omp.tool.lsp.summary')[0]?.props.text).toContain('(checked)')

      for (const failure of ['error', 'unavailable']) {
        const nodes = await h.show({ lsp_result: { ...base, kind: failure, operation: kind, message: 'index failed' } }, true)
        expect(byRole(nodes, `omp.tool.lsp.${failure}`)[0]?.props.text).toBe(`${kind}: index failed`)
        expect(byRole(nodes, 'omp.tool.lsp.summary')).toHaveLength(0)
        expect(nodes.find(node => node.kind === 'tool')?.props.status).toBe(failure === 'error' ? 'error' : 'done')
      }
    })
  })

  it.each([40, 80])('retains long paths, labels, every reference and hover source at width %s', async width => {
    await withApp(async h => {
      const long = 'long-label-'.repeat(100)
      const nodes = await h.show({ lsp_result: { ...base, path: `/project/${long}.py`, kind: 'references', locations: Array.from({ length: 250 }, () => target(base.path)) } })
      expect(byRole(nodes, 'omp.tool.reference')).toHaveLength(250)
      expect(nodes.some(node => node.props.text === `/project/${long}.py` && node.props.wrap === 'word')).toBe(true)
      const symbols = await h.show({ lsp_result: { ...base, kind: 'symbols', symbols: [symbol('long', long)] } }, true)
      expect(byRole(symbols, 'omp.tool.symbols')[0]?.props.nodes).toMatchObject([{ label: [{ t: long }, {}] }])

      const hover = await h.show({ lsp_result: { ...base, kind: 'hover', range: span, contents: [
        { format: 'markdown', text: `**${long}**`, language: null }, { format: 'plaintext', text: '<literal>', language: null }, { format: 'code', text: 'def fn(): pass', language: 'python' }
      ] } }, true)

      expect(byRole(hover, 'omp.tool.hover').map(node => node.kind)).toEqual(['md', 'text', 'code'])
      expect(byRole(hover, 'omp.tool.hover')[1]?.props).toMatchObject({ text: '<literal>', wrap: 'word' })
      expect(byRole(hover, 'omp.tool.hover')[2]?.props).toMatchObject({ lang: 'python', wrap: true })
    }, undefined, width)
  })

  it('falls back honestly for malformed or legacy semantic data', async () => {
    await withApp(async h => {
      for (const result of [{ text: '12 references' }, { lsp_result: { ...base, kind: 'references', locations: [{ path: 'bad.py', range: { start: { line: -1, col: 0 }, end: { line: 2, col: 1 } } }] } }]) {
        const nodes = await h.show(result, true)
        expect(byRole(nodes, 'omp.tool.reference')).toHaveLength(0)
        expect(nodes.some(node => node.kind === 'code' && node.props.text === JSON.stringify(result))).toBe(true)
      }

      expect(parseLspResult({ ...base, kind: 'symbols', symbols: [symbol('dup', 'A'), symbol('dup', 'B')] })).toBeUndefined()
    })
  })

  it('removes file links on remote stored-result replay', async () => {
    await withApp(async h => {
      h.app.info = { ...h.app.info, terminal_backend: 'ssh' }
      const nodes = await h.show({ lsp_result: { ...base, kind: 'references', locations: [target(base.path)] } }, true)
      expect(byRole(nodes, 'omp.tool.reference')[0]?.props.href).toBeUndefined()
      expect(byRole(nodes, 'omp.tool.notice')[0]?.props.text).toContain('links disabled')
    })
  })

  it('sends one explicit query and Close preserves the composer draft and main identity', async () => {
    await withApp(async h => {
      h.app.composer.set('unsent draft')
      h.app.changed()
      await tick()
      const main = h.nodes().find(node => node.id === 'main')?.id
      await localCommand('lsp')!.run(h.app, 'references src/a.py 2 3')
      await tick()
      expect(h.gw.request).toHaveBeenCalledWith('lsp.query', { session_id: 'lsp-fixture', operation: 'references', path: 'src/a.py', line: 2, col: 3 })
      const close = h.nodes().find(node => node.props.key === 'close' && node.props.role === 'omp.btn')!
      const action = h.surface.dispatch({ act: 'click', ev: 'action', id: close.id, raw: {}, sf: 'hermes' })
      expect(action).toBeTruthy()
      await action?.()
      await tick()
      expect(h.app.composer.text).toBe('unsent draft')
      expect(byRole(h.nodes(), 'omp.overlay.lsp')).toHaveLength(0)
      expect(h.nodes().find(node => node.id === main)?.id).toBe(main)
    }, async () => ({ lsp_result: { ...base, kind: 'references', locations: [target(base.path)] } }))
  })

  it('keeps an existing approval above semantic inspection', async () => {
    await withApp(async h => {
      h.app.open({ key: 'prompt:approval', modal: true, node: () => node('text', { text: 'Approval fixture' }), onKey: () => true })
      await localCommand('lsp')!.run(h.app, 'symbols src/a.py')
      expect(h.app.overlays.map(overlay => overlay.key)).toEqual(['lsp', 'prompt:approval'])
    }, async () => ({ lsp_result: { ...base, kind: 'symbols', symbols: [] } }))
  })

  it('does not reopen a dismissed inspection when a slow result arrives', async () => {
    let complete!: (value: unknown) => void
    await withApp(async h => {
      const pending = localCommand('lsp')!.run(h.app, 'symbols src/a.py')
      await tick()
      const close = h.nodes().find(node => node.props.key === 'close' && node.props.role === 'omp.btn')!
      await h.surface.dispatch({ act: 'click', ev: 'action', id: close.id, raw: {}, sf: 'hermes' })?.()
      complete({ lsp_result: { ...base, kind: 'symbols', symbols: [] } })
      await pending
      await tick()
      expect(byRole(h.nodes(), 'omp.overlay.lsp')).toHaveLength(0)
      expect(h.app.transcript.entries.filter(entry => entry.kind === 'turn')).toHaveLength(0)
    }, () => new Promise(resolve => { complete = resolve }))
  })
})
