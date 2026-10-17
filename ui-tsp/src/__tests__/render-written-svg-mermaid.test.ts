import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { TranscriptMessage } from '@hermes/shared/gateway-events'
import { Session, type Surface, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-written-artifacts-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const rendered = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

const svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>λ</text></svg>'
const mermaid = 'graph TD\n  A[Start] --> B[Done]'

interface Fixture {
  media?: boolean
  attached?: boolean
  backend?: string
  messages?: TranscriptMessage[]
}
interface Harness {
  app: App
  surface: Surface
  nodes(): Tree[]
  start(id: string, path: string, source: string): void
  complete(id: string, result: Record<string, unknown>): void
  theme(dark: boolean): void
}

async function withApp(fixture: Fixture, run: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({
    ...tern.caps, kinds: [...tern.caps.kinds.filter(kind => kind !== 'media'), ...(fixture.media === false ? [] : ['media'])],
    r: 'hello', v: 1, term: 'fixture', ver: '0'
  })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const attached = vi.spyOn(gw, 'attached', 'get').mockReturnValue(fixture.attached ?? false)
  const info = { cwd: '/project', terminal_backend: fixture.backend ?? 'local' }

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'session.resume') { return { session_id: 'resumed', messages: fixture.messages ?? [], info } }

    if (method === 'session.close' || method === 'complete.slash') { return { items: [] } }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'written-session'
  app.info = info
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = value => {
    latest = View.from(value)
    render(value)
  }

  const emit = (type: string, payload: Record<string, unknown>) => gw.emit('event', { type, session_id: app.sid, payload })
  const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])

  try {
    await run({
      app, surface,
      nodes: () => flatten(latest?.regions.find(region => region?.id === 'main')?.children ?? []),
      start: (id, path, source) => emit('tool.start', { tool_id: id, name: 'write_file', args: { path, content: source } }),
      complete: (id, result) => emit('tool.complete', { tool_id: id, name: 'write_file', result }),
      theme: dark => input.emit('data', `\x1b_tsp;e;${JSON.stringify({ ev: 'theme', dark })}\x1b\\`)
    })
  } finally {
    app.quit()
    await running
    attached.mockRestore()
    request.mockRestore()
  }
}

function success(source: string, extra: Record<string, unknown> = {}): Record<string, unknown> {
  return { bytes_written: Buffer.byteLength(source, 'utf8'), verified: true, ...extra }
}

function card(h: Harness, target: string): Tree {
  const found = h.nodes().find(node => node.kind === 'tool' && node.props.target === target)

  if (!found) { throw new Error(`Missing write card: ${target}`) }

  return found
}

function figures(h: Harness): Tree[] {
  return h.nodes().filter(node => node.props.role === 'omp.tool.write.figure' || node.kind === 'media')
}

