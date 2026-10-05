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
  apc?: number
  credits?: number
}

export type TspEnvelope = {
  verb: string
  params: Record<string, string>
  body: string
}

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
