import { z } from 'zod/v4'

import { EPHEMERAL_UI_APPS_BY_KIND, EPHEMERAL_UI_KINDS } from './ephemeral-ui-kinds.generated'

// ephemeral-ui cards for the `openui-v2` Board: the 50 card kinds of kvnloo/ephemeral-ui
// (schema/card.v0.json), drawn by the kit's own code in a sandboxed frame with no network.
// Ported from the T3 Code and Dash integrations of the same kit. A card may report what the reader
// pointed at; only the reader can add that to the composer. Nothing is sent, booked or approved.

export const EPHEMERAL_LIMITS = { cards: 12, title: 200, app: 60, inputBytes: 32_768 } as const
export const EPHEMERAL_OPTION_KEYS = ['range', 'view', 'sort', 'tab', 'focusTool', 'scope'] as const

export type EphemeralKind = (typeof EPHEMERAL_UI_KINDS)[number]

export const isTraceKind = (kind: string) => kind.startsWith('trace')

export const ephemeralCardsProps = z.object({
  title: z.string().min(1).max(EPHEMERAL_LIMITS.title),
  cards: z
    .array(
      z.object({
        kind: z.enum(EPHEMERAL_UI_KINDS),
        app: z.string().min(1).max(EPHEMERAL_LIMITS.app).regex(/^[a-z0-9-]+$/).optional(),
        input: z.unknown().optional(),
        options: z.partialRecord(z.enum(EPHEMERAL_OPTION_KEYS), z.string().max(EPHEMERAL_LIMITS.app)).optional()
      })
    )
    .min(1)
    .max(EPHEMERAL_LIMITS.cards)
})

export type EphemeralCardsProps = z.infer<typeof ephemeralCardsProps>
export type EphemeralCard = EphemeralCardsProps['cards'][number]

/** Cross-field rules the schema cannot express. */
export function ephemeralCardsProblem(props: EphemeralCardsProps): string | null {
  for (const card of props.cards) {
    if (card.input === undefined) {
      continue
    }

    if (!isTraceKind(card.kind)) {
      return `${card.kind} draws sample data and takes no input`
    }

    if (JSON.stringify(card.input).length > EPHEMERAL_LIMITS.inputBytes) {
      return `${card.kind} input exceeds ${EPHEMERAL_LIMITS.inputBytes / 1024} KiB`
    }
  }

  return null
}

/** The catalog app the kit draws a card as: the named app when it lists the kind, else the kind's default. */
export function ephemeralCardApp(kind: EphemeralKind, app?: string): string {
  const apps = EPHEMERAL_UI_APPS_BY_KIND[kind] ?? []

  return app && apps.includes(app) ? app : (apps[0] ?? kind)
}

/** What a card reported back (the kit's `eui:intent`), reduced to bounded text. */
export interface EphemeralIntent {
  kind: string
  app: string
  action: string
  label: string
  ids: string[]
}

export type EphemeralMessage =
  | { type: 'height'; value: number }
  | { type: 'ready' }
  | { type: 'intent'; intent: EphemeralIntent }
  | { type: 'error'; kind: string; reason: string }

const text = (value: unknown, max: number) => (typeof value === 'string' ? value.replace(/\s+/g, ' ').trim().slice(0, max) : '')

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value)

/** Parse a message posted by the card document on `channel`; anything else returns null. */
export function parseEphemeralMessage(raw: unknown, channel: string): EphemeralMessage | null {
  if (!isRecord(raw) || raw.source !== 'hermes-eui' || raw.channel !== channel) {
    return null
  }

  if (raw.type === 'height' && typeof raw.value === 'number' && Number.isFinite(raw.value)) {
    return { type: 'height', value: Math.max(0, Math.min(20_000, Math.round(raw.value))) }
  }

  if (raw.type === 'ready') {
    return { type: 'ready' }
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

    return action || label ? { type: 'intent', intent: { kind: text(detail.kind, 60), app: text(detail.app, 60), action, label, ids } } : null
  }

  return null
}

/** The composer text for a pick: one bounded line the agent can act on, marked as sample data. */
export function ephemeralIntentContext(intent: EphemeralIntent, app: string): string {
  const what = intent.label || intent.action
  const ids = intent.ids.length ? ` (${intent.ids.join(', ')})` : ''

  return `[ephemeral-ui ${intent.kind || 'card'} · ${app} · sample data] ${what}${ids}`
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
