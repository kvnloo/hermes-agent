import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { type Op, Session, type Surface, type WireNode } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { replay } from '../../bench/replay.js'
import { App } from '../app.js'
import type { TurnEntry } from '../model.js'
import * as transcriptView from '../view/transcript.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-retention-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const tick = () => new Promise<void>(resolve => setImmediate(resolve))

const settle = async () => {
  for (let i = 0; i < 6; i++) {
    await tick()
  }
}

/** Strict wire peer: unknown targets/siblings are errors, not silently accepted mocks. */
class Wire {
  readonly nodes = new Map<string, WireNode>([['hermes', { id: 'hermes', k: 'col' }]])
  readonly children = new Map<string, string[]>()
  readonly ops: Op[] = []
  readonly settled = new Set<string>()

  remove(id: string): void {
    for (const child of this.children.get(id) ?? []) {
      this.remove(child)
    }

    this.nodes.delete(id)
    this.children.delete(id)
    this.settled.delete(id)

    for (const [parent, children] of this.children) {
      this.children.set(
        parent,
        children.filter(child => child !== id)
      )
    }
  }

  write(bytes: Uint8Array | string): void {
    const data = Buffer.from(bytes).toString()

    for (const body of data.split('\x1b_tsp;f;').slice(1)) {
      const frame = JSON.parse(body.split('\x1b\\')[0]!) as { ops: Op[] }

      for (const op of frame.ops) {
        this.ops.push(op)

        if (op[0] === 'add') {
          expect(this.nodes.has(op[1]), `duplicate add ${op[1]}`).toBe(false)
          expect(this.nodes.has(op[2]), `missing parent ${op[2]}`).toBe(true)
          const siblings = this.children.get(op[2]) ?? []
          const before = op[3] === null ? siblings.length : siblings.indexOf(op[3])
          expect(before, `missing sibling ${op[3]}`).toBeGreaterThanOrEqual(0)
          siblings.splice(before, 0, op[1])
          this.children.set(op[2], siblings)

          const add = (node: WireNode) => {
            this.nodes.set(node.id, node)
            this.children.set(node.id, node.c?.map(child => child.id) ?? [])
            node.c?.forEach(add)
          }

          add(op[4])
        } else if (op[0] === 'del') {
          expect(this.nodes.has(op[1]), `delete missing ${op[1]}`).toBe(true)
          this.remove(op[1])
        } else if (['text', 'set', 'settle', 'reveal', 'scroll'].includes(op[0])) {
          expect(this.nodes.has(op[1]!), `unknown ${op[0]} ${op[1]}`).toBe(true)

          if (op[0] === 'settle') {
            this.settled.add(op[1])
          }

          if (op[0] === 'text') {
            const node = this.nodes.get(op[1])!
            this.nodes.set(op[1], {
              ...node,
              p: { ...node.p, text: op[2] === 'append' ? String(node.p?.text ?? '') + op[3] : op[3] }
            })
          }
        }
      }
    }
  }
}

function history(app: App, count = 25): TurnEntry[] {
  const turns: TurnEntry[] = []

  for (let i = 0; i < count; i++) {
    app.transcript.push({ kind: 'user', id: `user${i}`, text: `Prompt ${i}`, at: 1 })

    const turn: TurnEntry = {
      kind: 'turn',
      id: `turn${i}`,
      rev: 0,
      startedAt: 1,
      endedAt: 2,
      status: 'done',
      blocks: [{ kind: 'text', id: 'answer', text: `Answer ${i}` }]
    }

    app.transcript.push(turn)
    turns.push(turn)
  }

  return turns
}

async function withApp(
  seed: (app: App) => void,
  run: (app: App, surface: Surface, wire: Wire, input: EventEmitter, gw: GatewayClient) => Promise<void>
) {
  const input = new EventEmitter()
  const wire = new Wire()
  const tern = new Session(input, { write: bytes => wire.write(bytes) }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0', features: ['settle'], apc: 1_048_576, credits: 8 })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockResolvedValue({ items: [], jobs: [] })
  const app = new App(tern, gw, 'test')
  app.sid = 'retention-session'
  seed(app)
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!

  try {
    await settle()
    await run(app, surface, wire, input, gw)
  } finally {
    app.quit()
    await running
  }
}

function event(input: EventEmitter, body: object): void {
  input.emit('data', `\x1b_tsp;e;${JSON.stringify(body)}\x1b\\`)
}

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  if (isolated.splash === undefined) {
    delete process.env.HERMES_TUI_SPLASH
  } else {
    process.env.HERMES_TUI_SPLASH = isolated.splash
  }

  rmSync(isolated.home, { recursive: true, force: true })
})

