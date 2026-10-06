import { describe, expect, it } from 'vitest'

import { ACTIVE_TERN_UX_VARIANT } from './activeVariant.js'
import { BASE_TERN_UX_VARIANT, TERN_UX_VARIANT_IDS, validateTernUxVariant } from './variant.js'

describe('Tern UX variant contract', () => {
  it('keeps the shared contract valid on every experiment branch', () => {
    expect(TERN_UX_VARIANT_IDS).toEqual([
      'base',
      'omp-baseline',
      'hermes-baseline',
      'attention-minimal'
    ])
    expect(validateTernUxVariant(ACTIVE_TERN_UX_VARIANT)).toEqual([])
  })

  it('keeps the base descriptor presentation-neutral when selected', () => {
    if (ACTIVE_TERN_UX_VARIANT.id !== 'base') {
      return
    }

    expect(ACTIVE_TERN_UX_VARIANT).toBe(BASE_TERN_UX_VARIANT)
    expect(ACTIVE_TERN_UX_VARIANT.hypothesis).toContain('No presentation hypothesis')
  })
})
