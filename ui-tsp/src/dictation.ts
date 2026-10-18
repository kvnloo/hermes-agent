// Review-only dictation. Audio and hypotheses belong to the gateway; the final
// event is the only one that edits the composer. No capture starts on adoption.
import { randomUUID } from 'node:crypto'

import type { DictationPayload } from '@hermes/shared/gateway-events'
import type { AnyGatewayEvent } from '@tui/gatewayTypes.js'

import type { App } from './app.js'

// SDK 0.1.0 exposes presses only: it collapses CSI-u press/repeat/release
// into the same Key and negotiates kitty flag 1 (not event types). Never
// arm a hold from repeats, feature-name guesses or a simulated release timer.
export const DICTATION_HOLD_UNAVAILABLE = 'Hold-to-talk unavailable: this Tern SDK does not expose reliable key-down/key-up events. Use Mic / Alt+V to start and finish review-only dictation; Esc discards.'

interface Capture {
  id: string
  sid: string
  started: Promise<unknown>
  stopping: boolean
  cancelled: boolean
}

export class Dictation {
  state: DictationPayload['state'] = 'idle'
  partial = ''
  error = ''
  #capture: Capture | undefined

  constructor(readonly app: App) {}

  get blocked(): boolean {
    return Boolean(this.#capture) || (this.state !== 'idle' && this.state !== 'error')
  }

  get label(): string {
    const labels: Record<DictationPayload['state'], string> = {
      idle: 'Mic',
      starting: 'Starting microphone… · Send disabled · Esc cancels',
      recording: 'Recording · Send disabled · click Mic to finish · Esc discards',
      transcribing: this.#capture?.cancelled ? 'Discarding recording… · Send disabled' : 'Transcribing… · Send disabled · Esc discards',
      error: `Microphone error: ${this.error} · click to retry`
    }

    return labels[this.state]
  }

  /** An unavailable gesture is informational, never microphone activation. */
  explainHold() {
    this.app.transcript.notice(DICTATION_HOLD_UNAVAILABLE, 'warning')
    this.app.changed()
  }

  get holdHint(): string { return DICTATION_HOLD_UNAVAILABLE }

  toggle() {
    if (this.blocked) {
      if (this.state === 'recording' || this.state === 'error') {
        void this.stop(this.state === 'error')
      }

      return
    }

    const sid = this.app.sid

    if (!sid || this.app.liveVoice.blocked || this.app.overlays.some(o => o.modal)) {
      return
    }

    this.state = 'starting'
    this.partial = this.error = ''

    const capture: Capture = {
      id: randomUUID(), sid, started: Promise.resolve(), stopping: false, cancelled: false
    }

    this.#capture = capture
    capture.started = this.app.gw.request('voice.dictate.start', { capture_id: capture.id, session_id: sid })
    void capture.started.catch(error => this.#fail(capture, error))
    this.app.changed()
  }

  async stop(cancel = false) {
    const capture = this.#capture

    if (!capture || (capture.stopping && !cancel)) {
      return
    }

    capture.stopping = true
    capture.cancelled ||= cancel
    this.state = 'transcribing'
    this.app.changed()

    try {
      // Long-handler RPCs may execute out of order. Never stop an unaccepted start.
      await capture.started
      await this.app.gw.request('voice.dictate.stop', {
        cancel: capture.cancelled, capture_id: capture.id, session_id: capture.sid
      })

      if (capture.cancelled && this.#capture === capture) {
        this.reset()
      }
    } catch (error) {
      if (this.#capture === capture) {
        // A transport failure is not evidence the microphone stopped. Retain
        // ownership and Send gating so Escape/Mic can retry cancellation.
        this.state = 'error'
        this.error = `${error instanceof Error ? error.message : String(error)} · Esc retries cancellation`
        this.app.changed()
      }
    }
  }

  reset() {
    this.#capture = undefined
    this.state = 'idle'
    this.partial = this.error = ''
    this.app.changed()
  }

  event(ev: AnyGatewayEvent) {
    if (ev.type !== 'voice.dictation') {
      return
    }

    const capture = this.#capture
    const p = ev.payload

    if (!p || !capture || capture.cancelled || this.app.sid !== capture.sid ||
        ev.session_id !== capture.sid || p.capture_id !== capture.id) {
      return
    }

    if (p.state === 'error') {
      this.#fail(capture, p.error || 'Speech transcription failed')

      return
    }

    if (p.final) {
      if (p.text) {
        this.app.composer.splice(this.app.composer.cursor, this.app.composer.cursor, p.text)
      }

      this.reset()

      return
    }

    this.state = capture.stopping ? 'transcribing' : p.state

    if (p.text !== null && p.text !== undefined) {
      this.partial = p.text
    }

    this.app.changed()
  }

  #fail(capture: Capture, error: unknown) {
    if (this.#capture !== capture) {
      return
    }

    this.#capture = undefined
    this.state = 'error'
    this.error = error instanceof Error ? error.message : String(error)
    this.partial = ''
    this.app.changed()
  }
}
