import { describe, expect, it } from 'vitest'

import type { TspEvent, TspHello } from './protocol.js'
import { parseTspApc } from './protocol.js'
import {
  applyTernComposerEdit,
  TERN_COMPOSER_ID,
  TERN_SURFACE_ID,
  TernComposerTransport
} from './composerSurface.js'

const hello: TspHello = {
  r: 'hello',
  v: 1,
  term: 'tern',
  kinds: ['col', 'editor'],
  features: ['edit', 'send'],
  credits: 1
}

const messages = (writes: string[]) =>
  writes.map(wire => {
    const payload = wire.slice(2, -2)
    const envelope = parseTspApc(payload)

    return envelope ? { ...envelope, json: JSON.parse(envelope.body) } : null
  })

describe('Tern composer transport', () => {
  it('opens one inline surface with a native editor in dock', () => {
    const writes: string[] = []
    const transport = new TernComposerTransport(data => writes.push(data), hello)

    transport.start({ cursor: 5, text: 'hello' }, true)

    const decoded = messages(writes)

    expect(decoded[0]).toMatchObject({
      verb: 'o',
      json: { id: TERN_SURFACE_ID, mode: 'inline', role: 'hermes.session' }
    })
    expect(decoded[1]?.verb).toBe('f')
    expect(JSON.stringify(decoded[1]?.json)).toContain(TERN_COMPOSER_ID)
    expect(JSON.stringify(decoded[1]?.json)).toContain('"sendable":true')
  })

  it('coalesces composer updates while its only frame credit is in flight', () => {
    const writes: string[] = []
    const transport = new TernComposerTransport(data => writes.push(data), hello)

    transport.start({ cursor: 0, text: '' }, true)
    transport.update({ cursor: 1, text: 'a' }, true)
    transport.update({ cursor: 2, text: 'ab' }, true)

    expect(writes).toHaveLength(2)

    transport.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })

    expect(writes).toHaveLength(3)
    expect(messages(writes)[2]?.json).toMatchObject({ s: 2, sf: TERN_SURFACE_ID })
    expect(JSON.stringify(messages(writes)[2]?.json)).toContain('"text":"ab"')
  })
})

describe('Tern composer edits', () => {
  it('applies UTF-16 replacement edits only against the text version Tern saw', () => {
    const event: Extract<TspEvent, { ev: 'edit' }> = {
      ev: 'edit',
      sf: TERN_SURFACE_ID,
      id: TERN_COMPOSER_ID,
      from: 1,
      to: 3,
      text: 'X',
      cursor: 2,
      len: 4
    }

    expect(applyTernComposerEdit('abcd', event)).toEqual({ cursor: 2, text: 'aXd' })
    expect(applyTernComposerEdit('abcde', event)).toBeNull()
  })
})
