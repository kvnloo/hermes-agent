export type MoaStatus = 'queued' | 'running' | 'complete' | 'failed' | 'interrupted'
export type MoaPhase = 'idle' | 'fanout' | 'aggregating' | 'settled'
export type ThinkingOrbState = 'solving' | 'weaving' | 'searching' | 'working' | 'composing'

export interface MoaSlot {
  id: number
  label?: string
  output?: string
  status: MoaStatus
}

export interface MoaState {
  aggregatorLabel?: string
  elapsedSeconds?: number
  phase: MoaPhase
  refsDone: number
  refsTotal: number
  slots: MoaSlot[]
}

export interface MoaEvent {
  payload?: Record<string, unknown>
  type: string
}

const FAILED = /^\[(failed|skipped):/i
const INTERRUPTED = /interrupted by user/i

export function emptyMoaState(): MoaState {
  return { phase: 'idle', refsDone: 0, refsTotal: 0, slots: [] }
}

function number(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function text(value: unknown): string | undefined {
  return typeof value === 'string' && value ? value : undefined
}

function slotsFor(slots: MoaSlot[], total: number): MoaSlot[] {
  return Array.from({ length: total }, (_, offset) => slots[offset] ?? { id: offset + 1, status: 'running' })
}

function terminalCount(slots: MoaSlot[]): number {
  return slots.filter(slot => slot.status !== 'running' && slot.status !== 'queued').length
}

function progress(state: MoaState, payload: Record<string, unknown>): MoaState {
  const refsTotal = number(payload.refs_total) ?? state.refsTotal
  const refsDone = Math.min(refsTotal, Math.max(state.refsDone, number(payload.refs_done) ?? 0))
  const elapsedSeconds = number(payload.elapsed_seconds) ?? state.elapsedSeconds
  const index = number(payload.index)
  const label = text(payload.label)
  let slots = refsTotal ? slotsFor(state.slots, refsTotal) : state.slots

  if (index && index <= refsTotal && label) {
    slots = slots.map(slot =>
      slot.id === index ? { ...slot, label, status: payload.state === 'waiting' ? 'queued' : slot.status } : slot
    )
  }

  return { ...state, elapsedSeconds, phase: refsTotal ? 'fanout' : state.phase, refsDone, refsTotal, slots }
}

function reference(state: MoaState, payload: Record<string, unknown>): MoaState {
  const refsTotal = number(payload.count) ?? state.refsTotal
  const index = number(payload.index)
  const label = text(payload.label)
  const output = text(payload.text)
  let slots = refsTotal ? slotsFor(state.slots, refsTotal) : state.slots

  if (!index || index < 1 || index > refsTotal) {
    return { ...state, phase: refsTotal ? 'fanout' : state.phase, refsTotal, slots }
  }

  const status: MoaStatus = INTERRUPTED.test(output ?? '')
    ? 'interrupted'
    : FAILED.test(output ?? '')
      ? 'failed'
      : 'complete'

  slots = slots.map(slot => (slot.id === index ? { ...slot, label: label ?? slot.label, output, status } : slot))

  return {
    ...state,
    phase: 'fanout',
    refsDone: Math.min(refsTotal, Math.max(state.refsDone, terminalCount(slots))),
    refsTotal,
    slots
  }
}

function aggregate(state: MoaState, payload: Record<string, unknown>): MoaState {
  if (!state.refsTotal || state.refsDone < state.refsTotal) {
    return state
  }

  return { ...state, aggregatorLabel: text(payload.aggregator) ?? state.aggregatorLabel, phase: 'aggregating' }
}

export function applyMoaEvent(state: MoaState, event: MoaEvent): MoaState {
  const payload = event.payload ?? {}

  switch (event.type) {
    case 'moa.progress':
      return progress(state, payload)

    case 'moa.reference':
      return reference(state, payload)

    case 'moa.aggregating':
      return aggregate(state, payload)

    case 'moa.phase':
      return payload.phase === 'aggregator' ? aggregate(state, payload) : state

    case 'message.complete':
      return state.phase === 'idle'
        ? state
        : { ...state, phase: 'settled', slots: state.slots.map(({ output: _, ...slot }) => slot) }

    default:
      return state
  }
}

export function thinkingOrbStateFor(kind: 'advisor' | 'aggregator' | 'search' | 'tool' | 'response'): ThinkingOrbState {
  return {
    advisor: 'solving',
    aggregator: 'weaving',
    search: 'searching',
    tool: 'working',
    response: 'composing'
  }[kind] as ThinkingOrbState
}
