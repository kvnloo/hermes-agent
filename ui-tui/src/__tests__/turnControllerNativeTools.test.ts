import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { getTurnState, resetTurnState } from '../app/turnStore.js'
import { turnController } from '../app/turnController.js'

describe('structured native tool lifecycle snapshots', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    turnController.fullReset()
    resetTurnState()
  })

  afterEach(() => {
    turnController.fullReset()
    vi.useRealTimers()
  })

  it('moves one stable tool id from active to failed terminal snapshot', () => {
    turnController.recordToolStart('call-1', 'terminal', 'npm test', '{"command":"npm test"}')
    expect(getTurnState().tools.map(tool => tool.id)).toEqual(['call-1'])

    turnController.recordToolComplete(
      'call-1',
      'terminal',
      'exit 1',
      1.5,
      undefined,
      'permission denied',
      undefined,
      true
    )

    const state = getTurnState()
    expect(state.tools).toEqual([])
    const snapshot = state.streamSegments.flatMap(msg => msg.nativeTools ?? []).at(-1)

    expect(snapshot).toMatchObject({
      id: 'call-1',
      name: 'terminal',
      status: 'failed',
      summary: 'exit 1',
      resultText: 'permission denied',
      durationSeconds: 1.5
    })
    expect(state.streamSegments.some(msg => msg.tools?.some(line => line.endsWith(' ✗')))).toBe(true)
  })

  it('records structured success without inferring failure from result prose', () => {
    turnController.recordToolStart('call-2', 'read_file', 'src/tasks.ts')
    turnController.recordToolComplete(
      'call-2',
      'read_file',
      'read complete',
      0.4,
      undefined,
      'the word error appears in ordinary content',
      undefined,
      false
    )

    const snapshot = getTurnState().streamSegments.flatMap(msg => msg.nativeTools ?? []).at(-1)
    expect(snapshot?.status).toBe('done')
  })
})
