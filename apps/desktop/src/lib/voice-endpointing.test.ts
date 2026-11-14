import { describe, expect, it } from 'vitest'

import { AdaptiveEndpoint } from './voice-endpointing'

describe('AdaptiveEndpoint', () => {
  it('ignores a short noise spike and requires minimum voiced duration', () => {
    const endpoint = new AdaptiveEndpoint()
    expect(endpoint.push(0.01, 0)).toBe('idle')
    expect(endpoint.push(0.2, 40)).toBe('idle')
    expect(endpoint.push(0.01, 100)).toBe('idle')
    expect(endpoint.push(0.15, 200)).toBe('idle')
    expect(endpoint.push(0.15, 500)).toBe('voiced')
  })

  it('uses hysteresis and hangover before bounded silence endpointing', () => {
    const endpoint = new AdaptiveEndpoint({ silenceMs: 900 })
    endpoint.push(0.01, 0)
    endpoint.push(0.2, 100)
    expect(endpoint.push(0.2, 400)).toBe('voiced')
    expect(endpoint.push(0.01, 800)).toBe('voiced')
    expect(endpoint.push(0.01, 1_100)).toBe('silence')
    expect(endpoint.push(0.01, 2_050)).toBe('endpoint')
  })
})
