import { describe, expect, it } from 'vitest'

import {
  applyMoaEvent,
  emptyMoaState,
  type MoaOrchestrationState,
  moaStatusAnnouncement,
  slotIdentityKey,
  thinkingOrbStateFor
} from './moa-orchestration'

function progress(
  state: MoaOrchestrationState,
  payload: Record<string, unknown>
): MoaOrchestrationState {
  return applyMoaEvent(state, { payload, type: 'moa.progress' })
}

function reference(
  state: MoaOrchestrationState,
  payload: Record<string, unknown>
): MoaOrchestrationState {
  return applyMoaEvent(state, { payload, type: 'moa.reference' })
}

function phase(state: MoaOrchestrationState, payload: Record<string, unknown>): MoaOrchestrationState {
  return applyMoaEvent(state, { payload, type: 'moa.phase' })
}

describe('MoA orchestration reducer', () => {
  it('creates anonymous running slots from the first progress total without labeling them', () => {
    const next = progress(emptyMoaState(), { label: 'model-a', refs_done: 1, refs_total: 6 })

    expect(next.phase).toBe('fanout')
    expect(next.refsDone).toBe(1)
    expect(next.refsTotal).toBe(6)
    expect(next.parallel).toBe(true)
    expect(next.slots).toHaveLength(6)
    expect(next.slots.every(slot => slot.label === null)).toBe(true)
    expect(next.aggregatorStatus).toBe('waiting')
    expect(next.slots.filter(slot => slot.status === 'complete')).toHaveLength(0)
  })

  it('keeps waiting heartbeats from replacing slot identity or appending completions', () => {
    let state = progress(emptyMoaState(), {
      elapsed_seconds: 5,
      label: 'waiting on 6 advisors · 5s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })

    expect(state.refsDone).toBe(0)
    expect(state.slots).toHaveLength(6)
    expect(state.slots.every(slot => slot.status === 'running')).toBe(true)
    expect(state.elapsedSeconds).toBe(5)

    state = progress(state, {
      elapsed_seconds: 10,
      label: 'waiting on 6 advisors · 10s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })

    expect(state.elapsedSeconds).toBe(10)
    expect(state.refsDone).toBe(0)
    expect(state.slots.every(slot => slot.label === null)).toBe(true)
    expect(state.waitingLabel).toContain('10s')
  })

  it('does not attribute a completion-only label to a config-order slot', () => {
    let state = progress(emptyMoaState(), { label: 'model-delta', refs_done: 1, refs_total: 6 })
    state = progress(state, { label: 'model-alpha', refs_done: 2, refs_total: 6 })

    expect(state.refsDone).toBe(2)
    expect(state.slots.map(slot => slot.label)).toEqual([null, null, null, null, null, null])
    expect(state.unattributedCompletions).toBe(2)
  })

  it('updates a stable indexed slot in place when advisor 4 finishes before advisor 1', () => {
    let state = progress(emptyMoaState(), {
      index: 4,
      label: 'model-delta',
      refs_done: 1,
      refs_total: 6
    })

    expect(state.slots[3]?.label).toBe('model-delta')
    expect(state.slots[3]?.status).toBe('complete')
    expect(state.slots[0]?.status).toBe('running')
    expect(state.slots[0]?.label).toBeNull()

    state = progress(state, { index: 1, label: 'model-alpha', refs_done: 2, refs_total: 6 })

    expect(state.slots[0]?.label).toBe('model-alpha')
    expect(state.slots[0]?.status).toBe('complete')
    expect(state.slots[3]?.label).toBe('model-delta')
  })

  it('keeps duplicate model labels on distinct slots instead of merging them', () => {
    let state = progress(emptyMoaState(), { index: 1, label: 'same-model', refs_done: 1, refs_total: 2 })
    state = progress(state, { index: 2, label: 'same-model', refs_done: 2, refs_total: 2 })

    expect(state.slots).toHaveLength(2)
    expect(state.slots[0]?.label).toBe('same-model')
    expect(state.slots[1]?.label).toBe('same-model')
    expect(slotIdentityKey(state.slots[0]!)).not.toBe(slotIdentityKey(state.slots[1]!))
  })

  it('marks failed, skipped, and interrupted reference notes without success motion', () => {
    let state = progress(emptyMoaState(), { refs_done: 0, refs_total: 3 })
    state = reference(state, { count: 3, index: 1, label: 'ok', text: 'advice' })
    state = reference(state, { count: 3, index: 2, label: 'boom', text: '[failed: timeout]' })
    state = reference(state, {
      count: 3,
      index: 3,
      label: 'halted',
      text: '[skipped: interrupted by user]'
    })

    expect(state.slots[0]?.status).toBe('complete')
    expect(state.slots[1]?.status).toBe('failed')
    expect(state.slots[2]?.status).toBe('interrupted')
    expect(state.slots[0]?.playSuccessMotion).toBe(true)
    expect(state.slots[1]?.playSuccessMotion).toBe(false)
    expect(state.slots[2]?.playSuccessMotion).toBe(false)
  })

  it('queues advisors beyond the eight-worker cap', () => {
    const state = progress(emptyMoaState(), { refs_done: 0, refs_total: 10 })

    expect(state.slots).toHaveLength(10)
    expect(state.slots.slice(0, 8).every(slot => slot.status === 'running')).toBe(true)
    expect(state.slots.slice(8).every(slot => slot.status === 'queued')).toBe(true)
  })

  it('keeps the aggregator waiting until fan-out settles, then weaves', () => {
    let state = progress(emptyMoaState(), { label: 'a', refs_done: 1, refs_total: 2 })
    state = phase(state, { aggregator: 'agg-model', phase: 'aggregator', refs_done: 1, refs_total: 2 })

    expect(state.aggregatorStatus).toBe('waiting')
    expect(state.phase).toBe('fanout')

    state = progress(state, { index: 2, label: 'b', refs_done: 2, refs_total: 2 })
    state = phase(state, { aggregator: 'agg-model', phase: 'aggregator', refs_done: 2, refs_total: 2 })

    expect(state.aggregatorStatus).toBe('acting')
    expect(state.phase).toBe('aggregating')
    expect(state.aggregatorLabel).toBe('agg-model')
  })

  it('marks cached user_turn reuse without pretending a new fan-out started', () => {
    const state = applyMoaEvent(emptyMoaState(), {
      payload: { cached: true, fanout: 'user_turn', refs_done: 6, refs_total: 6 },
      type: 'moa.progress'
    })

    expect(state.cadence).toBe('cached')
    expect(state.phase).toBe('reused')
    expect(state.parallel).toBe(false)
  })

  it('settles to a compact expandable summary after the turn completes', () => {
    let state = progress(emptyMoaState(), { index: 1, label: 'a', refs_done: 1, refs_total: 1 })
    state = phase(state, { aggregator: 'mix', phase: 'aggregator', refs_done: 1, refs_total: 1 })
    state = applyMoaEvent(state, { payload: {}, type: 'message.complete' })

    expect(state.phase).toBe('settled')
    expect(state.summary).toContain('1')
    expect(state.summary).toContain('mix')
    expect(state.slots[0]?.output).toBeUndefined()
  })

  it('never infers thought percent from elapsed time', () => {
    const state = progress(emptyMoaState(), {
      elapsed_seconds: 45,
      label: 'waiting on model-c · 45s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })

    expect(state.slots.every(slot => slot.outputProgress === undefined)).toBe(true)
    expect(state.thoughtPercent).toBeUndefined()
  })

  it('accepts determinate output progress only from an explicit measurable field', () => {
    const state = progress(emptyMoaState(), {
      index: 1,
      label: 'a',
      output_progress: 0.4,
      refs_done: 1,
      refs_total: 1
    })

    expect(state.slots[0]?.outputProgress).toBe(0.4)
    expect(state.thoughtPercent).toBeUndefined()
  })
})

describe('thinking orb Hermes-state mapping', () => {
  it('maps every reachable Hermes state onto a library orb state', () => {
    expect(thinkingOrbStateFor({ kind: 'advisor', status: 'running' })).toBe('solving')
    expect(thinkingOrbStateFor({ kind: 'aggregator', status: 'acting' })).toBe('weaving')
    expect(thinkingOrbStateFor({ kind: 'tool', toolName: 'web_search' })).toBe('searching')
    expect(thinkingOrbStateFor({ kind: 'tool', toolName: 'browser_navigate' })).toBe('searching')
    expect(thinkingOrbStateFor({ kind: 'tool', toolName: 'terminal' })).toBe('working')
    expect(thinkingOrbStateFor({ kind: 'handshake', target: 'mcp' })).toBe('connecting')
    expect(thinkingOrbStateFor({ kind: 'response' })).toBe('composing')
    expect(thinkingOrbStateFor({ kind: 'approval' })).toBe('listening')
    expect(thinkingOrbStateFor({ kind: 'advisor', status: 'queued' })).toBe('breathing')
    expect(thinkingOrbStateFor({ kind: 'planning' })).toBe('shaping')
  })

  it('fails closed if mapping is sabotaged onto the idle orb', () => {
    expect(thinkingOrbStateFor({ kind: 'advisor', status: 'running' })).not.toBe('breathing')
    expect(thinkingOrbStateFor({ kind: 'aggregator', status: 'acting' })).not.toBe('breathing')
    expect(thinkingOrbStateFor({ kind: 'tool', toolName: 'terminal' })).not.toBe('breathing')
  })
})

describe('screen-reader announcements', () => {
  it('announces count and phase changes, not elapsed ticks', () => {
    let state = progress(emptyMoaState(), {
      elapsed_seconds: 1,
      label: 'waiting on 6 advisors · 1s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })

    const first = moaStatusAnnouncement(state)

    state = progress(state, {
      elapsed_seconds: 2,
      label: 'waiting on 6 advisors · 2s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })

    expect(moaStatusAnnouncement(state)).toBe(first)
    expect(first.toLowerCase()).toContain('parallel')
    expect(first).toContain('0/6')
    expect(first.toLowerCase()).not.toContain('1s')
  })
})
