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

describe('native composer buffered-line guard', () => {
  it('preserves a pending multiline prefix instead of submitting its visible suffix', () => {
    const state: TernComposerInputState & { bufferedLines: number } = {
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
    assert.deepEqual(submitted, [])
    assert.deepEqual(state.snapshot, { cursor: 6, text: 'suffix' })

    // Once the whole draft is represented by the editor, preserve it exactly.
    state.bufferedLines = 0
    state.snapshot = { text: '  prefix\nsuffix  ', cursor: 17 }
    handler(send(state.snapshot.text))
    assert.deepEqual(submitted, ['  prefix\nsuffix  '])
  })

  it('disables the native Send affordance while buffered lines exist without reopening the surface', () => {
    const writes: string[] = []
    const session = new TernInlineSession(wire => writes.push(wire), hello)
    const state = {
      blocked: false, busy: false, completionCount: 0, bufferedLines: 1,
      snapshot: { text: 'suffix', cursor: 6 }
    }
    session.sync(state)
    const first = parseTspApc(writes[1].slice(2, -2))!
    const initialOps = JSON.parse(first.body).ops
    const dock = initialOps.find((op: unknown[]) => op[0] === 'add' && op[1] === 'dock')
    assert.equal(dock[4].c[0].p.sendable, false)

    state.bufferedLines = 0
    session.sync(state)
    assert.equal(writes.filter(wire => parseTspApc(wire.slice(2, -2))?.verb === 'o').length, 1)
    assert.equal(writes.filter(wire => parseTspApc(wire.slice(2, -2))?.verb === 'x').length, 0)
    const last = parseTspApc(writes.at(-1)!.slice(2, -2))!
    const patch = JSON.parse(last.body).ops.find((op: unknown[]) => op[0] === 'set' && op[1] === TERN_COMPOSER_ID)
    assert.equal(patch[2].sendable, true)
    session.close()
  })
})
