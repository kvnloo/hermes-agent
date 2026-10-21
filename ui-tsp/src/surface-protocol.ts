import { Node, type Op, type Session, Surface, Tree, type TspEvent, View } from '@stencil-hq/tern'

export const ACK_STALL_MS = 5000
export const MAX_SURFACE_RECOVERIES = 3
export type SurfaceState = 'visible' | 'hidden' | 'detached' | 'failed' | 'disposed'

/** Forget exactly what the peer evicted, preserving the ids of surviving siblings. */
export function forgetView(view: View, ids: readonly string[]): View {
  class ResidentTree extends Tree {
    override readonly children: readonly Tree[]

    constructor(tree: Tree) {
      super(tree.id, new Node(tree.kind, tree.props, [], tree.node.handlers))
      this.children = tree.children.filter(child => !ids.includes(child.id)).map(child => new ResidentTree(child))
    }
  }

  return new View(view.regions.map(tree => (tree && !ids.includes(tree.id) ? new ResidentTree(tree) : undefined)))
}

/** Public SDK reconciliation with explicit eviction knowledge (Surface has no forget API). */
export class SurfaceView {
  #view = new View()
  recovering = false
  #dispatch: Surface | undefined

  remember(input: Parameters<Surface['render']>[0]) {
    this.#view = View.from(input)
  }

  forget(ids: readonly string[]) {
    this.recovering = true
    this.#view = forgetView(this.#view, ids)
    // Do not route a gesture to a node the terminal no longer owns.
    this.#dispatch = undefined
  }

