// Slash commands this frontend runs through the live session: quitting,
// clearing, reasoning settings and native sheets (model, sessions, help).
// Everything else goes to the gateway's `slash.exec`.

import type { ConfigGetResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { canonicalCommand, CLASSIC_COMMANDS } from './classic-commands.js'
import { forkSession } from './fork-session.js'
import { cycleModel } from './model-cycle.js'
import { openAgentHub } from './overlays/agent-hub.js'
import { openHelp } from './overlays/help.js'
import { openHistorySearch } from './overlays/history.js'
import { openLsp } from './overlays/lsp.js'
import { openModelHub } from './overlays/model-hub.js'
import { openModelPicker, switchModel } from './overlays/models.js'
import { confirmOverlay } from './overlays/prompts.js'
import { openSessionPicker } from './overlays/sessions.js'
import { openSettings } from './overlays/settings.js'
import { openVisualPicker } from './overlays/visual-picker.js'

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
  { name: 'models', run: app => openModelHub(app) },
  { name: 'tree', run: app => openSessionPicker(app, true) },
  { name: 'agents', run: (app, arg) => arg ? false : openAgentHub(app) },
  { name: 'history-search', run: openHistorySearch },
  { name: 'lsp', run: openLsp },
  { name: 'editor', run: app => app.editExternal() },
  { name: 'resume', run: (app, arg) => arg ? app.resume(arg) : openSessionPicker(app) },
  {
    name: 'branch',
    run: async (app, arg) => {
      if (!app.sid || app.busy) {
        app.transcript.notice('Wait for the current turn before branching.', 'warning')

        return
      }

      const sid = app.sid
      const result = await app.gw.request<{ session_id: string }>('session.fork', { session_id: sid })
      const title = arg.replace(/(?:^|\s)--here(?=\s|$)/g, ' ').trim()

      if (title) {
        await app.gw.request('session.rename', { session_key: result.session_id, title })
      }

      if (app.sid === sid) { await app.resume(result.session_id) }
    }
  },
  { name: 'model-next', run: app => cycleModel(app, 1) },
  { name: 'model-prev', run: app => cycleModel(app, -1) },
  {
    name: 'fork-message',
    run: (app, arg) => {
      if (arg && (!/^[1-9][0-9]*$/.test(arg) || !Number.isSafeInteger(Number(arg)))) {
        app.transcript.notice('Usage: /fork-message [durable-message-id]', 'warning')

        return
      }

      return forkSession(app, arg ? Number(arg) : undefined)
    }
  },
  {
    name: 'quit',
    run: async (app, arg) => {
      if (arg && !['--delete', '-d'].includes(arg.toLowerCase())) {
        app.transcript.notice('Usage: /quit [--delete]', 'warning')

        return
      }

      if (arg && app.sid && app.storedSid) {
        await app.gw.request('session.close', { session_id: app.sid })
        await app.gw.request('session.delete', { session_id: app.storedSid, ...(app.info?.profile ? { profile: app.info.profile } : {}) })
      }

      app.quit()
    }
  },
  {
    name: 'new',
    run: async (app, arg) => {
      const previous = app.sid
      await app.newSession()

      if (arg && app.sid && app.sid !== previous) {
        await app.gw.request('session.title', { session_id: app.sid, title: arg })
      }
    }
  },
  {
    name: 'clear',
    run: app => app.newSession()
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
    aliases: ['session', 'switch'],
    name: 'sessions',
    run: (app, arg) => {
      if (!arg) {
        return openSessionPicker(app)
      }

      return app.resume(arg)
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
    // Bare /plan reviews; argument forms retain Hermes's plan-generation builtin.
    name: 'plan',
    run: (app, arg) => arg ? false : app.reviewPlan()
  },
  {
    name: 'jobs',
    run: app => app.jobs.show()
  },
  {
    name: 'visual',
    run: (app, arg) => openVisualPicker(app, arg)
  },
  {
    // `/help <command>` is the backend's detailed usage.
    name: 'help',
    run: (app, arg) => (arg ? false : openHelp(app))
  }
]

/** Native extensions only. Classic descriptions/aliases are generated, not re-authored. */
const NATIVE_DESCRIPTIONS: Record<string, string> = {
  models: 'Open the model and provider hub',
  tree: 'Browse the session branch tree',
  'history-search': 'Search conversation history',
  lsp: 'Inspect language-server symbols, references and hover',
  editor: 'Edit the current composer draft in an external editor (does not send)',
  'model-next': 'Switch to the next favorite model',
  'model-prev': 'Switch to the previous favorite model',
  'fork-message': 'Fork into a new pane at an optional durable message id',
  settings: 'Open profile defaults and live session settings',
  jobs: 'Inspect background jobs',
  visual: 'Open the visual artifact picker'
}

export function localCompletions(): { text: string; display: string; meta: string; kind: 'command' }[] {
  return COMMANDS.flatMap(command => {
    const classic = CLASSIC_COMMANDS.find(item => item.name === command.name)
    const description = classic?.description ?? NATIVE_DESCRIPTIONS[command.name]!

    return [command.name, ...(classic?.aliases ?? command.aliases ?? [])].map(name => ({
      text: `/${name}`, display: `/${name}`, meta: description, kind: 'command' as const
    }))
  })
}

/** The client-side command `name` (without the slash) answers to, if any. */
export function localCommand(name: string): LocalCommand | undefined {
  const canonical = canonicalCommand(name)

  return COMMANDS.find(c => c.name === canonical || c.aliases?.includes(canonical))
}
