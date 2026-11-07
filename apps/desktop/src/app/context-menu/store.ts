import { atom } from 'nanostores'

import type { TerminalMenuHandle } from '@/app/right-sidebar/terminal/terminal-context-menu'

import type { ContextMenuDomTarget } from './target'

/** Spell-check facts for the open editable menu. They arrive AFTER the menu
 *  opens: Chromium reports them on the main-process `context-menu` event,
 *  which fires after the DOM gesture that opened the menu. */
export interface SpellcheckContext {
  misspelledWord: string
  suggestions: string[]
  /** Native context-menu coordinates, present in Electron's forward. */
  x?: number
  y?: number
}

/** What the guest page reported for the click, straight off the webview's
 *  `context-menu` event. Unlike the DOM shape, spell-check facts ride along
 *  immediately — the guest event IS the Chromium report. */
export interface GuestMenuParams {
  /** Chromium's own availability verdict for the edit verbs at the click
   *  point. This is what grays out cut/copy/paste/select-all — the same
   *  source the native menu used. */
  editFlags: {
    canCopy: boolean
    canCut: boolean
    canPaste: boolean
    canSelectAll: boolean
  }
  dictionarySuggestions: string[]
  hasImageContents: boolean
  isEditable: boolean
  linkURL: string
  misspelledWord: string
  selectionText: string
  srcURL: string
}

/** Verbs the preview pane binds over its webview element (and the guest IPC
 *  for the two things the tag cannot do: image bytes and the dictionary). */
export interface GuestMenuHandle {
  addToDictionary: (word: string) => void
  copyImage: () => void
  editCommand: (command: 'copy' | 'cut' | 'paste' | 'selectAll') => void
  inspectElement: () => void
  replaceMisspelling: (word: string) => void
}

export type OpenContextMenu =
  | {
      kind: 'dom'
      x: number
      y: number
      target: ContextMenuDomTarget
      spellcheck: SpellcheckContext | null
    }
  | {
      kind: 'guest'
      x: number
      y: number
      params: GuestMenuParams
      guest: GuestMenuHandle
    }
  | {
      kind: 'terminal'
      x: number
      y: number
      terminal: TerminalMenuHandle
      /** Whether the clipboard held text when the menu opened (grays out
       *  Paste). Arrives async right after open; false until then. Unlike
       *  the dom menu — whose paste runs webContents.paste() in main and
       *  must NOT depend on this probe (#91553) — the terminal paste item
       *  inserts the readClipboard() text itself, so its gate and its
       *  action share one mechanism. */
      clipboardHasText: boolean
    }

/** The one open context menu, or null. A single atom because two context
 *  menus can never be open at once. */
export const $contextMenu = atom<null | OpenContextMenu>(null)

/** Read the clipboard and flag the OPEN terminal menu when text is
 *  available. The read is an IPC round-trip, so the menu opens first
 *  (empty-clipboard verdict) and the flag lands a tick later — same
 *  late-fact pattern as spellcheck. Guarded by identity: a stale read
 *  never flags a newer menu. */
function probeClipboard(opened: Extract<OpenContextMenu, { kind: 'terminal' }>): void {
  void window.hermesDesktop
    ?.readClipboard?.()
    .then((text: string) => {
      const current = $contextMenu.get()

      if (current === opened && current.kind === 'terminal' && text) {
        $contextMenu.set({ ...current, clipboardHasText: true })
      }
    })
    .catch(() => undefined)
}

// Chromium and the DOM can report the same gesture in either order.
const EARLY_SPELLCHECK_MAX_MS = 500
let earlySpellcheck: { payload: SpellcheckContext; receivedAt: number } | null = null

function sameGesturePoint(payload: SpellcheckContext, x: number, y: number): boolean {
  return (
    (payload.x === undefined && payload.y === undefined) ||
    (typeof payload.x === 'number' &&
      typeof payload.y === 'number' &&
      Math.abs(payload.x - x) <= 2 &&
      Math.abs(payload.y - y) <= 2)
  )
}

export function openDomContextMenu(x: number, y: number, target: ContextMenuDomTarget): void {
  const early = earlySpellcheck

  earlySpellcheck = null
  $contextMenu.set({
    kind: 'dom',
    x,
    y,
    target,
    spellcheck:
      target.editable &&
      early &&
      Date.now() - early.receivedAt <= EARLY_SPELLCHECK_MAX_MS &&
      sameGesturePoint(early.payload, x, y)
        ? early.payload
        : null
  })
}

export function openGuestContextMenu(x: number, y: number, params: GuestMenuParams, guest: GuestMenuHandle): void {
  earlySpellcheck = null
  $contextMenu.set({ kind: 'guest', x, y, params, guest })
}

export function openTerminalContextMenu(x: number, y: number, terminal: TerminalMenuHandle): void {
  earlySpellcheck = null
  const opened: OpenContextMenu = { kind: 'terminal', x, y, terminal, clipboardHasText: false }

  $contextMenu.set(opened)

  if (terminal.paste) {
    probeClipboard(opened)
  }
}

export function closeContextMenu(): void {
  earlySpellcheck = null
  $contextMenu.set(null)
}

/** Attach late-arriving spell-check facts to the open editable menu. Ignored
 *  when the menu already closed or the click was not in an editable — the
 *  forward always belongs to the gesture that opened the current menu. */
export function augmentSpellcheck(payload: SpellcheckContext): void {
  if (!payload.misspelledWord) {
    return
  }

  const open = $contextMenu.get()

  if (!open) {
    // Only native reports with a point can be attached to a later DOM gesture.
    if (
      typeof payload.x === 'number' &&
      typeof payload.y === 'number' &&
      Number.isFinite(payload.x) &&
      Number.isFinite(payload.y)
    ) {
      earlySpellcheck = { payload, receivedAt: Date.now() }
    }

    return
  }

  if (open.kind !== 'dom' || !open.target.editable || !sameGesturePoint(payload, open.x, open.y)) {
    return
  }

  $contextMenu.set({ ...open, spellcheck: payload })
}
