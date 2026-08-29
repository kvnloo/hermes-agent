import { describe, expect, it } from 'vitest'

import { applyMoaEvent, emptyMoaState, thinkingOrbStateFor } from './moa-orchestration'

const event = (type: string, payload: Record<string, unknown> = {}) => ({ payload, type })

describe('MoA orchestration', () => {
  it('tracks current progress and optional waiting heartbeats', () => {
    let state = applyMoaEvent(emptyMoaState(), event('moa.progress', { refs_done: 0, refs_total: 6 }))
    expect(state.slots).toHaveLength(6)
    expect(state.slots.every(slot => slot.status === 'running')).toBe(true)

    state = applyMoaEvent(state, event('moa.progress', { state: 'waiting', index: 2, label: 'advisor-b', elapsed_seconds: 4 }))
    expect(state.slots[1]).toMatchObject({ label: 'advisor-b', status: 'queued' })
    expect(state.elapsedSeconds).toBe(4)
  })

  it('limits out-of-order completions and fails closed on duplicate labels', () => {
    let state = applyMoaEvent(emptyMoaState(), event('moa.progress', { refs_done: 0, refs_total: 2 }))
    state = applyMoaEvent(state, event('moa.reference', { count: 2, index: 2, label: 'same', text: 'second' }))
    state = applyMoaEvent(state, event('moa.reference', { count: 2, index: 1, label: 'same', text: 'first' }))
    state = applyMoaEvent(state, event('moa.reference', { count: 2, index: 3, label: 'overflow', text: 'ignored' }))

    expect(state.refsDone).toBe(2)
    expect(state.slots.map(slot => slot.label)).toEqual(['same', 'same'])
    expect(state.slots.some(slot => slot.label === 'overflow')).toBe(false)
  })

  it.each([
    ['[failed: timeout]', 'failed'],
    ['[skipped: interrupted by user]', 'interrupted'],
    ['[skipped: unavailable]', 'failed']
  ] as const)('classifies %s as %s', (text, status) => {
    let state = applyMoaEvent(emptyMoaState(), event('moa.progress', { refs_done: 0, refs_total: 1 }))
    state = applyMoaEvent(state, event('moa.reference', { count: 1, index: 1, label: 'advisor', text }))
    expect(state.slots[0]?.status).toBe(status)
  })

  it('accepts both aggregating event shapes only after fanout settles', () => {
    let state = applyMoaEvent(emptyMoaState(), event('moa.progress', { refs_done: 0, refs_total: 1 }))
    expect(applyMoaEvent(state, event('moa.aggregating', { aggregator: 'agg' })).phase).toBe('fanout')

    state = applyMoaEvent(state, event('moa.reference', { count: 1, index: 1, label: 'ref', text: 'done' }))
    expect(applyMoaEvent(state, event('moa.phase', { phase: 'aggregator', aggregator: 'agg' }))).toMatchObject({
      aggregatorLabel: 'agg',
      phase: 'aggregating'
    })
    expect(applyMoaEvent(state, event('moa.aggregating', { aggregator: 'agg' })).phase).toBe('aggregating')
  })

  it('settles only an active MoA turn and drops advisor output from its summary', () => {
    expect(applyMoaEvent(emptyMoaState(), event('message.complete'))).toEqual(emptyMoaState())

    let state = applyMoaEvent(emptyMoaState(), event('moa.progress', { refs_done: 1, refs_total: 1 }))
    state = applyMoaEvent(state, event('message.complete'))
    expect(state).toMatchObject({ phase: 'settled', refsDone: 1, refsTotal: 1 })
  })

  it('maps only relevant semantic actions to library states', () => {
    expect(thinkingOrbStateFor('advisor')).toBe('solving')
    expect(thinkingOrbStateFor('aggregator')).toBe('weaving')
    expect(thinkingOrbStateFor('search')).toBe('searching')
    expect(thinkingOrbStateFor('tool')).toBe('working')
    expect(thinkingOrbStateFor('response')).toBe('composing')
  })
})
