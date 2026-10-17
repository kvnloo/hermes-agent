import type { SessionUndoResult } from '@hermes/shared/gateway-events'
import type { GatewayClient } from '@tui/gatewayClient.js'

import type { App } from './app.js'
import type { UserEntry } from './model.js'
import { confirmOverlay } from './overlays/prompts.js'

const loading = new WeakSet<App>()

export function rewindDisabledReason(app: App, entry: UserEntry): string | undefined {
  if (!app.sid || app.busy || app.rewinding || app.queue.length) {
    return 'Wait until this session is idle and its prompt queue is empty.'
  }

  return entry.rewindUnavailable ?? (entry.rowId === undefined ? 'This message has no durable rewind address. Reopen the session to reload stored messages.' : undefined)
}

/** Preview at the authority, then confirm that exact snapshot before any destructive RPC. */
export async function openRewind(app: App, gw: GatewayClient, entry: UserEntry) {
  if (rewindDisabledReason(app, entry) || loading.has(app)) {
    return
  }

  const sid = app.sid!
  const target = entry.rowId!
  const current = () => app.sid === sid && app.transcript.entries.includes(entry)
  loading.add(app)

  try {
    const preview = await gw.request<SessionUndoResult>('session.rewind_preview', {
      session_id: sid, target_message_id: target
    })

    if (!current() || rewindDisabledReason(app, entry)) {
      return
    }

    if (!preview.history_token || typeof preview.text !== 'string' || !preview.turns_removed || preview.turns_removed < 1) {
      throw new Error('The backend cannot preview a targeted rewind for this history.')
    }

    let confirmed = false
    app.open(confirmOverlay(app, {
      confirm: 'Rewind',
      detail: `Remove ${preview.turns_removed} user turn${preview.turns_removed === 1 ? '' : 's'} and all replies from this message onward? This cannot be undone. The selected message will replace the composer draft so you can edit and resend it. File changes are not reverted.`,
      title: 'Rewind to this message?',
      onCancel: () => { confirmed = true },
      onConfirm: () => {
        if (confirmed || !current() || rewindDisabledReason(app, entry)) {
          return
        }

        confirmed = true
        app.rewinding = { label: 'Rewinding…', since: {}, startedAt: Date.now() }
        app.changed()
        void gw.request<SessionUndoResult>('session.undo', {
          expected_history_token: preview.history_token, session_id: sid, target_message_id: target
        }).then(result => {
          if (!current()) {
            return
          }

          if (!result.messages || typeof result.text !== 'string' || result.removed < 1) {
            throw new Error('The backend did not return the rewound transcript and message text. Reopen the session to reload it.')
          }

          app.transcript.load(result.messages)
          app.composer.set(result.text)
        }).catch((error: unknown) => {
          if (app.sid === sid) {
            app.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
          }
        }).finally(() => {
          app.rewinding = null
          app.changed()
        })
      }
    }))
  } catch (error) {
    if (current()) {
      entry.rewindUnavailable = error instanceof Error ? error.message : String(error)
      app.transcript.notice(`Rewind unavailable: ${entry.rewindUnavailable}`, 'warning')
      app.changed()
    }
  } finally {
    loading.delete(app)
  }
}
