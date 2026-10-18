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
  const home = mkdtempSync(join(tmpdir(), 'hermes-tool-adapters-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

interface Fixture {
  name: string
  args: Record<string, unknown>
  result?: Record<string, unknown>
  status?: 'done' | 'error' | 'running'
}

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])

async function withTools(fixtures: Fixture[], check: (nodes: Tree[]) => void) {
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({
    ...tern.caps, kinds: tern.caps.kinds.filter(kind => kind !== 'media'),
    r: 'hello', v: 1, term: 'fixture', ver: '0'
  })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'complete.slash') { return { items: [] } }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'adapter-session'
  app.info = { cwd: '/project', terminal_backend: 'local' }
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
    for (const [index, fixture] of fixtures.entries()) {
      const payload = { tool_id: `tool-${index}`, name: fixture.name, args: fixture.args }
      gw.emit('event', { type: 'tool.start', session_id: app.sid, payload })

      if (fixture.status !== 'running') {
        gw.emit('event', {
          type: 'tool.complete', session_id: app.sid,
          payload: { ...payload, result: fixture.result ?? {}, success: fixture.status !== 'error' }
        })
      }
    }

    await rendered()
    await rendered()
    check(flatten(latest?.regions.find(region => region?.id === 'main')?.children ?? []))
  } finally {
    app.quit()
    await running
    request.mockRestore()

    if (previousSplash === undefined) { delete process.env.HERMES_TUI_SPLASH }
    else { process.env.HERMES_TUI_SPLASH = previousSplash }
  }
}

function tool(nodes: Tree[], name: string): Tree {
  const found = nodes.find(node => node.kind === 'tool' && node.props.name === name)

  if (!found) { throw new Error(`Missing tool card: ${name}`) }

  return found
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME }
  else { process.env.HERMES_HOME = isolated.previous }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('tool adapter registry', () => {
  it('preserves ordinary read, shell, edit, and web cards through App', async () => {
    await withTools([
      { name: 'read_file', args: { path: 'x.ts' }, result: { content: '1|const x = 1', total_lines: 1 } },
      { name: 'terminal', args: { command: 'pwd' }, result: { output: '/project', exit_code: 0 } },
      { name: 'patch', args: { path: 'x.ts' }, result: { diff: '@@ -1 +1 @@\n-a\n+b' } },
      { name: 'web_search', args: { query: 'tern' }, result: { data: { web: [{ title: 'Tern', url: 'https://example.org/' }] } } }
    ], nodes => {
      expect(tool(nodes, 'read').props).toMatchObject({ target: 'x.ts', lang: 'typescript', preview: { lines: 3 } })
      expect(nodes.find(node => node.kind === 'code' && node.props.numbers)?.props.text).toBe('const x = 1')
      expect(tool(nodes, 'bash').props).toMatchObject({ target: 'pwd', status: 'done', collapsible: false })
      expect(tool(nodes, 'edit').props.meta).toEqual(['+1 −1'])
      expect(tool(nodes, 'web_search').props.meta).toEqual(['1 source'])
    })
  })

  it('shows browser_navigate action, final URL with href, and title', async () => {
    await withTools([{ name: 'browser_navigate', args: { url: 'https://example.org' },
      result: { success: true, url: 'https://example.org/final', title: 'Example page' } }], nodes => {
      expect(tool(nodes, 'browser').props).toMatchObject({ title: 'Navigate', target: 'https://example.org/final', href: 'https://example.org/final', meta: ['Example page'] })
    })
  })

  it('renders README.md as folded Markdown without numbered code', async () => {
    await withTools([{ name: 'read_file', args: { path: 'README.md' }, result: { content: '1|# Hello\n2|**world**', total_lines: 2 } }], nodes => {
      const card = tool(nodes, 'read')
      expect(card.props.collapsed).toBe(true)
      expect(card.children.some(node => node.kind === 'md')).toBe(true)
      expect(card.children.some(node => node.kind === 'code')).toBe(false)
      expect(card.children.find(node => node.kind === 'md')?.props.text).toBe('# Hello\n**world**')
    })
  })

  it('renders x.png as an image with a session-local path link', async () => {
    await withTools([{ name: 'read_file', args: { path: 'x.png' } }], nodes => {
      expect(nodes.find(node => node.kind === 'image')?.props.path).toBe('/project/x.png')
      expect(tool(nodes, 'read').props.href).toBe('file:///project/x.png')
    })
  })

  it.each(['mystery_tool', 'constructor', 'toString', '__proto__'])('keeps an honest generic fallback for %s', async name => {
    await withTools([{ name, args: { query: 'needle' }, result: { detail: 'opaque result' } }], nodes => {
      expect(tool(nodes, name).props).toMatchObject({ target: 'needle', collapsed: true, status: 'done' })
      expect(nodes.find(node => node.kind === 'code')?.props.text).toContain('opaque result')
    })
  })

  it.each([false, true])('renders the confirmed browser screenshot path (native envelope: %s)', async native => {
    const result = native
      ? { _multimodal: true, meta: { screenshot_path: '/project/screen.png' }, text_summary: 'Image attached natively' }
      : { success: true, screenshot_path: '/project/screen.png', analysis: 'A browser page' }

    await withTools([{ name: 'browser_vision', args: { question: 'What is visible?' }, result }], nodes => {
      expect(nodes.find(node => node.kind === 'image')?.props.path).toBe('/project/screen.png')
    })
  })

  it('shows vision image path, question and actual analysis, not an invented answer field', async () => {
    await withTools([{ name: 'vision_analyze', args: { image_url: 'x.png', question: 'What is this?' }, result: { success: true, analysis: 'A red bird.' } }], nodes => {
      expect(tool(nodes, 'image').props).toMatchObject({ target: 'x.png', href: 'file:///project/x.png' })
      const wire = JSON.stringify(nodes.map(node => node.node.toJSON()))
      expect(wire).toContain('What is this?')
      expect(wire).toContain('A red bird.')
    })
  })

  it('keeps browser errors visible even when the card has a body', async () => {
    await withTools([{ name: 'browser_navigate', args: { url: 'https://example.org' }, status: 'error', result: { error: 'Navigation failed' } }], nodes => {
      expect(tool(nodes, 'browser').props.status).toBe('error')
      expect(JSON.stringify(nodes.map(node => node.node.toJSON()))).toContain('Navigation failed')
    })
  })
})
