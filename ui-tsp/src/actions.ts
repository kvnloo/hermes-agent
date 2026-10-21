// OMP-style app actions. Composer editing and overlay-local keys stay with
// their owners. Inspired by oh-my-pi (Can Bölük / Stencil), MIT.

import type { Key, ScrollTo } from '@stencil-hq/tern'

import type { App } from './app.js'
import { forkSession } from './fork-session.js'
import { cycleModel } from './model-cycle.js'
import { openBrowserBlocks } from './overlays/browser-blocks.js'
import { openHistorySearch } from './overlays/history.js'
import { openModelHub } from './overlays/model-hub.js'
import { openModelPicker } from './overlays/models.js'
import { openSessionPicker } from './overlays/sessions.js'

export interface ActionContext {
  composerEmpty: boolean
  busy: boolean
  queued: boolean
  overlayOpen: boolean
  completionOpen: boolean
  approval?: boolean
}

export interface Action {
  id: string
  title: string
  group: string
  scope?: 'approval'
  keys: readonly string[]
  /** Preserve the permissive modifiers of the original app shortcuts. */
  extraModifiers?: boolean
  when(ctx: ActionContext): boolean
  run(app: App): void
}

const always = () => true

// Defaults are immutable. Each session projects its effective profile bindings.
export const APP_ACTIONS: readonly Action[] = [
  { id: 'app.keyboard.actions', title: 'Keyboard traversal of rendered card / composer actions', group: 'Navigation',
    keys: ['f6', 'tab'], when: ctx => !ctx.completionOpen, run: app => app.keyboardActions() },
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
      if (app.liveVoice.blocked) {
        void app.liveVoice.control('stop')
      } else if (app.dictation.blocked) {
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
    id: 'app.clarify.toggle',
    title: 'Hide / show the waiting clarification (preserve answers)',
    group: 'Control',
    keys: ['alt+h'],
    when: always,
    run: app => app.toggleClarify()
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
    id: 'app.live.toggle',
    title: 'Live voice (explicit consent; automatic spoken turns)',
    group: 'Control',
    keys: ['alt+shift+v'],
    when: ctx => !ctx.overlayOpen && !ctx.completionOpen,
    run: app => app.liveVoice.toggle()
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
    id: 'app.model.manage',
    title: 'Manage profile auxiliary roles, fallbacks and providers',
    group: 'Navigation',
    keys: ['alt+shift+o'],
    when: always,
    run: openModelHub
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
    id: 'app.retry',
    title: 'Retry the latest retryable text-only failure (idle, empty prompt)',
    group: 'Control',
    keys: ['f5', 'alt+r'],
    when: ctx => ctx.composerEmpty && !ctx.busy && !ctx.overlayOpen,
    run: app => app.retryLatest()
  },
  {
    id: 'app.approval.approve',
    title: 'Allow a pending tool once (empty prompt, approval owns input)',
    group: 'Approval',
    scope: 'approval',
    keys: ['ctrl+enter', 'ctrl+q'],
    when: ctx => ctx.approval === true && ctx.composerEmpty,
    run: app => app.approvePending()
  },
  {
    id: 'app.clipboard.copyLine',
    title: 'Copy the current composer line',
    group: 'Control',
    keys: ['alt+shift+l'],
    when: always,
    run: app => app.copyPrompt(true)
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

/** Composer-local defaults, deliberately separate from globally active app chords. */
export const VIM_ACTIONS = [
  { id: 'escape', keys: ['escape'] },
  { id: 'h', keys: ['h', 'left', 'backspace'] },
  { id: 'j', keys: ['j', 'down'] },
  { id: 'k', keys: ['k', 'up'] },
  { id: 'l', keys: ['l', 'right', 'space'] },
  { id: '0', keys: ['0', 'home'] },
  { id: '^', keys: ['shift+6'] },
  { id: '$', keys: ['shift+4', 'end'] },
  ...['w', 'b', 'e', 'g', 'i', 'a', 'o', 'v', 'd', 'c', 'y', 'x', 'r', 'u', 'p'].map(id => ({ id, keys: [id] })),
  ...['g', 'i', 'a', 'o', 'v', 'd', 'c', 'p'].map(id => ({ id: id.toUpperCase(), keys: [`shift+${id}`] })),
  ...['1', '2', '3', '4', '5', '6', '7', '8', '9'].map(id => ({ id, keys: [id] })),
  { id: 'redo', keys: ['ctrl+r'] }
] as const

export function vimActionForKey(key: Key): string | undefined {
  // Legacy terminal input reports punctuation directly rather than a shifted number.
  const punctuation = key.text === '^' || key.text === '$'

  if (punctuation && !key.ctrl && !key.alt && !key.meta) { return key.text }

  return VIM_ACTIONS.find(binding => matchesAction(binding, key))?.id
}

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

export const KEYBOARD_ACTIONS = [
  { keys: ['escape'], action: 'close' },
  { keys: ['enter', 'space'], action: 'activate' },
  { keys: ['tab', 'down', 'f6'], action: 'next' },
  { keys: ['shift+tab', 'up', 'shift+f6'], action: 'previous' }
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
export function actionForKey(key: Key, ctx: ActionContext, actions = APP_ACTIONS): Action | undefined {
  return actions.find(action => matchesAction(action, key) && action.when(ctx))
}

export function actionGroups(actions = APP_ACTIONS): { group: string; rows: [readonly string[], string][] }[] {
  const groups = new Map<string, [readonly string[], string][]>()

  for (const action of actions) {
    const rows = groups.get(action.group) ?? []
    rows.push([action.keys.length ? action.keys : ['(unbound)'], action.title])
    groups.set(action.group, rows)
  }

  return [...groups].map(([group, rows]) => ({ group, rows }))
}

/** The compact composer hint is sourced from the same binding as the sheet. */
export function actionHint(id: string, actions = APP_ACTIONS): string {
  return actions.find(action => action.id === id)?.keys[0] ?? ''
}

export const HELP_HINT = `${actionHint('app.help')} help`

const MODIFIERS = ['ctrl', 'alt', 'shift', 'meta'] as const

const ALIASES: Readonly<Record<string, string>> = {
  control: 'ctrl', option: 'alt', cmd: 'meta', command: 'meta', super: 'meta',
  esc: 'escape', return: 'enter', arrowup: 'up', arrowdown: 'down',
  arrowleft: 'left', arrowright: 'right', pageup: 'page_up', pagedown: 'page_down'
}

/** Canonical spelling also prevents alias/order collisions and hidden host chords. */
export function normalizeChord(raw: string): string {
  const parts = raw.toLowerCase().split('+').map(part => part.trim()).map(part => ALIASES[part] ?? part)
  const name = parts.pop() ?? ''

  if (!/^(?:[a-z0-9,./;`'[\]\\=-]|f(?:[1-9]|1[0-9]|2[0-4])|enter|escape|tab|space|backspace|delete|home|end|up|down|left|right|page_up|page_down)$/.test(name) ||
      parts.some(part => !MODIFIERS.some(mod => mod === part)) || new Set(parts).size !== parts.length) {
    throw new Error(`Invalid key chord: ${raw}`)
  }

  if (parts.includes('meta') || (parts.includes('ctrl') && parts.includes('shift') && ['c', 'v'].includes(name)) ||
      (parts.includes('alt') && ['f4', 'tab'].includes(name))) {
    throw new Error(`Host-reserved key chord: ${raw}`)
  }

  return [...MODIFIERS.filter(mod => parts.includes(mod)), name].join('+')
}

// These are editor ownership exclusions, not another app shortcut/hint registry.
const EDITOR_KEYS = new Set(['enter', 'shift+enter', 'tab', 'up', 'down', 'left', 'right',
  'home', 'end', 'backspace', 'delete', 'ctrl+a', 'ctrl+e', 'ctrl+u', 'ctrl+k', 'ctrl+w',
  'ctrl+y', 'ctrl+z', 'ctrl+shift+z', 'alt+b', 'alt+f', 'alt+d', 'alt+left', 'alt+right', 'alt+backspace'])

/** Atomic resolution: an invalid map never installs a partially rebound keyboard. */
export function effectiveActions(raw: unknown): readonly Action[] {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error('Tern keybindings must be an object keyed by action id.')
  }

  const overrides = new Map<string, readonly string[]>()

  for (const [id, value] of Object.entries(raw)) {
    const action = APP_ACTIONS.find(item => item.id === id)

    if (!action) {
      throw new Error(`Unknown Tern action: ${id}`)
    }

    if (value === null) {
      continue
    }

    const keys: unknown[] = typeof value === 'string' ? [value] : Array.isArray(value) ? value : [value]

    const normalized = keys.map(key => {
      if (typeof key !== 'string') {
        throw new Error(`Bindings for ${id} must be strings.`)
      }

      const chord = normalizeChord(key)

      const parts = chord.split('+')
      const name = parts.at(-1)!
      const typing = (name.length === 1 || name === 'space') && !parts.includes('ctrl') && !parts.includes('alt')

      if ((EDITOR_KEYS.has(chord) || typing || (action.scope === 'approval' && chord === 'escape')) && !action.keys.includes(chord)) {
        throw new Error(`Composer-owned key chord: ${chord}`)
      }

      return chord
    })

    overrides.set(id, normalized)
  }

  const actions = APP_ACTIONS.map(action => overrides.has(action.id)
    ? { ...action, extraModifiers: false, keys: overrides.get(action.id)! } : action)

  const used = new Map<string, string>()

  for (const action of actions) {
    for (const key of action.keys) {
      const identity = `${action.scope ?? 'app'}:${key}`
      const previous = used.get(identity)

      if (previous) {
        throw new Error(`Duplicate chord ${key}: ${previous} and ${action.id} (${action.scope ?? 'app'} context).`)
      }

      used.set(identity, action.id)
    }
  }

  // Rebound keys must not alias a permissive legacy binding (e.g. Ctrl+Shift+D).
  for (const action of actions.filter(item => overrides.has(item.id))) {
    for (const chord of action.keys) {
      const parts = chord.split('+')

      const key: Key = { name: parts.pop()!, ctrl: parts.includes('ctrl'), alt: parts.includes('alt'),
        shift: parts.includes('shift'), meta: false }

      const collision = actions.find(other => other.id !== action.id && (other.scope === action.scope || [other.id, action.id].some(id => ['app.clear', 'app.interrupt.owned'].includes(id))) && matchesAction(other, key))

      if (collision) {
        throw new Error(`Overlapping chord ${chord}: ${action.id} and ${collision.id}.`)
      }
    }
  }

  return actions
}

export function shortcutsMarkdown(actions = APP_ACTIONS): string {
  return ['| Context | Action id | Chords | Intent |', '| --- | --- | --- | --- |',
    ...actions.map(action => `| ${action.scope ?? 'app'} | ${action.id} | ${action.keys.join(' / ') || '(unbound)'} | ${action.title} |`)].join('\n')
}
