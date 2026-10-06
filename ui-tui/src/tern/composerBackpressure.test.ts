import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import { TernComposerTransport, TERN_SURFACE_ID } from './composerSurface.js'
import { parseTspApc, type TspHello } from './protocol.js'

const hello: TspHello = { r: 'hello', v: 1, term: 'tern', kinds: ['col', 'text', 'editor'], features: ['dock'], credits: 1 }
const snapshot = (text: string) => ({ text, cursor: text.length })

function makeTransport() {
  const writes: string[] = []
  const transport = new TernComposerTransport(data => writes.push(data), hello)
  return { transport, writes }
}

describe('live composer backpressure', () => {
  it('discards a blocked intermediate update when the latest draft returns to the sent draft', () => {
    const { transport, writes } = makeTransport()
    transport.start(snapshot('a'), true)
    transport.update(snapshot('ab'), false)
    transport.update(snapshot('a'), true)
    transport.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })
    assert.equal(writes.length, 2, 'ACK must not resurrect the superseded draft or readiness')
  })

  it('does not grant frame credit to future or fractional ACKs', () => {
    const { transport, writes } = makeTransport()
    transport.start(snapshot('a'), true)
    transport.update(snapshot('latest'), false)
    for (const s of [0.5, 2]) {
      transport.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s })
      assert.equal(writes.length, 2, `invalid ACK ${s} released pending state`)
    }
    transport.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })
    assert.equal(writes.length, 3)
    const frame = parseTspApc(writes[2].slice(2, -2))!
    assert.equal(JSON.parse(frame.body).ops[0][2].text, 'latest')
  })
})
