import { EventEmitter } from 'node:events'

import { type Op, Session, type WireNode } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import type { ToolCall } from '../model.js'

import { acknowledgeFrames } from './helpers/paint.js'

vi.mock('@tui/lib/history.js', () => ({ append() {}, load: () => [] }))

const at = new Date(2026, 0, 1, 15, 5).getTime()

const settle = async () => {
  for (let i = 0; i < 8; i++) {
    await new Promise<void>(resolve => setImmediate(resolve))
  }
}

interface Fixture {
  hour12?: boolean
  retained?: boolean
  calls?: ToolCall[]
}
interface Harness {
  app: App
  nodes: Map<string, WireNode>
  clock(hour12: boolean | undefined): Promise<void>
}

async function withApp(fixture: Fixture, run: (h: Harness) => Promise<void>) {
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const input = new EventEmitter()
  const nodes = new Map<string, WireNode>()

  const add = (node: WireNode) => {
    nodes.set(node.id, node)
    node.c?.forEach(add)
  }

  const tern = new Session(
    input,
    {
      write(bytes) {
        for (const part of Buffer.from(bytes).toString().split('\x1b_tsp;f;').slice(1)) {
          const frame: { ops: Op[] } = JSON.parse(part.split('\x1b\\')[0]!)

          for (const op of frame.ops) {
            if (op[0] === 'add') {
              add(op[4])
            }

            if (op[0] === 'set') {
              const node = nodes.get(op[1])

              if (!node) {
                throw new Error(`Missing native node ${op[1]}`)
              }

              nodes.set(node.id, { ...node, p: { ...node.p, ...op[2] } })
            }

            if (op[0] === 'del') {
              for (const id of nodes.keys()) {
                if (id === op[1] || id.startsWith(op[1] + '.')) {
                  nodes.delete(id)
                }
              }
            }
          }
        }
      }
    },
    { exitHooks: false, record: '' }
  )

  const clock = (hour12: boolean | undefined) =>
    input.emit(
      'data',
      `\x1b_tsp;r;${JSON.stringify({
        ...tern.caps,
        r: 'hello',
        v: 1,
        term: 'fixture',
        ver: '0',
        features: fixture.retained ? ['settle'] : [],
        hour12
      })}\x1b\\`
    )

  const connecting = tern.handshake()
  clock(fixture.hour12)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockResolvedValue({ items: [] })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.info = { cwd: '/session/project', terminal_backend: 'local' }
  app.transcript.push({ kind: 'user', id: 'stored-user', text: 'Replayed history', at })
  app.transcript.push({
    kind: 'turn',
    id: 'stored-turn',
    rev: 0,
    startedAt: at,
    endedAt: at + 1,
    status: 'done',
    blocks: (fixture.calls ?? []).map(call => ({ kind: 'tool', id: call.id, call }))
  })
  acknowledgeFrames(tern)
  const running = app.run()

  try {
    await settle()
    await run({
      app,
      nodes,
      clock: async hour12 => {
        clock(hour12)
        app.changed()
        await settle()
      }
    })
  } finally {
    app.quit()
    await running

    if (splash === undefined) {
      delete process.env.HERMES_TUI_SPLASH
    } else {
      process.env.HERMES_TUI_SPLASH = splash
    }
  }
}

function props(h: Harness, role: string) {
  const node = [...h.nodes.values()].find(node => node.p?.role === role)

  if (!node?.p) {
    throw new Error(`Missing ${role}`)
  }

  return node.p
}

function code(h: Harness, kind = 'code') {
  return [...h.nodes.values()].filter(node => node.k === kind).map(node => node.p ?? {})
}

function call(name: string, path: string, result: unknown = {}, args: ToolCall['args'] = {}): ToolCall {
  return {
    name,
    id: `${name}-${path}`,
    args: { path, ...args },
    context: path,
    argsText: '',
    startedAt: at,
    status: 'done',
    result
  }
}

// Force a runtime locale opposite to the terminal preference, not a fixture-only clock formatter.
const localeTime = Date.prototype.toLocaleTimeString

