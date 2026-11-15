/** Regression for NousResearch/hermes-agent#150614: a session_reset tip and its FIFO owner differ. */
import { afterEach, describe, expect, it } from 'vitest'

import { createClientSessionState } from '@/lib/chat-runtime'
import {
  $activeSessionStoredIdRotation,
  $selectedStoredSessionId,
  $sessions,
  setActiveSessionId
} from '@/store/session'
import { makeSessionInfo } from '@/test/session-info'

import { $sessionStates, clearAllSessionStates, publishSessionState } from './session-states'

const owner = 'local-creation'
const middle = 'local-reset-middle'
const tip = 'local-reset-continuation'

function listResetLineage() {
  $sessions.set([makeSessionInfo({ id: tip, _lineage_ids: [owner, middle, tip], _lineage_root_id: owner })])
}

function publish(storedId: string) {
  publishSessionState(owner, createClientSessionState(storedId))
}

afterEach(() => {
  clearAllSessionStates()
  $activeSessionStoredIdRotation.set(null)
  $selectedStoredSessionId.set(null)
  $sessions.set([])
  setActiveSessionId(null)
  window.location.hash = ''
})

describe('canonical local reset: one runtime owner, a later stored tip', () => {
  it.each([owner, middle])('keeps the visible continuation on a late projection of %s', ancestor => {
    listResetLineage()
    setActiveSessionId(owner)
    $selectedStoredSessionId.set(tip)
    window.location.hash = '#/' + tip

    publish(tip)
    $activeSessionStoredIdRotation.set(null)
    const incoming = { ...createClientSessionState(ancestor), busy: true }
    publishSessionState(owner, incoming)

    expect($sessionStates.get()[owner]?.storedSessionId).toBe(tip)
    expect($sessionStates.get()[owner]?.busy).toBe(true)
    expect(incoming.storedSessionId).toBe(ancestor)
    expect($activeSessionStoredIdRotation.get()).toBeNull()
    expect($selectedStoredSessionId.get()).toBe(tip)
    expect(window.location.hash).toBe('#/' + tip)
  })

  it('still allows a real forward rotation from the creation row to its reset tip', () => {
    listResetLineage()
    setActiveSessionId(owner)
    $selectedStoredSessionId.set(owner)
    window.location.hash = '#/' + owner

    publish(owner)
    publish(tip)

    expect($sessionStates.get()[owner]?.storedSessionId).toBe(tip)
    expect($activeSessionStoredIdRotation.get()).toMatchObject({
      previousStoredSessionId: owner,
      nextStoredSessionId: tip,
      runtimeSessionId: owner
    })
  })
})
