/**
 * One semantic frame per burst of state changes, paced by Tern's acks.
 *
 * A change marks the view dirty. A free credit sends that frame. Further
 * changes while the surface is blocked stay in the model. The next ack
 * flushes the newest view once. There is no render timer.
 */
export class FramePump {
  #dirty = false
  #queued = false

  constructor(
    private readonly blocked: () => boolean,
    private readonly render: () => void,
    private readonly schedule: (fn: () => void) => void = queueMicrotask
  ) {}

  /** State changed. Send now if Tern has credit. Otherwise wait for an ack. */
  changed() {
    this.#dirty = true

    if (this.blocked()) {
      return
    }

    this.#queue()
  }

  /** Tern displayed a frame. Flush the newest view if one is waiting. */
  credit() {
    if (!this.#dirty || this.blocked()) {
      return
    }

    this.#queue()
  }

  #queue() {
    if (this.#queued) {
      return
    }

    this.#queued = true
    this.schedule(() => {
      this.#queued = false
      this.#flush()
    })
  }

  #flush() {
    if (!this.#dirty || this.blocked()) {
      return
    }

    this.#dirty = false
    this.render()
  }
}
