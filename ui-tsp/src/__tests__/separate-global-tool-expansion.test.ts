import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { type Op, Session, type WireNode } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import type { ToolCall, TurnEntry } from '../model.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-tool-presentation-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

afterAll(() => {
  if (isolated.previous === undefined) {delete process.env.HERMES_HOME}
  else {process.env.HERMES_HOME = isolated.previous}

  if (isolated.splash === undefined) {delete process.env.HERMES_TUI_SPLASH}
  else {process.env.HERMES_TUI_SPLASH = isolated.splash}

  rmSync(isolated.home, { recursive: true, force: true })
})

const paint = async () => {
  for (let i = 0; i < 8; i++) {await new Promise<void>(resolve => setImmediate(resolve))}
}

/** Apply the actual SDK frames, including incremental retention frames. */
class Peer {
  readonly nodes = new Map<string, WireNode>()
  readonly children = new Map<string, string[]>()
  readonly settled = new Set<string>()
  readonly ops: Op[] = []

  remove(id: string): void {
    for (const child of this.children.get(id) ?? []) {this.remove(child)}
    this.nodes.delete(id)
    this.children.delete(id)
    this.settled.delete(id)

    for (const [parent, children] of this.children) {this.children.set(parent, children.filter(child => child !== id))}
  }

  write(bytes: Uint8Array | string): void {
    for (const packet of Buffer.from(bytes).toString().split('\x1b_tsp;f;').slice(1)) {
      const frame = JSON.parse(packet.split('\x1b\\')[0]!) as { ops: Op[] }

      for (const op of frame.ops) {
        this.ops.push(op)

        if (op[0] === 'add') {
          expect(this.nodes.has(op[1]), `duplicate ${op[1]}`).toBe(false)

          const add = (n: WireNode) => {
            this.nodes.set(n.id, n)
            this.children.set(n.id, n.c?.map(c => c.id) ?? [])
            n.c?.forEach(add)
          }

          add(op[4])
        } else if (op[0] === 'del') {
          expect(this.nodes.has(op[1]), `missing ${op[1]}`).toBe(true)
          this.remove(op[1])

          continue
        } else if (op[0] === 'set' || op[0] === 'text') {
          const n = this.nodes.get(op[1])

          if (!n) {throw new Error(`Unknown ${op[0]} ${op[1]}`)}
          this.nodes.set(op[1], { ...n, p: { ...n.p, ...(op[0] === 'set' ? op[2] : { text: op[2] === 'append' ? String(n.p?.text ?? '') + op[3] : op[3] }) } })
        } else if (op[0] === 'settle') {
          expect(this.nodes.has(op[1])).toBe(true)
          this.settled.add(op[1])
        }

        if (op[0] === 'add' || op[0] === 'move') {
          for (const [parent, children] of this.children) {this.children.set(parent, children.filter(id => id !== op[1]))}
          const siblings = this.children.get(op[2]) ?? []
          const at = op[3] === null ? siblings.length : siblings.indexOf(op[3])
          expect(at, `missing sibling ${op[3]}`).toBeGreaterThanOrEqual(0)
          siblings.splice(at, 0, op[1])
          this.children.set(op[2], siblings)
        }
      }
    }
  }

  tools(): WireNode[] { return [...this.nodes.values()].filter(n => n.k === 'tool') }
}

function turn(id = 'turn'): TurnEntry {
  return {
    kind: 'turn', id, rev: 0, status: 'done', startedAt: 1, endedAt: 100,
    usage: { input: 5, output: 5, total: 10 },
    blocks: [
      { kind: 'thinking', id: 'thought1', text: 'First thought', startedAt: 1, endedAt: 2 },
      { kind: 'thinking', id: 'thought2', text: 'Second thought', startedAt: 2, endedAt: 3 },
      ...['one', 'two'].map(call => ({ kind: 'tool' as const, id: call, call: {
        id: call, name: 'read_file', args: { path: `${call}.ts` }, argsText: '', context: '', status: 'done' as const,
        startedAt: 1, result: { content: 'one\ntwo\nthree\nfour\nfive\nsix\nseven\neight\nnine\nten' }
      } })),
      { kind: 'text', id: 'answer', text: 'Final answer' }
    ]
  }
}

