import { EPHEMERAL_UI_APPS, EPHEMERAL_UI_CONNECTORS, EPHEMERAL_UI_KINDS } from './kit-meta.generated'

// ephemeral-ui cards in Hermes Desktop: when the agent calls a tool on a known app's MCP server,
// that tool row grows the app's card from the kit (drawn by the kit's own code in a sandboxed frame).
// The card lives while its task runs, then its ring runs out and it dissolves into a one-line receipt
// unless the reader pins it to the input bar. Cards never send, book or approve anything; a pick only
// reaches the agent when the reader adds it to the composer.

export type EphemeralKind = (typeof EPHEMERAL_UI_KINDS)[number]

/** How long a card stays once its task is done, before it dissolves (the kit's ring). */
export const EPHEMERAL_LIFETIME_MS = 9000
/** Cards one session can keep pinned to the input bar; the oldest is unpinned first. */
export const EPHEMERAL_PIN_LIMIT = 4

export interface EphemeralMatch {
  server: string
  tool: string
  app: string
  appName: string
  hex: string | null
  kind: EphemeralKind
}

const KINDS = new Set<string>(EPHEMERAL_UI_KINDS)
const normalize = (value: string) => value.toLowerCase().replace(/[_\s]+/g, '-')

const CONNECTORS = Object.entries(EPHEMERAL_UI_CONNECTORS).map(([server, entry]) => ({
  names: [server, ...entry.aliases],
  app: entry.app,
  tools: entry.tools.map(([pattern, kind]) => [new RegExp(pattern, 'i'), kind] as const)
}))

/** The card a tool call grows: Hermes registers MCP tools as `mcp__<server>__<tool>`. */
export function matchEphemeralTool(toolName: string): EphemeralMatch | null {
  const parts = /^mcp__(.+?)__(.+)$/.exec(toolName)

  if (!parts) {
    return null
  }

  const server = normalize(parts[1])
  const tool = parts[2]

  for (const connector of CONNECTORS) {
    const named = connector.names.some(name => server === name || server.startsWith(`${name}-`) || server.endsWith(`-${name}`))

    if (!named) {
      continue
    }

    const kind = connector.tools.find(([pattern]) => pattern.test(tool))?.[1]
    const app = EPHEMERAL_UI_APPS[connector.app]

    if (kind && KINDS.has(kind) && app) {
      return { server, tool, app: connector.app, appName: app.name, hex: app.hex, kind: kind as EphemeralKind }
    }
  }

  return null
}

/** What a card reported back (the kit's `eui:intent`), reduced to bounded text. */
export interface EphemeralIntent {
  kind: string
  action: string
  label: string
  ids: string[]
}

export type EphemeralMessage =
  | { type: 'height'; value: number }
  | { type: 'ready'; summary: string }
  | { type: 'intent'; intent: EphemeralIntent; summary: string }
  | { type: 'dissolved'; summary: string }
  | { type: 'error'; kind: string; reason: string }

const text = (value: unknown, max: number) => (typeof value === 'string' ? value.replace(/\s+/g, ' ').trim().slice(0, max) : '')

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

/** Parse a message posted by a card document on `channel`; anything else returns null. */
export function parseEphemeralMessage(raw: unknown, channel: string): EphemeralMessage | null {
  if (!isRecord(raw) || raw.source !== 'hermes-eui' || raw.channel !== channel) {
    return null
  }

  if (raw.type === 'height' && typeof raw.value === 'number' && Number.isFinite(raw.value)) {
    return { type: 'height', value: Math.max(0, Math.min(4000, Math.round(raw.value))) }
  }

  if (raw.type === 'ready' || raw.type === 'dissolved') {
    return { type: raw.type, summary: text(raw.summary, 160) }
  }

  if (raw.type === 'error') {
    return { type: 'error', kind: text(raw.kind, 60), reason: text(raw.reason, 300) }
  }

  if (raw.type === 'intent' && isRecord(raw.detail)) {
    const detail = raw.detail

    const ids = Array.isArray(detail.ids)
      ? detail.ids.filter((id): id is string => typeof id === 'string' && /^[a-z][\w-]*:\S/i.test(id)).slice(0, 8).map(id => id.slice(0, 120))
      : []

    const action = text(detail.action, 40)
    const label = text(detail.label, 200)

    return action || label
      ? { type: 'intent', intent: { kind: text(detail.kind, 60), action, label, ids }, summary: text(detail.summary, 160) }
      : null
  }

  return null
}

/** The host side of the card protocol: start the ring once the card's task is done. */
export const lifetimeMessage = (channel: string, ms: number) => ({ source: 'hermes-eui-host', channel, type: 'ttl', ms })

/** The composer text for a card: one bounded line the agent can act on, marked as sample data. */
export function ephemeralContextLine(card: { kind: string; appName: string }, what: string, ids: readonly string[] = []): string {
  const refs = ids.length ? ` (${ids.join(', ')})` : ''

  return `[ephemeral-ui ${card.kind} · ${card.appName} · sample data] ${what}${refs}`
}

// Desktop palette tokens the kit theme reads, probed through the same utility classes the app paints
// with, so skins, glass and accent overrides all come through without knowing their variable names.
const PALETTE = [
  ['bg', 'bg-background', 'backgroundColor'],
  ['fg', 'text-foreground', 'color'],
  ['card', 'bg-card', 'backgroundColor'],
  ['muted', 'bg-muted', 'backgroundColor'],
  ['mutedFg', 'text-muted-foreground', 'color'],
  ['accent', 'bg-accent', 'backgroundColor'],
  ['border', 'border border-border', 'borderTopColor'],
  ['input', 'bg-input', 'backgroundColor'],
  ['primary', 'bg-primary', 'backgroundColor'],
  ['primaryFg', 'text-primary-foreground', 'color'],
  ['danger', 'text-destructive', 'color']
] as const

/** Resolve the live desktop theme to opaque hex colours (the kit's colour maths needs hex). */
export function readDesktopPalette(): Record<string, string> {
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = 1
  const ctx = canvas.getContext('2d', { willReadFrequently: true })

  if (!ctx) {
    return {}
  }

  const probe = document.createElement('div')
  probe.setAttribute('aria-hidden', 'true')
  probe.style.cssText = 'position:fixed;left:-9999px;top:0;width:1px;height:1px;pointer-events:none'
  document.body.append(probe)
  const out: Record<string, string> = {}

  try {
    // Translucent (glass) tokens are composited over the page background, as the desktop paints them.
    for (const [token, className, property] of PALETTE) {
      probe.className = className
      const value = getComputedStyle(probe)[property]

      if (!value) {
        continue
      }

      ctx.clearRect(0, 0, 1, 1)

      if (out.bg) {
        ctx.fillStyle = out.bg
        ctx.fillRect(0, 0, 1, 1)
      }

      ctx.fillStyle = 'transparent'
      ctx.fillStyle = value
      ctx.fillRect(0, 0, 1, 1)
      const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data

      if (a > 0) {
        out[token] = '#' + [r, g, b].map(n => n.toString(16).padStart(2, '0')).join('')
      }
    }
  } finally {
    probe.remove()
  }

  return out
}
