import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { ToolOutputDeltaPayload } from '@hermes/shared/gateway-events'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { Transcript } from '../transcript.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-ansi-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const start = (tool_id = 'a', turn_id = 'turn-1') => ({ name: 'terminal', tool_id, turn_id, args: { command: 'printf output' } })

const delta = (text: string, extra: Partial<ToolOutputDeltaPayload> = {}): ToolOutputDeltaPayload => ({
  tool_id: 'a', turn_id: 'turn-1', stream_id: 'stream-a', seq: 1,
  output_kind: 'terminal', operation: 'append', text, capture_truncated: false, ...extra
})

interface Fixture {
  app: App
  gw: GatewayClient
  nodes(): NonNullable<View['regions'][number]>['children']
  flush(): Promise<void>
}

async function withApp(run: (fixture: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const original = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => {
    latest = View.from(view)
    original(view)
  }

  try {
    await run({
      app, gw,
      nodes() {
        const visit = (nodes: NonNullable<View['regions'][number]>['children']): NonNullable<View['regions'][number]>['children'] =>
          nodes.flatMap(node => [node, ...visit(node.children)])

        return visit(latest?.regions.find(region => region?.id === 'main')?.children ?? [])
      },
      async flush() {
        app.changed()
        await rendered()
        await rendered()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

it('emits ANSI wire nodes with raw colored, carriage-return progress and Unicode output', async () => {
  await withApp(async ({ app, gw, nodes, flush }) => {
    app.composer.set('keep draft', 4)
    gw.emit('event', { type: 'tool.start', session_id: 'session-1', payload: start() })
    const chunks = ['\x1b[31m紅', '色\x1b[0m\n0%', '\r100% ✓']
    chunks.forEach((text, index) => gw.emit('event', {
      type: 'tool.output.delta', session_id: 'session-1', payload: delta(text, { seq: index + 1 })
    }))
    await flush()
    const output = nodes().find(node => node.props.role === 'omp.run.output')
    expect(output?.kind).toBe('ansi')
    expect(output?.props.text).toBe(chunks.join(''))
    expect(output?.props.follow).toBe(true)
    expect(app.composer.text).toBe('keep draft')
    expect(nodes().some(node => node.props.role === 'omp.run.state')).toBe(true)
  })
})

it('routes concurrent IDs only to their session, turn and call and drops replayed or late frames', async () => {
  await withApp(async ({ app, gw, nodes, flush }) => {
    for (const id of ['a', 'b']) {
      gw.emit('event', { type: 'tool.start', session_id: 'session-1', payload: start(id) })
    }

    const send = (payload: ToolOutputDeltaPayload, session_id = 'session-1') => gw.emit('event', { type: 'tool.output.delta', session_id, payload })
    send(delta('alpha'))
    send(delta('beta', { tool_id: 'b', stream_id: 'stream-b' }))
    send(delta('foreign', { seq: 2 }), 'session-2')
    send(delta('old turn', { seq: 2, turn_id: 'old' }))
    send(delta('unknown', { tool_id: 'missing' }))
    send(delta('alpha'))
    send(delta('wrong generation', { seq: 2, stream_id: 'wrong' }))
    await flush()
    expect(nodes().filter(node => node.kind === 'ansi').map(node => node.props.text)).toEqual(['alpha', 'beta'])
    expect(app.transcript.live?.blocks).toHaveLength(2)
  })
})

it('keeps captured truncation distinct from native preview and follows the retained tail', async () => {
  await withApp(async ({ gw, nodes, flush }) => {
    gw.emit('event', { type: 'tool.start', session_id: 'session-1', payload: start() })
    const text = '\x1b[32m' + Array.from({ length: 30 }, (_, n) => `line ${n}`).join('\n')
    gw.emit('event', { type: 'tool.output.delta', session_id: 'session-1', payload: delta(text, { operation: 'replace', seq: 30, capture_truncated: true }) })
    await flush()
    const output = nodes().find(node => node.kind === 'ansi')
    expect(output?.props.text).toBe(text)
    expect(output?.props.preview).toEqual({ lines: 10 })
    expect(output?.props.follow).toBe(true)
    const facts = nodes().find(node => node.props.role === 'omp.run.facts')
    expect(JSON.stringify(facts?.props)).toContain('capture truncated: head + tail retained')
    expect(JSON.stringify(facts?.props)).toContain('truncated: showing last 10 lines')
  })
})

it('retains cancellation output, stops follow and rejects subsequent deltas', async () => {
  await withApp(async ({ app, gw, nodes, flush }) => {
    gw.emit('event', { type: 'tool.start', session_id: 'session-1', payload: start() })
    gw.emit('event', { type: 'tool.output.delta', session_id: 'session-1', payload: delta('partial') })
    app.transcript.interrupt()
    gw.emit('event', { type: 'tool.output.delta', session_id: 'session-1', payload: delta('late', { seq: 2 }) })
    await flush()
    const output = nodes().find(node => node.kind === 'ansi')
    expect(output?.props.text).toBe('partial')
    expect(output?.props.follow).toBe(false)
    expect(JSON.stringify(nodes().find(node => node.props.role === 'omp.run.state')?.props)).toContain('cancelled')
  })
})

it.each(['authoritative\n[truncated]', ''])('replaces rather than appends final output, including %j', async final => {
  await withApp(async ({ gw, nodes, flush }) => {
    gw.emit('event', { type: 'tool.start', session_id: 'session-1', payload: start() })
    gw.emit('event', { type: 'tool.output.delta', session_id: 'session-1', payload: delta('streamed') })
    gw.emit('event', { type: 'tool.complete', session_id: 'session-1', payload: { tool_id: 'a', name: 'terminal', result: { output: final, exit_code: 0 } } })
    gw.emit('event', { type: 'tool.output.delta', session_id: 'session-1', payload: delta('late', { seq: 2 }) })
    await flush()
    const output = nodes().find(node => node.props.role === 'omp.run.output')
    expect(output?.props.text ?? '').toBe(final)
    expect(output?.kind).not.toBe('ansi')
  })
})

it('restores a live output snapshot and resumes from its sequence without duplicating bytes', () => {
  const transcript = new Transcript()
  transcript.load([{ role: 'tool', name: 'terminal', tool_call_id: 'a', args: { command: 'printf output' } }])
  transcript.inflight({ streaming: true, tools: [{ start: start(), output: delta('snapshot', { seq: 9, operation: 'replace' }) }] })
  expect(transcript.entries.flatMap(entry => entry.kind === 'turn' ? entry.blocks : []).filter(block => block.kind === 'tool')).toHaveLength(1)
  transcript.toolOutput(delta('snapshot', { seq: 9 }))
  transcript.toolOutput(delta(' tail', { seq: 10 }))
  expect(transcript.live?.blocks[0]).toMatchObject({ call: { output: { text: 'snapshot tail' }, startedObserved: false } })
  transcript.complete({ status: 'complete' })
  transcript.toolStart(start('a', 'turn-2'))
  transcript.toolOutput(delta('old', { seq: 11 }))
  transcript.toolOutput(delta('new', { turn_id: 'turn-2', stream_id: 'new' }))
  expect(transcript.live?.blocks[0]).toMatchObject({ call: { output: { text: 'new' } } })
  transcript.load([{ role: 'tool', name: 'terminal', tool_call_id: 'a', content: JSON.stringify({ output: 'final', exit_code: 0 }) }])
  expect(transcript.live).toBeUndefined()
  expect(JSON.stringify(transcript.entries)).not.toContain('snapshot tail')
})

it('keeps literal output as code instead of interpreting escape sequences', async () => {
  await withApp(async ({ gw, nodes, flush }) => {
    gw.emit('event', { type: 'tool.start', session_id: 'session-1', payload: start() })
    gw.emit('event', { type: 'tool.output.delta', session_id: 'session-1', payload: delta('\x1b[31mliteral', { output_kind: 'literal' }) })
    await flush()
    expect(nodes().find(node => node.props.role === 'omp.run.output')?.kind).toBe('code')
  })
})
