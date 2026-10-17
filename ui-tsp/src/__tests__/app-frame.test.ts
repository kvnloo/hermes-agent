import { rmSync } from 'node:fs'

import { afterAll, describe, expect, it, vi } from 'vitest'

import { replay } from '../../bench/replay.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-frame-test-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { recursive: true, force: true })
})

describe('App credit-paced streaming (real SDK)', () => {
  it('builds only once per credit, preserving 5000 deltas and every tool result on the wire', async () => {
    const result = await replay()
    expect(result.events).toBe(5042)
    expect(result.renders).toBe(127) // baseline 502: counter gate, never a wall-clock assertion
    expect(result.frames).toBe(128)
    expect(result.droppedSemanticEvents).toBe(0)
    expect(result.toolRecords).toBe(20)
    expect(result.toolRunningSnapshotsMerged).toBe(0)
  }, 15000)

  it.each([1, 8])(
    'does no hidden-pane builds with %i credits, then flushes the newest state',
    async credits => {
      const result = await replay({ credits, hidden: true })
      expect(result.hiddenRenders).toBe(0)
      expect(result.renders).toBe(2)
      expect(result.frames).toBe(3)
      expect(result.droppedSemanticEvents).toBe(0)
      expect(result.toolRecords).toBe(20)
    },
    15000
  )

  it('keeps the final model in scrollback when quitting hidden without an ACK', async () => {
    const result = await replay({ hidden: true, quitBeforeAck: true })
    expect(result.droppedSemanticEvents).toBe(0)
    expect(result.toolRecords).toBe(20)
  }, 15000)
})
