// Host progress is separate from app dispatch notices and frame visibility.
// OSC sequences follow OMP's terminal.ts (Can Bölük / Stencil, MIT).

export interface HostState {
  sid: string | null
  working: boolean
  /** A queued handoff awaiting admission; retain progress, never invent a new run. */
  submitting?: boolean
  waiting: boolean
}

type Phase = 'idle' | 'working' | 'waiting'

const PROGRESS: Record<Phase, string> = {
  idle: '\x1b]9;4;0;\x07',
  working: '\x1b]9;4;3\x07',
  waiting: '\x1b]9;4;4\x07'
}

/** Edge-only projection: no polling, percentages, bells or duplicate completion alerts. */
export class HostLifecycle {
  #sid: string | null = null
  #phase: Phase = 'idle'

  constructor(private readonly write: (text: string) => void) {}

  /** Only the final confirmed turn in a queued batch needs completion attention. */
  finish(status: string | null | undefined): void {
    if (this.#phase === 'idle') {
      return
    }

    this.#phase = 'idle'
    this.write(PROGRESS.idle)
    const message = status === 'error' ? 'Turn failed' : status === 'interrupted' ? 'Turn interrupted' : 'Turn finished'
    this.write(`\x1b]777;notify;Hermes;${message}\x07`)
  }

  project(state: HostState): void {
    // A different session must not inherit the previous session's progress.
    if (this.#sid !== state.sid && this.#phase !== 'idle') {
      this.write(PROGRESS.idle)
      this.#phase = 'idle'
    }

    this.#sid = state.sid
    const working = state.working || (state.submitting && this.#phase !== 'idle')
    const phase = !state.sid ? 'idle' : state.waiting ? 'waiting' : working ? 'working' : 'idle'

    if (phase !== this.#phase) {
      this.#phase = phase
      this.write(PROGRESS[phase])

      if (phase === 'waiting') {
        this.write('\x1b]777;notify;Hermes;Input required\x07')
      }
    }
  }
}
