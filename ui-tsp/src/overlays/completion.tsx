// Completions for the composer: slash commands, inline `/skill` references and
// `@`/path words, fetched from the gateway as the text before the caret
// changes and shown as a caret-anchored list (`omp.autocomplete`).
// Tab accepts; Enter accepts a row that changes the token, else submits.

import type { CompletionItem } from '@hermes/shared/gateway-events'
import type { JSX, Key } from '@stencil-hq/tern'
import { applyCompletion, completionRequestForInput, completionToApplyOnSubmit } from '@tui/domain/slash.js'
import type { GatewayClient } from '@tui/gatewayClient.js'

import type { Composer } from '../composer.js'
import { FORK_COMMANDS } from '../fork-session.js'
import type { OverlayHost } from '../overlay.js'
import { REFERENCE_COMMANDS } from '../reference-commands.js'

import { LSP_COMMANDS } from './lsp.js'
import { TREE_COMMANDS } from './sessions.js'
import { SETTINGS_COMMANDS } from './settings.js'

const DEBOUNCE_MS = 60

/** The composer's completion list: queries the gateway as the text before the caret changes and accepts rows into it. */
export class Completion {
  items: CompletionItem[] = []
  selected = 0
  /** Where an accepted row's text replaces the input. */
  #replaceFrom = 0
  #replaceTo = 0
  #snapshot: { cursor: number; sid: string | null; text: string } = { cursor: 0, sid: null, text: '' }
  /** The text before the caret the items answer. */
  #for = ''
  /** The text before the caret last queried (scheduled, in flight or answered); null until the first update. */
  #asked: string | null = null
  /** Bumped by every new query and every dismissal: replies of an older generation are dropped. */
  #gen = 0
  #timer: NodeJS.Timeout | undefined
  #composer: Composer | undefined
  readonly #host: OverlayHost
  readonly #gw: GatewayClient
  readonly #sid: () => string | null

  constructor(host: OverlayHost, gw: GatewayClient, sid: () => string | null) {
    this.#host = host
    this.#gw = gw
    this.#sid = sid
  }

  get open(): boolean {
    return this.items.length > 0
  }

