import { describe, expect, it } from 'vitest'

import { TURBO_ROUTE_IDS, turboRouteId } from './turbo-models'

describe('vLLM Semantic Router virtual model identity', () => {
  it('recognizes every advertised route on bare and custom providers', () => {
    for (const id of TURBO_ROUTE_IDS) {
      expect(turboRouteId('vllm-sr', id)).toBe(id)
      expect(turboRouteId('custom:vllm-sr', `vllm-sr/${id}`)).toBe(id)
    }
  })

  it('does not claim other providers or unknown routes', () => {
    expect(turboRouteId('openrouter', 'vllm-sr/turbo')).toBeNull()
    expect(turboRouteId('custom:vllm-sr', 'free-unknown')).toBeNull()
  })
})
