export type MoaSlotStatus = 'queued' | 'running' | 'complete' | 'failed' | 'interrupted'
export type MoaPhase = 'idle' | 'fanout' | 'aggregating' | 'reused' | 'settled'
export type MoaAggregatorStatus = 'waiting' | 'acting' | 'idle'
export type MoaCadence = 'fresh' | 'cached'
export type ThinkingOrbState =
  | 'solving'
  | 'weaving'
  | 'searching'
  | 'working'
  | 'connecting'
  | 'composing'
  | 'listening'
  | 'breathing'
  | 'shaping'

export interface MoaAdvisorSlot {
  id: string
  index: number
  label: string | null
  status: MoaSlotStatus
  output?: string
  outputProgress?: number
  playSuccessMotion: boolean
}

export interface MoaOrchestrationState {
  phase: MoaPhase
  parallel: boolean
  refsDone: number
  refsTotal: number
  slots: MoaAdvisorSlot[]
  aggregatorStatus: MoaAggregatorStatus
  aggregatorLabel: string | null
  elapsedSeconds?: number
  waitingLabel?: string
  unattributedCompletions: number
  cadence: MoaCadence
  summary?: string
  thoughtPercent?: number
}

export interface MoaGatewayEvent {
  type: string
  payload?: Record<string, unknown>
}

export type ThinkingOrbKind =
  | { kind: 'advisor'; status: MoaSlotStatus }
  | { kind: 'aggregator'; status: MoaAggregatorStatus }
  | { kind: 'tool'; toolName: string }
  | { kind: 'handshake'; target: string }
  | { kind: 'response' }
  | { kind: 'approval' }
  | { kind: 'planning' }