describe('terminal clock preferences and path-based syntax', () => {
  it.each([
    { locale: 'en-US', hour12: false },
    { locale: 'en-GB', hour12: true }
  ])('honors terminal hour12=$hour12 despite runtime locale $locale', async ({ locale, hour12 }) => {
    const spy = vi.spyOn(Date.prototype, 'toLocaleTimeString').mockImplementation(function (
      this: Date,
      _locale,
      options
    ) {
      return localeTime.call(this, locale, options)
    })

    try {
      await withApp({ hour12 }, async h => {
        expect(props(h, 'omp.user.time').spans).toEqual([
          { s: 'dim mono', t: localeTime.call(new Date(at), locale, { hour: '2-digit', minute: '2-digit', hour12 }) }
        ])
        expect(props(h, 'omp.user.time').title).toBe(new Date(at).toLocaleString([], { hour12 }))
      })
    } finally {
      spy.mockRestore()
    }
  })

  it.each([false, true])('rebuilds cached history when the negotiated clock changes (retention=$0)', async retained => {
    await withApp({ hour12: false, retained }, async h => {
      const original = props(h, 'omp.user.time').spans
      h.app.changed()
      await settle()
      expect(props(h, 'omp.user.time').spans).toEqual(original)
      await h.clock(true)
      expect(props(h, 'omp.user.time').spans).not.toEqual(original)
      expect(props(h, 'omp.user.time').spans).toEqual([
        { s: 'dim mono', t: new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true }) }
      ])
      await h.clock(false)
      expect(props(h, 'omp.user.time').spans).toEqual(original)
    })
  })

  it('defaults older hosts with no clock preference to 24 hours', async () => {
    await withApp({}, async h => {
      expect(props(h, 'omp.user.time').spans).toEqual([
        { s: 'dim mono', t: new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false }) }
      ])
    })
  })

  it.each(['Dockerfile', 'Makefile', 'src/plugin.zig', 'src/type.nix', 'src/module.tsx', 'unknown.xyz'])(
    'sends the original file path %s without a competing language override',
    async path => {
      await withApp({ calls: [call('read_file', path, { content: '1|source bytes', total_lines: 1 })] }, async h => {
        expect(code(h)).toContainEqual(expect.objectContaining({ path, text: 'source bytes', wrap: true }))
        expect(code(h).find(node => node.path === path)?.lang).toBeUndefined()
        const read = [...h.nodes.values()].find(node => node.k === 'tool' && node.p?.name === 'read')
        expect(read?.p?.href).toBe(`file:///session/project/${path}#L1`)
      })
    }
  )

  it('uses path for writes, single and multi-file diffs and structured search, not href as syntax context', async () => {
    await withApp(
      {
        calls: [
          call('write_file', 'Dockerfile', {}, { content: 'FROM alpine' }),
          call('patch', 'single.zig', { diff: '@@ -1 +1 @@\n-old\n+new' }),
          call('patch', 'multi', {
            files_modified: ['one.nix', 'Makefile'],
            diff: '--- a/one.nix\n+++ b/one.nix\n@@ -1 +1 @@\n-old\n+new\n--- a/Makefile\n+++ b/Makefile\n@@ -1 +1 @@\n-old\n+new'
          }),
          call('search_files', '.', { matches: [{ path: 'source.zig', line: 4, content: 'match' }] })
        ]
      },
      async h => {
        expect(code(h).map(node => node.path)).toEqual(expect.arrayContaining(['Dockerfile', 'source.zig']))
        expect(code(h, 'diff').map(node => node.path)).toEqual(
          expect.arrayContaining(['single.zig', 'one.nix', 'Makefile'])
        )
        const search = code(h).find(node => node.path === 'source.zig')
        expect(search?.href).toBe('file:///session/project/source.zig#L4')
        expect([...code(h), ...code(h, 'diff')].every(node => node.lang === undefined)).toBe(true)
      }
    )
  })

  it('keeps dense search output lossless while selecting syntax separately per file', async () => {
    const text = 'Dockerfile\n  1: FROM alpine\nsource.zig\n  5: const x = 1;\n'
    await withApp(
      {
        calls: [
          call('search_files', '.', {
            matches_text: text,
            matches_format: 'path-grouped: each file path on its own line'
          })
        ]
      },
      async h => {
        const blocks = code(h).filter(node => node.path)
        expect(blocks.map(node => node.path)).toEqual(['Dockerfile', 'source.zig'])
        expect(blocks.map(node => node.text).join('')).toBe(text)
      }
    )
  })

  it('retains explicit bash/python/json language for non-file snippets even if tool args contain a path', async () => {
    await withApp(
      {
        calls: [
          call('terminal', 'not-a-script.nix', { output: 'done', exit_code: 0 }, { command: 'pwd' }),
          call('execute_code', 'not-python.zig', { output: 'done' }, { code: 'print(1)' }),
          call('unknown_tool', 'not-json.sh', { object: true })
        ]
      },
      async h => {
        expect(code(h).map(node => node.lang)).toEqual(expect.arrayContaining(['bash', 'python', 'json']))
        expect(code(h).every(node => node.path === undefined)).toBe(true)
      }
    )
  })

  it('keeps old-host/unknown-format output readable without requiring a new kind or capability', async () => {
    await withApp(
      {
        calls: [
          call('read_file', 'unknown.xyz', { content: '1|literal fallback' }),
          call('search_files', '.', { matches_text: 'opaque search response' })
        ]
      },
      async h => {
        expect(code(h)).toContainEqual(expect.objectContaining({ path: 'unknown.xyz', text: 'literal fallback' }))
        expect(code(h)).toContainEqual(expect.objectContaining({ lang: 'text', text: 'opaque search response' }))
        expect(code(h).every(node => typeof node.text === 'string')).toBe(true)
      }
    )
  })
})
