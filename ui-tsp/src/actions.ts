// OMP-style app actions. Composer editing and overlay-local keys stay with
// their owners. Inspired by oh-my-pi (Can Bölük / Stencil), MIT.

import type { Key } from '@stencil-hq/tern'

import type { App } from './app.js'
import { openModelPicker } from './overlays/models.js'

export interface ActionContext {
  composerEmpty: boolean
  busy: boolean
  queued: boolean
  overlayOpen: boolean
  completionOpen: boolean
}

export interface Action {
  id: string
  title: string
  group: string
  keys: readonly string[]
  /** Preserve the permissive modifiers of the original app shortcuts. */
  extraModifiers?: boolean
  when(ctx: ActionContext): boolean
  run(app: App): void
}

const always = () => true

// TODO: load user-configurable bindings here, keeping dispatch and help in sync.
export const APP_ACTIONS: readonly Action[] = [
  {
    id: 'app.clear',
    title: 'Clear the draft / interrupt / exit (twice)',
    group: 'Control',
    keys: ['ctrl+c'],
    extraModifiers: true,
    when: always,
    run: app => app.ctrlC()
  },
  {
    id: 'app.interrupt',
    title: 'Close completion / interrupt the agent',
    group: 'Control',
    keys: ['escape'],
    extraModifiers: true,
    when: always,
    run: app => {
      if (app.busy) {
        app.interrupt()
      }
    }
  },
  {
    id: 'app.exit',
    title: 'Exit (empty prompt; otherwise delete forward)',
    group: 'Control',
    keys: ['ctrl+d'],
    extraModifiers: true,
    when: ctx => ctx.composerEmpty,
    run: app => app.quit()
  },
  {
    id: 'app.thinking.cycle',
    title: 'Cycle the reasoning effort',
    group: 'Reasoning and tools',
    keys: ['shift+tab'],
    extraModifiers: true,
    when: always,
    run: app => app.cycleEffort()
  },
  {
    id: 'app.thinking.toggle',
    title: 'Toggle reasoning display (profile setting)',
    group: 'Reasoning and tools',
    keys: ['ctrl+t'],
    when: always,
    run: app => app.toggleReasoning()
  },
  {
    // Ctrl+Shift+O was already accepted by the Ctrl+O handler. Keep that
    // alias rather than hiding active/error/approval tool state globally.
    id: 'app.tools.expand',
    title: 'Toggle latest tool detail (empty prompt)',
    group: 'Reasoning and tools',
    keys: ['ctrl+o', 'ctrl+shift+o'],
    when: ctx => ctx.composerEmpty && !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.toggleRecentTool()
  },
  {
    id: 'app.message.dequeue',
    title: 'Edit the oldest queued prompt',
    group: 'Control',
    keys: ['alt+up'],
    extraModifiers: true,
    when: ctx => ctx.queued,
    run: app => app.dequeue()
  },
  {
    id: 'app.model.select',
    title: 'Select model',
    group: 'Navigation',
    keys: ['alt+m'],
    when: always,
    run: app => {
      void app.slash('/model')
    }
  },
  {
    id: 'app.model.selectTemporary',
    title: 'Select model for this session only',
    group: 'Navigation',
    keys: ['alt+p'],
    when: always,
    run: app => openModelPicker(app, { sessionOnly: true })
  },
  {
    id: 'app.settings',
    title: 'Open Hermes settings',
    group: 'Navigation',
    keys: ['alt+,', 'ctrl+,'],
    when: always,
    run: app => {
      void app.slash('/settings')
    }
  },
  {
    id: 'app.context',
    title: 'Show context window',
    group: 'Session',
    keys: ['alt+c'],
    when: always,
    run: app => {
      void app.slash('/context')
    }
  },
  {
    id: 'app.usage',
    title: 'Show usage',
    group: 'Session',
    keys: ['alt+u'],
    when: always,
    run: app => {
      void app.slash('/usage')
    }
  },
  {
    id: 'app.agents.hub',
    title: 'Show agents',
    group: 'Session',
    keys: ['alt+a'],
    when: always,
    run: app => {
      void app.slash('/agents')
    }
  },
  {
    id: 'app.session.resume',
    title: 'Open session picker',
    group: 'Navigation',
    keys: ['alt+s'],
    when: always,
    run: app => {
      void app.slash('/sessions')
    }
  },
  {
    id: 'app.clipboard.copyPrompt',
    title: 'Copy composer text',
    group: 'Control',
    keys: ['alt+shift+c'],
    when: always,
    run: app => app.copyPrompt()
  },
  {
    id: 'app.help',
    title: 'Commands and shortcuts',
    group: 'Navigation',
    keys: ['f1', 'alt+/'],
    when: always,
    run: app => {
      void app.slash('/help')
    }
  }
]

/** Modifier order in a chord is immaterial; new chords require exact modifiers. */
export function matchesAction(action: Action, key: Key): boolean {
  return action.keys.some(chord => {
    const parts = chord.split('+')
    const name = parts.pop()

    return (
      key.name.toLowerCase() === name &&
      (['ctrl', 'alt', 'shift', 'meta'] as const).every(mod =>
        parts.includes(mod) ? key[mod] : action.extraModifiers || !key[mod]
      )
    )
  })
}

/** First enabled action wins, only after overlay and completion ownership. */
export function actionForKey(key: Key, ctx: ActionContext): Action | undefined {
  return APP_ACTIONS.find(action => matchesAction(action, key) && action.when(ctx))
}

export function actionGroups(): { group: string; rows: [readonly string[], string][] }[] {
  const groups = new Map<string, [readonly string[], string][]>()

  for (const action of APP_ACTIONS) {
    const rows = groups.get(action.group) ?? []
    rows.push([action.keys, action.title])
    groups.set(action.group, rows)
  }

  return [...groups].map(([group, rows]) => ({ group, rows }))
}

/** The compact composer hint is sourced from the same binding as the sheet. */
export const HELP_HINT = `${APP_ACTIONS.find(action => action.id === 'app.help')?.keys[0]} help`