describe('long-session retention (App and real SDK)', () => {
  it('settles entries older than 20 completed turns, never running or failed/unacknowledged state', async () => {
    await withApp(
      app => {
        const turns = history(app, 30)
        turns[0]!.status = 'live'
        turns[1]!.status = 'error'
        turns[2]!.blocks.push({
          kind: 'tool',
          id: 'running',
          call: {
            id: 'running',
            name: 'bash',
            args: {},
            argsText: '',
            context: '',
            startedAt: 1,
            status: 'running'
          }
        })
        turns[3]!.blocks.push({
          kind: 'tool',
          id: 'failed',
          call: {
            id: 'failed',
            name: 'bash',
            args: {},
            argsText: '',
            context: '',
            startedAt: 1,
            status: 'error'
          }
        })
      },
      async (_app, _surface, wire) => {
        for (let i = 0; i < 4; i++) {
          expect(wire.settled.has(`main.turn${i}`)).toBe(false)
          expect(wire.settled.has(`main.user${i}`)).toBe(false)
        }

        expect(wire.settled.has('main.turn4')).toBe(true)
        expect(wire.settled.has('main.user4')).toBe(true)
        expect(wire.settled.has('main.turn9')).toBe(true)
        expect(wire.settled.has('main.turn10')).toBe(false)
        expect(wire.settled.has('main.turn29')).toBe(false)
      }
    )
  })

  it('does not settle new old entries while an approval is pending', async () => {
    await withApp(
      () => {},
      async (app, _surface, wire, _input, gw) => {
        gw.emit('request', {
          id: 'approval',
          method: 'approval',
          params: { session_id: app.sid, command: 'printf fixture' },
          respond() {},
          fail() {}
        })
        history(app)
        app.changed()
        await settle()
        expect(app.overlays.some(overlay => overlay.placement === 'dock')).toBe(true)
        expect(wire.settled.size).toBe(0)
        app.close(app.overlays[0]!)
        await settle()
        expect(wire.settled.has('main.turn0')).toBe(true)
      }
    )
  })

  it('never rebuilds settled nodes on tokens, and preserves main/scroll identity', async () => {
    const builds = vi.spyOn(transcriptView, 'projectedEntryNodes')

    try {
      await withApp(
        app => {
          history(app)
        },
        async (app, _surface, wire, _input, gw) => {
          const oldBuilds = () => builds.mock.calls.filter(([entry]) => entry.id === 'turn0').length
          const initial = oldBuilds()
          const from = wire.ops.length

          for (let i = 0; i < 10; i++) {
            gw.emit('event', { type: 'message.delta', session_id: app.sid, payload: { text: `token${i}` } })
            await settle()
          }

          expect(initial).toBe(1)
          expect(oldBuilds()).toBe(initial)
          expect(wire.ops.slice(from).some(op => (op[0] === 'add' || op[0] === 'del') && op[1] === 'main')).toBe(false)
          expect(wire.ops.slice(from).some(op => op[0] === 'move' || op[0] === 'reveal')).toBe(false)
        }
      )
    } finally {
      builds.mockRestore()
    }
  })

  it('reloads exactly the evicted IDs in transcript order only on an explicit history request', async () => {
    await withApp(
      app => {
        history(app)
      },
      async (app, surface, wire, input) => {
        const ids = ['main.user1', 'main.turn0', 'main.user0', 'main.turn1']

        for (const id of ids) {
          wire.remove(id)
        }

        event(input, { ev: 'gone', sf: 'hermes', ids })
        await settle()
        const before = wire.ops.length
        app.changed()
        await settle()
        expect(wire.ops.slice(before).filter(op => op[0] === 'add')).toHaveLength(0)
        expect(wire.nodes.get('main.retention-load')).toMatchObject({
          k: 'el', p: { tag: 'button', aria: 'Load older history', actions: { click: 'click' } }
        })

        const action = surface.dispatch({
          ev: 'action',
          sf: 'hermes',
          id: 'main.retention-load',
          act: 'click',
          raw: {}
        })

        expect(action).toBeTypeOf('function')
        await action!()
        await settle()

        const restored = wire.ops
          .slice(before)
          .filter(op => op[0] === 'add' && ids.includes(op[1]))
          .map(op => op[1])

        expect(new Set(restored)).toEqual(new Set(ids))
        expect(restored).toHaveLength(ids.length)
        expect(wire.children.get('main')?.slice(0, 4)).toEqual(['main.user0', 'main.turn0', 'main.user1', 'main.turn1'])
        expect(wire.nodes.has('main.retention-load')).toBe(false)
      }
    )
  })

  it('reloads a bounded page via registry Ctrl+Home without changing the composer', async () => {
    await withApp(
      app => {
        history(app, 50)
      },
      async (app, _surface, wire, input) => {
        const ids = [...wire.settled]
        ids.forEach(id => wire.remove(id))
        event(input, { ev: 'gone', sf: 'hermes', ids })
        await settle()
        app.composer.set('keep this draft', 4)
        const start = wire.ops.length
        input.emit('data', '\x1b[1;5H')
        await settle()
        const adds = wire.ops.slice(start).filter(op => op[0] === 'add' && ids.includes(op[1]))
        expect(adds).toHaveLength(40)
        expect(wire.ops.slice(start)).toContainEqual(['reveal', 'main.user10', 'start'])
        expect(wire.nodes.has('main.retention-load')).toBe(true)
        expect(app.composer.text).toBe('keep this draft')
        expect(app.composer.cursor).toBe(4)
        expect(wire.settled.has('main.turn10')).toBe(false)
        app.olderHistory()
        await settle()
        expect(wire.settled.has('main.turn10')).toBe(true)
        expect(wire.settled.has('main.turn0')).toBe(false)
        expect(wire.nodes.has('main.retention-load')).toBe(false)
      }
    )
  })

  it('ignores foreign/unknown evictions and never acts on stale removed entry handlers', async () => {
    await withApp(
      app => {
        history(app)
      },
      async (app, surface, wire, input) => {
        event(input, { ev: 'gone', sf: 'other', ids: ['main.turn0'] })
        event(input, { ev: 'gone', sf: 'hermes', ids: ['main.unknown'] })
        await settle()
        expect(wire.nodes.has('main.retention-load')).toBe(false)

        const stale = surface.dispatch({
          ev: 'action',
          sf: 'hermes',
          id: 'main.turn0.answer-actions.copy',
          act: 'click',
          raw: {}
        })

        app.transcript.clear()
        await stale?.()
        app.changed()
        await settle()
        expect(wire.nodes.has('main.turn0')).toBe(false)
        expect(wire.children.get('main')).toEqual([])
      }
    )
  })

  it('updates a late settled turn by ID, then settles it again; evicted changes wait for reload', async () => {
    await withApp(
      app => {
        history(app)
      },
      async (app, _surface, wire, input) => {
        const turn = app.transcript.entries.find(entry => entry.id === 'turn0')!
        expect(turn.kind).toBe('turn')

        if (turn.kind !== 'turn') {
          throw new Error('fixture turn')
        }

        const from = wire.ops.length
        app.transcript.steer('late correction', turn)
        app.changed()
        await settle()
        expect(wire.ops.slice(from)).toContainEqual(['settle', 'main.turn0'])
        expect(wire.nodes.has(`main.turn0.${turn.blocks.at(-1)!.id}`)).toBe(true)
        wire.remove('main.turn0')
        event(input, { ev: 'gone', sf: 'hermes', ids: ['main.turn0'] })
        await settle()
        const evictedAt = wire.ops.length
        app.transcript.steer('after eviction', turn)
        app.changed()
        await settle()
        expect(wire.ops.slice(evictedAt).some(op => op[1] === 'main.turn0')).toBe(false)
        app.olderHistory()
        await settle()
        expect(wire.nodes.has(`main.turn0.${turn.blocks.at(-1)!.id}`)).toBe(true)
      }
    )
  })

  it('keeps Copy handlers on settled entries without retaining their descriptions', async () => {
    await withApp(app => { history(app) }, async (_app, surface) => {
      const output: string[] = []

      const write = vi.spyOn(process.stdout, 'write').mockImplementation(bytes => { output.push(String(bytes));

 return true })

      try {
        const action = surface.dispatch({ ev: 'action', sf: 'hermes', id: 'main.turn0.answer-actions.copy', act: 'click', raw: {} })
        await action?.()
        expect(output).toContain(`\x1b]52;c;${Buffer.from('Answer 0').toString('base64')}\x07`)
      } finally { write.mockRestore() }
    })
  })

  it('routes native action descendants through their emitted roots in a long session', async () => {
    await withApp(app => { history(app, 240) }, async (app, surface) => {
      const output: string[] = []
      const write = vi.spyOn(process.stdout, 'write').mockImplementation(bytes => {
        output.push(String(bytes))

        return true
      })

      try {
        for (const index of [0, 9, 100, 239]) {
          const action = surface.dispatch({
            ev: 'action', sf: 'hermes', id: `main.turn\${index}.answer-actions.copy`,
            act: 'click', raw: {}
          })
          expect(action, `missing \${index} action`).toBeTypeOf('function')
          await action?.()
          expect(output).toContain(`\x1b]52;c;\${Buffer.from(`Answer \${index}`).toString('base64')}\x07`)
        }

        // Not a child of an emitted root. "turn23" must not steal sibling actions.
        expect(surface.dispatch({
          ev: 'action', sf: 'hermes', id: 'main.turn23extra.answer-actions.copy',
          act: 'click', raw: {}
        })).toBeUndefined()

        app.transcript.clear()
        app.changed()
        await settle()
        expect(surface.dispatch({
          ev: 'action', sf: 'hermes', id: 'main.turn100.answer-actions.copy',
          act: 'click', raw: {}
        })).toBeUndefined()
      } finally {
        write.mockRestore()
      }
    })
  })

  it('forgets evicted removed entries on clear without targeting unknown nodes', async () => {
    await withApp(app => { history(app) }, async (app, _surface, wire, input) => {
      wire.remove('main.turn0')
      event(input, { ev: 'gone', sf: 'hermes', ids: ['main.turn0'] })
      await settle()
      const start = wire.ops.length
      app.transcript.clear()
      app.changed()
      await settle()
      expect(wire.ops.slice(start)).not.toContainEqual(['del', 'main.turn0'])
      expect(wire.children.get('main')).toEqual([])
      app.olderHistory()
      await settle()
      expect(wire.children.get('main')).toEqual([])
    })
  })

  it.each([false, true])('flushes final retained history with credits held (quit hidden: %s)', async quitBeforeAck => {
    const result = await replay({ retention: true, history: 2000, hidden: true, quitBeforeAck })
    expect(result.droppedSemanticEvents).toBe(0)
    expect(result.toolRecords).toBe(20)
  }, 15_000)

  it('builds cold history once with size-independent streaming work and bytes', async () => {
    // Wall-clock p95 belongs to bench:retention, not parallel unit-worker scheduling.
    const builds = vi.spyOn(transcriptView, 'projectedEntryNodes')
    const rows: Awaited<ReturnType<typeof replay>>[] = []
    const streamingBuilds: number[] = []

    try {
      for (const count of [200, 2000]) {
        builds.mockClear()
        const row = await replay({ retention: true, history: count })
        const historical = builds.mock.calls.filter(([entry]) => entry.id.startsWith('history'))
        const perEntry = new Map<string, number>()

        for (const [entry] of historical) {
          perEntry.set(entry.id, (perEntry.get(entry.id) ?? 0) + 1)
        }

        expect(perEntry.size).toBe(count)

        // The retained hot window is 20 turns (40 alternating user/assistant entries).
        for (let i = 0; i < count - 40; i++) {
          expect(perEntry.get(`history${i}`)).toBe(1)
        }

        streamingBuilds.push(historical.length - count)
        expect(row.droppedSemanticEvents).toBe(0)
        expect(row.toolRecords).toBe(20)
        rows.push(row)
      }

      expect(streamingBuilds[0]).toBeGreaterThan(0)
      expect(streamingBuilds[1]).toBe(streamingBuilds[0])
      const bytes = rows.map(row => row.streamingBytes)
      expect(Math.max(...bytes) / Math.min(...bytes)).toBeLessThan(1.01)
    } finally {
      builds.mockRestore()
    }
  }, 15_000)
})
