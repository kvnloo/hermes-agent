import { act, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { RpcEvent } from '@/types/hermes'

import { renderMessageStream } from './test-harness'

const SID = 'moa-session'

afterEach(cleanup)

describe('structured MoA stream state', () => {
  it('routes progress, references, phase compatibility, aggregating, and completion', () => {
    const stream = renderMessageStream(SID)

    const emit = (type: RpcEvent['type'], payload: RpcEvent['payload'] = {}) =>
      act(() => stream.handleEvent({ payload, session_id: SID, type }))

    emit('message.start')
    emit('moa.progress', { refs_done: 0, refs_total: 2 })
    expect(stream.state().moa).toMatchObject({ phase: 'fanout', refsDone: 0, refsTotal: 2 })

    emit('moa.reference', { count: 2, index: 1, label: 'one', text: 'advice' })
    emit('moa.reference', { count: 2, index: 2, label: 'two', text: 'advice' })
    emit('moa.phase', { aggregator: 'judge', phase: 'aggregator' })
    expect(stream.state().moa).toMatchObject({ aggregatorLabel: 'judge', phase: 'aggregating' })

    emit('moa.aggregating', { aggregator: 'judge-2' })
    expect(stream.state().moa).toMatchObject({ aggregatorLabel: 'judge-2', phase: 'aggregating' })

    emit('message.complete', { text: 'answer' })
    expect(stream.state().moa).toMatchObject({ phase: 'settled', refsDone: 2, refsTotal: 2 })
  })
})
