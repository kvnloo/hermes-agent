import { act, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { RpcEvent } from '@/types/hermes'

import { type MessageStreamHarness, renderMessageStream } from './test-harness'

const SID = 'session-1'
let stream: MessageStreamHarness

function mountStream() {
  stream = renderMessageStream(SID)
}

function emit(type: RpcEvent['type'], payload: RpcEvent['payload'] = {}) {
  act(() => stream.handleEvent({ payload, session_id: SID, type }))
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('useMessageStream moa.progress / moa.phase surfacing', () => {
  it('records refs k/n in orchestration state as references complete, not in Thinking', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', { label: 'model-a', refs_done: 1, refs_total: 3 })
    emit('moa.progress', { label: 'model-b', refs_done: 2, refs_total: 3 })

    expect(stream.reasoningText()).not.toContain('MoA refs')
    expect(stream.state().moa?.refsDone).toBe(2)
    expect(stream.state().moa?.refsTotal).toBe(3)
    expect(stream.state().moa?.unattributedCompletions).toBe(2)
  })

  it('restarts orchestration on the first ref of a new fan-out', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', { label: 'stale', refs_done: 1, refs_total: 2 })
    emit('moa.progress', { label: 'stale-2', refs_done: 2, refs_total: 2 })
    emit('moa.progress', { label: 'fresh', refs_done: 1, refs_total: 2 })

    expect(stream.reasoningText()).not.toContain('stale')
    expect(stream.state().moa?.refsDone).toBe(1)
    expect(stream.state().moa?.refsTotal).toBe(2)
  })

  it('ignores unknown phases and waits to act until fan-out settles', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', { label: 'model-a', refs_done: 1, refs_total: 1 })
    emit('moa.phase', { phase: 'reference', refs_done: 1, refs_total: 1 })
    expect(stream.state().moa?.phase).not.toBe('aggregating')

    emit('moa.phase', { aggregator: 'agg-model', phase: 'aggregator', refs_done: 1, refs_total: 1 })
    expect(stream.reasoningText()).not.toContain('aggregating')
    expect(stream.state().moa?.phase).toBe('aggregating')
    expect(stream.state().moa?.aggregatorLabel).toBe('agg-model')
  })

  it('a following moa.reference fills a labelled slot without Thinking prose', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', { label: 'model-a', refs_done: 1, refs_total: 1 })
    emit('moa.phase', { phase: 'aggregator', refs_done: 1, refs_total: 1 })
    emit('moa.reference', { count: 1, index: 1, label: 'model-a', text: 'advice-a' })

    expect(stream.reasoningText()).not.toContain('Reference 1/1')
    expect(stream.reasoningText()).not.toContain('MoA refs')
    expect(stream.state().moa?.slots[0]?.label).toBe('model-a')
    expect(stream.state().moa?.slots[0]?.output).toBe('advice-a')
  })
})
