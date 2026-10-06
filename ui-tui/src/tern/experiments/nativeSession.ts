import type { TspEvent, TspHello } from '../protocol.js'
import {
  INITIAL_NATIVE_FIXTURE, NATIVE_FIXTURE_SURFACE, fixtureNodes, fixtureRequiredKinds,
  reduceNativeFixture, renderNativeFixture, type FixtureNode, type FixtureView
} from './nativeView.js'

export type FixtureOp =
  | ['add', string, string, string | null, FixtureNode]
  | ['set', string, Record<string, unknown>]
  | ['text', string, 'append' | 'replace', string]
  | ['move', string, string, string | null]
  | ['del', string]

const same = (left: unknown, right: unknown) => JSON.stringify(left) === JSON.stringify(right)

/** Fixture-only keyed reconciliation, following OMP's stable-ID/minimal-op pattern.
 * It has no model of task execution; its only inputs are two presentation trees. */
export function diffFixtureViews(previous: FixtureView | null, next: FixtureView): FixtureOp[] {
  if (!previous) return Object.values(next).map(root => ['add', root.id, NATIVE_FIXTURE_SURFACE, null, root])
  const ops: FixtureOp[] = []
  const visit = (before: FixtureNode, after: FixtureNode): void => {
    if (before.id !== after.id || before.k !== after.k) throw new Error('Fixture node identity changed')
    const patch: Record<string, unknown> = {}
    for (const key of new Set([...Object.keys(before.p ?? {}), ...Object.keys(after.p ?? {})])) {
      const old = before.p?.[key]
      const value = after.p?.[key]
      if (same(old, value)) continue
      if (key === 'text' && typeof old === 'string' && typeof value === 'string') {
        const appends = value.startsWith(old)
        ops.push(['text', after.id, appends ? 'append' : 'replace', appends ? value.slice(old.length) : value])
      } else patch[key] = value ?? null
    }
    if (Object.keys(patch).length) ops.push(['set', after.id, patch])
    const oldChildren = new Map((before.c ?? []).map(child => [child.id, child]))
    const newChildren = after.c ?? []
    const desiredIds = new Set(newChildren.map(child => child.id))
    const order = (before.c ?? []).map(child => child.id).filter(id => desiredIds.has(id))
    for (const child of before.c ?? []) if (!desiredIds.has(child.id)) ops.push(['del', child.id])
    // Work backwards: every insertion anchor already exists in the document.
    for (let i = newChildren.length - 1; i >= 0; i--) {
      const child = newChildren[i]
      const anchor = newChildren[i + 1]?.id ?? null
      const old = oldChildren.get(child.id)
      if (!old) {
        ops.push(['add', child.id, after.id, anchor, child])
        order.splice(anchor === null ? order.length : order.indexOf(anchor), 0, child.id)
        continue
      }
      const index = order.indexOf(child.id)
      if ((order[index + 1] ?? null) !== anchor) {
        ops.push(['move', child.id, after.id, anchor])
        order.splice(index, 1)
        order.splice(anchor === null ? order.length : order.indexOf(anchor), 0, child.id)
      }
      visit(old, child)
    }
  }
  for (const region of ['main', 'dock', 'layer'] as const) visit(previous[region], next[region])
  return ops
}

export class NativeFixtureSession {
  state = { ...INITIAL_NATIVE_FIXTURE }
  private started = false
  private closed = false
  private visible = true
  private seq = 0
  private acked = 0
  private sent: FixtureView | null = null
  private desired: FixtureView | null = null
  private folds = new Map<string, boolean>()
  private credits: number

  constructor(hello: TspHello, private write: (verb: 'o' | 'f' | 'x', value: Record<string, unknown>) => void) {
    const missing = fixtureRequiredKinds().filter(kind => !hello.kinds.includes(kind))
    if (hello.v !== 1 || missing.length || !hello.features?.includes('dock')) {
      throw new Error(`Native fixture needs TSP v1, dock and its semantic kinds. Missing: ${missing.join(', ') || 'version/dock'}`)
    }
    this.credits = hello.credits ?? 2
    if (!Number.isSafeInteger(this.credits) || this.credits < 1 || this.credits > 64) throw new Error('Invalid TSP frame credits')
    if (hello.apc !== undefined && (!Number.isSafeInteger(hello.apc) || hello.apc < 4)) throw new Error('Invalid TSP APC limit')
  }

  start(): void {
    if (this.started || this.closed) return
    this.started = true
    this.write('o', { id: NATIVE_FIXTURE_SURFACE, mode: 'inline', role: 'hermes.ux.fixture', title: 'Hermes UX · A · fixture' })
    this.refresh()
  }

  dispatch(action: string): void {
    if (!this.started || this.closed) return
    this.state = reduceNativeFixture(this.state, action)
    if (action === 'reset') this.folds.clear()
    this.refresh()
  }

  event(event: TspEvent): 'quit' | 'invalidated' | undefined {
    if (this.closed || !this.started) return
    if ('sf' in event && event.sf !== undefined && event.sf !== NATIVE_FIXTURE_SURFACE) return
    if (event.ev === 'ack') {
      if (!Number.isSafeInteger(event.s) || event.s <= this.acked || event.s > this.seq) return
      this.acked = event.s
      this.flush()
    } else if (event.ev === 'visible') {
      this.visible = event.visible
      this.flush()
    } else if (event.ev === 'error' || (event.ev === 'gone' && event.ids.some(id =>
      id === NATIVE_FIXTURE_SURFACE || this.desired && fixtureNodes(this.desired).some(node => node.id === id)))) {
      this.close()
      return 'invalidated'
    } else if (event.ev === 'toggle' || event.ev === 'action') {
      const target = this.desired && fixtureNodes(this.desired).find(node => node.id === event.id)
      if (!target) return
      if (event.ev === 'toggle' && target.p?.collapsible === true) {
        this.folds.set(target.id, event.collapsed)
        this.refresh()
      } else if (event.ev === 'action') {
        const actions = target.p?.actions as { click?: string } | undefined
        if (actions?.click !== event.act) return
        if (event.act === 'quit') return 'quit'
        this.dispatch(event.act)
      }
    }
    // No edit/send/approval authority is advertised or implemented in this viewer.
  }

  close(): void {
    if (this.closed) return
    this.closed = true
    this.desired = null
    if (this.started) this.write('x', { id: NATIVE_FIXTURE_SURFACE, keep: false })
  }

  private refresh(): void {
    const view = renderNativeFixture(this.state)
    for (const node of fixtureNodes(view)) {
      if (node.p?.collapsible && this.folds.has(node.id)) node.p.collapsed = this.folds.get(node.id)
    }
    // Replace even if it equals the last sent view: A → B → A must discard B.
    this.desired = view
    this.flush()
  }

  private flush(): void {
    if (this.closed || !this.visible || !this.desired || this.seq - this.acked >= this.credits) return
    const ops = diffFixtureViews(this.sent, this.desired)
    if (!ops.length) return
    this.sent = this.desired
    this.seq++
    this.write('f', { sf: NATIVE_FIXTURE_SURFACE, s: this.seq, ops })
  }
}
