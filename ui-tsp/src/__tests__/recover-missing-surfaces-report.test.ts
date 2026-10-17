import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { node, type Op, Session, type Surface, type WireNode } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'
import { approvalPrompt } from '../overlays/approval.js'
import { openSettings } from '../overlays/settings.js'
import { ACK_STALL_MS, MAX_SURFACE_RECOVERIES, SurfaceProtocol } from '../surface-protocol.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-surface-recovery-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const tick = () => new Promise<void>(resolve => setImmediate(resolve))

async function painted() {
  for (let i = 0; i < 8; i++) {
    await tick()
  }
}

/** Separate documents per epoch; unknown targets and duplicate adds fail the test. */
class Peer {
  readonly documents = new Map<string, Map<string, WireNode>>()
  readonly frames: { sf: string; s: number; ops: Op[] }[] = []
  readonly palettes: { sf: string; [key: string]: unknown }[] = []

  remove(sf: string, id: string) {
    const nodes = this.documents.get(sf)!
    const root = nodes.get(id)

    for (const child of root?.c ?? []) {
      this.remove(sf, child.id)
    }

    // A later add might have populated descendants independently of the original wire subtree.
    for (const key of [...nodes.keys()]) {
      if (key.startsWith(`${id}.`)) {
        nodes.delete(key)
      }
    }

    nodes.delete(id)
  }

  write(bytes: Uint8Array | string) {
    const data = Buffer.from(bytes).toString()

    for (const message of data.split('\x1b_tsp;').slice(1)) {
      const verb = message[0]

      if (!['o', 'f', 't'].includes(verb!)) {
        continue
      }

      const body = JSON.parse(message.slice(2).split('\x1b\\')[0]!)

      if (verb === 'o') {
        this.documents.set(body.id, new Map([[body.id, { id: body.id, k: 'col' }]]))
      } else if (verb === 't') {
        this.palettes.push(body)
      } else {
        this.frames.push(body)
        const nodes = this.documents.get(body.sf)!

        for (const op of body.ops as Op[]) {
          if (op[0] === 'add') {
            expect(nodes.has(op[1]), `duplicate ${op[1]}`).toBe(false)
            expect(nodes.has(op[2]), `missing parent ${op[2]}`).toBe(true)

            if (op[3] !== null) {
              expect(nodes.has(op[3]), `missing sibling ${op[3]}`).toBe(true)
            }

            const add = (node: WireNode) => {
              nodes.set(node.id, node)
              node.c?.forEach(add)
            }

            add(op[4])
          } else if (op[0] === 'del') {
            expect(nodes.has(op[1]), `missing del ${op[1]}`).toBe(true)
            this.remove(body.sf, op[1])
          } else if (['set', 'text', 'settle', 'scroll', 'reveal', 'focus'].includes(op[0]) && op[1] !== null) {
            expect(nodes.has(op[1]!), `unknown ${op[0]} ${op[1]}`).toBe(true)
          }
        }
      }
    }
  }
}

interface Harness {
  app: App
  tern: Session
  gw: GatewayClient
  peer: Peer
  event(body: object): Promise<void>
  batch(events: object[]): Promise<void>
  surface(): Surface
}

async function withApp(
  run: (h: Harness) => Promise<void>,
  options: { auto?: boolean; retention?: boolean; credits?: number } = {}
) {
  const input = new EventEmitter()
  const peer = new Peer()
  const tern = new Session(input, { write: bytes => peer.write(bytes) }, { exitHooks: false, record: '' })
  const hello = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0', features: options.retention === false ? [] : ['settle'], credits: options.credits ?? 8, apc: 1048576 })}\x1b\\`
  )
  expect(await hello).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockResolvedValue({ items: [], jobs: [], fields: {}, profile: 'fixture' })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'

  if (options.auto !== false) {
    acknowledgeFrames(tern)
  }

  const running = app.run()

  const h: Harness = {
    app,
    tern,
    gw,
    peer,
    surface: () => tern.surfaces[0]!,
    batch: async events => {
      input.emit('data', events.map(body => `\x1b_tsp;e;${JSON.stringify(body)}\x1b\\`).join(''))
      await painted()
    },
    event: async body => {
      input.emit('data', `\x1b_tsp;e;${JSON.stringify(body)}\x1b\\`)
      await painted()
    }
  }

  try {
    await painted()
    await run(h)
  } finally {
    vi.useRealTimers()
    app.quit()
    await running
  }
}

