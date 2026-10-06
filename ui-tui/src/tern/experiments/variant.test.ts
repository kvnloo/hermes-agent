import { describe, expect, it } from 'vitest'

import { ACTIVE_TERN_UX_VARIANT } from './activeVariant.js'
import { BASE_TERN_UX_VARIANT, TERN_UX_VARIANT_IDS, validateTernUxVariant } from './variant.js'

describe('Tern UX variant contract', () => {
  it('keeps the shared branch presentation-neutral', () => {
    expect(ACTIVE_TERN_UX_VARIANT).toBe(BASE_TERN_UX_VARIANT)
    expect(ACTIVE_TERN_UX_VARIANT.id).toBe('base')
  })

  it('accepts the four experiment identities only', () => {
    expect(TERN_UX_VARIANT_IDS).toEqual([
      'base',
      'omp-baseline',
      'hermes-baseline',
      'attention-minimal'
    ])
    expect(validateTernUxVariant(ACTIVE_TERN_UX_VARIANT)).toEqual([])
  })
})
