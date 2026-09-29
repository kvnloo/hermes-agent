import { describe, expect, it } from 'vitest'

import { allocateToolRowBudgets, visibleRowSpan } from '../lib/toolRowBudget.js'

describe('visibleRowSpan', () => {
  it('clips a measured row to the visible viewport', () => {
    expect(visibleRowSpan(8, 14, 10, 20)).toBe(4)
    expect(visibleRowSpan(22, 25, 10, 20)).toBe(0)
  })
})

describe('allocateToolRowBudgets', () => {
  const candidates = [
    { index: 4, key: 'old' },
    { index: 9, key: 'new' }
  ]

  it('keeps every visible candidate at one row under pressure', () => {
    const out = allocateToolRowBudgets({
      candidates,
      occupiedRows: 10,
      viewportHeight: 8
    })

    expect(out.get('old')).toBe(1)
    expect(out.get('new')).toBe(1)
  })

  it('spends a single surplus row on the newest tool first', () => {
    const out = allocateToolRowBudgets({
      candidates,
      occupiedRows: 4,
      viewportHeight: 7
    })

    expect(out.get('old')).toBe(1)
    expect(out.get('new')).toBe(2)
  })

  it('fills newer tools to three rows before older tools', () => {
    const out = allocateToolRowBudgets({
      candidates,
      occupiedRows: 4,
      viewportHeight: 9
    })

    expect(out.get('new')).toBe(3)
    expect(out.get('old')).toBe(2)
  })

  it('charges fixed rows such as a group-boundary lead gap', () => {
    const out = allocateToolRowBudgets({
      candidates: [
        { fixedRows: 1, index: 4, key: 'old' },
        { index: 9, key: 'new' }
      ],
      occupiedRows: 4,
      viewportHeight: 7
    })

    expect(out.get('old')).toBe(1)
    expect(out.get('new')).toBe(1)
  })

  it('honors a lower maximum allocation', () => {
    const out = allocateToolRowBudgets({
      candidates,
      maxRowsPerTool: 2,
      occupiedRows: 0,
      viewportHeight: 20
    })

    expect(out.get('old')).toBe(2)
    expect(out.get('new')).toBe(2)
  })
})
