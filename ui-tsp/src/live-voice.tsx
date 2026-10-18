// Separate opt-in conversation, never the review-only dictation path.
import { randomUUID } from 'node:crypto'

import type { LiveVoicePayload } from '@hermes/shared/gateway-events'
import type { AnyGatewayEvent } from '@tui/gatewayTypes.js'

import type { App } from './app.js'
import { ActionButton } from './view/action-button.js'

interface Lease {
  id: string
  sid: string
  started: Promise<unknown>
  stopping: boolean
}

export class LiveVoice {
  phase: LiveVoicePayload['phase'] | 'consent' = 'idle'
  muted = false
  error = ''
  assistant = ''
  #lease: Lease | undefined

  constructor(readonly app: App) {}

  get blocked(): boolean {
    return Boolean(this.#lease) || this.phase === 'consent'
  }

  get captureBlocked(): boolean { return this.blocked || this.app.dictation.blocked }

  toggle() {
    if (this.#lease) {
      void this.control('stop')

      return
    }

    if (!this.app.sid || this.app.dictation.blocked || this.app.overlays.some(o => o.modal)) {
      return
    }

    this.error = ''
    this.phase = this.phase === 'consent' ? 'idle' : 'consent'
    this.app.changed()
  }

  start() {
    const sid = this.app.sid

    if (this.phase !== 'consent' || !sid || this.app.dictation.blocked) {
      return
    }

    const lease: Lease = { id: randomUUID(), sid, started: Promise.resolve(), stopping: false }
    this.#lease = lease
    this.phase = 'starting'
    this.muted = false
    this.assistant = ''
    lease.started = this.app.gw.request('voice.live.start', { session_id: sid, live_id: lease.id, consent: true })
    void lease.started.catch(error => {
      if (this.#lease === lease) {
        this.#lease = undefined
        this.#fail(error)
      }
    })
    this.app.changed()
  }

  async control(action: 'stop' | 'mute' | 'interrupt') {
    const lease = this.#lease

    if (!lease) {
      if (action === 'stop') {
        this.phase = 'idle'
        this.app.changed()
      }

      return
    }

    if (action === 'stop') {
      lease.stopping = true
      this.phase = 'stopping'
      this.app.changed()
    }

    try {
      await lease.started
      await this.app.gw.request('voice.live.control', {
        session_id: lease.sid,
        live_id: lease.id,
        action,
        muted: !this.muted
      })
    } catch (error) {
      // Keep the lease and Send gate until an idle event proves audio was released.
      if (this.#lease === lease) {
        this.#fail(error)
      }
    }
  }

  disconnect() {
    this.#lease = undefined
    this.phase = 'idle'
    this.muted = false
    this.app.changed()
  }

  event(ev: AnyGatewayEvent) {
    if (ev.type !== 'voice.live') {
      return
    }

    const lease = this.#lease
    const p = ev.payload

    if (!lease || !p || p.live_id !== lease.id || ev.session_id !== lease.sid) {
      return
    }

    if (p.phase === 'idle') {
      this.#lease = undefined
      this.phase = this.error ? 'error' : 'idle'
    } else if (this.app.sid === lease.sid && !lease.stopping) {
      this.phase = p.phase
      this.muted = p.muted ?? false
      this.error = p.error || this.error
      this.assistant = p.assistant_text || this.assistant

      if (p.user_text) {
        this.app.transcript.push({ id: this.app.transcript.id('u'), kind: 'user', text: p.user_text, at: Date.now() })
      }
    }

    this.app.changed()
  }

  #fail(error: unknown) {
    this.phase = 'error'
    this.error = error instanceof Error ? error.message : String(error)
    this.app.changed()
  }

  view() {
    return (
      <col key="live-voice" role={`omp.live.${this.phase}`}>
        <ActionButton
          key="toggle"
          onClick={() => this.toggle()}
          role="omp.live.toggle"
          text={this.#lease ? 'Stop live voice' : 'Live voice…'}
        />
        {this.phase === 'consent' ? (
          <col key="consent">
            <text
              key="notice"
              text="Live voice opens the gateway machine’s microphone and speaker. Spoken turns are sent automatically and replies spoken through your configured Hermes STT/TTS providers. Your draft is not sent. Device permission is required. Use Mic / Alt+V for review-only dictation instead."
            />
            <ActionButton
              key="start"
              onClick={() => this.start()}
              role="omp.live.start"
              text="Allow microphone + automatic spoken turns"
            />
            <ActionButton key="cancel" onClick={() => void this.control('stop')} role="omp.live.cancel" text="Cancel" />
          </col>
        ) : null}
        {this.#lease ? (
          <row gap="sm" key="controls">
            <text
              key="phase"
              role="omp.live.phase"
              text={`Live voice: ${this.phase}${this.muted ? ' · microphone muted' : ''} · draft Send disabled`}
            />
            <ActionButton
              key="mute"
              onClick={() => void this.control('mute')}
              role="omp.live.mute"
              text={this.muted ? 'Unmute' : 'Mute'}
            />
            <ActionButton
              key="interrupt"
              onClick={() => void this.control('interrupt')}
              role="omp.live.interrupt"
              text="Barge in / silence reply"
            />
          </row>
        ) : null}
        {this.assistant ? <text key="assistant" role="omp.live.assistant" text={this.assistant} /> : null}
        {this.error ? (
          <text
            key="error"
            role="omp.live.failure"
            text={`${this.error}${this.#lease ? ' · Stop retries device release' : ' · activate Live voice to retry'}`}
            tone="error"
          />
        ) : null}
      </col>
    )
  }
}
