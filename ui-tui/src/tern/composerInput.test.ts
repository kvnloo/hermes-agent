import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import { dispatchNativeSend, type NativeSendOwner, type NativeSendState } from './composerInput.js'

function harness(draft = 'first\nsecond') {
  const state: NativeSendState = { draft, blocked: false, busy: false, completions: 0, bufferedLines: 0, sendEnabled: true }
  const sent: string[] = []
  let clears = 0
  const owner: NativeSendOwner = {
    read: () => ({ ...state }),
    clearDraft: () => { clears++; state.draft = '' },
    submit: text => { sent.push(text) }
  }
  return { state, sent, owner, clears: () => clears }
}

describe('live native send dispatch', () => {
  it('submits exact multiline text once, including a reentrant duplicate', () => {
    const h = harness('  first\nsecond  ')
    const original = h.owner.submit
    h.owner.submit = text => {
      original(text)
      assert.equal(dispatchNativeSend(text, h.owner), false)
    }
    assert.equal(dispatchNativeSend('  first\nsecond  ', h.owner), true)
    assert.deepEqual(h.sent, ['  first\nsecond  '])
    assert.equal(h.clears(), 1)
  })

  it('reads busy and modal transitions after the owner was created', () => {
    const h = harness('draft')
    h.state.busy = true
    assert.equal(dispatchNativeSend('draft', h.owner), false)
    h.state.busy = false
    h.state.blocked = true
    assert.equal(dispatchNativeSend('draft', h.owner), false)
    assert.equal(h.state.draft, 'draft')
    assert.equal(h.clears(), 0)
    h.state.blocked = false
    assert.equal(dispatchNativeSend('draft', h.owner), true)
    assert.deepEqual(h.sent, ['draft'])
  })

  for (const changes of [
    { completions: 1 }, { bufferedLines: 1 }, { sendEnabled: false }
  ]) {
    it(`preserves the draft when not natively sendable: ${JSON.stringify(changes)}`, () => {
      const h = harness('draft')
      Object.assign(h.state, changes)
      assert.equal(dispatchNativeSend('draft', h.owner), false)
      assert.equal(h.state.draft, 'draft')
      assert.equal(h.clears(), 0)
      assert.deepEqual(h.sent, [])
    })
  }

  it('rejects stale and blank payloads without modifying the current draft', () => {
    const h = harness('newer')
    assert.equal(dispatchNativeSend('older', h.owner), false)
    assert.equal(dispatchNativeSend('  \n ', h.owner), false)
    h.state.draft = '  \n '
    assert.equal(dispatchNativeSend('  \n ', h.owner), false)
    assert.equal(h.clears(), 0)
    assert.deepEqual(h.sent, [])
  })
})
