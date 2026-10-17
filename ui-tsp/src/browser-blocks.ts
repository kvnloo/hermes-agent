import type { BrowserTargetResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'

/** User intent only: the gateway checks live task ownership, never transcript metadata. */
export async function focusBrowserBlock(app: App, targetId: string, sid = app.sid): Promise<void> {
  if (!sid || app.sid !== sid) {
    return
  }

  try {
    await app.gw.request<BrowserTargetResult>('browser.focus', { session_id: sid, target_id: targetId })
  } catch (error) {
    if (app.sid === sid) {
      app.notice(error instanceof Error ? error.message : String(error))
    }
  }
}
