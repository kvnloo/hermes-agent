// W2 probe (evidence only): #99042's orphan detector on consecutive calls.
// Only meaningful on states that include #99042 (expandTokens returns {expanded, unresolved}).
import { describe, expect, it } from 'vitest'

import { expandTokens } from '../domain/attachments.js'

const label = '[[ lost.. [5 lines] .. data ]]'

describe('probe: orphaned paste label detection is stable', () => {
  it('flags the same orphaned label on four consecutive submits', () => {
    const results = [1, 2, 3, 4].map(() => (expandTokens([])(`submit: ${label}`) as unknown as { unresolved: string[] }).unresolved)

    expect(results).toEqual([[label], [label], [label], [label]])
  })
})
