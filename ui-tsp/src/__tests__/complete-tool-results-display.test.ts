import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { TranscriptMessage } from '@hermes/shared/gateway-events'
import { Session, type Surface, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { fileHref } from '../links.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-complete-results-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

interface Fixture {
  name: string
  args: Record<string, unknown>
  result: Record<string, unknown>
}

interface Harness {
  app: App
  surface: Surface
  nodes(): Tree[]
  card(): Tree
  click(role: string): Promise<void>
}

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])
const body = (card: Tree) => JSON.stringify(card.children.map(node => ({ kind: node.kind, props: node.props, children: node.children })))

async function withResult(fixture: Fixture, check: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  acknowledgeFrames(tern)
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const message: TranscriptMessage = { role: 'tool', tool_call_id: 'call', name: fixture.name, args: fixture.args, content: JSON.stringify(fixture.result) }

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'session.resume') { return { session_id: 'resumed', messages: [message], info: { cwd: '/project' } } }

    if (method === 'session.close' || method === 'complete.slash') { return { items: [] } }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'initial'
  app.info = { cwd: '/project' }
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = value => { latest = View.from(value); render(value) }
  const nodes = () => flatten(latest?.regions.find(region => region?.id === 'main')?.children ?? [])

  const card = () => {
    const found = nodes().find(node => node.kind === 'tool')

    if (!found) { throw new Error('Missing tool card') }

    return found
  }

  try {
    gw.emit('event', { type: 'tool.complete', session_id: app.sid, payload: { tool_id: 'call', ...fixture } })
    gw.emit('event', { type: 'message.complete', session_id: app.sid, payload: { status: 'completed' } })
    await rendered()
    await rendered()
    await check({ app, surface, nodes, card, click: async role => {
      const target = nodes().find(node => node.props.role === role)

      if (!target) { throw new Error(`Missing action: ${role}`) }
      const action = surface.dispatch({ act: 'click', ev: 'action', id: target.id, raw: {}, sf: 'hermes' })

      if (!action) { throw new Error(`No action registered: ${role}`) }
      await action()
      await rendered()
      await rendered()
    } })
  } finally {
    app.quit()
    await running
    request.mockRestore()
  }
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME }
  else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.splash === undefined) { delete process.env.HERMES_TUI_SPLASH }
  else { process.env.HERMES_TUI_SPLASH = isolated.splash }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('complete tool results and safe display text', () => {
  it('retains more than 200 files and separates returned, total and source-omitted counts', async () => {
    const files = Array.from({ length: 251 }, (_, i) => `src/file ${i}.ts`)
    await withResult({ name: 'search_files', args: { target: 'files', pattern: '*.ts' }, result: { files, total_count: 300, truncated: true, total_count_is_lower_bound: true } }, async h => {
      const rows = h.nodes().filter(node => node.props.role === 'omp.tool.file')
      expect(rows).toHaveLength(251)
      expect(flatten(rows).at(-1)?.props.spans).toEqual([{ s: 'path', t: 'file 250.ts' }])
      expect(rows.at(-1)?.props.href).toBe('file:///project/src/file%20250.ts')
      expect(h.card().props.meta).toEqual(expect.arrayContaining(['251 files returned', '≥300 total', '≥49 omitted', 'source truncated']))
      expect(h.card().props.preview).toEqual({ lines: 20 })
      await h.app.resume('stored')
      await rendered()
      await rendered()
      expect(h.nodes().filter(node => node.props.role === 'omp.tool.file')).toHaveLength(251)
      expect(h.card().props.meta).toEqual(expect.arrayContaining(['251 files returned', '≥300 total', '≥49 omitted', 'source truncated']))
    })
  })

  it('retains dense search output and reports source counts instead of an empty card', async () => {
    const matches_text = 'src/file with space.ts\n' + Array.from({ length: 205 }, (_, i) => `  ${i + 1}: match ${i}`).join('\n')
    await withResult({ name: 'search_files', args: { pattern: 'match' }, result: { matches_text, total_count: 220 } }, async h => {
      expect(h.nodes().find(node => node.kind === 'code')?.props.text).toBe(matches_text)
      expect(h.card().props.meta).toEqual(['205 matches returned', '220 total', '15 omitted'])
    })
  })

  it('keeps source read truncation distinct and resolves raw relative/spaced Markdown destinations', async () => {
    const content = '1|# Read\n2|[Good](<src/file with space.ts>)\n3|[Bad](<src/has\u0007control.ts>)\n4|last returned line'
    await withResult({ name: 'read_file', args: { path: 'README.md' }, result: { content, total_lines: 100, truncated: true, hint: 'Only 4 of 100 source lines returned' } }, async h => {
      const markdown = h.nodes().find(node => node.kind === 'md')?.props.text
      expect(markdown).toContain('[Good](file:///project/src/file%20with%20space.ts)')
      expect(markdown).toContain('Bad (src/has\\u0007control.ts)')
      expect(markdown).not.toContain('[Bad](')
      expect(body(h.card())).toContain('Only 4 of 100 source lines returned')
    })
  })

  it.each(['web_extract', 'custom_result'])('expands all available >4000-character %s output with an explicit native action', async name => {
    const content = 'start\n' + 'long line\n'.repeat(600) + 'FINAL AVAILABLE OUTPUT'
    const result = name === 'web_extract' ? { results: [{ url: 'https://example.org', title: 'Page', content }] } : { content }
    await withResult({ name, args: {}, result }, async h => {
      expect(h.card().props.collapsed).toBe(true)
      await h.click('omp.tool.load')
      expect(h.card().props.collapsed).toBe(false)
      expect(body(h.card())).toContain('FINAL AVAILABLE OUTPUT')
      await h.click('omp.tool.load')
      expect(h.card().props.collapsed).toBe(true)
      await h.click('omp.tool.load')
      expect(body(h.card())).toContain('FINAL AVAILABLE OUTPUT')
    })
  })

  it('keeps source capture truncation and exact backend artifacts after output-only expansion', async () => {
    const path = 'captures/full output.txt'
    const result = { output: 'head\n' + 'captured\n'.repeat(20) + 'tail', exit_code: 0, truncation_note: 'spilled', full_output_path: path, output_total_chars: 90000 }
    await withResult({ name: 'terminal', args: { command: 'produce output' }, result }, async h => {
      expect(body(h.card())).toContain('capture truncated: head + tail retained')
      const artifact = h.nodes().find(node => node.props.role === 'omp.tool.artifact')
      expect(artifact?.props.href).toBe(fileHref(path, '/project'))
      await h.click('omp.run.toggle')
      expect(body(h.card())).not.toContain('truncated: showing last')
      expect(body(h.card())).toContain('capture truncated: head + tail retained')
      expect(body(h.card())).toContain('90000 chars total')
      expect(h.nodes().find(node => node.props.role === 'omp.run.output')?.props.text).toBe(result.output)
    })
  })

  it('uses execute_code byte metadata and stdout_spill_path, without inventing artifacts', async () => {
    await withResult({ name: 'execute_code', args: { code: 'print(result)' }, result: { output: 'head\ntail', stdout_truncated: true, stdout_bytes_captured: 10, stdout_bytes_total: 100, stdout_bytes_omitted: 90, stdout_spill_path: '/cache/real stdout.txt' } }, async h => {
      expect(body(h.card())).toContain('10 bytes returned · 100 bytes total · 90 bytes omitted')
      expect(h.nodes().find(node => node.props.role === 'omp.tool.artifact')?.props.href).toBe('file:///cache/real%20stdout.txt')
    })
    await withResult({ name: 'terminal', args: {}, result: { output: 'head/tail', truncation_note: 'not saved' } }, async h => {
      expect(h.nodes().filter(node => node.props.role === 'omp.tool.artifact')).toHaveLength(0)
    })
  })

  it('preserves each multi-file patch identity, own diff and raw file link', async () => {
    const diff = '--- a/src/first file.ts\n+++ b/src/first file.ts\n@@ -1 +1 @@\n-old1\n+new1\n\n--- a/src/second.ts\n+++ b/src/second.ts\n@@ -8 +8 @@\n-old2\n+new2\n'
    await withResult({ name: 'patch', args: {}, result: { diff, files_modified: ['src/first file.ts', 'src/second.ts'] } }, async h => {
      const files = h.nodes().filter(node => node.props.role === 'omp.tool.edit.file')
      expect(files).toHaveLength(2)
      expect(flatten(files).filter(node => node.kind === 'diff').map(node => node.props.text)).toEqual(['@@ -1 +1 @@\n-old1\n+new1\n', '@@ -8 +8 @@\n-old2\n+new2\n'])
      expect(flatten(files).filter(node => node.props.href).map(node => node.props.href)).toEqual(['file:///project/src/first%20file.ts#L1', 'file:///project/src/second.ts#L8'])
      expect(h.card().props).toMatchObject({ target: '2 files', targetKind: 'text' })
    })
  })

  it('does not mistake header-like edited source lines for another file', async () => {
    const diff = '--- a/one.txt\n+++ b/one.txt\n@@ -1 +1 @@\n--- old source\n+++ new source\n--- a/two.txt\n+++ b/two.txt\n@@ -1 +1 @@\n-x\n+y\n'
    await withResult({ name: 'patch', args: {}, result: { diff, files_modified: ['one.txt', 'two.txt'] } }, async h => {
      const files = h.nodes().filter(node => node.props.role === 'omp.tool.edit.file')
      expect(files).toHaveLength(2)
      expect(flatten(files).filter(node => node.kind === 'diff')[0]?.props.text).toBe('@@ -1 +1 @@\n--- old source\n+++ new source')
    })
  })

  it('sanitizes control-byte filenames and text without retargeting sanitized paths', async () => {
    const path = 'src/has\u0007control.ts'
    await withResult({ name: 'read_file', args: { path }, result: { content: '1|hello\u0000\u001b[31mred\u001b[0m', total_lines: 1 } }, async h => {
      expect(h.card().props.target).toBe('src/has\\u0007control.ts')
      expect(h.card().props.href).toBeUndefined()
      expect(h.nodes().find(node => node.kind === 'code')?.props.text).toBe('hello\\u0000red')
      expect(h.app.transcript.entries.some(entry => entry.kind === 'turn' && entry.blocks.some(block => block.kind === 'tool' && block.call.args.path === path))).toBe(true)
    })
  })

  it('shows search descriptions and preserves relative/spaced raw source URLs', async () => {
    const url = '../relative folder/page?q=hello world'
    await withResult({ name: 'web_search', args: { query: 'test\u0007query' }, result: { data: { web: [{ url, title: 'A\u0000 title', description: 'The\u0007 description' }] } } }, async h => {
      expect(h.nodes().find(node => node.props.role === 'omp.tool.description')?.props.text).toBe('The\\u0007 description')
      expect(body(h.card())).toContain('A\\\\u0000 title')
      expect(h.nodes().some(node => Array.isArray(node.props.spans) && node.props.spans.some(span => typeof span === 'object' && span !== null && 'href' in span && span.href === url))).toBe(true)
      expect(h.card().props.target).toBe('test\\u0007query')
    })
  })

  it('opens only the actual web_extract footer descriptor and preserves it on resume', async () => {
    const content = 'head\n──────── [TRUNCATED] ────────\nShowing 10 chars of 100 total clean characters.\nFull text saved to: /cache/page with space.txt\nTo read the omitted middle: read_file path="/cache/page with space.txt" offset=2 limit=200\n─────────────────────────────'
    await withResult({ name: 'web_extract', args: { urls: ['https://example.org/a b'] }, result: { results: [{ url: 'https://example.org/a b', title: 'Page', content }] } }, async h => {
      expect(h.nodes().find(node => node.props.role === 'omp.tool.artifact')?.props.href).toBe('file:///cache/page%20with%20space.txt')
      await h.app.resume('stored')
      await rendered()
      await rendered()
      await h.click('omp.tool.load')
      expect(h.card().props.collapsed).toBe(false)
      expect(body(h.card())).toContain('TRUNCATED')
      expect(h.nodes().find(node => node.props.role === 'omp.tool.artifact')?.props.href).toBe('file:///cache/page%20with%20space.txt')
    })
  })
})
