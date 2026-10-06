import { describe, expect, it } from 'vitest'

import type { TranscriptRow } from '../app/interfaces.js'
import type { Msg } from '../types.js'
import { TernComposerTransport, TERN_SURFACE_ID } from './composerSurface.js'
import { projectTernTranscript } from './liveProjection.js'
import { parseTspApc, type TspHello } from './protocol.js'

const hello: TspHello = {
  r: 'hello',
  v: 1,
  term: 'tern',
  kinds: ['col', 'editor', 'card', 'md', 'text'],
  features: ['dock'],
  credits: 1
}

const row = (index: number, key: string, msg: Msg): TranscriptRow => ({ index, key, msg })
const decoded = (wire: string) => {
  const envelope = parseTspApc(wire.slice(2, -2))!
  return { verb: envelope.verb, body: JSON.parse(envelope.body) }
}

describe('live native transcript transport', () => {
  it('opens the inline surface with the projected settled transcript in main', () => {
    const writes: string[] = []
    const transport = new TernComposerTransport(data => writes.push(data), hello)
    const main = projectTernTranscript(
      [row(0, 'msg:1:c80', { role: 'user', text: 'Please inspect this.' })],
      ''
    )

    transport.start({ cursor: 0, text: '' }, true, main)

    expect(decoded(writes[1]!).body).toMatchObject({ sf: TERN_SURFACE_ID, s: 1 })
    expect(JSON.stringify(decoded(writes[1]!).body.ops)).toContain('Please inspect this.')
  })

  it('coalesces streaming main updates through the same frame-credit window', () => {
    const writes: string[] = []
    const transport = new TernComposerTransport(data => writes.push(data), hello)
    const rows = [row(0, 'msg:1:c80', { role: 'user', text: 'Please inspect this.' })]

    transport.start({ cursor: 0, text: '' }, false, projectTernTranscript(rows, 'Working'))
    transport.update({ cursor: 0, text: '' }, false, projectTernTranscript(rows, 'Working on'))
    transport.update({ cursor: 0, text: '' }, false, projectTernTranscript(rows, 'Working on it'))

    expect(writes).toHaveLength(2)
    transport.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })

    expect(writes).toHaveLength(3)
    const frame = decoded(writes[2]!).body
    expect(frame.s).toBe(2)
    expect(frame.ops).toEqual([['text', 'hermes:streaming', 'append', ' on it']])
    expect(JSON.stringify(frame.ops)).not.toContain('Working on"')
  })
})