interface Harness {
  app: App
  gw: GatewayClient
  peer: Peer
  input: EventEmitter
  press(modifiers: number): Promise<void>
  event(body: object): Promise<void>
}

async function withApp(retention: boolean, run: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const peer = new Peer()
  const tern = new Session(input, { write: bytes => peer.write(bytes) }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0', features: retention ? ['settle'] : [], credits: 8, apc: 1_048_576 })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'session.resume') {return { session_id: 'resumed', messages: [
      ...['one', 'two'].map(id => ({ role: 'tool', tool_call_id: id, name: 'read_file', args: { path: `${id}.ts` }, content: { content: 'restored result' } })),
      { role: 'assistant', content: 'Resumed answer' }
    ] }}

    return { items: [], jobs: [] }
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'fixture'
  app.transcript.push(turn())
  acknowledgeFrames(tern)
  const running = app.run()

  try {
    await paint()
    await run({ app, gw, peer, input,
      press: async modifiers => { input.emit('data', `\x1b[111;${modifiers}u`); await paint() },
      event: async body => { input.emit('data', `\x1b_tsp;e;${JSON.stringify(body)}\x1b\\`); await paint() }
    })
  } finally {
    app.quit()
    await running
  }
}

describe.each([false, true])('independent tool presentation (retention %s)', retention => {
  it('projects two work siblings, preserves thought chains, answer/usage order, and globally expands every tool', async () => {
    await withApp(retention, async ({ app, peer, press }) => {
      expect(peer.children.get('main')?.slice(0, 4)).toEqual(['main.turn', 'main.turn~one', 'main.turn~two', 'main.turn~two~after'])
      expect(peer.children.get('main.turn')).toEqual(['main.turn.thought1', 'main.turn.thought2'])
      expect(peer.children.get('main.turn~two~after')?.slice(0, 2)).toEqual(['main.turn~two~after.answer', 'main.turn~two~after.usage'])
      const before = JSON.stringify(app.transcript.entries)
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([true, true])
      await press(5)
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([false, false])
      await press(6)
      expect(peer.tools().map(n => n.p?.hidden)).toEqual([true, true])
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([false, false])
      await press(5)
      await press(6)
      expect(peer.tools().every(n => !n.p?.hidden)).toBe(true)
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([true, true])
      expect(JSON.stringify(app.transcript.entries)).toBe(before)
    })
  })

  it('synchronizes pointer folds in both directions with all-tool keyboard expansion', async () => {
    await withApp(retention, async ({ peer, event, press }) => {
      await event({ ev: 'toggle', sf: 'hermes', id: 'main.turn~one', key: 'turn~one', collapsed: false })
      await press(5)
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([false, false])

      for (const id of ['one', 'two']) {await event({ ev: 'toggle', sf: 'hermes', id: `main.turn~${id}`, key: `turn~${id}`, collapsed: true })}
      await press(5)
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([false, false])
      await press(5)
      expect(peer.tools().map(n => n.p?.collapsed)).toEqual([true, true])
    })
  })

  it('keeps running, failed, unknown, background and approval state outside hidden/foldable work', async () => {
    await withApp(retention, async ({ app, peer, press, gw }) => {
      const active = turn('active')

      const states: Pick<ToolCall, 'id' | 'name' | 'status' | 'result'>[] = [
        { id: 'running', name: 'read_file', status: 'running', result: {} },
        { id: 'failed', name: 'read_file', status: 'error', result: { error: 'failed' } },
        { id: 'unknown', name: 'read_file', status: 'unknown', result: {} },
        { id: 'background', name: 'terminal', status: 'done', result: { status: 'yielded_to_background', session_id: 'bg' } },
        { id: 'exit', name: 'terminal', status: 'done', result: { exit_code: 2 } }
      ]

      const calls: ToolCall[] = states.map(call => ({ ...call, args: {}, argsText: '', context: '', startedAt: 1 }))

      active.blocks = calls.map(call => ({ kind: 'tool', id: call.id, call }))
      app.transcript.push(active)
      app.changed()
      await press(6)
      expect(peer.tools().filter(n => n.id.startsWith('main.active')).every(n => !n.p?.hidden)).toBe(true)
      expect(peer.children.get('main')?.filter(id => id.startsWith('main.active~')).every(id => peer.nodes.get(id)?.k === 'col')).toBe(true)
      gw.emit('request', { id: 'approval', method: 'approval', params: { session_id: app.sid, command: 'printf fixture' }, respond() {}, fail() {} })
      await paint()
      expect(app.overlays.some(o => o.placement === 'dock')).toBe(true)
      expect(peer.tools().every(n => !n.p?.hidden)).toBe(true)
    })
  })

  it('processes hidden completion, late errors and resume without dropping results or stale fold identity', async () => {
    await withApp(retention, async ({ app, gw, peer, press }) => {
      await press(6)
      gw.emit('event', { type: 'tool.start', session_id: app.sid, payload: { tool_id: 'live', name: 'read_file', args: { path: 'live.ts' } } })
      await paint()
      expect(peer.tools().find(n => n.id.endsWith('.live'))).toMatchObject({ p: { status: 'running' } })
      gw.emit('event', { type: 'tool.complete', session_id: app.sid, payload: { tool_id: 'live', name: 'read_file', result: { content: 'Completed while hidden' } } })
      await paint()
      expect(peer.tools().find(n => n.id.endsWith('~live'))?.p?.hidden).toBe(true)
      expect(JSON.stringify(app.transcript.entries)).toContain('Completed while hidden')
      gw.emit('event', { type: 'tool.complete', session_id: app.sid, payload: { tool_id: 'live', name: 'read_file', result: { error: 'late error' }, error: true } })
      await paint()
      expect(peer.tools().find(n => n.id.endsWith('.live'))).toMatchObject({ p: { status: 'error' } })
      await app.resume('stored')
      await paint()
      expect(peer.tools()).toHaveLength(2)
      expect(peer.tools().every(n => n.p?.hidden)).toBe(true)
      await press(6)
      expect(peer.tools().every(n => !n.p?.hidden)).toBe(true)
      expect(JSON.stringify(app.transcript.entries)).toContain('restored result')
    })
  })
})

it('retains all projection parts across pending approval, partial eviction and explicit reload', async () => {
  await withApp(true, async ({ app, gw, peer, event, press }) => {
    gw.emit('request', { id: 'approval', method: 'approval', params: { session_id: app.sid, command: 'printf fixture' }, respond() {}, fail() {} })

    for (let i = 0; i < 25; i++) {app.transcript.push(turn(`history${i}`))}
    app.changed()
    await paint()
    expect(peer.settled.has('main.turn~one')).toBe(false)
    app.close(app.overlays[0]!)
    await paint()
    expect(peer.settled.has('main.turn~one')).toBe(true)
    peer.remove('main.turn~one')
    await event({ ev: 'gone', sf: 'hermes', ids: ['main.turn~one'] })
    const from = peer.ops.length
    await press(6)
    expect(peer.ops.slice(from).some(op => op[1] === 'main.turn~one')).toBe(false)
    app.olderHistory()
    await paint()
    expect(peer.nodes.get('main.turn~one')?.p?.hidden).toBe(true)
    expect(peer.children.get('main')?.slice(0, 4)).toEqual(['main.turn', 'main.turn~one', 'main.turn~two', 'main.turn~two~after'])
  })
})