function history(app: App) {
  for (let i = 0; i < 25; i++) {
    app.transcript.push({ kind: 'user', id: `user${i}`, text: `Prompt ${i}`, at: 1 })
    app.transcript.push({
      kind: 'turn',
      id: `turn${i}`,
      rev: 0,
      startedAt: 1,
      endedAt: 2,
      status: 'done',
      blocks: [{ kind: 'text', id: 'answer', text: `Answer ${i}` }]
    })
  }

  app.changed()
}

afterAll(() => {
  for (const [key, value] of [
    ['HERMES_HOME', isolated.previous],
    ['HERMES_TUI_SPLASH', isolated.splash]
  ]) {
    if (value === undefined) {
      delete process.env[key!]
    } else {
      process.env[key!] = value
    }
  }

  rmSync(isolated.home, { recursive: true, force: true })
})

describe('surface protocol recovery', () => {
  it.each([
    { ev: 'error', sf: 'hermes', s: 1, op: 0, msg: 'bad node kind' },
    { ev: 'error', sf: 'hermes', msg: 23 }
  ])('reports a rejected or malformed operation and fails closed: %j', async event => {
    const diagnostic = vi.spyOn(process.stderr, 'write').mockReturnValue(true)

    try {
      await withApp(async h => {
        await h.event(event)
        const frames = h.peer.frames.length
        h.app.composer.set('must not submit unseen input')
        h.app.changed()
        await painted()
        expect(h.peer.frames).toHaveLength(frames)
        expect(h.app.transcript.entries.some(e => e.kind === 'notice' && e.text.includes('Tern protocol'))).toBe(true)
        expect(diagnostic).toHaveBeenCalled()
      })
    } finally {
      diagnostic.mockRestore()
    }
  })

  it('keeps evicted settled children cold, restores active roots and descendants without unknown-node ops', async () => {
    await withApp(async h => {
      history(h.app)
      await painted()
      const sf = h.surface().id
      h.peer.remove(sf, 'main.turn0')
      await h.event({ ev: 'gone', sf, ids: ['main.turn0'] })
      expect(h.peer.documents.get(sf)!.has('main.turn0')).toBe(false)
      expect(h.peer.documents.get(sf)!.has('main.retention-load')).toBe(true)
      h.peer.remove(sf, 'main.turn24')
      await h.event({ ev: 'gone', sf, ids: ['main.turn24'] })
      expect(h.peer.documents.get(sf)!.has('main.turn24')).toBe(true)
      h.peer.remove(sf, INPUT_ID)
      await h.event({ ev: 'gone', sf, ids: [INPUT_ID] })
      expect(h.peer.documents.get(sf)!.has(INPUT_ID)).toBe(true)
      h.peer.remove(sf, 'main')
      await h.event({ ev: 'gone', sf, ids: ['main'] })
      expect(h.peer.documents.get(sf)!.has('main.turn24')).toBe(true)
      expect(h.tern.surfaces).toHaveLength(1)
    })
  })

  it.each([true, false])(
    'recreates a whole missing surface with palette, chrome, draft, and safe history (retention=%s)',
    async retention => {
      await withApp(
        async h => {
          history(h.app)
          h.app.composer.set('draft survives', 5)
          h.gw.emit('event', {
            type: 'skin.changed',
            payload: { name: 'recovery-palette', colors: { accent: '#aabbcc' } }
          })
          await painted()
          const old = h.surface()
          await h.event({ ev: 'gone', sf: old.id, ids: [old.id] })
          const fresh = h.surface()
          expect(fresh.id).not.toBe(old.id)
          expect(old.closed).toBe(true)
          expect(h.peer.palettes.at(-1)).toMatchObject({ sf: fresh.id, name: { dark: 'recovery-palette' } })
          expect(h.peer.documents.get(fresh.id)!.has(INPUT_ID)).toBe(true)
          expect(h.peer.documents.get(fresh.id)!.has('main.turn24')).toBe(true)
          expect(h.peer.frames.filter(f => f.sf === fresh.id).flatMap(f => f.ops)).toContainEqual(['focus', INPUT_ID])
          expect(h.app.composer.text).toBe('draft survives')
          expect(h.app.composer.cursor).toBe(5)
        },
        { retention }
      )
    }
  )

  it('bounds repeated reattach, ignores stale ACKs and never borrows credits from a former epoch', async () => {
    const diagnostic = vi.spyOn(process.stderr, 'write').mockReturnValue(true)

    try {
      await withApp(
        async h => {
          const old = h.surface()
          await h.event({ ev: 'gone', sf: old.id, ids: [old.id] })
          const fresh = h.surface()
          expect(fresh.blocked).toBe(true)
          h.app.composer.set('waiting for new epoch credit')
          h.app.changed()
          const sent = h.peer.frames.length
          await h.event({ ev: 'ack', sf: old.id, s: 1000 })
          await h.event({ ev: 'ack', sf: fresh.id, s: 1000 })
          expect(h.peer.frames).toHaveLength(sent)
          await h.event({ ev: 'ack', sf: fresh.id, s: fresh.seq })
          expect(h.peer.frames.length).toBeGreaterThan(sent)

          for (let i = 0; i < MAX_SURFACE_RECOVERIES; i++) {
            const sf = h.surface().id
            await h.event({ ev: 'gone', sf, ids: [sf] })
          }

          expect(h.tern.surfaces).toHaveLength(0)
          expect(h.peer.documents.size).toBe(1 + MAX_SURFACE_RECOVERIES)
          expect(diagnostic).toHaveBeenCalledWith(expect.stringContaining('recovery limit'))
        },
        { auto: false, credits: 1 }
      )
    } finally {
      diagnostic.mockRestore()
    }
  })

  it('diagnoses a visible ACK stall once, suppresses hidden/detached stalls, and only resumes on actual ACK', async () => {
    const diagnostic = vi.spyOn(process.stderr, 'write').mockReturnValue(true)

    try {
      await withApp(
        async h => {
          // Existing startup watchdog predates fake timers; a hide/show edge owns a fresh one.
          await h.event({ ev: 'visible', sf: 'hermes', visible: false })
          vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
          await h.event({ ev: 'visible', sf: 'hermes', visible: true })
          const frames = h.peer.frames.length
          await vi.advanceTimersByTimeAsync(ACK_STALL_MS * 4)
          expect(diagnostic).toHaveBeenCalledTimes(1)
          expect(h.peer.frames).toHaveLength(frames)
          await h.event({ ev: 'visible', sf: 'hermes', visible: false })
          await h.event({ ev: 'gone', sf: 'hermes', ids: ['hermes'] })
          await vi.advanceTimersByTimeAsync(ACK_STALL_MS * 4)
          expect(diagnostic).toHaveBeenCalledTimes(1)
          expect(h.peer.documents.size).toBe(1)
          await h.event({ ev: 'visible', sf: 'hermes', visible: true })
          const fresh = h.surface()
          expect(fresh.id).not.toBe('hermes')
          await h.event({ ev: 'ack', sf: fresh.id, s: fresh.seq })
          expect(h.peer.frames.filter(f => f.sf === fresh.id).length).toBeGreaterThan(0)
        },
        { auto: false, credits: 1 }
      )
    } finally {
      diagnostic.mockRestore()
    }
  })

  it('preserves settings edits and approval ownership across replacement without repeating user intents', async () => {
    await withApp(async h => {
      const saved = Promise.withResolvers<unknown>()
      const request = vi.mocked(h.gw.request)
      request.mockImplementation(async method =>
        method === 'settings.set'
          ? saved.promise
          : {
              fields: {
                enabled: { category: 'general', default: false, description: '', type: 'boolean', value: false }
              },
              profile: 'fixture'
            }
      )
      openSettings(h.app)
      await painted()
      const old = h.surface()
      const prefs = [...h.peer.documents.get(old.id)!.values()].find(n => n.k === 'prefs')!
      const commit = old.dispatch({ ev: 'change', sf: old.id, id: prefs.id, item: 'enabled', value: true, raw: {} })!()
      await painted()
      await h.event({ ev: 'gone', sf: old.id, ids: [old.id] })
      saved.resolve({ key: 'enabled', value: true, confirm_required: false, confirm_message: '' })
      await commit
      await painted()
      expect(request.mock.calls.filter(([method]) => method === 'settings.set')).toHaveLength(1)
      const settings = h.app.overlays.find(o => o.key === 'settings')!
      h.app.close(settings)
      const respond = vi.fn()

      const approval = approvalPrompt(h.app, {
        id: 'approval-1',
        method: 'approval',
        params: { command: 'echo safe' },
        respond,
        fail: vi.fn()
      })

      h.app.open(approval)
      await painted()
      const surface = h.surface()
      await h.event({ ev: 'gone', sf: surface.id, ids: [surface.id] })
      expect(h.app.owns(approval)).toBe(true)
      expect(respond).not.toHaveBeenCalled()
      await approval.answer('once')
      expect(respond).toHaveBeenCalledTimes(1)
    })
  })

  it('forgets queued caret targets before an ACK arriving in the same input read as child eviction', async () => {
    await withApp(
      async h => {
        const sf = h.surface().id
        const seq = h.surface().seq
        h.peer.remove(sf, INPUT_ID)
        await h.batch([
          { ev: 'gone', sf, ids: [INPUT_ID] },
          { ev: 'ack', sf, s: seq }
        ])
        expect(h.peer.documents.get(sf)!.has(INPUT_ID)).toBe(true)
        expect(h.tern.surfaces).toHaveLength(1)
      },
      { auto: false, credits: 1 }
    )
  })

  it('reports locally malformed views without replaying a partial build', async () => {
    const diagnostic = vi.spyOn(process.stderr, 'write').mockReturnValue(true)

    try {
      await withApp(async h => {
        h.app.open({
          key: 'bad-view',
          modal: true,
          onKey: () => false,
          node: () =>
            node('col', {}, [
              node('text', { key: 'duplicate', text: 'a' }),
              node('text', { key: 'duplicate', text: 'b' })
            ])
        })
        await painted()
        expect(diagnostic).toHaveBeenCalledWith(expect.stringContaining('could not build a frame'))
        expect(h.tern.surfaces).toHaveLength(0)
      })
    } finally {
      diagnostic.mockRestore()
    }
  })

  it('keeps hidden, detached and disposed distinct; disposed instances cannot reopen or arm timers', async () => {
    const tern = {
      open: vi.fn(() => ({
        id: 'hermes',
        seq: 0,
        closed: false,
        blocked: false,
        send() {},
        acknowledge() {},
        gone() {}
      }))
    } as unknown as Session

    const host = { replace: vi.fn(), changed: vi.fn(), credit: vi.fn(), report: vi.fn() }
    const protocol = new SurfaceProtocol(tern, host)
    protocol.open()
    protocol.event({ ev: 'visible', visible: false, raw: {} })
    expect(protocol.state).toBe('hidden')
    protocol.event({ ev: 'gone', ids: ['hermes'], raw: {} })
    expect(protocol.state).toBe('detached')
    protocol.dispose()
    protocol.event({ ev: 'visible', visible: true, raw: {} })
    expect(protocol.state).toBe('disposed')
    expect(() => protocol.open()).toThrow('disposed')
    expect(tern.open).toHaveBeenCalledTimes(1)
  })
})
