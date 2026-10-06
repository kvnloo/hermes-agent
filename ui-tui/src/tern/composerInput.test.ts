import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import { createTernComposerInputHandler, TernInlineSession, TERN_COMPOSER_ID, TERN_SURFACE_ID, type TernComposerInputState } from './composerSurface.js'
import { parseTspApc, type TspEvent, type TspHello } from './protocol.js'

const hello: TspHello = { r: 'hello', v: 1, term: 'tern', kinds: ['col', 'text', 'editor'], features: ['dock'], credits: 2 }
const send = (text: string): TspEvent => ({ ev: 'send', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, text })

function input(text = 'first line\nsecond line') {
  const state: TernComposerInputState = { busy: false, blocked: false, completionCount: 0, snapshot: { text, cursor: text.length } }
  const submitted: string[] = []
  let edits = 0
  const handle = createTernComposerInputHandler(hello, {
    read: () => state,
    edit: snapshot => { edits++; state.snapshot = snapshot },
    submit: value => {
      state.snapshot = { text: '', cursor: 0 }
      submitted.push(value)
    }
  })
  return { state, submitted, handle, edits: () => edits }
}

describe('live native composer input', () => {
  it('uses current busy state through one listener and submits unchanged multiline text once', () => {
    const h = input()
    const text = h.state.snapshot.text
    h.state.busy = true
    h.handle(send(text))
    assert.deepEqual(h.submitted, [])
    h.state.busy = false
    h.handle(send(text))
    h.handle(send(text))
    assert.deepEqual(h.submitted, [text])
  })

  it('blocks both edit and send when a modal opens before listener cleanup', () => {
    const h = input('draft')
    h.state.blocked = true
    h.handle(send('draft'))
    h.handle({ ev: 'edit', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, from: 0, to: 5, text: 'changed', cursor: 7, len: 5 })
    assert.deepEqual(h.submitted, [])
    assert.equal(h.edits(), 0)
    assert.equal(h.state.snapshot.text, 'draft')
  })

  it('requires current text, correct target and no unresolved completion', () => {
    const h = input('draft')
    h.handle({ ev: 'send', sf: 'other', id: TERN_COMPOSER_ID, text: 'draft' })
    h.handle({ ev: 'send', sf: TERN_SURFACE_ID, id: 'other', text: 'draft' })
    h.handle(send('stale'))
    h.state.completionCount = 1
    h.handle(send('draft'))
    assert.deepEqual(h.submitted, [])
    h.state.completionCount = 0
    h.handle({ ev: 'edit', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, from: 0, to: 5, text: 'ok', cursor: 2, len: 99 })
    assert.equal(h.edits(), 0)
    h.handle({ ev: 'edit', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, from: 0, to: 5, text: 'ok', cursor: 2, len: 5 })
    h.handle(send('ok'))
    assert.equal(h.edits(), 1)
    assert.deepEqual(h.submitted, ['ok'])
  })

  it('projects the same completion readiness into the native editor without reopening it', () => {
    const writes: string[] = []
    const session = new TernInlineSession(wire => writes.push(wire), hello)
    const snapshot = { text: 'draft', cursor: 5 }
    session.sync({ blocked: false, busy: false, completionCount: 1, snapshot })
    session.sync({ blocked: false, busy: false, completionCount: 0, snapshot })
    const decoded = writes.map(wire => parseTspApc(wire.slice(2, -2))!)
    assert.equal(decoded.filter(item => item.verb === 'o').length, 1)
    const frames = decoded.filter(item => item.verb === 'f').map(item => JSON.parse(item.body))
    assert.equal(frames[0].ops[1][4].c[0].p.sendable, false)
    assert.equal(frames[1].ops[0][2].sendable, true)
  })
})
