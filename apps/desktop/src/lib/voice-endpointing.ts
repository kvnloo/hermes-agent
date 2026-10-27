export type EndpointState = 'idle' | 'voiced' | 'silence' | 'endpoint'

export interface AdaptiveEndpointOptions {
  /** Minimum continuous speech before a turn is accepted. */
  minSpeechMs?: number
  /** Silence required after accepted speech. */
  silenceMs?: number
  /** Keep the turn voiced through short dips below the end threshold. */
  hangoverMs?: number
  /** End an empty recording instead of holding the microphone forever. */
  idleTimeoutMs?: number
  /** Hard upper bound for every recording, including intermittent noise. */
  maxDurationMs?: number
  /** Threshold above the learned floor required to begin speech. */
  startMargin?: number
  /** Lower margin used after speech begins (hysteresis). */
  endMargin?: number
  /** Initial floor before enough ambient samples have arrived. */
  initialNoiseFloor?: number
  /** Prevent a loud room from adapting the speech threshold without bound. */
  maxNoiseFloor?: number
}

const DEFAULTS: Required<AdaptiveEndpointOptions> = {
  minSpeechMs: 300,
  silenceMs: 1_250,
  hangoverMs: 250,
  idleTimeoutMs: 12_000,
  maxDurationMs: 60_000,
  startMargin: 0.045,
  endMargin: 0.02,
  initialNoiseFloor: 0.01,
  maxNoiseFloor: 0.08
}

/**
 * Adaptive, timestamp-driven endpoint detector shared by browser capture and
 * deterministic tests. Samples are normalized RMS values in [0, 1].
 *
 * The floor only learns while speech is not accepted, and only from samples
 * below the current start threshold. This lets it follow fans/room tone without
 * allowing speech or spikes to ratchet the threshold upward. Separate start/end
 * margins provide hysteresis; minimum speech and hangover reject clicks and
 * preserve natural intra-sentence dips. Idle and total bounds guarantee exit.
 */
export class AdaptiveEndpoint {
  private readonly options: Required<AdaptiveEndpointOptions>
  private firstAt: number | null = null
  private candidateAt: number | null = null
  private acceptedAt: number | null = null
  private belowEndAt: number | null = null
  private silenceAt: number | null = null
  private floor: number
  private done = false

  constructor(options: AdaptiveEndpointOptions = {}) {
    const defined = Object.fromEntries(Object.entries(options).filter(([, value]) => value !== undefined))
    this.options = { ...DEFAULTS, ...defined }
    this.floor = this.options.initialNoiseFloor
  }

  get noiseFloor(): number {
    return this.floor
  }

  get heardSpeech(): boolean {
    return this.acceptedAt !== null
  }

  reset(): void {
    this.firstAt = null
    this.candidateAt = null
    this.acceptedAt = null
    this.belowEndAt = null
    this.silenceAt = null
    this.floor = this.options.initialNoiseFloor
    this.done = false
  }

  push(rawLevel: number, now: number): EndpointState {
    if (this.done) {
      return 'endpoint'
    }

    const level = Math.max(0, Math.min(1, Number.isFinite(rawLevel) ? rawLevel : 0))
    this.firstAt ??= now

    if (now - this.firstAt >= this.options.maxDurationMs) {
      return this.finish()
    }
    if (!this.heardSpeech && now - this.firstAt >= this.options.idleTimeoutMs) {
      return this.finish()
    }

    const startThreshold = Math.min(1, this.floor + this.options.startMargin)
    const endThreshold = Math.min(1, this.floor + this.options.endMargin)

    if (!this.heardSpeech) {
      if (level >= startThreshold) {
        this.candidateAt ??= now
        if (now - this.candidateAt >= this.options.minSpeechMs) {
          this.acceptedAt = this.candidateAt
          this.belowEndAt = null
          return 'voiced'
        }
      } else {
        this.candidateAt = null
        this.learnFloor(level)
      }
      return 'idle'
    }

    if (level >= endThreshold) {
      this.belowEndAt = null
      this.silenceAt = null
      return 'voiced'
    }

    this.belowEndAt ??= now
    if (now - this.belowEndAt < this.options.hangoverMs) {
      return 'voiced'
    }

    this.silenceAt ??= now
    if (now - this.silenceAt >= this.options.silenceMs) {
      return this.finish()
    }

    return 'silence'
  }

  private learnFloor(level: number): void {
    const bounded = Math.min(level, this.options.maxNoiseFloor)
    // Slow enough to ignore one-frame spikes, quick enough to calibrate during
    // the opening second of room tone.
    this.floor = Math.min(this.options.maxNoiseFloor, this.floor * 0.92 + bounded * 0.08)
  }

  private finish(): EndpointState {
    this.done = true
    return 'endpoint'
  }
}
