import type { SessionForkResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { launchPane } from './pane-launcher.js'

export const FORK_COMMANDS: [string, string][] = [
  ['/fork-message', 'Fork this conversation into a new pane; optional durable message id (inclusive)']
]

const pending = new WeakSet<App>()

/** Fork is a gateway intent; the returned stored id belongs to another process. */
export async function forkSession(app: App, targetMessageId?: number): Promise<void> {
  const sid = app.sid

  if (!sid) {
    app.transcript.notice('Start a session before forking.', 'warning')
    app.changed()

    return
  }

  if (pending.has(app)) {
    return
  }

  if (app.busy || app.rewinding) {
    app.transcript.notice('Wait for the current turn to finish before forking.', 'warning')
    app.changed()

    return
  }

  pending.add(app)

  try {
    const result = await app.gw.request<SessionForkResult>('session.fork', {
      session_id: sid,
      ...(targetMessageId === undefined ? {} : { target_message_id: targetMessageId })
    })

    const argv = ['hermes', '--resume', result.session_id, '-p', result.profile]
    const hint = argv.map(value => /^[a-zA-Z0-9_./-]+$/.test(value) ? value : JSON.stringify(value)).join(' ')
    // The stored fork survives a launcher failure or a switch of the original pane.
    app.transcript.notice(`Forked session ${result.session_id}. Resume with: ${hint}`)

    if (process.env.TERN_WINDOW_KEY && app.sid === sid) {
      try {
        await launchPane(argv)
        app.transcript.notice(`Opened fork ${result.session_id} in a new Tern pane.`)
      } catch (error) {
        app.transcript.notice(`Fork saved, but the Tern pane could not open: ${error instanceof Error ? error.message : String(error)}`, 'error')
      }
    }
  } catch (error) {
    app.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
  } finally {
    pending.delete(app)
    app.changed()
  }
}