const MAX_REFERENCE_WORKERS = 8
const FAILED_NOTE = /^\[failed:/i
const SKIPPED_NOTE = /^\[skipped:/i
const INTERRUPTED_NOTE = /interrupted by user/i

const SEARCH_TOOLS = new Set([
  'web_search',
  'web_extract',
  'browser_navigate',
  'browser_snapshot',
  'browser_click',
  'browser_fill',
  'browser_type',
  'browser_take_screenshot'
])

export function emptyMoaState(): MoaOrchestrationState {
  return {
    aggregatorLabel: null,
    aggregatorStatus: 'idle',
    cadence: 'fresh',
    parallel: false,
    phase: 'idle',
    refsDone: 0,
    refsTotal: 0,
    slots: [],
    unattributedCompletions: 0
  }
}

function asNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function asString(value: unknown): string | undefined {
  return typeof value === 'string' && value.length > 0 ? value : undefined
}

function makeSlot(index: number, total: number): MoaAdvisorSlot {
  return {
    id: `moa-slot-${index}`,
    index,
    label: null,
    playSuccessMotion: false,
    status: index <= Math.min(MAX_REFERENCE_WORKERS, total) ? 'running' : 'queued'
  }
}

function ensureSlots(state: MoaOrchestrationState, total: number): MoaAdvisorSlot[] {
  if (state.slots.length === total) {
    return state.slots
  }

  if (state.slots.length > total) {
    return state.slots.slice(0, total)
  }

  const next = state.slots.slice()

  for (let index = next.length + 1; index <= total; index += 1) {
    next.push(makeSlot(index, total))
  }

  return next
}

function classifyReferenceText(text: string | undefined): MoaSlotStatus {
  if (!text) {
    return 'complete'
  }

  if (FAILED_NOTE.test(text)) {
    return 'failed'
  }

  if (SKIPPED_NOTE.test(text)) {
    return INTERRUPTED_NOTE.test(text) ? 'interrupted' : 'failed'
  }

  return 'complete'
}

function fanoutSettled(slots: MoaAdvisorSlot[], refsDone: number, refsTotal: number): boolean {
  if (refsTotal <= 0) {
    return false
  }

  const terminal = slots.filter(slot => slot.status !== 'running' && slot.status !== 'queued').length

  return refsDone >= refsTotal || terminal >= refsTotal
}

function withAggregatorGate(state: MoaOrchestrationState): MoaOrchestrationState {
  if (state.phase === 'settled' || state.phase === 'reused') {
    return state
  }

  const settled = fanoutSettled(state.slots, state.refsDone, state.refsTotal)

  if (!settled) {
    return {
      ...state,
      aggregatorStatus: state.refsTotal > 0 ? 'waiting' : state.aggregatorStatus,
      phase: state.refsTotal > 0 ? 'fanout' : state.phase
    }
  }

  if (state.phase === 'aggregating') {
    return { ...state, aggregatorStatus: 'acting' }
  }

  return {
    ...state,
    aggregatorStatus: 'waiting',
    phase: 'fanout'
  }
}

function applyProgress(state: MoaOrchestrationState, payload: Record<string, unknown>): MoaOrchestrationState {
  if (payload.cached === true) {
    const total = asNumber(payload.refs_total) ?? state.refsTotal
    const done = asNumber(payload.refs_done) ?? total

    return {
      ...state,
      cadence: 'cached',
      parallel: false,
      phase: 'reused',
      refsDone: done,
      refsTotal: total,
      slots: total > 0 ? ensureSlots(state, total).map(slot => ({ ...slot, status: 'complete' })) : state.slots
    }
  }

  const total = asNumber(payload.refs_total)
  const done = asNumber(payload.refs_done)
  const waiting = payload.state === 'waiting'
  const index = asNumber(payload.index)
  const label = asString(payload.label)
  const outputProgress = asNumber(payload.output_progress)
  const elapsedSeconds = asNumber(payload.elapsed_seconds)

  if (total === undefined && done === undefined && !waiting) {
    return state
  }

  const refsTotal = total ?? state.refsTotal
  const refsDone = done ?? state.refsDone
  let slots = refsTotal > 0 ? ensureSlots(state, refsTotal) : state.slots
  let unattributedCompletions = state.unattributedCompletions

  if (!waiting && index !== undefined && index >= 1 && index <= slots.length) {
    slots = slots.map(slot =>
      slot.index === index
        ? {
            ...slot,
            label: label ?? slot.label,
            outputProgress: outputProgress ?? slot.outputProgress,
            playSuccessMotion: true,
            status: 'complete'
          }
        : slot
    )
  } else if (!waiting && label && index === undefined) {
    unattributedCompletions = Math.max(unattributedCompletions, refsDone)
  }

  return withAggregatorGate({
    ...state,
    cadence: 'fresh',
    elapsedSeconds: elapsedSeconds ?? state.elapsedSeconds,
    parallel: refsTotal > 1,
    phase: 'fanout',
    refsDone,
    refsTotal,
    slots,
    unattributedCompletions,
    waitingLabel: waiting ? label ?? state.waitingLabel : state.waitingLabel
  })
}

function applyReference(state: MoaOrchestrationState, payload: Record<string, unknown>): MoaOrchestrationState {
  const count = asNumber(payload.count) ?? state.refsTotal
  const index = asNumber(payload.index)
  const label = asString(payload.label)
  const text = asString(payload.text)
  const slots = count > 0 ? ensureSlots(state, count) : state.slots
  const status = classifyReferenceText(text)

  const nextSlots =
    index !== undefined && index >= 1 && index <= slots.length
      ? slots.map(slot =>
          slot.index === index
            ? {
                ...slot,
                label: label ?? slot.label,
                output: text,
                playSuccessMotion: status === 'complete',
                status
              }
            : slot
        )
      : slots

  const terminal = nextSlots.filter(slot => slot.status !== 'running' && slot.status !== 'queued').length

  return withAggregatorGate({
    ...state,
    parallel: count > 1,
    phase: 'fanout',
    refsDone: Math.max(state.refsDone, terminal),
    refsTotal: count,
    slots: nextSlots
  })
}

function applyPhase(state: MoaOrchestrationState, payload: Record<string, unknown>): MoaOrchestrationState {
  if (payload.phase !== 'aggregator') {
    return state
  }

  const aggregatorLabel = asString(payload.aggregator) ?? state.aggregatorLabel
  const refsTotal = asNumber(payload.refs_total) ?? state.refsTotal
  const refsDone = asNumber(payload.refs_done) ?? state.refsDone
  const slots = refsTotal > 0 ? ensureSlots(state, refsTotal) : state.slots
  const settled = fanoutSettled(slots, refsDone, refsTotal)

  if (!settled) {
    return {
      ...state,
      aggregatorLabel,
      aggregatorStatus: 'waiting',
      phase: 'fanout',
      refsDone,
      refsTotal,
      slots
    }
  }

  return {
    ...state,
    aggregatorLabel,
    aggregatorStatus: 'acting',
    phase: 'aggregating',
    refsDone,
    refsTotal,
    slots
  }
}

function applyComplete(state: MoaOrchestrationState): MoaOrchestrationState {
  if (state.phase === 'idle' && state.refsTotal === 0) {
    return state
  }

  const advisorCount = state.refsTotal || state.slots.length
  const aggregator = state.aggregatorLabel ?? 'aggregator'
  const elapsed = state.elapsedSeconds
  const elapsedPart = elapsed !== undefined ? ` · ${Math.round(elapsed)}s` : ''

  return {
    ...state,
    aggregatorStatus: 'idle',
    parallel: false,
    phase: 'settled',
    slots: state.slots.map(slot => ({ ...slot, output: undefined })),
    summary: `${advisorCount} advisors → ${aggregator}${elapsedPart}`
  }
}

export function applyMoaEvent(state: MoaOrchestrationState, event: MoaGatewayEvent): MoaOrchestrationState {
  const payload = event.payload ?? {}

  switch (event.type) {
    case 'moa.progress':
      return applyProgress(state, payload)

    case 'moa.reference':
      return applyReference(state, payload)

    case 'moa.phase':
      return applyPhase(state, payload)

    case 'message.complete':
      return applyComplete(state)

    default:
      return state
  }
}

export function slotIdentityKey(slot: MoaAdvisorSlot): string {
  return slot.id
}

export function thinkingOrbStateFor(kind: ThinkingOrbKind): ThinkingOrbState {
  switch (kind.kind) {
    case 'advisor':
      return kind.status === 'queued' ? 'breathing' : 'solving'

    case 'aggregator':
      return kind.status === 'acting' ? 'weaving' : 'breathing'

    case 'tool':
      return SEARCH_TOOLS.has(kind.toolName) ? 'searching' : 'working'

    case 'handshake':
      return 'connecting'

    case 'response':
      return 'composing'

    case 'approval':
      return 'listening'

    case 'planning':
      return 'shaping'
  }
}

export function moaStatusAnnouncement(state: MoaOrchestrationState): string {
  if (state.phase === 'idle') {
    return ''
  }

  if (state.phase === 'reused') {
    return `MoA reused ${state.refsTotal} advisors`
  }

  if (state.phase === 'settled') {
    return state.summary ?? `MoA ${state.refsTotal} advisors`
  }

  if (state.phase === 'aggregating') {
    return `MoA aggregating ${state.refsDone}/${state.refsTotal}`
  }

  const parallel = state.parallel ? 'parallel ' : ''

  return `MoA ${parallel}${state.refsDone}/${state.refsTotal}`
}