  /** The dim suffix the selected row would add after the caret, while the live text still leads to it. */
  get ghost(): string {
    const row = this.items[this.selected]
    const composer = this.#composer

    if (!row || !composer || !this.#current() || composer.cursor !== composer.text.length) {
      return ''
    }

    const next = applyCompletion(this.#for, row.text, this.#replaceFrom)

    return next.startsWith(composer.text) ? next.slice(composer.text.length) : ''
  }

  /** Re-queries when the text before the composer's caret changed since the last query; cheap otherwise. */
  update(composer: Composer) {
    this.#composer = composer
    const before = composer.text.slice(0, composer.cursor)

    const snapshot = { cursor: composer.cursor, sid: this.#sid(), text: composer.text }
    const asked = JSON.stringify(snapshot)

    if (asked === this.#asked) {
      return
    }

    this.#asked = asked
    const gen = ++this.#gen
    clearTimeout(this.#timer)
    this.#timer = undefined
    // The gateway accepts a command line or one path word, never a multiline draft.
    const lineStart = before.lastIndexOf('\n') + 1
    const context = before.slice(lineStart)
    const request = completionRequestForInput(context)

    if (!request) {
      this.dismiss()

      return
    }

    this.#timer = setTimeout(() => {
      this.#timer = undefined
      const sid = snapshot.sid

      if (gen !== this.#gen || this.#sid() !== sid) {
        return
      }

      const params =
        request.method === 'complete.slash' && sid ? { ...request.params, session_id: sid } : request.params

      this.#gw
        .request<{ items?: CompletionItem[]; replace_from?: number | null }>(request.method, params)
        .then(r => {
          if (
            gen !== this.#gen ||
            composer.text !== snapshot.text ||
            composer.cursor !== snapshot.cursor ||
            this.#sid() !== sid
          ) {
            return
          }

          const items = r?.items ?? []

          if (request.method === 'complete.slash' && !request.skillsOnly && /^\/\S*$/.test(context)) {
            for (const [text, meta] of [...SETTINGS_COMMANDS, ...FORK_COMMANDS, ...TREE_COMMANDS, ...LSP_COMMANDS, ...REFERENCE_COMMANDS]) {
              if (text.startsWith(context) && !items.some(item => item.text === text)) {
                items.push({ display: text, kind: 'command', meta, text })
              }
            }
          }

          this.items =
            request.method === 'complete.slash' && request.skillsOnly ? items.filter(i => i.kind === 'skill') : items
          this.selected = 0
          this.#for = before
          this.#snapshot = snapshot
          // Gateway offsets are Python code points; Composer/TSP offsets are UTF-16.
          this.#replaceFrom =
            lineStart +
            (request.method === 'complete.slash' && !request.skillsOnly
              ? [...context].slice(0, r?.replace_from ?? 1).join('').length
              : request.replaceFrom)
          this.#replaceTo = composer.cursor + (composer.text.slice(composer.cursor).match(/^\S*/u)?.[0].length ?? 0)
          this.#host.changed()
        })
        .catch(() => {
          if (gen === this.#gen && this.#sid() === sid) {
            this.dismiss()
          }
        })
    }, DEBOUNCE_MS)
  }

  /** Hides the list and drops pending queries; it reopens once the text before the caret changes. */
  dismiss() {
    this.#gen++
    clearTimeout(this.#timer)
    this.#timer = undefined

    if (this.items.length) {
      this.items = []
      this.#host.changed()
    }

    this.#for = ''
  }

  /** Keys while the list is open: ↑/↓ move, Tab accepts, Enter accepts a changing row, Esc closes. */
  onKey(key: Key): boolean {
    const composer = this.#composer

    if (!this.open || !composer) {
      return false
    }

    switch (key.name) {
      case 'up':
        this.selected = (this.selected - 1 + this.items.length) % this.items.length

        return true

      case 'down':
        this.selected = (this.selected + 1) % this.items.length

        return true

      case 'escape':
        this.dismiss()

        return true

      case 'tab':
        return this.#accept(applyCompletion(this.#for, this.items[this.selected]?.text ?? '', this.#replaceFrom))
      case 'enter': {
        // A list answering older text (keys outran the render) must not rewrite what was typed since.
        if (key.shift || key.alt || !this.#current()) {
          return false
        }

        const current = this.#for + composer.text.slice(composer.cursor, this.#replaceTo)
        const next = completionToApplyOnSubmit(current, this.items[this.selected]?.text, this.#replaceFrom)

        if (next === null) {
          this.dismiss()

          return false
        }

        return this.#accept(next)
      }
    }

    return false
  }

  /** The overlay nodes for the `layer` region (none while closed). */
  nodes(inputId: string): JSX.Element[] {
    if (!this.open) {
      return []
    }

    const listId = 'layer.complete.select.list'

    return [
      <overlay anchor={{ caret: inputId }} key="complete" role="omp.autocomplete">
        <col key="select" role="omp.select">
          <list
            empty={this.#for.includes('@') ? 'No files' : 'No items'}
            key="list"
            max={{ lines: 8 }}
            onActivate={ev => this.#pick(ev.item, listId, { accept: true })}
            onSelect={ev => this.#pick(ev.item, listId, { accept: false })}
            selected={`${listId}.${this.selected}`}
          >
            {this.items.map((item, i) => (
              <item
                detail={item.meta && item.meta !== 'dir' ? item.meta : undefined}
                icon={iconOf(item)}
                key={String(i)}
                label={labelOf(item, this.#for, this.#replaceFrom)}
              />
            ))}
          </list>
        </col>
      </overlay>
    ]
  }

  #pick(itemId: string, listId: string, { accept }: { accept: boolean }) {
    const i = Number(itemId.slice(listId.length + 1))

    if (Number.isInteger(i) && this.items[i]) {
      this.selected = i

      if (accept) {
        this.#accept(applyCompletion(this.#for, this.items[i].text, this.#replaceFrom))
      }

      this.#host.changed()
    }
  }

  #current(): boolean {
    return (
      this.#composer?.text === this.#snapshot.text &&
      this.#composer.cursor === this.#snapshot.cursor &&
      this.#sid() === this.#snapshot.sid
    )
  }

  /** Replace only the active token, including its suffix when the caret is inside it. */
  #accept(before: string): boolean {
    const composer = this.#composer

    if (!composer || !this.#current()) {
      return false
    }

    composer.splice(this.#replaceFrom, this.#replaceTo, before.slice(this.#replaceFrom))
    this.dismiss()
    this.update(composer)

    return true
  }
}

/** Icons for hermes's common commands; others fall back by kind. */
const COMMAND_ICONS: Record<string, string> = {
  clear: 'eraser',
  compress: 'compress',
  cron: 'clock',
  help: 'help',
  history: 'history',
  model: 'sparkle',
  new: 'plus',
  personality: 'user',
  quit: 'log-out',
  reasoning: 'brain',
  resume: 'play',
  retry: 'repeat',
  save: 'save',
  skills: 'skill',
  tools: 'tools',
  undo: 'undo',
  usage: 'gauge',
  yolo: 'shield-alert'
}

/** A path row: `@file:src/a.ts` / `@folder:src/`, or a bare listing entry. */
function isPath(item: CompletionItem): boolean {
  return !item.kind && !item.text.startsWith('/')
}

function iconOf(item: CompletionItem): string {
  if (isPath(item)) {
    return (item.display || item.text).endsWith('/') ? 'folder' : 'file'
  }

  if (item.kind === 'skill') {
    return 'skill'
  }

  return COMMAND_ICONS[item.text.replace(/^\//, '').split(/\s/)[0] ?? ''] ?? 'slash'
}

/** The row's label (without the leading `/`) with the typed text marked; path names are strong like omp's. */
function labelOf(item: CompletionItem, typed: string, replaceFrom: number) {
  const label = (item.display || item.text).replace(/^\//, '')
  const base = isPath(item) ? 'strong' : undefined

  const query =
    typed
      .slice(replaceFrom)
      .replace(/^[/@]/, '')
      .replace(/^(file|folder):/, '')
      .split('/')
      .pop() ?? ''

  const at = query ? label.toLowerCase().indexOf(query.toLowerCase()) : -1

  if (at < 0) {
    return [{ s: base, t: label }]
  }

  return [
    { s: base, t: label.slice(0, at) },
    { s: base ? `${base} mark` : 'mark', t: label.slice(at, at + query.length) },
    { s: base, t: label.slice(at + query.length) }
  ].filter(s => s.t)
}
