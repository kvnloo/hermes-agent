// Slash commands this frontend runs through the live session: quitting,
// clearing, reasoning settings and native sheets (model, sessions, help).
// Everything else goes to the gateway's `slash.exec`.

import type { ConfigGetResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { openHelp } from './overlays/help.js'
import { openModelPicker, switchModel } from './overlays/models.js'
import { confirmOverlay } from './overlays/prompts.js'
import { openSessionPicker } from './overlays/sessions.js'
import { openSettings } from './overlays/settings.js'

/** A client-side slash command. */
export interface LocalCommand {
  name: string
  aliases?: readonly string[]
  /**
   * Runs `/name arg`. Returning false hands the command to `slash.exec`
   * instead (a form this frontend leaves to the backend).
   */
  run(app: App, arg: string): boolean | void | Promise<boolean | void>
}

const COMMANDS: readonly LocalCommand[] = [
  {
    aliases: ['exit', 'q'],
    name: 'quit',
    run: app => app.quit()
  },
  {
    aliases: ['reset'],
    name: 'new',
    run: app => app.newSession()
  },
  {
    name: 'clear',
    run: app => {
      app.transcript.clear()
      app.transcript.push({ id: app.transcript.id('w'), kind: 'welcome' })
    }
  },
  {
    name: 'model',
    run: async (app, arg) => {
      if (!arg) {
        return openModelPicker(app)
      }

      const sid = app.sid
      const r = await switchModel(app, arg, false, sid)

      if (r.confirm_required && app.sid === sid) {
        app.open(
          confirmOverlay(app, {
            confirm: 'Switch anyway',
            detail: `Session: ${sid}. Model request: ${arg}. ${r.confirm_message || r.warning || ''}`,
            onConfirm: () => {
              if (app.sid === sid) {
                void switchModel(app, arg, true, sid).catch((error: Error) => {
                  if (app.sid === sid) {
                    app.transcript.notice(error.message, 'error')
                    app.changed()
                  }
                })
              }
            },
            title: 'Switch to an expensive model?'
          })
        )
      }
    }
  },
  {
    name: 'reasoning',
    run: async (app, arg) => {
      const sid = app.sid

      if (!sid) {
        return
      }

      if (!arg) {
        const r = await app.gw.request<ConfigGetResult>('config.get', { key: 'reasoning', session_id: sid })

        if (app.sid === sid && typeof r.value === 'string') {
          app.info = { ...app.info, reasoning_effort: r.value }
          app.transcript.panel('/reasoning', `Reasoning effort: ${r.value} (display: ${r.display ?? 'show'}).`)
        }

        return
      }

      let scope: 'global' | 'session' | undefined

      const value = arg
        .split(/\s+/)
        .filter(part => {
          const flag = part.toLowerCase()

          if (flag === '--global') {
            scope = 'global'

            return false
          }

          if (flag === '--session') {
            scope ??= 'session'

            return false
          }

          return true
        })
        .join(' ')

      const r = await app.setReasoning(value, scope, sid)

      if (app.sid === sid && typeof r?.value === 'string') {
        app.transcript.panel(`/reasoning ${arg}`, `Reasoning: ${r.value}.`)
      }
    }
  },
  {
    aliases: ['resume', 'session', 'switch'],
    name: 'sessions',
    run: (app, arg) => {
      if (!arg) {
        return openSessionPicker(app)
      }

      return arg === 'new' ? app.newSession() : app.resume(arg)
    }
  },
  {
    aliases: ['prefs'],
    name: 'settings',
    run: (app, arg) => {
      if (arg) {
        app.transcript.panel('/settings', 'Open /settings or /prefs to edit profile defaults and live session controls.')
        app.changed()

        return
      }

      openSettings(app)
    }
  },
  {
    // `/help <command>` is the backend's detailed usage.
    name: 'help',
    run: (app, arg) => (arg ? false : openHelp(app))
  }
]

/** The client-side command `name` (without the slash) answers to, if any. */
export function localCommand(name: string): LocalCommand | undefined {
  return COMMANDS.find(c => c.name === name || c.aliases?.includes(name))
}
