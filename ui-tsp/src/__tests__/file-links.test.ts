import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Node, Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { fileHref, rewriteLocalMarkdownLinks } from '../links.js'
import type { ToolCall, TurnEntry } from '../model.js'
import { Transcript } from '../transcript.js'
import { toolNode } from '../view/tools.js'
import { entryNode } from '../view/transcript.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-tern-file-links-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {delete process.env.HERMES_HOME}
  else {process.env.HERMES_HOME = isolated.previous}

  rmSync(isolated.home, { force: true, recursive: true })
})

const cwd = '/workspace/project'

function node(value: unknown): Node {
  if (!(value instanceof Node)) {
    throw new Error('Expected a semantic Tern node')
  }

  return value
}

function call(name: string, args: Record<string, unknown>, result: unknown = {}): ToolCall {
  return { args, argsText: '', context: '', id: 'tool-1', name, result, startedAt: 0, status: 'done' }
}

function childrenOf(node: Node, kind: string): Node[] {
  return node.children.filter(child => child instanceof Node && child.kind === kind) as Node[]
}

describe('fileHref', () => {
  it('resolves absolute, relative, parent and encoded local paths', () => {
    expect(fileHref('/tmp/a.ts', cwd)).toBe('file:///tmp/a.ts')
    expect(fileHref('src/a.ts', cwd)).toBe('file:///workspace/project/src/a.ts')
    expect(fileHref('../README.md', cwd)).toBe('file:///workspace/README.md')
    expect(fileHref('a b.ts', cwd)).toBe('file:///workspace/project/a%20b.ts')
    expect(fileHref('a#b?.ts', cwd)).toBe('file:///workspace/project/a%23b%3F.ts')
  })

  it('provides single lines, ranges and optional columns', () => {
    expect(fileHref('a.ts', cwd, { line: 10 })).toBe('file:///workspace/project/a.ts#L10')
    expect(fileHref('a.ts', cwd, { line: 10, endLine: 20 })).toBe('file:///workspace/project/a.ts#L10-L20')
    expect(fileHref('a.ts', cwd, { line: 10, col: 3 })).toBe('file:///workspace/project/a.ts#L10C3')
    expect(fileHref('a.ts', cwd, { line: -2, endLine: 5 })).toBe('file:///workspace/project/a.ts')
  })

  it('rejects nonlocal targets and ambiguous session-relative paths without throwing', () => {
    for (const path of ['http://x.y/a', 'https://x.y/a', 'mailto:x@y.z', 'javascript:alert(1)', 'file:///etc/passwd', '', '   ', 'a\0b', '//host/share']) {
      expect(fileHref(path, cwd)).toBeUndefined()
    }

    expect(fileHref('src/a.ts', '')).toBeUndefined()
    expect(fileHref('/etc/hosts', '')).toBe('file:///etc/hosts')
  })
})

describe('tool file links', () => {
  it('makes read targets openable at the requested offset/range', () => {
    const read = node(toolNode(call('read_file', { path: 'src/a.ts', offset: 10 }, { content: '10|hello' }), 0, cwd))
    expect(read.props.href).toBe('file:///workspace/project/src/a.ts#L10')

    const range = node(toolNode(call('read_file', { path: 'src/a.ts', offset: 10, limit: 5 }, {
      content: '10|hello\n11|world\n12|one\n13|two\n14|three'
    }), 0, cwd))

    expect(range.props.href).toBe('file:///workspace/project/src/a.ts#L10-L14')
  })

  it('makes edits, new files and glob paths openable', () => {
    const edit = node(toolNode(call('patch', { path: 'src/a.ts' }, {
      diff: '@@ -12,2 +20,3 @@\n-old\n+new'
    }), 0, cwd))

    expect(edit.props.href).toBe('file:///workspace/project/src/a.ts#L20-L22')

    const write = node(toolNode(call('write_file', { path: 'src/new.ts', content: 'hello' }), 0, cwd))
    expect(write.props.href).toBe('file:///workspace/project/src/new.ts')

    const glob = node(toolNode(call('search_files', { target: 'files', pattern: '*.ts' }, {
      files: ['src/a.ts', 'src/b.ts']
    }), 0, cwd))

    const rows = childrenOf(glob, 'row')
    expect(rows.map(row => row.props.href)).toEqual([
      'file:///workspace/project/src/a.ts',
      'file:///workspace/project/src/b.ts'
    ])
    expect(childrenOf(rows[0]!, 'text')[0]?.props.href).toBe('file:///workspace/project/src/a.ts')
  })

  it('opens each search match run at its own line or range', () => {
    const search = node(toolNode(call('search_files', { pattern: 'todo', target: 'content' }, {
      matches: [
        { path: 'src/a.ts', line: 7, content: 'const a = 1' },
        { path: 'src/a.ts', line: 8, content: 'const b = 2' },
        { path: 'src/a.ts', line: 14, content: 'const c = 3' }
      ]
    }), 0, cwd))

    expect(childrenOf(search, 'row')[0]?.props.href).toBe('file:///workspace/project/src/a.ts#L7')
    expect(childrenOf(search, 'code').map(code => code.props.href)).toEqual([
      'file:///workspace/project/src/a.ts#L7-L8',
      'file:///workspace/project/src/a.ts#L14'
    ])
  })

  it('does not attach file URLs to browser-target tool cards', () => {
    const web = node(toolNode(call('web_search', { query: 'test' }), 0, cwd))
    expect(web.props.href).toBeUndefined()
    const unsafe = node(toolNode(call('read_file', { path: 'https://x.y' }), 0, cwd))
    expect(unsafe.props.href).toBeUndefined()
  })
})

