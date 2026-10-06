import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import {
  createTernComposerInputHandler, TernInlineSession,
  TERN_COMPOSER_ID, TERN_SURFACE_ID, type TernComposerInputState
} from './composerSurface.js'
import { projectTernTranscript } from './liveProjection.js'
import { parseTspApc, type TspHello } from './protocol.js'

const hello: TspHello = {
  r: 'hello', v: 1, term: 'tern',
  kinds: ['col', 'editor', 'card', 'md', 'text'], features: ['dock'], credits: 1
}

const initialRows = [{ index: 0, key: 'msg:1:c80', msg: { role: 'user' as const, text: 'Please inspect this.' } }]
const frames = (writes: string[]) => writes.flatMap(wire => {
  const envelope = parseTspApc(wire.slice(2, -2))!
  return envelope.verb === 'f' ? [JSON.parse(envelope.body)] : []
})

describe('live input and transcript share one native frame window', () => {
  it('coalesces an edit with the newest transcript without reopening or submitting while busy', () => {
    const writes: string[] = []
    const submissions: string[] = []
    const session = new TernInlineSession(wire => writes.push(wire), hello)
    const state: TernComposerInputState = {
      blocked: false, busy: true, completionCount: 0, snapshot: { text: 'draft', cursor: 5 }
    }
    let main = projectTernTranscript(initialRows, 'Working')
    const sync = () => session.sync({ ...state, main })
    const input = createTernComposerInputHandler(hello, {
      read: () => state,
      edit: snapshot => { state.snapshot = snapshot; sync() },
      submit: text => { state.snapshot = { text: '', cursor: 0 }; sync(); submissions.push(text) }
    })
    sync()
    main = projectTernTranscript(initialRows, 'Working on it')
    sync()
    input({ ev: 'edit', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, from: 5, to: 5, text: '\nfollow-up', cursor: 15, len: 5 })
    input({ ev: 'send', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, text: state.snapshot.text })
    assert.deepEqual(submissions, [])
    assert.equal(writes.length, 2)

    session.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })
    const emitted = frames(writes)
    assert.equal(emitted.length, 2)
    assert.deepEqual(emitted[1].ops, [
      ['text', 'hermes:streaming', 'append', ' on it'],
      ['set', TERN_COMPOSER_ID, { cursor: 15, sendable: false, text: 'draft\nfollow-up' }]
    ])
    assert.equal(writes.filter(wire => parseTspApc(wire.slice(2, -2))?.verb === 'o').length, 1)
    assert.equal(writes.filter(wire => parseTspApc(wire.slice(2, -2))?.verb === 'x').length, 0)
  })

  it('keeps a pending transcript when the composer alone converges back to its sent draft', () => {
    const writes: string[] = []
    const session = new TernInlineSession(wire => writes.push(wire), hello)
    const base = { blocked: false, busy: false, completionCount: 0 }
    const draft = { text: 'a', cursor: 1 }
    const latestMain = projectTernTranscript(initialRows, 'Working on it')
    session.sync({ ...base, snapshot: draft, main: projectTernTranscript(initialRows, 'Working') })
    session.sync({ ...base, snapshot: { text: 'ab', cursor: 2 }, main: latestMain })
    session.sync({ ...base, snapshot: draft, main: latestMain })
    session.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })

    const emitted = frames(writes)
    assert.equal(emitted.length, 2)
    assert.deepEqual(emitted[1].ops, [['text', 'hermes:streaming', 'append', ' on it']])
    session.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 2 })
    assert.equal(frames(writes).length, 2)
  })
})
