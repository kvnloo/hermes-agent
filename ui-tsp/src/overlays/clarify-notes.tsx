// Ask note state is request/question-owned, never the user's main composer.
import type { ClarifyNote } from '@hermes/shared/gateway-events'
import type { Key } from '@stencil-hq/tern'

import { type Attachments, pastedImageSource } from '../attachments.js'
import { Composer } from '../composer.js'
import { composerAttachments } from '../view/attachments.js'

import type { PromptHost } from './approval.js'

export function clarifyNoteOf(raw: unknown, qid: string): ClarifyNote | undefined {
  if (!raw || typeof raw !== 'object') {
    return undefined
  }

  const value: unknown = Reflect.get(raw, qid)

  if (!value || typeof value !== 'object') {
    return undefined
  }

  const text: unknown = Reflect.get(value, 'text')
  const paths: unknown = Reflect.get(value, 'image_paths')

  return {
    text: typeof text === 'string' ? text : '',
    image_paths: Array.isArray(paths) ? paths.filter((path: unknown): path is string => typeof path === 'string') : []
  }
}

export class ClarifyNotes {
  readonly text = new Composer()
  readonly images?: Attachments
  active = false
  #hasNote = false

  constructor(
    readonly host: PromptHost,
    readonly session: string,
    readonly enabled: boolean,
    imageRefs: boolean,
    preset?: ClarifyNote
  ) {
    this.#hasNote = preset !== undefined
    this.images = enabled && imageRefs ? host.promptAttachments?.() : undefined
    this.text.set(preset?.text ?? '')
    this.images?.restore(
      (preset?.image_paths ?? []).map(path => ({ id: path, name: path, path, mime: '', bytes: 0 })),
      session
    )
  }

  paste(text: string): boolean {
    const source = this.images ? pastedImageSource(text, false) : undefined

    if (!source || !this.session) {
      return false
    }

    void this.images?.add(source, this.session)

    return true
  }

  key(key: Key): void {
    if (key.name === 'escape') {
      this.active = false
    } else if (key.name !== 'paste' || !key.text || !this.paste(key.text)) {
      this.text.key(key)
    }
  }

  result(): ClarifyNote | undefined {
    const image_paths = this.images?.snapshot(this.session).map(image => image.path) ?? []

    this.#hasNote ||= Boolean(this.text.text || image_paths.length)

    return this.enabled && this.#hasNote ? { text: this.text.text, image_paths } : undefined
  }

  node() {
    if (!this.enabled) {
      return null
    }

    return (
      <col gap="xs" key="notes" role="omp.ask.notes">
        <input
          cursor={this.text.cursor}
          key="input"
          onEdit={ev => {
            this.active = true

            if (!this.paste(ev.text)) {
              this.text.edit(ev)
            }

            this.host.changed()
          }}
          onFocus={() => {
            this.active = true
            this.host.changed()
          }}
          onUndo={() => {
            this.text.undo()
            this.host.changed()
          }}
          placeholder={this.images ? 'Optional note · paste an image path/data URL for a reference' : 'Optional note'}
          role="omp.ask.note"
          text={this.text.text}
        />
        {this.images
          ? composerAttachments(
              this.images.items,
              id => void this.images?.remove(id),
              id => this.images?.retry(id)
            )
          : null}
        {this.images ? (
          <text key="hint" text="Images are workspace references, not automatic vision input." tone="muted" />
        ) : null}
      </col>
    )
  }
}

/** Static, authoritative deadline: expiry arrives as request.cancel. No idle interval. */
export function clarifyTimer(deadline: unknown): string {
  if (deadline === null) {
    return 'No time limit · waits until answered or cancelled'
  }

  if (typeof deadline !== 'number' || !Number.isFinite(deadline) || deadline < 0 || deadline > 8.64e15) {
    return 'Time limit not supplied by this gateway'
  }

  return `Expires ${new Date(deadline).toISOString()} · gateway cancels unanswered requests`
}
