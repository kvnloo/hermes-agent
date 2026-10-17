import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-lsp-cards-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {delete process.env.HERMES_HOME}
  else {process.env.HERMES_HOME = isolated.previous}

  rmSync(isolated.home, { force: true, recursive: true })
})

function descendants(root: Tree): Tree[] {
  return [root, ...root.children.flatMap(descendants)]
}

async function withCard(result: unknown, run: (nodes: Tree[]) => void, name = 'patch') {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)

  if (!await connecting) {throw new Error('SDK fixture handshake failed')}
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'complete.slash') {return { items: [] }}
    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'lsp-fixture'
  app.info = { cwd: '/project', model: 'fixture' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => {
    latest = View.from(view)
    render(view)
  }

  try {
    const args = { content: 'x = 2\n', path: 'src/a.py' }
    app.transcript.toolStart({ args, name, tool_id: 'edit-1' }, 1)
    app.transcript.toolComplete({ name, result, tool_id: 'edit-1' }, 2)
    app.transcript.complete({ status: 'complete', text: '' }, 3)
    app.changed()
    await new Promise<void>(resolve => setImmediate(resolve))
    await new Promise<void>(resolve => setImmediate(resolve))
    const nodes = latest?.regions.flatMap(region => region?.children.flatMap(descendants) ?? []) ?? []
    expect(nodes.some(node => node.kind === 'tool')).toBe(true)
    run(nodes)
  } finally {
    app.quit()
    await running
  }
}

const diagnostic = (severity: string, line: number, message: string) => ({ col: 3, line, message, severity })
const file = (path: string, diagnostics: unknown[]) => ({ diagnostics, path, status: 'ok' })
const byRole = (nodes: Tree[], role: string) => nodes.filter(node => node.props.role === role)

describe('structured LSP edit/write cards', () => {
  it.each(['patch', 'write_file'])('counts 2 errors + 1 warning, groups files and links distinct severity rows in %s', async name => {
    await withCard({
      diff: '@@ -1 +1 @@\n-x = 1\n+x = 2',
      lsp_diagnostics: 'Legacy text must not be duplicated',
      lsp_diagnostics_data: [
        file('src/a.py', [diagnostic('error', 2, 'Unknown name'), diagnostic('warn', 5, 'Unused variable')]),
        file('src/b.py', [diagnostic('error', 7, 'Type mismatch')])
      ]
    }, nodes => {
      const section = byRole(nodes, 'omp.tool.diagnostics')[0]!
      expect(section.props.head).toEqual([{ s: 'chip', t: '2 errors · 1 warning' }])
      expect(section.props.collapsed).toBe(false)
      const groups = byRole(nodes, 'omp.tool.diagnostics.file')
      expect(groups).toHaveLength(2)
      expect(groups.map(group => byRole(descendants(group), 'omp.tool.diagnostic').length)).toEqual([2, 1])
      expect(byRole(nodes, 'omp.tool.diagnostic').map(row => row.props.href)).toEqual([
        'file:///project/src/a.py#L2C3', 'file:///project/src/a.py#L5C3', 'file:///project/src/b.py#L7C3'
      ])
      expect(byRole(nodes, 'omp.tool.diagnostic.error').map(node => node.props.spans)).toEqual([
        [{ s: 'error', t: '●' }], [{ s: 'error', t: '●' }]
      ])
      expect(byRole(nodes, 'omp.tool.diagnostic.warn')[0]?.props.spans).toEqual([{ s: 'warning', t: '▲' }])
      expect(nodes.some(node => node.props.text === 'Unknown name')).toBe(true)
      expect(JSON.stringify(section.props)).not.toContain('Legacy text')
    }, name)
  })

  it.each([8, 9])('uses the native fold threshold for %s rows', async count => {
    await withCard({ lsp_diagnostics_data: [file('src/a.py', Array.from({ length: count }, (_, i) => diagnostic('error', i + 1, `Issue ${i}`)))] }, nodes => {
      const section = byRole(nodes, 'omp.tool.diagnostics')[0]!
      expect(section.props).toMatchObject({ collapsed: count > 8, collapsible: true, head: [{ s: 'chip', t: `${count} errors` }] })
      expect(byRole(descendants(section), 'omp.tool.diagnostic')).toHaveLength(count)
    })
  })

  it('shows LSP-unavailable as a muted note without an error count or failed tool status', async () => {
    await withCard({ lsp_diagnostics_data: [{ message: 'LSP unavailable: no fresh diagnostics received in time', path: 'src/a.py', status: 'unavailable' }] }, nodes => {
      expect(byRole(nodes, 'omp.tool.diagnostics')).toHaveLength(0)
      expect(byRole(nodes, 'omp.tool.diagnostic.error')).toHaveLength(0)
      expect(byRole(nodes, 'omp.tool.diagnostics.unavailable')[0]?.props.spans).toEqual([
        { s: 'muted', t: 'src/a.py: LSP unavailable: no fresh diagnostics received in time' }
      ])
      expect(nodes.find(node => node.kind === 'tool')?.props.status).toBe('done')
    })
  })

  it('keeps the string-only legacy result visible as a fallback', async () => {
    const text = 'LSP diagnostics introduced by this edit:\nERROR [2:3] Unknown name'
    await withCard({ lsp_diagnostics: text }, nodes => {
      expect(byRole(nodes, 'omp.tool.notice')[0]?.props.spans).toEqual([{ s: 'muted', t: text }])
      expect(byRole(nodes, 'omp.tool.diagnostics')).toHaveLength(0)
    })
  })

  it('falls back on malformed structured data rather than trusting invalid coordinates', async () => {
    await withCard({ lsp_diagnostics: 'legacy', lsp_diagnostics_data: [file('a.py', [diagnostic('error', -1, 'bad')])] }, nodes => {
      expect(byRole(nodes, 'omp.tool.notice')[0]?.props.spans).toEqual([{ s: 'muted', t: 'legacy' }])
    })
  })
})
