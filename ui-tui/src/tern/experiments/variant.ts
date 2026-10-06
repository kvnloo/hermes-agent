export const TERN_UX_VARIANT_IDS = [
  'base',
  'omp-baseline',
  'hermes-baseline',
  'attention-minimal'
] as const

export type TernUxVariantId = (typeof TERN_UX_VARIANT_IDS)[number]

export interface TernUxVariantDefinition {
  id: TernUxVariantId
  label: string
  hypothesis: string
  primaryReference: string
  invariants: readonly string[]
  forbidden: readonly string[]
}

export function defineTernUxVariant(definition: TernUxVariantDefinition): TernUxVariantDefinition {
  return definition
}

export function validateTernUxVariant(definition: TernUxVariantDefinition): string[] {
  const violations: string[] = []

  if (!TERN_UX_VARIANT_IDS.includes(definition.id)) {
    violations.push('unknown-variant')
  }

  if (!definition.label.trim()) {
    violations.push('missing-label')
  }

  if (!definition.hypothesis.trim()) {
    violations.push('missing-hypothesis')
  }

  if (!definition.primaryReference.trim()) {
    violations.push('missing-primary-reference')
  }

  if (definition.invariants.length === 0) {
    violations.push('missing-invariants')
  }

  if (definition.forbidden.length === 0) {
    violations.push('missing-forbidden-list')
  }

  return violations
}

export const BASE_TERN_UX_VARIANT = defineTernUxVariant({
  id: 'base',
  label: 'Shared experiment base',
  hypothesis: 'No presentation hypothesis. This branch only owns shared fixtures, tooling and receipts.',
  primaryReference: 'https://github.com/kvnloo/hermes-agent/issues/436',
  invariants: [
    'All variants use the same tern-ux-v1 fixture and viewport matrix.',
    'The shared base does not choose a visual design.',
    'Hermes runtime, session, tool and approval authority remain unchanged.'
  ],
  forbidden: [
    'Variant-specific visual choices.',
    'A second runtime or session state model.',
    'Generated mockups presented as evidence from Tern.'
  ]
})
