// @vitest-environment node
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

import { HermesGateway } from './client'

interface Frame { id: number; method: string; params: Record<string, unknown> }

// Only the wire is substituted: real desktop preparation/settlement, gateway
// dispatch and channel timeout/cancellation remain in the consumer path.
class MemorySocket extends EventTarget {
  static readonly OPEN = 1
  static latest: MemorySocket
  readonly frames: Frame[] = []
  readyState = 0

  constructor() {
    super()
    MemorySocket.latest = this
  }

  send(text: string): void { this.frames.push(JSON.parse(text)) }
  close(): void { this.readyState = 3 }
  open(): void {
    this.readyState = MemorySocket.OPEN
    this.dispatchEvent(new Event('open'))
  }

  reply(frame: Frame, result: Record<string, unknown>): void {
    this.dispatchEvent(new MessageEvent('message', { data: JSON.stringify({ jsonrpc: '2.0', id: frame.id, result }) }))
  }
}

let client: HermesGateway
let socket: MemorySocket

beforeEach(async () => {
  vi.useFakeTimers()
  vi.stubGlobal('WebSocket', MemorySocket)
  client = new HermesGateway()
  const connected = client.connect('ws://fixture.invalid/api/ws?native_dial=fixture&ticket=fixture')
  socket = MemorySocket.latest
  socket.open()
  await connected
  // Prime the real canonical revision/generation cache through its public API.
  const resumed = client.request('session.resume', { session_id: 's' })
  socket.reply(socket.frames.at(-1)!, { session_id: 's', revision: 4, execution_generation: 9, messages: [] })
  await resumed
  socket.frames.length = 0
})

afterEach(() => {
  client?.close()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

const receipt = { session_id: 's', revision: 5, operation: 'compress', target_session_id: 's', message_count: 1 }

function observe(pending: Promise<unknown>) {
  const state: { status: string; value?: unknown; error?: Error } = { status: 'pending' }
  void pending.then(value => { state.status = 'fulfilled'; state.value = value }, error => { state.status = 'rejected'; state.error = error })

  return state
}

test('compression resume obeys caller cancellation; a preview does not request a transcript', async () => {
  const controller = new AbortController()
  const outcome = observe(client.request('session.compress', { session_id: 's' }, 1_000, controller.signal))
  expect(socket.frames[0]).toMatchObject({ method: 'session.mutate', params: { operation: 'compress', expected_revision: 4, expected_generation: 9 } })
  socket.reply(socket.frames[0], receipt)
  await vi.advanceTimersByTimeAsync(0)
  expect(socket.frames.map(frame => frame.method)).toEqual(['session.mutate', 'session.resume'])
  controller.abort()
  await vi.advanceTimersByTimeAsync(0)
  expect(outcome.status).toBe('rejected')
  expect(outcome.error?.name).toBe('AbortError')
  // A late reply cannot resolve the canceled consumer.
  socket.reply(socket.frames[1], { session_id: 's', revision: 5, execution_generation: 9, messages: [] })
  await vi.advanceTimersByTimeAsync(0)
  expect(outcome.status).toBe('rejected')

  socket.frames.length = 0
  const preview = client.request('session.compress', { session_id: 's', focus_topic: '--preview' }, 1_000)
  socket.reply(socket.frames[0], { ...receipt, status: 'preview', lines: ['preview only'] })
  await expect(preview).resolves.toMatchObject({ host_ack: { output: 'preview only' } })
  expect(socket.frames.map(frame => frame.method)).toEqual(['session.mutate'])
  expect(vi.getTimerCount()).toBe(0)
})

test('compression resume gets the caller per-RPC timeout and successful calls retain the refreshed transcript', async () => {
  // First prove ordinary settlement still traverses the follow-up request.
  const successful = client.request('session.compress', { session_id: 's' }, 1_000)
  socket.reply(socket.frames[0], receipt)
  await vi.advanceTimersByTimeAsync(0)
  const messages = [{ role: 'assistant', content: 'retained summary' }]
  socket.reply(socket.frames[1], { session_id: 's', revision: 5, execution_generation: 9, messages, info: { title: 'T' } })
  await expect(successful).resolves.toMatchObject({ messages, info: { title: 'T' } })

  socket.frames.length = 0
  const outcome = observe(client.request('session.compress', { session_id: 's' }, 1_000))
  await vi.advanceTimersByTimeAsync(900)
  socket.reply(socket.frames[0], { ...receipt, revision: 6 })
  await vi.advanceTimersByTimeAsync(0)
  expect(socket.frames.map(frame => frame.method)).toEqual(['session.mutate', 'session.resume'])
  // This is a per-RPC allowance, not a new overall elapsed deadline.
  await vi.advanceTimersByTimeAsync(999)
  expect(outcome.status).toBe('pending')
  await vi.advanceTimersByTimeAsync(1)
  expect(outcome.status).toBe('rejected')
  expect(outcome.error?.message).toBe('request timed out after 1s: session.resume')
  expect(vi.getTimerCount()).toBe(0)
})