  paint(surface: Surface, input: Parameters<Surface['render']>[0], history: readonly Op[] = []) {
    const next = View.from(input)
    const ops = [...this.#view.ops(next, surface.id), ...history]
    this.#view = next
    // A non-listening surface is only a handler router; it never writes to the tty.
    this.#dispatch = new Surface({ send() {}, credits: () => 1, dropped() {} }, surface.id, { listen: false })
    this.#dispatch.render(input)

    if (ops.length) {
      surface.send(ops)
    }
  }

  get trees(): readonly Tree[] { return this.#view.regions.flatMap(tree => tree ? [tree] : []) }

  dispatch(event: TspEvent) {
    return this.#dispatch?.dispatch(event)
  }
}

interface ProtocolHost {
  replace(surface: Surface): void
  changed(): void
  credit(): void
  report(message: string): void
}

/** Epochs isolate ACKs. A timeout diagnoses a visible stall; it never grants credit. */
export class SurfaceProtocol {
  #surface!: Surface
  #state: SurfaceState = 'visible'
  #visible = true
  #recoveries = 0
  #missing = false
  #timer: ReturnType<typeof setTimeout> | undefined
  #pending: Op[] = []
  #stalled = false

  constructor(
    private readonly tern: Session,
    private readonly host: ProtocolHost
  ) {}

  get state(): SurfaceState {
    return this.#state
  }
  get blocked(): boolean {
    return this.#state !== 'visible' || this.#surface.closed || this.#surface.blocked
  }

  open(): Surface {
    if (this.#state === 'disposed') {
      throw new Error('Cannot reopen a disposed Tern protocol boundary')
    }

    const surface = this.tern.open({
      id: this.#recoveries ? `hermes.recovery-${this.#recoveries}` : 'hermes',
      mode: 'inline',
      role: 'omp.session',
      title: 'hermes'
    })

    this.#surface = surface
    this.#pending = []
    this.#stalled = false
    const send = surface.send.bind(surface)
    const acknowledge = surface.acknowledge.bind(surface)

    surface.send = ops => {
      if (surface !== this.#surface || this.#state === 'disposed' || this.#state === 'failed' || surface.closed) {
        return
      }

      // Unlike SDK's private raw-op queue, this queue can forget evicted targets.
      if (surface.blocked) {
        this.#pending.push(...ops)
      } else {
        send([...this.#pending, ...ops])
        this.#pending = []
      }

      this.#watch()
    }

    surface.acknowledge = s => {
      if (surface !== this.#surface || surface.closed || !Number.isInteger(s) || s < 1 || s > surface.seq) {
        return
      }

      const before = surface.blocked
      acknowledge(s)

      if (before && !surface.blocked) {
        this.#stalled = false
        this.#clearTimer()
      }

      if (!this.blocked && this.#pending.length) {
        // Session handles ACKs synchronously, but delivers gone through its async
        // iterator. Let that eviction retire queued targets from the same read first.
        setImmediate(() => {
          if (surface !== this.#surface || this.blocked) {
            return
          }

          if (this.#pending.length) {
            const pending = this.#pending
            this.#pending = []
            send(pending)
          }

          this.#watch()
          this.host.credit()
        })
      } else {
        this.host.credit()
      }

      this.#watch()
    }

    return surface
  }

  event(event: TspEvent): void {
    if (this.#state === 'disposed') {
      return
    }

    const current = this.#surface
    const addressed = !('sf' in event) || !event.sf || event.sf === current.id

    if (event.ev === 'gone' && event.ids.includes(current.id)) {
      this.#missing = true
      this.#state = 'detached'
      this.#pending = []
      this.#clearTimer()
      this.#recover()

      return
    }

    if (!addressed) {
      return
    }

    if (event.ev === 'gone') {
      // Reconciliation will restore active children, or leave cold history evicted.
      this.#pending = []
    }

    if ((event.ev === 'visible' || event.ev === 'resize') && event.visible !== undefined) {
      this.#visible = event.visible

      if (this.#state !== 'failed') {
        this.#state = this.#missing ? 'detached' : event.visible ? 'visible' : 'hidden'
      }

      this.#clearTimer()

      if (event.visible) {
        this.#recover()
        this.#watch()
      }
    }

    if (event.ev === 'error') {
      const where = [event.s === undefined ? '' : `frame ${event.s}`, event.op === undefined ? '' : `op ${event.op}`]
        .filter(Boolean)
        .join(', ')

      this.#fail(`Tern protocol rejected ${where || 'an operation'}: ${event.msg}`)
    }

    if (event.ev === 'unknown' && ['error', 'gone', 'ack'].includes(String(event.raw.ev))) {
      this.#fail(`Tern protocol sent a malformed ${String(event.raw.ev)} event.`)
    }
  }

  rendered() {
    this.#watch()
  }

  failure(error: unknown) {
    this.#fail(`Tern protocol could not build a frame: ${error instanceof Error ? error.message : String(error)}`)
  }

  dispose() {
    this.#state = 'disposed'
    this.#pending = []
    this.#clearTimer()
  }

  #recover() {
    if (!this.#missing || !this.#visible || this.#state === 'failed') {
      return
    }

    if (this.#recoveries >= MAX_SURFACE_RECOVERIES) {
      this.#fail('Tern surface recovery limit reached; reconnect the frontend.')

      return
    }

    this.#recoveries++
    this.#missing = false
    this.#state = 'visible'
    this.host.replace(this.open())
    this.host.changed()
  }

  #fail(message: string) {
    if (this.#state === 'failed') {
      return
    }

    this.#state = 'failed'
    this.#pending = []
    this.#clearTimer()
    // Do not close/flush an untrusted SDK queue, and do not replay a rejected frame.
    this.#surface.gone()
    this.host.report(message)
  }

  #watch() {
    if (this.#timer || this.#stalled || this.#state !== 'visible' || !this.#surface.blocked) {
      return
    }

    this.#timer = setTimeout(() => {
      this.#timer = undefined

      if (this.#state === 'visible' && this.#surface.blocked) {
        this.#stalled = true
        this.host.report('Tern is not acknowledging visible frames; waiting for credit (no frames bypassed).')
      }
    }, ACK_STALL_MS)
    this.#timer.unref()
  }

  #clearTimer() {
    clearTimeout(this.#timer)
    this.#timer = undefined
  }
}
