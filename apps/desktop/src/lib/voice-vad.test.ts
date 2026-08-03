import { describe, expect, it } from 'vitest'

import { createVoiceFloor, voiceThreshold } from './voice-vad'

describe('voice VAD policy', () => {
  it('uses a robust floor that ignores a single spike', () => {
    const floor = createVoiceFloor()

    for (const level of [0.02, 0.021, 0.019, 0.8, 0.02]) {
      floor.add(level)
    }

    expect(floor.value()).toBe(0.02)
  })

  it('bounds the adaptive threshold', () => {
    expect(voiceThreshold(0.01, 0.075, 0.37)).toBe(0.075)
    expect(voiceThreshold(0.04, 0.075, 0.37)).toBeCloseTo(0.14)
    expect(voiceThreshold(0.2, 0.075, 0.37)).toBe(0.37)
  })

  it('keeps only the configured recent samples', () => {
    const floor = createVoiceFloor(3)

    for (const level of [0.01, 0.5, 0.02, 0.03]) {
      floor.add(level)
    }

    expect(floor.value()).toBe(0.02)
  })
})
