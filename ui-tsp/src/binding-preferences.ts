import type { SettingsGetResult } from '@hermes/shared/gateway-events'

import { type Action, APP_ACTIONS, effectiveActions } from './actions.js'
import type { App } from './app.js'

/** A session-bound projection of profile config; no independent settings authority. */
export class BindingPreferences {
  #sid: string | null = null
  #read = 0
  #actions: readonly Action[] = APP_ACTIONS
  #profile = ''

  constructor(private readonly app: App) {}

  get actions(): readonly Action[] {
    return this.app.sid === this.#sid ? this.#actions : APP_ACTIONS
  }

  get profile(): string {
    return this.app.sid === this.#sid ? this.#profile : ''
  }

  accept(result: SettingsGetResult, sid: string): void {
    if (this.app.sid !== sid) {
      return
    }

    const actions = effectiveActions(result.fields['display.tern_keybindings']?.value ?? {})
    this.#sid = sid
    this.#actions = actions
    this.#profile = result.fields['display.tern_profile_identity']?.value === true ? result.profile : ''
    // Retire older adoption reads when a Settings readback wins.
    this.#read++
    this.app.changed()
  }

  async refresh(): Promise<void> {
    const sid = this.app.sid
    const read = ++this.#read

    if (!sid) {
      return
    }

    try {
      const result = await this.app.gw.request<SettingsGetResult>('settings.get', { session_id: sid })

      if (this.app.sid === sid && read === this.#read) {
        this.accept(result, sid)
      }
    } catch (error) {
      if (this.app.sid === sid && read === this.#read) {
        this.app.transcript.notice(`Tern preferences not applied: ${error instanceof Error ? error.message : String(error)}. Open Settings to repair or reset them.`, 'warning')
        this.app.changed()
      }
    }
  }
}
