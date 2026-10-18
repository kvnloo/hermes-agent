// OMP-style app actions. Composer editing and overlay-local keys stay with
// their owners. Inspired by oh-my-pi (Can Bölük / Stencil), MIT.

import type { Key, ScrollTo } from '@stencil-hq/tern'

import type { App } from './app.js'
import { forkSession } from './fork-session.js'
import { cycleModel } from './model-cycle.js'
import { openBrowserBlocks } from './overlays/browser-blocks.js'
import { openHistorySearch } from './overlays/history.js'
import { openModelPicker } from './overlays/models.js'
import { openSessionPicker } from './overlays/sessions.js'

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
      if (app.dictation.blocked) {
        void app.dictation.stop(true)
      } else if (app.busy) {
        app.interrupt()
      }
    }
  },
  {
    id: 'app.interrupt.owned',
    title: 'Interrupt the agent (preserve draft, including under a modal)',
    group: 'Control',
    keys: ['ctrl+shift+x'],
    when: always,
    run: app => app.interrupt()
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
    id: 'app.tools.expand',
    title: 'Expand / collapse all tool detail (empty prompt)',
    group: 'Reasoning and tools',
    keys: ['ctrl+o'],
    when: ctx => ctx.composerEmpty && !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.toggleToolExpansion()
  },
  {
    id: 'app.tools.toggleVisibility',
    title: 'Show / hide settled tool activity (empty prompt)',
    group: 'Reasoning and tools',
    keys: ['ctrl+shift+o'],
    when: ctx => ctx.composerEmpty && !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.toggleToolVisibility()
  },
  {
    id: 'app.message.alternate',
    title: 'Steer while busy (queue instead when busy mode is steer)',
    group: 'Control',
    keys: ['alt+enter'],
    when: ctx => ctx.busy,
    run: app => app.submitAlternate()
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
    id: 'app.stt.toggle',
    title: 'Toggle microphone dictation (review before sending)',
    group: 'Control',
    keys: ['alt+v'],
    when: ctx => !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.dictation.toggle()
  },
  {
    id: 'app.stt.hold.info',
    title: 'Push-to-talk availability (Mic / Alt+V fallback)',
    group: 'Control',
    keys: ['alt+shift+space'],
    when: ctx => !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.dictation.explainHold()
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
    id: 'app.model.cycleForward',
    title: 'Cycle to the next recent model',
    group: 'Navigation',
    keys: ['ctrl+p'],
    when: always,
    run: app => cycleModel(app, 1)
  },
  {
    id: 'app.model.cycleBackward',
    title: 'Cycle to the previous recent model',
    group: 'Navigation',
    keys: ['ctrl+shift+p'],
    when: always,
    run: app => cycleModel(app, -1)
  },
  {
    id: 'app.history.search',
    title: 'Search prompt history (fill draft, never send)',
    group: 'Control',
    keys: ['ctrl+r'],
    when: always,
    run: openHistorySearch
  },
  {
    id: 'app.editor.external',
    title: 'Edit the draft in an external editor',
    group: 'Control',
    keys: ['ctrl+g'],
    when: always,
    run: app => { void app.editExternal() }
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
    id: 'app.plan.review',
    title: 'Review the latest plan',
    group: 'Session',
    keys: ['alt+shift+p'],
    when: always,
    run: app => app.reviewPlan()
  },
  {
    id: 'app.jobs',
    title: 'Show background jobs',
    group: 'Session',
    keys: ['alt+j'],
    when: always,
    run: app => app.jobs.show()
  },
  {
    id: 'app.browser.blocks',
    title: 'Show / hand over Tern browser blocks',
    group: 'Session',
    keys: ['alt+shift+b'],
    when: ctx => !ctx.overlayOpen,
    run: app => openBrowserBlocks(app)
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
    id: 'app.tree',
    title: 'Browse the copied-session branch tree',
    group: 'Navigation',
    keys: ['alt+t'],
    when: always,
    run: app => openSessionPicker(app, true)
  },
  {
    id: 'app.tree.search',
    title: 'Search saved sessions and branch paths',
    group: 'Navigation',
    keys: ['alt+shift+s'],
    when: always,
    run: app => openSessionPicker(app, true)
  },
  {
    id: 'app.session.fork',
    title: '/fork [message-id]: fork into a new Tern pane',
    group: 'Session',
    keys: ['alt+shift+f'],
    when: ctx => !ctx.busy,
    run: app => { void forkSession(app) }
  },
  {
    id: 'app.history.older',
    title: 'Load and scroll to older retained history',
    group: 'Navigation',
    keys: ['ctrl+home'],
    when: ctx => !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.olderHistory()
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

type ApprovalAction =
  { kind: 'move'; delta: number } | { kind: 'choose' } | { kind: 'deny' } | { kind: 'digit'; index: number }

const APPROVAL_ACTIONS: readonly { keys: readonly string[]; action: ApprovalAction }[] = [
  { keys: ['up'], action: { kind: 'move', delta: -1 } },
  { keys: ['down'], action: { kind: 'move', delta: 1 } },
  { keys: ['enter'], action: { kind: 'choose' } },
  { keys: ['escape'], action: { kind: 'deny' } },
  ...['1', '2', '3', '4'].map((key, index) => ({
    keys: [key],
    action: { kind: 'digit', index } satisfies ApprovalAction
  }))
]

/** App offers these overlay-owned keys only while its composer is empty. */
export function approvalActionForKey(key: Key): ApprovalAction | undefined {
  return APPROVAL_ACTIONS.find(binding => matchesAction(binding, key))?.action
}

/** Session/tree-local intents; no branch key resumes or rewinds implicitly. */
export const SESSION_ACTIONS = [
  { id: 'close', keys: ['escape'], label: 'Close' },
  { id: 'activate', keys: ['enter'], label: 'Resume…' },
  { id: 'previousBranch', keys: ['ctrl+left'], label: 'Previous branch' },
  { id: 'nextBranch', keys: ['ctrl+right'], label: 'Next branch' },
  { id: 'search', keys: ['ctrl+f'], label: 'Search' },
  { id: 'rename', keys: ['f2'], label: 'Rename' },
  { id: 'sort', keys: ['ctrl+s'], label: 'Sort' },
  { id: 'path', keys: ['ctrl+l'], label: 'Paths' },
  { id: 'more', keys: ['ctrl+down'], label: 'Load more' },
  { id: 'fork', keys: ['alt+shift+f'], label: 'Fork current…' },
  { id: 'delete', keys: ['ctrl+backspace'], label: 'Delete…' }
] as const

export function sessionKeyAction(key: Key) {
  return SESSION_ACTIONS.find(binding => matchesAction(binding, key))?.id
}

interface ReportAction {
  keys: readonly string[]
  intent: { kind: 'close' } | { kind: 'scroll'; to: ScrollTo }
}

/** Overlay-local bindings live beside the app shortcuts, never in the view. */
export const REPORT_ACTIONS: readonly ReportAction[] = [
  { keys: ['escape'], intent: { kind: 'close' } },
  { keys: ['up'], intent: { kind: 'scroll', to: 'line-up' } },
  { keys: ['down'], intent: { kind: 'scroll', to: 'line-down' } },
  { keys: ['page_up'], intent: { kind: 'scroll', to: 'page-up' } },
  { keys: ['page_down'], intent: { kind: 'scroll', to: 'page-down' } },
  { keys: ['home'], intent: { kind: 'scroll', to: 'start' } },
  { keys: ['end'], intent: { kind: 'scroll', to: 'end' } }
]

/** Side-thread bindings; pane scrolling never moves the main conversation. */
export const BTW_ACTIONS = [
  { keys: ['escape'], action: 'close' },
  { keys: ['tab'], action: 'focus' },
  { keys: ['ctrl+n'], action: 'next' },
  { keys: ['ctrl+p'], action: 'previous' },
  { keys: ['alt+enter'], action: 'send' },
  { keys: ['ctrl+x'], action: 'cancel' },
  { keys: ['alt+c'], action: 'copy' }
] as const

/** Plan-local commands; editing keys remain owned by its private note editor. */
export const PLAN_ACTIONS = [
  { keys: ['escape'], action: 'close' },
  { keys: ['up'], action: 'previous' },
  { keys: ['down'], action: 'next' },
  { keys: ['alt+a'], action: 'approve' },
  { keys: ['alt+r'], action: 'refine' },
  { keys: ['enter'], action: 'submit' }
] as const

/** Jobs-local bindings live beside app bindings, never in a rendering module. */
export function jobsKeyAction(key: Key): 'close' | 'next' | 'previous' | undefined {
  const bindings = [
    { action: 'close', keys: ['escape'] },
    { action: 'next', keys: ['down', 'ctrl+n'] },
    { action: 'previous', keys: ['up', 'ctrl+p'] }
  ] as const

  return bindings.find(binding => matchesAction({ ...binding, extraModifiers: false }, key))?.action
}

export function browserBlocksKeyAction(key: Key): 'close' | undefined {
  return matchesAction({ keys: ['escape'] }, key) ? 'close' : undefined
}

/** Modifier order in a chord is immaterial; new chords require exact modifiers. */
export function matchesAction(action: Pick<Action, 'keys' | 'extraModifiers'>, key: Key): boolean {
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
