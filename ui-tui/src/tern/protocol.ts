/**
 * Minimal Tern Surface Protocol (TSP) v1 wire kernel for Hermes.
 *
 * Framing and hello semantics follow Tern's TSP and the mature OMP implementation
 * in can1357/oh-my-pi, authored/maintained by Can Bölük / Stencil Labs. Keep this
 * module deliberately small: Hermes owns agent/runtime state; Tern only becomes
 * an optional terminal surface after capability negotiation succeeds.
 */

const APC = '\x1b_'
const ST = '\x1b\\'
const PARAM_PATTERN = /^[A-Za-z0-9_-]+=[\x21-\x3a\x3c-\x7e]*$/

export const TSP_VERSION = 1
export const TSP_PREFIX = 'tsp;'

export type TspHello = {
  r: 'hello'
  v: number
  term: string
  kinds: string[]
  features?: string[]
  apc?: number
  credits?: number
  cols?: number
  dark?: boolean
  reduceMotion?: boolean
}

export type TspEnvelope = {
  verb: string
  params: Record<string, string>
  body: string
}

export type TspEvent =
  | { ev: 'ack'; sf: string; s: number }
  | { ev: 'resize'; sf?: string; cols: number; visible?: boolean }
  | { ev: 'theme'; dark: boolean }
  | { ev: 'motion'; reduce: boolean }
  | { ev: 'visible'; sf?: string; visible: boolean }
  | { ev: 'toggle'; sf: string; id: string; collapsed: boolean }
  | { ev: 'select'; sf: string; id: string; item: string }
  | { ev: 'activate'; sf: string; id: string; item: string }
  | { ev: 'action'; sf: string; id: string; act: string; value?: string; mods?: string[] }
  | { ev: 'change'; sf: string; id: string; item: string; value: boolean | number | string | string[] | null }
  | { ev: 'edit'; sf: string; id: string; from: number; to: number; text: string; cursor: number; len: number }
  | { ev: 'undo'; sf: string; id: string }
  | { ev: 'send'; sf: string; id: string; text: string }
  | { ev: 'focus'; sf: string; id: string }
  | { ev: 'error'; sf?: string; s?: number; op?: number; msg: string }
  | { ev: 'gone'; sf?: string; ids: string[] }

export function encodeTspHelloQuery(version?: string): string {
  const body = {
    q: 'hello',
    v: [TSP_VERSION],
    app: 'hermes',
    features: [] as string[],
    ...(version ? { ver: version } : {})
  }

  return APC + TSP_PREFIX + 'q;' + JSON.stringify(body) + ST
}

/**
 * Parse an APC payload after Ink has removed the APC/ST framing.
 *
 * TSP is: tsp;<verb>[;k=v]*;<body>. The body is intentionally left opaque so
 * later rendering/events can reuse this parser without coupling Ink to Tern.
 */
export function parseTspApc(data: string): TspEnvelope | null {
  if (!data.startsWith(TSP_PREFIX)) {
    return null
  }

  const inner = data.slice(TSP_PREFIX.length)
  let semi = inner.indexOf(';')

  if (semi <= 0) {
    return null
  }

  const verb = inner.slice(0, semi)
  const params: Record<string, string> = {}
  let pos = semi + 1

  for (;;) {
    semi = inner.indexOf(';', pos)

    if (semi === -1) {
      break
    }

    const segment = inner.slice(pos, semi)

    if (!PARAM_PATTERN.test(segment)) {
      break
    }

    const eq = segment.indexOf('=')
    params[segment.slice(0, eq)] = segment.slice(eq + 1)
    pos = semi + 1
  }

  return { verb, params, body: inner.slice(pos) }
}

const isStringArray = (value: unknown): value is string[] =>
  Array.isArray(value) && value.every(item => typeof item === 'string')

