import type { ConfigGetResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'

/** Presentation of the existing config-only display.vim_mode; no frontend preference store. */
export class VimPreference {
  #read = 0

  constructor(private readonly app: App) {}

  async refresh() {
    const sid = this.app.sid
    const read = ++this.#read

    if (!sid) {
      return
    }

    try {
      const result = await this.app.gw.request<ConfigGetResult>('config.get', { key: 'full', session_id: sid })

      if (this.app.sid !== sid || read !== this.#read) {
        return
      }

      const config = result.config as { display?: { vim_mode?: unknown } } | undefined
      this.app.composer.vim.setEnabled(config?.display?.vim_mode === true)
      this.app.changed()
    } catch {
      // Failed reads never enable modal editing or discard the current draft.
    }
  }
}
