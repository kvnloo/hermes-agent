import { EventEmitter } from 'node:events'

import { encodeMessage } from '@stencil-hq/tern'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { filterTernInput, probeTern } from '../tern/transport.js'

const frame = (verb: string, body: object) => encodeMessage(verb, JSON.stringify(body))
const hello = { r: 'hello', v: 1, term: 'tern', ver: 'test', kinds: ['editor'], features: ['dock'], credits: 1, apc: 65536, cols: 80, cell: { w: 8, h: 16 }, dark: true, reduceMotion: false }

function terminal(reply: object | null = hello) {
  const input = Object.assign(new EventEmitter(), { isTTY: true, isRaw: false, resume() {}, pause() {}, setRawMode(raw: boolean) { this.isRaw = raw }, ref() {}, unref() {} })
  const messages: { verb: string; body: Record<string, unknown> }[] = []

  const output = { isTTY: true, columns: 80, write(data: Uint8Array | string) {
    const text = typeof data === 'string' ? data : new TextDecoder().decode(data)
    const prefix = '\x1b_tsp;'

    if (text.startsWith(prefix) && text.endsWith('\x1b\\')) {
      const [verb, ...parts] = text.slice(prefix.length, -2).split(';')
      const body = JSON.parse(parts.join(';'))
      messages.push({ verb: verb!, body })

      if (body.q === 'hello' && reply) { queueMicrotask(() => input.emit('data', frame('r', reply))) }
    }
  } }

  return { input, output, messages, options: { input, output, env: { TERN_TSP: '1' }, exitHooks: false } }
}

afterEach(() => vi.useRealTimers())

describe('real SDK protocol seam (fixture terminal, not real Tern)', () => {
  it('times out, restores raw input, and starts no surface without a hello', async () => {
    vi.useFakeTimers()
    const t = terminal(null)
    const pending = probeTern(t.options)
    await vi.advanceTimersByTimeAsync(800)
    expect(await pending).toBeNull()
    expect(t.input.isRaw).toBe(false)
    expect(t.input.listenerCount('data')).toBe(0)
    expect(t.messages.map(message => message.verb)).toEqual(['q'])
  })

  it('uses negotiated credits=1 and coalesces 1000 updates until an ACK', async () => {
    const t = terminal()
    const native = (await probeTern(t.options))!
    let revision = 0
    native.composer.bind({ read: () => ({ owner: 'a', revision, text: `draft-${revision}`, ready: true, busy: false, modal: false }), edit() {}, submit() {} })
    const frames = () => t.messages.filter(message => message.verb === 'f')
    expect(frames()).toHaveLength(1)
    expect(t.messages[0]!.body.features).toEqual(['edit', 'send'])

    for (revision = 1; revision <= 1000; revision++) { native.composer.refresh() }
    expect(frames()).toHaveLength(1)
    t.input.emit('data', frame('e', { ev: 'ack', sf: 'hermes-composer', s: 1 }))
    expect(frames()).toHaveLength(2)
    expect(JSON.stringify(frames()[1])).toContain('draft-1000')
    t.input.emit('data', frame('e', { ev: 'ack', sf: 'hermes-composer', s: 1 }))
    expect(frames()).toHaveLength(2)
    await native.close()
    expect(t.input.listenerCount('data')).toBe(0)
    expect(t.input.isRaw).toBe(false)
  })

  it('keeps ordinary bytes intact while stripping fragmented protocol input from Ink', () => {
    const t = terminal()
    const filter = filterTernInput(t.input as unknown as NodeJS.ReadStream)
    const received: Buffer[] = []
    filter.stdin.on('data', chunk => received.push(Buffer.from(chunk)))
    const bytes = frame('e', { ev: 'ack', sf: 'hermes-composer', s: 1 })
    t.input.emit('data', Buffer.from('before 😀\n'))
    t.input.emit('data', bytes.slice(0, 8))
    t.input.emit('data', bytes.slice(8))
    t.input.emit('data', Buffer.from('after\x1b[A'))
    expect(Buffer.concat(received).toString()).toBe('before 😀\nafter\x1b[A')
    filter.close()
    expect(t.input.listenerCount('data')).toBe(0)
  })

  it.each([{ ...hello, kinds: ['text'] }, { ...hello, features: [] }, { ...hello, credits: 9 }])('rejects an incompatible hello before starting a native surface: %j', async reply => {
    const t = terminal(reply)
    expect(await probeTern(t.options)).toBeNull()
    expect(t.messages.some(message => message.verb === 'o')).toBe(false)
    expect(t.input.isRaw).toBe(false)
  })
})