describe('assistant Markdown file links', () => {
  it('resolves local targets and line fragments but preserves web URLs and literal code', () => {
    const fence = String.fromCharCode(96).repeat(3)
    const inline = String.fromCharCode(96)

    const text = [
      'see [a](src/a.ts) and [line](./README.md#L3) and [web](https://x.y)',
      'file [hash](src/a#b.ts) stays a filename',
      inline + '[inline](src/ignored.ts)' + inline,
      fence + 'md',
      '[fenced](src/ignored.ts)',
      fence,
      '![image](src/image.png)'
    ].join('\n')

    const rewritten = rewriteLocalMarkdownLinks(text, cwd)

    expect(rewritten).toContain('[a](file:///workspace/project/src/a.ts)')
    expect(rewritten).toContain('[line](file:///workspace/project/README.md#L3)')
    expect(rewritten).toContain('[hash](file:///workspace/project/src/a%23b.ts)')
    expect(rewritten).toContain('[web](https://x.y)')
    expect(rewritten).toContain(inline + '[inline](src/ignored.ts)' + inline)
    expect(rewritten).toContain(fence + 'md\n[fenced](src/ignored.ts)\n' + fence)
    expect(rewritten).toContain('![image](src/image.png)')
  })

  it('leaves assistant Markdown untouched until a streaming turn is complete', () => {
    const t = new Transcript()
    t.start(0)
    t.reasoning('thinking', 1)
    t.text('See [a](src/a.ts)', 2)
    const turn = t.live as TurnEntry
    const cx = { cwd, now: 2, welcome: { tip: '', version: '' }, copy: () => undefined }

    let view = node(entryNode(turn, 'main.turn', cx))
    let md = childrenOf(view, 'md')
    expect(md[0]?.props.text).toBe('See [a](src/a.ts)')
    expect(childrenOf(view, 'section')).toHaveLength(1)

    t.complete({ status: 'complete', text: 'See [a](src/a.ts)' }, 3)
    view = node(entryNode(turn, 'main.turn', cx))
    md = childrenOf(view, 'md')
    expect(md[0]?.props.text).toBe('See [a](file:///workspace/project/src/a.ts)')

    // Cached historical turns must not keep links from another cwd.
    const alternate = node(entryNode(turn, 'main.turn', { ...cx, cwd: '/other' }))
    expect(childrenOf(alternate, 'md')[0]?.props.text).toBe('See [a](file:///other/src/a.ts)')
  })

  it('passes the live Hermes session cwd into the emitted Tern surface', async () => {
    const savedSplash = process.env.HERMES_TUI_SPLASH
    process.env.HERMES_TUI_SPLASH = '0'
    const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
    const app = new App(tern, new GatewayClient(), 'test')
    app.sid = 'session-1'
    app.info = { cwd, model: 'fixture' }
    const running = app.run()
    const surface = tern.surfaces[0]!
    const render = surface.render.bind(surface)
    let latest: View | undefined

    surface.render = view => {
      latest = View.from(view)
      render(view)
    }

    try {
      app.transcript.start(0)
      app.transcript.text('See [a](src/a.ts)', 1)
      app.transcript.complete({ status: 'complete', text: 'See [a](src/a.ts)' }, 2)
      app.changed()
      await new Promise<void>(resolve => setImmediate(resolve))

      const assistant = latest?.regions.find(region => region?.id === 'main')?.children.find(n => n.kind === 'col' && n.props.role === 'omp.assistant')
      const md = assistant?.children.find(n => n.kind === 'md')
      expect(md?.props.text).toBe('See [a](file:///workspace/project/src/a.ts)')
    } finally {
      app.quit()
      await running

      if (savedSplash === undefined) {delete process.env.HERMES_TUI_SPLASH}
      else {process.env.HERMES_TUI_SPLASH = savedSplash}
    }
  })

  it('does not resolve a relative target without an absolute Hermes session cwd', () => {
    expect(rewriteLocalMarkdownLinks('See [a](src/a.ts)', '')).toBe('See [a](src/a.ts)')
  })
})
