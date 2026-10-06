import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import {
  createTernComposerInputHandler,
  TernInlineSession,
  TERN_COMPOSER_ID,
  TERN_SURFACE_ID,
  type TernComposerInputState
} from './composerSurface.js'
import { parseTspApc, type TspHello } from './protocol.js'

const hello: TspHello = {
  r: 'hello', v: 1, term: 'tern', kinds: ['col', 'text', 'editor'],
  features: ['dock'], credits: 2
}
const send = (text: string) => ({ ev: 'send' as const, sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, text })

describe('native composer buffered-line handoff', () => {
  it('ignores late native input while a buffered prefix requires Ink, then accepts the whole native draft', () => {
    const state: TernComposerInputState = {
      snapshot: { text: 'suffix', cursor: 6 },
      blocked: false, busy: false, completionCount: 0, bufferedLines: 1
    }
    const submitted: string[] = []
    const handler = createTernComposerInputHandler(hello, {
      read: () => state,
      edit: next => { state.snapshot = next },
      submit: text => {
        submitted.push(text)
        state.snapshot = { cursor: 0, text: '' }
      }
    })

    handler(send('suffix'))
    handler({ ev: 'edit', sf: TERN_SURFACE_ID, id: TERN_COMPOSER_ID, from: 0, to: 6, len: 6, cursor: 3, text: 'new' })
    assert.deepEqual(submitted, [])
    assert.deepEqual(state.snapshot, { cursor: 6, text: 'suffix' })

    state.bufferedLines = 0
    state.snapshot = { text: '  prefix\nsuffix  ', cursor: 17 }
    handler(send(state.snapshot.text))
    assert.deepEqual(submitted, ['  prefix\nsuffix  '])
  })

  it('releases the native surface for the existing multiline composer and can resume afterward', () => {
    const writes: string[] = []
    const session = new TernInlineSession(wire => writes.push(wire), hello)
    const state = {
      blocked: false, busy: false, completionCount: 0, bufferedLines: 0,
      snapshot: { text: 'prefix', cursor: 6 }
    }
    const decoded = () => writes.map(wire => parseTspApc(wire.slice(2, -2))!)
    session.sync(state)
    assert.equal(decoded().filter(message => message.verb === 'o').length, 1)

    state.bufferedLines = 1
    state.snapshot = { text: 'suffix', cursor: 6 }
    session.sync(state)
    session.sync(state)
    assert.equal(decoded().filter(message => message.verb === 'x').length, 1)
    assert.equal(decoded().filter(message => message.verb === 'o').length, 1)
    assert.deepEqual(state.snapshot, { text: 'suffix', cursor: 6 })

    state.bufferedLines = 0
    state.snapshot = { text: 'prefix\nsuffix', cursor: 13 }
    session.sync(state)
    assert.equal(decoded().filter(message => message.verb === 'o').length, 2)
    const frame = decoded().filter(message => message.verb === 'f').at(-1)!
    const dock = JSON.parse(frame.body).ops.find((op: unknown[]) => op[0] === 'add' && op[1] === 'dock')
    assert.equal(dock[4].c[0].p.text, 'prefix\nsuffix')
    assert.equal(dock[4].c[0].p.sendable, true)
    session.close()
  })
})
