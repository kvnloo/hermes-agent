import { EPHEMERAL_UI_APPS, EPHEMERAL_UI_COMMANDS, EPHEMERAL_UI_CONNECTORS, EPHEMERAL_UI_KINDS } from './kit-meta.generated'

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

/** A card the agent wrote itself (an `ephemeral-ui` fence): its markup inside the kit's card shell. */
export interface EphemeralWritten {
  title: string
  status?: string
  html: string
  summary?: string
}

export interface EphemeralMatch {
  server: string
  tool: string
  app: string
  appName: string
  hex: string | null
  /** A kit kind (cached card), or any short label when `written` carries the agent's own card. */
  kind: string
  written?: EphemeralWritten
}

/** What the card document draws: a cached kit card, or the agent's own markup in the kit's shell. */
export const ephemeralCardSpec = (match: EphemeralMatch) =>
  match.written
    ? { kind: match.kind, app: match.app, appName: match.appName, hex: match.hex, ...match.written }
    : { kind: match.kind, app: match.app }

export const EPHEMERAL_FENCE_MAX = 32_768

/**
 * An `ephemeral-ui` fence the agent wrote: JSON `{app, kind?, title?, status?, html?, summary?}`.
 * With `html` it is the agent's own card (any app, any content); without, `kind` must be a cached kit
 * card. Returns null for anything else, and the fence then shows as its source.
 */
export function parseEphemeralFence(code: string): EphemeralMatch | null {
  if (code.length > EPHEMERAL_FENCE_MAX) {
    return null
  }

  let raw: unknown

  try {
    raw = JSON.parse(code)
  } catch {
    return null
  }

  if (!isRecord(raw)) {
    return null
  }

  const appId = text(raw.app, 60).toLowerCase().replace(/[^a-z0-9-]+/g, '-')
  const known = EPHEMERAL_UI_APPS[appId]
  const appName = text(raw.appName, 60) || known?.name || text(raw.app, 60) || 'Hermes'
  const hex = /^#[0-9a-f]{6}$/i.test(text(raw.hex, 7)) ? text(raw.hex, 7) : (known?.hex ?? null)
  const html = typeof raw.html === 'string' ? raw.html : ''
  const kind = text(raw.kind, 40).toLowerCase()
  const title = text(raw.title, 120)

  if (html.trim()) {
    const label = kind.replace(/[^a-z0-9-]+/g, '-') || 'card'
    const written: EphemeralWritten = { title, html, ...(text(raw.status, 60) && { status: text(raw.status, 60) }), ...(text(raw.summary, 200) && { summary: text(raw.summary, 200) }) }

    return { server: 'agent', tool: title || label, app: appId || 'hermes', appName, hex, kind: label, written }
  }

  return KINDS.has(kind) ? { server: 'agent', tool: title || kind, app: appId || 'hermes', appName, hex, kind } : null
}

const KINDS = new Set<string>(EPHEMERAL_UI_KINDS)
const normalize = (value: string) => value.toLowerCase().replace(/[_\s]+/g, '-')

const CONNECTORS = Object.entries(EPHEMERAL_UI_CONNECTORS).map(([server, entry]) => ({
  names: [server, ...entry.aliases],
  app: entry.app,
  tools: entry.tools.map(([pattern, kind]) => [new RegExp(pattern, 'i'), kind] as const)
}))

/** The card a tool call grows: Hermes registers MCP tools as `mcp__<server>__<tool>`; CLIs run in `terminal`. */
export function matchEphemeralTool(toolName: string, args?: unknown): EphemeralMatch | null {
  if (toolName === 'terminal') {
    return matchEphemeralCommand(isRecord(args) && typeof args.command === 'string' ? args.command : '')
  }

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

    // The server is this app's: its first matching rule decides, and a null kind means no card.
    const kind = connector.tools.find(([pattern]) => pattern.test(tool))?.[1]
    const app = EPHEMERAL_UI_APPS[connector.app]

    return kind && KINDS.has(kind) && app
      ? { server, tool, app: connector.app, appName: app.name, hex: app.hex, kind }
      : null
  }

  return null
}

const COMMANDS = Object.entries(EPHEMERAL_UI_COMMANDS).map(([cli, entry]) => ({
  cli,
  app: entry.app,
  rules: entry.subcommands.map(([pattern, kind]) => [new RegExp(pattern, 'i'), kind] as const)
}))

/**
 * The card a shell command grows when it drives a known app's CLI (`gh run list -R o/r` → GitHub CI).
 * Only the first simple command of each `&&`/`;`/`|` segment is read, past `cd …` and VAR=… prefixes.
 */
export function matchEphemeralCommand(command: string): EphemeralMatch | null {
  for (const segment of command.split(/&&|\|\||[;|\n]/)) {
    const words = segment.trim().split(/\s+/).filter(Boolean)

    while (words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[0])) {
      words.shift()
    }

    const cli = (words[0] ?? '').split('/').pop() ?? ''
    const entry = COMMANDS.find(command => command.cli === cli)

    if (!entry) {
      continue
    }

    const args = words.slice(1)
    const firstFlag = args.findIndex(word => word.startsWith('-'))
    const sub = (firstFlag < 0 ? args : args.slice(0, firstFlag)).slice(0, 2).join(' ')
    const kind = entry.rules.find(([pattern]) => pattern.test(sub))?.[1]
    const app = EPHEMERAL_UI_APPS[entry.app]

    return kind && KINDS.has(kind) && app
      ? { server: 'terminal', tool: `${cli} ${sub}`.trim(), app: entry.app, appName: app.name, hex: app.hex, kind }
      : null
  }

  return null
}

/**
 * The one-line receipt a card leaves behind, written from the real tool call. The kit's own summaries
 * narrate its scripted outcomes ("Paid…", "Booked…", "Merged…"); a Hermes card never acts, so they would lie.
 * A pick is reported as a pick, never as done.
 */
export function ephemeralReceipt(match: Pick<EphemeralMatch, 'appName' | 'tool'>, picked?: string): string {
  const step = match.tool.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase()
  const line = `${match.appName} · ${step}`

  return picked ? `${line} · you picked ${picked}, not sent` : line
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
export function ephemeralContextLine(card: { kind: string; appName: string; written?: unknown }, what: string, ids: readonly string[] = []): string {
  const refs = ids.length ? ` (${ids.join(', ')})` : ''
  // A cached kit card draws sample visuals; a card the agent wrote shows what the agent put in it.
  const source = card.written ? 'agent card' : 'sample data'

  return `[ephemeral-ui ${card.kind} · ${card.appName} · ${source}] ${what}${refs}`
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
