import assert from 'node:assert/strict'
import { EventEmitter } from 'node:events'
import { performance } from 'node:perf_hooks'

import { encodeJson, Surface, type OutMessage, type Session, type SessionInput, type WireNode } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'

import { App } from '../src/app.js'

const tick = () => new Promise<void>(resolve => setImmediate(resolve))
const epoch = 1_700_000_000_000

/** Real App + SDK Surface/reconciler/encoder; no gateway process or ambient terminal. */
export async function replay({
  credits = 1,
  hidden = false,
  deltas = 5000,
  history = 1000,
  quitBeforeAck = false,
  retention = false
} = {}) {
  const gw = new EventEmitter() as EventEmitter & { drain(): void; kill(): void }
  gw.drain = () => {}
  gw.kill = () => {}
  let bytes = 0
  let frames = 0
  let renders = 0
  let hiddenRenders = 0
  let isHidden = false
  let textSnapshots = 0
  const liveTextIds = new Set<string>()
  const nodes = new Map<string, { id: string; k: string; p: Record<string, import('@stencil-hq/tern').Json> }>()
  const children = new Map<string, string[]>()
  const toolStates = new Map<string, Set<string>>()
  const builds: number[] = []
  const frameBuilds: number[] = []
  let buildSinceFrame = 0
  let sentFrame = false
  let ackTotalMs = 0
  const finishCost = (ms: number) => {
    buildSinceFrame += ms
    if (sentFrame) {
      frameBuilds.push(buildSinceFrame)
      buildSinceFrame = 0
      sentFrame = false
    }
  }
  const sdkMs: number[] = []
  const globals = globalThis as typeof globalThis & { __frameBuildSample?: (ms: number) => void }
  globals.__frameBuildSample = ms => {
    builds.push(ms)
    finishCost(ms)
  }
  const add = (n: WireNode) => {
    nodes.set(n.id, { ...n, p: { ...n.p } })
    if (liveTextIds.has(n.id) && n.p?.text) textSnapshots++
    children.set(n.id, n.c?.map(c => c.id) ?? [])
    n.c?.forEach(add)
  }
  const place = (id: string, parent: string, before: string | null) => {
    for (const [key, ids] of children)
      if (ids.includes(id))
        children.set(
          key,
          ids.filter(child => child !== id)
        )
    const ids = children.get(parent) ?? []
    const at = before === null ? ids.length : ids.indexOf(before)
    assert(at >= 0, `missing sibling ${before}`)
    ids.splice(at, 0, id)
    children.set(parent, ids)
  }
  const messages: OutMessage[] = []
  const send = (message: OutMessage) => {
    bytes += Buffer.byteLength(encodeJson(message, { limit: 1_048_576, chunk: () => 'bench' }))
    if (message.verb !== 'f') return
    frames++
    sentFrame = true
    messages.push(message)
  }
  // Verification is intentionally outside the timed region, not fake-terminal CPU in App builds.
  const apply = (message: OutMessage) => {
    if (message.verb !== 'f') return
    for (const op of message.body.ops) {
      if (op[0] === 'add') {
        add(op[4])
        place(op[1], op[2], op[3])
      } else if (op[0] === 'move') place(op[1], op[2], op[3])
      else if (op[0] === 'del') {
        for (const id of nodes.keys())
          if (id === op[1] || id.startsWith(op[1] + '.')) {
            nodes.delete(id)
            children.delete(id)
          }
        for (const [id, ids] of children)
          children.set(
            id,
            ids.filter(child => child !== op[1])
          )
      } else if (op[0] === 'set') {
        const n = nodes.get(op[1])
        assert(n, `set missing ${op[1]}`)
        n.p = { ...n.p, ...op[2] }
      } else if (op[0] === 'text') {
        const n = nodes.get(op[1])
        assert(n, `text missing ${op[1]}`)
        n.p = { ...n.p, text: op[2] === 'append' ? String(n.p?.text ?? '') + op[3] : op[3] }
        if (liveTextIds.has(op[1])) textSnapshots++
      }
    }
    for (const n of nodes.values()) {
      if (n.k === 'tool' && typeof n.p?.status === 'string') {
        const seen = toolStates.get(n.id) ?? new Set<string>()
        seen.add(n.p.status)
        toolStates.set(n.id, seen)
      }
    }
  }
  const surface = new Surface({ send, credits: () => credits, dropped() {} }, 'hermes', {})
  const ack = () => {
    const start = performance.now()
    surface.acknowledge(surface.seq)
    const ms = performance.now() - start
    ackTotalMs += ms
    finishCost(ms)
  }
  const render = surface.render.bind(surface)
  surface.render = view => {
    renders++
    if (isHidden) hiddenRenders++
    const start = performance.now()
    render(view)
    sdkMs.push(performance.now() - start)
  }
  let deliver: ((value: IteratorResult<SessionInput>) => void) | undefined
  const pending: SessionInput[] = []
  const input = (event: SessionInput) => {
    if (deliver) {
      const resolve = deliver
      deliver = undefined
      resolve({ value: event, done: false })
    } else pending.push(event)
  }
  const tern = {
    caps: { features: retention ? ['settle'] : [], kinds: [], reduceMotion: true, cols: 120 },
    open: () => surface,
    close: async () => {
      await surface.close()
      deliver?.({ value: undefined, done: true })
    },
    [Symbol.asyncIterator]() {
      return {
        next: () =>
          pending.length
            ? Promise.resolve({ value: pending.shift()!, done: false })
            : new Promise<IteratorResult<SessionInput>>(resolve => {
                deliver = resolve
              })
      }
    }
  } as unknown as Session
  const random = Math.random
  Math.random = () => 0
  const app = new App(tern, gw as unknown as GatewayClient, 'bench')
  Math.random = random
  app.sid = 'bench-session'
  app.info = { cwd: '/bench', model: 'fixture', reasoning_effort: 'medium' }
  // Fixed dates and content, half settled assistant turns, half user entries.
  for (let i = 0; i < history; i++) {
    app.transcript.push(
      i % 2 === 0
        ? { kind: 'user', id: `history${i}`, at: epoch, text: `Prompt ${i}` }
        : {
            kind: 'turn',
            id: `history${i}`,
            rev: 0,
            startedAt: epoch,
            endedAt: epoch + 10,
            status: 'done',
            blocks: [{ kind: 'text', id: 'answer', text: `Settled answer ${i}: [file](src/app.ts)` }]
          }
    )
  }
  let serial = 0
  const emit = (type: string, payload: object = {}) => {
    serial++
    gw.emit('event', { type, session_id: app.sid, payload })
  }
  const visible = async (value: boolean) => {
    input({ type: 'event', event: { ev: 'visible', sf: 'hermes', visible: value, raw: {} } })
    await tick()
    isHidden = !value
  }
  // Date.now is fixture time, not the performance clock. This eliminates elapsed-prop noise.
  const originalNow = Date.now
  Date.now = () => epoch
  const started = performance.now()
  const running = app.run()
  try {
    await tick()
    ack()
    await tick()
    if (retention) for (let i = 0; i < 3; i++) { ack(); await tick() }
    const initialBytes = bytes
    const initialFrames = frames
    const initialBuilds = frameBuilds.length
    if (hidden) await visible(false)
    emit('message.start')
    let expected = ''
    const toolCount = Math.ceil(deltas / 250)
    for (let i = 0; i < deltas; i++) {
      if (i % 250 === 0)
        emit('tool.start', {
          tool_id: `call${i / 250}`,
          name: 'terminal',
          args: { command: `printf result${i / 250}` }
        })
      const text = `delta${i} 😀\n`
      expected += text
      emit('message.delta', { text })
      if (i % 250 === 125 || (i === deltas - 1 && i % 250 < 125)) {
        const id = Math.floor(i / 250)
        emit('tool.complete', {
          tool_id: `call${id}`,
          name: 'terminal',
          result: { output: `result${id}`, exit_code: 0 },
          result_text: `result${id}`,
          duration_s: 0.125
        })
      }
      // Ten deltas per ingress burst; one cumulative ACK every four bursts.
      if ((i + 1) % 10 === 0) await tick()
      if ((i + 1) % 40 === 0 && !hidden) {
        ack()
        await tick()
      }
    }
    emit('message.complete', { status: 'complete' })
    await tick()
    const turn = app.transcript.entries.findLast(e => e.kind === 'turn')!
    assert(turn.kind === 'turn')
    assert.equal(
      turn.blocks
        .filter(b => b.kind === 'text')
        .map(b => b.text)
        .join(''),
      expected
    )
    const tools = turn.blocks.filter(b => b.kind === 'tool')
    assert.equal(tools.length, toolCount)
    assert(tools.every(b => b.call.status === 'done' && b.call.resultText === `result${b.call.id.slice(4)}`))
    assert.equal(turn.status, 'done')
    assert.equal(app.transcript.rev, history + 1 + serial, 'each semantic event must reach the reducer')
    if (quitBeforeAck) {
      app.quit()
      await running
    } else {
      if (hidden) await visible(true)
      for (let i = 0; i < 4; i++) {
        ack()
        await tick()
      }
    }
    const wallMs = performance.now() - started
    const prefix = `main.${turn.id}.`
    for (const b of turn.blocks) if (b.kind === 'text') liveTextIds.add(`${prefix}${b.id}`)
    messages.forEach(apply)
    const ordered: string[] = []
    const walk = (id: string) => {
      const n = nodes.get(id)
      assert(n, `wire node missing ${id}`)
      if (liveTextIds.has(id)) ordered.push(String(n.p.text ?? ''))
      for (const child of children.get(id) ?? []) walk(child)
    }
    walk(`main.${turn.id}`)
    const wireText = ordered.join('')
    assert.equal(wireText, expected, 'wire reconstruction must preserve every delta, in order')
    for (const b of tools) {
      const card = nodes.get(`${prefix}${b.id}`)
      assert(card, `wire tool ${b.id}`)
      assert.equal(card.p?.status, 'done')
      assert(
        [...nodes.values()].some(
          n => n.id.startsWith(`${prefix}${b.id}.`) && JSON.stringify(n.p).includes(b.call.resultText!)
        ),
        'wire output missing'
      )
    }
    for (let i = 0; i < history; i++) assert(nodes.has(`main.history${i}`))
    const pct = (values: number[], p: number) =>
      [...values].sort((a, b) => a - b)[Math.max(0, Math.ceil(values.length * p) - 1)] ?? 0
    return {
      credits,
      hidden,
      deltas,
      history,
      retention,
      streamingBytes: bytes - initialBytes,
      streamingFrames: frames - initialFrames,
      streamingBuildP95Ms: pct(frameBuilds.slice(initialBuilds), 0.95),
      events: serial,
      frames,
      bytes,
      renders: builds.length || renders,
      hiddenRenders,
      buildP50Ms: pct(frameBuilds, 0.5),
      buildP95Ms: pct(frameBuilds, 0.95),
      renderP50Ms: pct(builds, 0.5),
      renderP95Ms: pct(builds, 0.95),
      buildTotalMs: builds.reduce((a, b) => a + b, 0) + ackTotalMs,
      ackTotalMs,
      sdkTotalMs: sdkMs.reduce((a, b) => a + b, 0),
      wallMs,
      droppedSemanticEvents: 0,
      textUpdatesMerged: deltas - textSnapshots,
      toolRecords: tools.length,
      toolRunningSnapshotsMerged: tools.filter(b => !toolStates.get(`${prefix}${b.id}`)?.has('running')).length
    }
  } finally {
    app.quit()
    await running
    Date.now = originalNow
    delete globals.__frameBuildSample
  }
}