export function decodeTspHello(data: string): TspHello | null {
  const envelope = parseTspApc(data)

  if (!envelope || envelope.verb !== 'r') {
    return null
  }

  let value: unknown

  try {
    value = JSON.parse(envelope.body)
  } catch {
    return null
  }

  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return null
  }

  const reply = value as Record<string, unknown>

  if (
    reply.r !== 'hello' ||
    typeof reply.v !== 'number' ||
    typeof reply.term !== 'string' ||
    !isStringArray(reply.kinds)
  ) {
    return null
  }

  const hello: TspHello = {
    r: 'hello',
    v: reply.v,
    term: reply.term,
    kinds: reply.kinds
  }

  if (isStringArray(reply.features)) {
    hello.features = reply.features
  }

  if (typeof reply.cols === 'number') {
    hello.cols = reply.cols
  }

  if (typeof reply.dark === 'boolean') {
    hello.dark = reply.dark
  }

  if (typeof reply.reduceMotion === 'boolean') {
    hello.reduceMotion = reply.reduceMotion
  }

  if (typeof reply.apc === 'number') {
    hello.apc = reply.apc
  }

  if (typeof reply.credits === 'number') {
    hello.credits = reply.credits
  }

  return hello
}

export function isTspHelloApcResponse(response: {
  type: string
  data?: string
}): response is { type: 'apc'; data: string } {
  return response.type === 'apc' && typeof response.data === 'string' && decodeTspHello(response.data) !== null
}


const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

const isString = (value: unknown): value is string => typeof value === 'string'
const isNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)
const isBoolean = (value: unknown): value is boolean => typeof value === 'boolean'
const optionalString = (value: unknown): value is string | undefined => value === undefined || isString(value)
const optionalNumber = (value: unknown): value is number | undefined => value === undefined || isNumber(value)

export function decodeTspEvent(data: string): TspEvent | null {
  const envelope = parseTspApc(data)

  if (!envelope || envelope.verb !== 'e') {
    return null
  }

  let value: unknown

  try {
    value = JSON.parse(envelope.body)
  } catch {
    return null
  }

  if (!isRecord(value) || !isString(value.ev)) {
    return null
  }

  const event = value

  switch (event.ev) {
    case 'ack':
      return isString(event.sf) && isNumber(event.s) ? (event as TspEvent) : null
    case 'resize':
      return optionalString(event.sf) && isNumber(event.cols) && (event.visible === undefined || isBoolean(event.visible))
        ? (event as TspEvent)
        : null
    case 'theme':
      return isBoolean(event.dark) ? (event as TspEvent) : null
    case 'motion':
      return isBoolean(event.reduce) ? (event as TspEvent) : null
    case 'visible':
      return optionalString(event.sf) && isBoolean(event.visible) ? (event as TspEvent) : null
    case 'toggle':
      return isString(event.sf) && isString(event.id) && isBoolean(event.collapsed) ? (event as TspEvent) : null
    case 'select':
    case 'activate':
      return isString(event.sf) && isString(event.id) && isString(event.item) ? (event as TspEvent) : null
    case 'action':
      return isString(event.sf) &&
        isString(event.id) &&
        isString(event.act) &&
        optionalString(event.value) &&
        (event.mods === undefined || isStringArray(event.mods))
        ? (event as TspEvent)
        : null
    case 'change':
      return isString(event.sf) &&
        isString(event.id) &&
        isString(event.item) &&
        (event.value === null ||
          isBoolean(event.value) ||
          isNumber(event.value) ||
          isString(event.value) ||
          isStringArray(event.value))
        ? (event as TspEvent)
        : null
    case 'edit':
      return isString(event.sf) &&
        isString(event.id) &&
        isNumber(event.from) &&
        isNumber(event.to) &&
        isString(event.text) &&
        isNumber(event.cursor) &&
        isNumber(event.len)
        ? (event as TspEvent)
        : null
    case 'undo':
    case 'focus':
      return isString(event.sf) && isString(event.id) ? (event as TspEvent) : null
    case 'send':
      return isString(event.sf) && isString(event.id) && isString(event.text) ? (event as TspEvent) : null
    case 'error':
      return optionalString(event.sf) && optionalNumber(event.s) && optionalNumber(event.op) && isString(event.msg)
        ? (event as TspEvent)
        : null
    case 'gone':
      return optionalString(event.sf) && isStringArray(event.ids) ? (event as TspEvent) : null
    default:
      return null
  }
}

export function isTspEventApcResponse(response: {
  type: string
  data?: string
}): response is { type: 'apc'; data: string } {
  return response.type === 'apc' && typeof response.data === 'string' && decodeTspEvent(response.data) !== null
}
