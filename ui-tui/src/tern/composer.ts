import { type EditEvent, node, type SendEvent, type Surface } from '@stencil-hq/tern'

export const MAX_NATIVE_DRAFT = 256 * 1024

export interface ComposerSnapshot {
  owner: string
  revision: number
  text: string
  ready: boolean
  busy: boolean
  modal: boolean
}

export interface ComposerBinding {
  read(): ComposerSnapshot
  edit(text: string): void
  submit(fullText: string): void
}

/** Presentation only: no RPC, sessions, history or queue of its own. */
export class TernComposer {
  #binding?: ComposerBinding
  #snapshot = ''
  #serial = 0
  #closed = false
  #visible = true

  setVisible(visible: boolean) {
    this.#visible = visible
    this.#snapshot = ''
    this.refresh()
  }

  constructor(readonly surface: Surface) {}

  bind(binding: ComposerBinding) {
    this.#binding = binding
    this.refresh()
  }

  refresh() {
    if (this.#closed || this.surface.closed || !this.#binding) {
      return
    }

    const snapshot = this.#binding.read()
    const key = JSON.stringify(snapshot)

    if (key === this.#snapshot) {
      return
    }

    this.#snapshot = key
    const serial = ++this.#serial

    if (!this.#visible) {
      this.surface.render({ dock: [] })

      return
    }

    const enabled = snapshot.ready && !snapshot.busy && !snapshot.modal && snapshot.text.length <= MAX_NATIVE_DRAFT
    // Changing the node identity rejects even equal-length edits or delayed sends from a prior draft.
    this.surface.render({
      dock: [
        node('editor', {
          key: `composer-${serial}`,
          onEdit: (event: EditEvent) => this.#edit(serial, key, event),
          onSend: (event: SendEvent) => this.#send(serial, key, event),
          readonly: !enabled,
          role: 'omp.editor',
          sendable: enabled,
          text: snapshot.modal ? '' : snapshot.text.slice(0, MAX_NATIVE_DRAFT)
        })
      ]
    })
  }

  #current(serial: number, key: string): ComposerBinding | undefined {
    const binding = this.#binding
    const live = binding?.read()

    if (
      !binding || !live || this.#closed || !this.#visible || this.surface.closed || serial !== this.#serial ||
      JSON.stringify(live) !== key || !live.ready || live.busy || live.modal || live.text.length > MAX_NATIVE_DRAFT
    ) {
      return
    }

    return binding
  }

  #edit(serial: number, key: string, event: EditEvent) {
    const binding = this.#current(serial, key)

    if (!binding) {
      return
    }

    const text = binding.read().text
    const { from, to, cursor, len } = event
    const size = text.length - (to - from) + event.text.length

    if (
      len !== text.length || ![from, to, cursor].every(Number.isSafeInteger) ||
      from < 0 || to < from || to > len || cursor < 0 || cursor > size || size > MAX_NATIVE_DRAFT
    ) {
      return
    }

    ++this.#serial
    binding.edit(text.slice(0, from) + event.text + text.slice(to))
    this.refresh()
  }

  #send(serial: number, key: string, event: SendEvent) {
    const binding = this.#current(serial, key)

    if (!binding || !event.text.trim() || event.text.length > MAX_NATIVE_DRAFT) {
      return
    }

    // Invalidate synchronously, before any durable admission or asynchronous continuation.
    this.#snapshot = ''
    ++this.#serial
    binding.submit(event.text)
    this.refresh()
  }

  unbind() {
    this.#binding = undefined
    ++this.#serial
    this.#snapshot = ''
  }

  close() {
    this.#closed = true
    this.unbind()
  }
}
