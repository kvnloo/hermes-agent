import { act, cleanup } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { applyMoaEvent, emptyMoaState } from '@/lib/moa-orchestration'
import type { RpcEvent } from '@/types/hermes'

import { type MessageStreamHarness, renderMessageStream } from './test-harness'
import { STREAM_DELTA_FLUSH_MS } from './utils'

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
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('useMessageStream MoA orchestration (#97674)', () => {
  it('keeps current-main completion progress out of the Thinking transcript', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', { label: 'model-a', refs_done: 1, refs_total: 6 })

    expect(stream.reasoningText()).not.toContain('MoA refs')
    expect(stream.state().moa?.refsDone).toBe(1)
    expect(stream.state().moa?.refsTotal).toBe(6)
    expect(stream.state().moa?.slots).toHaveLength(6)
    expect(stream.state().moa?.slots.every(slot => slot.label === null)).toBe(true)
  })

  it('applies optional #71796 waiting metadata without appending heartbeat noise', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', {
      elapsed_seconds: 5,
      label: 'waiting on 6 advisors · 5s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })
    emit('moa.progress', {
      elapsed_seconds: 10,
      label: 'waiting on 6 advisors · 10s',
      refs_done: 0,
      refs_total: 6,
      state: 'waiting'
    })

    expect(stream.reasoningText()).toBe('')
    expect(stream.state().moa?.elapsedSeconds).toBe(10)
    expect(stream.state().moa?.waitingLabel).toContain('10s')
    expect(stream.state().moa?.refsDone).toBe(0)
  })

  it('sabotaging applyMoaEvent into a no-op would hide waiting metadata', () => {
    const waiting = applyMoaEvent(emptyMoaState(), {
      payload: {
        elapsed_seconds: 4,
        label: 'waiting on 6 advisors · 4s',
        refs_done: 0,
        refs_total: 6,
        state: 'waiting'
      },
      type: 'moa.progress'
    })

    expect(waiting.elapsedSeconds).toBe(4)
    expect(emptyMoaState().elapsedSeconds).toBeUndefined()
  })

  it('does not treat a following reference as six default prose blocks', () => {
    mountStream()

    emit('message.start')
    emit('moa.progress', { refs_done: 1, refs_total: 1 })
    emit('moa.phase', { aggregator: 'mix', phase: 'aggregator', refs_done: 1, refs_total: 1 })
    emit('moa.reference', { count: 1, index: 1, label: 'model-a', text: 'advice-a' })

    expect(stream.reasoningText()).not.toContain('Reference 1/1')
    expect(stream.reasoningText()).not.toContain('advice-a')
    expect(stream.state().moa?.slots[0]?.label).toBe('model-a')
    expect(stream.state().moa?.slots[0]?.output).toBe('advice-a')
  })

  it('leaves ordinary reasoning deltas unchanged', async () => {
    vi.useFakeTimers()
    mountStream()

    emit('message.start')
    emit('reasoning.delta', { text: 'checking the file' })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(STREAM_DELTA_FLUSH_MS)
    })

    expect(stream.reasoningText()).toContain('checking the file')
    expect(stream.state().moa).toBeUndefined()
  })
})
