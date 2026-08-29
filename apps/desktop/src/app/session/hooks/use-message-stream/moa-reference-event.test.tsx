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

describe('useMessageStream moa.reference accumulation (#64658)', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('keeps every reference model labelled slot instead of only the latest one', () => {
    mountStream()

    emit('moa.reference', { count: 2, index: 1, label: 'model-a', text: 'advice-a' })
    emit('moa.reference', { count: 2, index: 2, label: 'model-b', text: 'advice-b' })

    expect(stream.reasoningText()).not.toContain('advice-a')
    expect(stream.state().moa?.slots[0]?.label).toBe('model-a')
    expect(stream.state().moa?.slots[0]?.output).toBe('advice-a')
    expect(stream.state().moa?.slots[1]?.label).toBe('model-b')
    expect(stream.state().moa?.slots[1]?.output).toBe('advice-b')
  })

  it('handles a single-reference MoA turn (count=1) without regression', () => {
    mountStream()

    emit('moa.reference', { count: 1, index: 1, label: 'model-a', text: 'only-advice' })

    expect(stream.state().moa?.slots[0]?.label).toBe('model-a')
    expect(stream.state().moa?.slots[0]?.output).toBe('only-advice')
  })

  it('accumulates three or more references in stable slot order', () => {
    mountStream()

    emit('moa.reference', { count: 3, index: 1, label: 'model-a', text: 'advice-a' })
    emit('moa.reference', { count: 3, index: 2, label: 'model-b', text: 'advice-b' })
    emit('moa.reference', { count: 3, index: 3, label: 'model-c', text: 'advice-c' })

    expect(stream.state().moa?.slots.map(slot => slot.output)).toEqual(['advice-a', 'advice-b', 'advice-c'])
  })
})
