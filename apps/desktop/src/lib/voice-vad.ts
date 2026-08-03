export const VOICE_FLOOR_CALIBRATION_MS = 400
export const VOICE_TRIGGER_CEILING = 0.37

const VOICE_FLOOR_MULTIPLIER = 3.5

export function createVoiceFloor(capacity = 200) {
  const samples: number[] = []

  return {
    add(level: number) {
      samples.push(level)
      samples.splice(0, Math.max(0, samples.length - capacity))
    },
    value() {
      const ordered = [...samples].sort((a, b) => a - b)

      return ordered[Math.floor((ordered.length - 1) * 0.25)] ?? 0
    }
  }
}

export function voiceThreshold(floor: number, minimum: number, maximum: number): number {
  return Math.min(maximum, Math.max(minimum, floor * VOICE_FLOOR_MULTIPLIER))
}
