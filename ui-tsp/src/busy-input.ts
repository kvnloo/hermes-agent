import type { ConfigGetResult, SessionCorrectionResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'

/** Presentation of the gateway's busy setting; never interrupts or owns a second prompt queue. */
export class BusyInput {
  mode: 'queue' | 'steer' = 'queue'
  #pending = false
  #read = 0

  constructor(private readonly app: App) {}

  async refresh() {
    const sid = this.app.sid
    const read = ++this.#read

    if (!sid) {
      return
    }

    try {
      const result = await this.app.gw.request<ConfigGetResult>('config.get', { key: 'busy', session_id: sid })

      if (this.app.sid === sid && read === this.#read) {
        // Explicit queue/steer must not inherit the gateway's interrupt mode.
        this.mode = result.value === 'steer' ? 'steer' : 'queue'
        this.app.changed()
      }
    } catch {
      // Keep the last confirmed hint; a failed preference read must not discard a draft.
    }
  }

  shouldSteer(alternate: boolean): boolean {
    return (this.mode === 'steer') !== alternate
  }

  async steer(raw: string) {
    const { app } = this
    const sid = app.sid
    const text = raw.trim()

    if (this.#pending || !sid || !text) {
      return
    }

    if (raw !== app.composer.text) {
      app.composer.set(raw)
    }

    const revision = app.composer.rev
    const turn = app.transcript.live ?? app.transcript.start(app.busy?.startedAt)
    this.#pending = true

    try {
      const result = await app.gw.request<SessionCorrectionResult>('session.steer', { session_id: sid, text })

      if (app.sid !== sid) {
        return
      }

      if (result.status !== 'queued') {
        throw new Error('Steering was rejected. The draft is kept; queue it as a follow-up or retry.')
      }

      app.transcript.steer(text, turn)

      if (app.composer.rev === revision) {
        app.composer.take(raw)
      }
    } catch (error) {
      if (app.sid === sid) {
        app.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
      }
    } finally {
      this.#pending = false
      app.changed()
    }
  }
}