function shape(node: Tree): unknown {
  return { kind: node.kind, props: node.props, children: node.children.map(shape) }
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME }
  else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.splash === undefined) { delete process.env.HERMES_TUI_SPLASH }
  else { process.env.HERMES_TUI_SPLASH = isolated.splash }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('confirmed written artifacts', () => {
  it.each([
    ['drawing.svg', svg, 'svg'],
    ['diagram.mmd', mermaid, 'mermaid'],
    ['diagram.mermaid', mermaid, 'mermaid']
  ])('leads a successful %s write with its native fence and keeps source below', async (path, source, language) => {
    await withApp({}, async h => {
      h.start('write', path, source)
      h.complete('write', success(source))
      await rendered()
      const tool = card(h, path)
      expect(tool.props).toMatchObject({ name: 'write', status: 'done', collapsed: false, href: `file:///project/${path}` })
      expect(tool.props.preview).toBeUndefined()
      expect(tool.children[0]?.props).toMatchObject({ role: 'omp.tool.write.figure', text: `\x60\x60\x60${language}\n${source}\n\x60\x60\x60` })
      expect(tool.children[1]?.props.text).toBe(source)
      expect(tool.children[1]?.kind).toBe('code')
    })
  })

  it('renders a confirmed host-local GLB with the negotiated media kind and authoritative path', async () => {
    await withApp({}, async h => {
      h.start('model', 'model.glb', 'glTF')
      h.complete('model', success('glTF', { resolved_path: '/actual/model.glb', mime: 'model/gltf-binary' }))
      await rendered()
      const tool = card(h, '/actual/model.glb')
      expect(tool.props.href).toBe('file:///actual/model.glb')
      expect(tool.children[0]?.node.toJSON()).toMatchObject({ k: 'media', p: { path: '/actual/model.glb' } })
      expect(tool.children[0]?.props.rev).toBeUndefined()
      expect(tool.children[1]?.props.text).toBe('glTF')
      expect(tool.props.preview).toBeUndefined()
    })
  })

  it.each([
    ['running', undefined],
    ['failed', { error: 'Permission denied', verified: true, bytes_written: Buffer.byteLength(svg) }],
    ['partial', success(svg, { bytes_written: 3 })],
    ['explicit partial', success(svg, { partial: true })],
    ['unverified', success(svg, { verified: false })],
    ['old result', { bytes_written: Buffer.byteLength(svg) }],
    ['arguments only', {}],
    ['success false', success(svg, { success: false })]
  ])('never previews a %s write or hides its source/state', async (state, result) => {
    await withApp({}, async h => {
      h.start('write', 'drawing.svg', svg)

      if (result) { h.complete('write', result) }
      await rendered()
      expect(figures(h)).toHaveLength(0)
      const tool = card(h, 'drawing.svg')
      expect(tool.props.status).toBe(state === 'running' ? 'running' : state === 'failed' ? 'error' : 'done')
      expect(tool.children.find(node => node.kind === 'code')?.props.text).toBe(svg)

      if (state === 'failed') { expect(JSON.stringify(shape(tool))).toContain('Permission denied') }
    })
  })

  it.each([
    ['drawing.svg', 'image/png'], ['drawing.svg', 'text/html'],
    ['diagram.mmd', 'application/javascript'], ['model.glb', 'text/html'], ['model.glb', 'model/obj']
  ])('rejects MIME disagreement for %s (%s) and keeps the fallback file link', async (path, mime) => {
    await withApp({}, async h => {
      h.start('write', path, svg)
      h.complete('write', success(svg, { mime }))
      await rendered()
      expect(figures(h)).toHaveLength(0)
      expect(card(h, path).props.href).toBe(`file:///project/${path}`)
    })
  })

  it('retains diff and diagnostics under the figure without code-line clipping', async () => {
    await withApp({}, async h => {
      h.start('write', 'drawing.svg', svg)
      h.complete('write', success(svg, { diff: `@@ -1 +1 @@\n-old\n+${svg}`, lsp_diagnostics: 'Fixture warning: invalid attribute' }))
      await rendered()
      const tool = card(h, 'drawing.svg')
      expect(tool.children[0]?.props.role).toBe('omp.tool.write.figure')
      expect(tool.children[1]?.kind).toBe('diff')
      expect(JSON.stringify(shape(tool))).toContain('invalid attribute')
      expect(tool.props.preview).toBeUndefined()
    })
  })

  it('invalidates a stale completion, scopes figures to their owner, and remounts changed revisions', async () => {
    await withApp({}, async h => {
      h.start('one', 'one.svg', svg)
      h.complete('one', success(svg))
      h.start('two', 'two.mmd', mermaid)
      h.complete('two', success(mermaid))
      await rendered()
      const first = card(h, 'one.svg').children[0]?.props.key
      h.complete('one', success(svg, { mime: 'image/png' }))
      await rendered()
      expect(figures(h)).toHaveLength(1)
      expect(card(h, 'one.svg').children[0]?.kind).toBe('code')
      expect(card(h, 'two.mmd').children[0]?.props.role).toBe('omp.tool.write.figure')
      h.complete('one', success(svg, { mime: 'image/svg+xml' }))
      await rendered()
      expect(card(h, 'one.svg').children[0]?.props.key).not.toBe(first)
      h.complete('one', { error: 'Late verification failed' })
      await rendered()
      expect(card(h, 'one.svg').props.status).toBe('error')
      expect(card(h, 'one.svg').children[0]?.kind).toBe('code')
    })
  })

  it('falls back for models without media support but still renders native SVG/Mermaid fences', async () => {
    await withApp({ media: false }, async h => {
      h.start('model', 'model.glb', 'glTF')
      h.complete('model', success('glTF'))
      h.start('svg', 'drawing.svg', svg)
      h.complete('svg', success(svg))
      h.start('mermaid', 'diagram.mmd', mermaid)
      h.complete('mermaid', success(mermaid))
      await rendered()
      expect(h.nodes().filter(node => node.kind === 'media')).toHaveLength(0)
      expect(figures(h)).toHaveLength(2)
      expect(card(h, 'model.glb').props.href).toBe('file:///project/model.glb')
    })
  })

  it.each([{ backend: 'ssh' }, { backend: 'docker' }, { attached: true }])('does not reinterpret non-host-local paths as local models: %j', async fixture => {
    await withApp(fixture, async h => {
      h.start('model', 'model.glb', 'glTF')
      h.complete('model', success('glTF'))
      h.start('svg', 'drawing.svg', svg)
      h.complete('svg', success(svg))
      await rendered()
      expect(h.nodes().some(node => node.kind === 'media')).toBe(false)
      expect(card(h, 'model.glb').props.href).toBeUndefined()
      expect(JSON.stringify(shape(card(h, 'model.glb')))).toContain('not host-local')
      expect(figures(h)).toHaveLength(1)
    })
  })

  it('invalidates cached host-local media when session backend changes', async () => {
    await withApp({}, async h => {
      h.start('model', 'model.glb', 'glTF')
      h.complete('model', success('glTF'))
      await rendered()
      expect(figures(h)).toHaveLength(1)
      h.app.info = { cwd: '/project', terminal_backend: 'ssh' }
      h.app.changed()
      await rendered()
      expect(figures(h)).toHaveLength(0)
      expect(card(h, 'model.glb').props.href).toBeUndefined()
    })
  })

  it('reconstructs the same confirmed SVG/Mermaid/model figures from stored results on resume', async () => {
    const writes = [['drawing.svg', svg], ['diagram.mmd', mermaid], ['model.glb', 'glTF']]

    const messages: TranscriptMessage[] = writes.map(([path = '', content = ''], i) => ({
      role: 'tool', tool_call_id: `write-${i}`, name: 'write_file', args: { path, content }, content: JSON.stringify(success(content))
    }))

    await withApp({ messages }, async h => {
      for (const [i, [path = '', source = '']] of writes.entries()) {
        h.start(`write-${i}`, path, source)
        h.complete(`write-${i}`, success(source))
      }

      await rendered()
      const live = figures(h).map(shape)
      expect(live).toHaveLength(3)
      await h.app.resume('stored')
      await rendered()
      expect(figures(h).map(shape)).toEqual(live)
    })
  })

  it('delegates dark/light appearance to native figure roles without hardcoded colors', async () => {
    await withApp({}, async h => {
      h.start('write', 'drawing.svg', svg)
      h.complete('write', success(svg))
      await rendered()
      const before = figures(h).map(shape)
      expect(before).toHaveLength(1)
      h.theme(false)
      await rendered()
      expect(figures(h).map(shape)).toEqual(before)
      h.theme(true)
      await rendered()
      expect(figures(h).map(shape)).toEqual(before)
      expect(figures(h)[0]?.props.color).toBeUndefined()
    })
  })

  it('contains fence delimiters and never routes generated JS/Luau to an executable node', async () => {
    await withApp({}, async h => {
      const source = svg + '\n```js\nglobalThis.__must_not_execute = true\n```'
      h.start('svg', 'drawing.svg', source)
      h.complete('svg', success(source))

      for (const path of ['generated.js', 'generated.luau', 'constructor', 'https://host/drawing.svg']) {
        h.start(path, path, source)
        h.complete(path, success(source))
      }

      await rendered()
      expect(figures(h)).toHaveLength(1)
      expect(figures(h)[0]?.props.text).toBe(`\x60\x60\x60\x60svg\n${source}\n\x60\x60\x60\x60`)
      expect(h.nodes().some(node => node.kind === 'eval' || node.kind === 'terminal')).toBe(false)
    })
  })
})
