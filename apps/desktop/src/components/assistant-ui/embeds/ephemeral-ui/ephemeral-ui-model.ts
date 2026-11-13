import { z } from 'zod/v4'

import cardSchema from './vendor/schema/card.v0.json'

// The 50 card kinds of the ephemeral-ui spec, read from the vendored
// card.v0.json so the host's list can never drift from the repo's.
export const EPHEMERAL_KINDS = cardSchema.properties.kind.enum as readonly string[]
const KIND_SET = new Set(EPHEMERAL_KINDS)

export const MAX_CARDS = 6
export const MAX_FENCE_BYTES = 8_192
/** Trace kinds read the kit's trace fixture; only those frames embed it. */
export const isTraceKind = (kind: string) => kind === 'trace' || kind.startsWith('trace-')

/** Desktop's own binding of the card.v0 contract: kind + catalog app, plus
 *  the optional host fields. Extra keys are allowed by the spec and ignored. */
export const ephemeralCardSchema = z.object({
  kind: z.string().refine(kind => KIND_SET.has(kind), { message: 'unknown kind' }),
  app: z.string().regex(/^[a-z0-9][a-z0-9.-]{0,63}$/).optional(),
  ttl: z.union([z.enum(['until-done', 'pinned']), z.number().int().min(0)]).optional(),
  actions: z.enum(['read-only', 'host-confirmed']).optional(),
  wide: z.boolean().optional()
})

export type EphemeralCard = z.infer<typeof ephemeralCardSchema>

export type EphemeralFence =
  | { kind: 'ready'; cards: EphemeralCard[] }
  | { kind: 'invalid'; reason: 'json' | 'empty' | 'tooMany' | 'oversized' | 'card'; detail?: string }

/** Parse an ```ephemeral-ui fence: one card object, an array of them, or
 *  `{ "cards": [...] }`. Everything is validated before anything renders. */
export function parseEphemeralFence(code: string): EphemeralFence {
  if (new TextEncoder().encode(code).byteLength > MAX_FENCE_BYTES) {
    return { kind: 'invalid', reason: 'oversized' }
  }

  let raw: unknown

  try {
    raw = JSON.parse(code)
  } catch {
    return { kind: 'invalid', reason: 'json' }
  }

  const list = Array.isArray(raw)
    ? raw
    : raw && typeof raw === 'object' && Array.isArray((raw as { cards?: unknown }).cards)
      ? (raw as { cards: unknown[] }).cards
      : [raw]

  if (list.length === 0) {
    return { kind: 'invalid', reason: 'empty' }
  }

  if (list.length > MAX_CARDS) {
    return { kind: 'invalid', reason: 'tooMany' }
  }

  const cards: EphemeralCard[] = []

  for (const item of list) {
    const parsed = ephemeralCardSchema.safeParse(item)

    if (!parsed.success) {
      const kind = item && typeof item === 'object' ? String((item as { kind?: unknown }).kind ?? '') : ''

      return { kind: 'invalid', reason: 'card', detail: kind.slice(0, 40) }
    }

    cards.push(parsed.data)
  }

  return { kind: 'ready', cards }
}

/** Prefix of the hidden user turn a card intent becomes. Says what it is so
 *  the agent never mistakes a click for typed instructions or an approval. */
export const INTENT_PREFIX = 'ephemeral-ui card intent (the user clicked a card control; a request, not an approval): '

// The kit ships its own token copies of the desktop skins (data/themes.json:
// "Hermes desktop <skin>"). Light skins other than Nous have no kit copy.
const KIT_DARK_SKINS = new Set(['nous', 'midnight', 'ember', 'mono', 'cyberpunk', 'slate'])

/** The kit theme for the app's active skin and light/dark mode: the same
 *  skin when the kit has it, else the kit's Nous light / Mono dark. */
export function kitTheme(scheme: 'light' | 'dark', skin = ''): string {
  if (scheme === 'light') {
    return 'hermes-nous'
  }

  if (skin === 'nous') {
    return 'hermes-nous-dark'
  }

  return KIT_DARK_SKINS.has(skin) ? `hermes-${skin}` : 'hermes-mono'
}

const jsonInScript = (text: string) => text.replace(/</g, '\\u003c')

/** The frame document: kit CSS, embedded data files, config, then the
 *  bundled runtime. Pure, so tests can assert on exactly what ships. */
export function ephemeralFrameDocument({
  cards,
  chrome,
  css,
  files,
  runtime,
  scheme,
  skin
}: {
  cards: EphemeralCard[]
  /** The host's size + intent scripts (inline-preview-directive), last. */
  chrome: string
  css: string
  files: Record<string, string>
  runtime: string
  scheme: 'light' | 'dark'
  /** The app's active skin (`data-hermes-theme`). */
  skin?: string
}): string {
  const config = { cards, intentPrefix: INTENT_PREFIX, theme: kitTheme(scheme, skin) }
  const data = Object.entries(files)
    .map(([name, text]) => `<script type="application/json" data-eui-file="${name}">${jsonInScript(text)}</script>`)
    .join('')

  return (
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<style>${css.replace(/<\/style/gi, '<\\/style')}</style>` +
    '<style>html,body{background:transparent!important;margin:0;overflow:hidden}' +
    '#eui-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px;padding:2px}' +
    '#eui-grid>.eui-cell.wide{grid-column:1/-1}#eui-grid>.eui-cell>.eu-card{margin:0;max-width:none}' +
    '.eui-error{font:12px/1.4 system-ui;color:#b42318;padding:8px}</style>' +
    '</head><body><div id="eui-grid"></div>' +
    data +
    `<script type="application/json" id="eui-config">${jsonInScript(JSON.stringify(config))}</script>` +
    `<script>${runtime.replace(/<\/script/gi, '<\\/script')}</script>` +
    chrome +
    '</body></html>'
  )
}
