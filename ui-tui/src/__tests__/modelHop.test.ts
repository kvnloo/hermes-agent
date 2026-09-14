import { describe, expect, it } from 'vitest'

import { flattenHopModels, hopSelectValue, modelHopOverlay } from '../domain/modelHop.js'
import { TUI_SESSION_MODEL_FLAG } from '../domain/slash.js'
import type { ModelOptionProvider } from '../gatewayTypes.js'

const provider = (partial: Partial<ModelOptionProvider> & Pick<ModelOptionProvider, 'name' | 'slug'>): ModelOptionProvider => ({
  authenticated: true,
  models: [],
  ...partial
})

describe('flattenHopModels', () => {
  it('flattens authenticated providers into a single type-to-search list', () => {
    const rows = flattenHopModels([
      provider({ name: 'Nous', slug: 'nous', is_current: true, models: ['hermes-4', 'gpt-oss'] }),
      provider({ name: 'Ollama', slug: 'ollama', models: ['llama3'] })
    ])

    expect(rows.map(r => r.id)).toEqual(['hermes-4', 'gpt-oss', 'llama3'])
    expect(rows[0]).toMatchObject({ provider: 'nous', label: 'nous/hermes-4' })
  })

  it('skips unauthenticated providers so hop never opens a setup menu', () => {
    const rows = flattenHopModels([
      provider({ name: 'OpenAI', slug: 'openai', authenticated: false, models: ['gpt-4o'] }),
      provider({ name: 'Nous', slug: 'nous', models: ['hermes-4'] })
    ])

    expect(rows.map(r => r.id)).toEqual(['hermes-4'])
  })

  it('marks the current session model', () => {
    const rows = flattenHopModels(
      [provider({ name: 'Nous', slug: 'nous', models: ['a', 'b'] })],
      'b'
    )

    expect(rows.find(r => r.id === 'b')?.current).toBe(true)
    expect(rows.find(r => r.id === 'a')?.current).toBe(false)
  })
})

describe('hopSelectValue', () => {
  it('applies a session-only switch without --global', () => {
    expect(
      hopSelectValue({ current: false, id: 'hermes-4', label: 'nous/hermes-4', provider: 'nous' })
    ).toBe(`hermes-4 --provider nous ${TUI_SESSION_MODEL_FLAG}`)
  })
})

describe('modelHopOverlay', () => {
  it('opens the full picker for a bare /model', () => {
    expect(modelHopOverlay('')).toBe(true)
  })

  it('opens hop mode for --session', () => {
    expect(modelHopOverlay('--session')).toEqual({ sessionOnly: true })
  })

  it('does not steal a typed model name', () => {
    expect(modelHopOverlay('--session sonnet')).toBe(false)
  })
})
