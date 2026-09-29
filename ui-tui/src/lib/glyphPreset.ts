/**
 * Global chrome glyph preset (`display.tui_glyph_preset`).
 *
 * Terminal-compatibility layer beneath busy-indicator animation
 * (`display.tui_status_indicator` remains animation/style only).
 *
 * Presets: `nerd | unicode | ascii`
 * - One shared table covers disclosure, status marks, tree rails,
 *   tool-card chrome, and process/agent status glyphs.
 * - `ascii` emits zero non-ASCII chrome (no tofu at call sites).
 * - Call sites resolve through `chromeGlyph` / the process+agent helpers
 *   rather than feature-specific literals.
 */

export const GLYPH_PRESETS = ['nerd', 'unicode', 'ascii'] as const
export type GlyphPreset = (typeof GLYPH_PRESETS)[number]
export const DEFAULT_GLYPH_PRESET: GlyphPreset = 'unicode'

/** Runtime active preset — `applyDisplay` updates this so existing call sites
 * that omit an explicit preset still re-render when config changes. */
let activeGlyphPreset: GlyphPreset = DEFAULT_GLYPH_PRESET

export const getActiveGlyphPreset = (): GlyphPreset => activeGlyphPreset

export const setActiveGlyphPreset = (preset: GlyphPreset): void => {
  activeGlyphPreset = preset
}

export type ChromeGlyphKey =
  | 'disclosure.collapsed'
  | 'disclosure.expanded'
  | 'status.running'
  | 'status.success'
  | 'status.failure'
  | 'status.skipped'
  | 'status.warn'
  | 'status.queued'
  | 'status.unknown'
  | 'rail.vertical'
  | 'rail.branch'
  | 'rail.last'
  | 'rail.space'
  | 'tool.prefix'
  | 'busy.static'
  | 'process.running'
  | 'process.done'
  | 'process.failed'
  | 'process.killed'
  | 'process.lost'
  | 'agent.running'
  | 'agent.queued'
  | 'agent.dispatched'
  | 'agent.finalizing'
  | 'agent.completed'
  | 'agent.interrupted'
  | 'agent.cancelled'
  | 'agent.rejected'
  | 'agent.failed'
  | 'agent.timeout'
  | 'agent.error'

type GlyphTable = Record<ChromeGlyphKey, string>

// Nerd Font private-use glyphs (fa / md). Terminals without the font may
// tofu these; operators who pick `nerd` opt into that trade-off. Ascii
// and unicode remain the portable defaults.
const NERD: GlyphTable = {
  'disclosure.collapsed': '\uf054', // nf-fa-chevron_right
  'disclosure.expanded': '\uf078', // nf-fa-chevron_down
  'status.running': '\uf111', // nf-fa-circle
  'status.success': '\uf00c', // nf-fa-check
  'status.failure': '\uf00d', // nf-fa-times
  'status.skipped': '\uf068', // nf-fa-minus
  'status.warn': '\uf071', // nf-fa-exclamation_triangle
  'status.queued': '\uf10c', // nf-fa-circle_o
  'status.unknown': '\uf128', // nf-fa-question
  'rail.vertical': '│',
  'rail.branch': '├',
  'rail.last': '└',
  'rail.space': ' ',
  'tool.prefix': '┊',
  'busy.static': '\uf110', // nf-fa-spinner
  'process.running': '\uf013', // nf-fa-cog
  'process.done': '\uf00c',
  'process.failed': '\uf00d',
  'process.killed': '\uf00d',
  'process.lost': '?',
  'agent.running': '\uf111',
  'agent.queued': '\uf10c',
  'agent.dispatched': '\uf10c',
  'agent.finalizing': '\uf1ce', // nf-fa-circle_o_notch
  'agent.completed': '\uf00c',
  'agent.interrupted': '\uf04c', // nf-fa-pause
  'agent.cancelled': '\uf04c',
  'agent.rejected': '\uf05e', // nf-fa-ban
  'agent.failed': '\uf00d',
  'agent.timeout': '\uf017', // nf-fa-clock_o
  'agent.error': '\uf071'
}

const UNICODE: GlyphTable = {
  'disclosure.collapsed': '▸',
  'disclosure.expanded': '▾',
  'status.running': '●',
  'status.success': '✓',
  'status.failure': '✗',
  'status.skipped': '–',
  'status.warn': '!',
  'status.queued': '○',
  'status.unknown': '·',
  'rail.vertical': '│',
  'rail.branch': '├',
  'rail.last': '└',
  'rail.space': ' ',
  'tool.prefix': '┊',
  'busy.static': '◌',
  'process.running': '⚙',
  'process.done': '✔',
  'process.failed': '✘',
  'process.killed': '✘',
  'process.lost': '?',
  'agent.running': '●',
  'agent.queued': '○',
  'agent.dispatched': '○',
  'agent.finalizing': '◐',
  'agent.completed': '✓',
  'agent.interrupted': '■',
  'agent.cancelled': '■',
  'agent.rejected': '⊘',
  'agent.failed': '✗',
  'agent.timeout': '⌛',
  'agent.error': '⚠'
}

/** Pure ASCII chrome — every value is in the printable ASCII range. */
const ASCII: GlyphTable = {
  'disclosure.collapsed': '>',
  'disclosure.expanded': 'v',
  'status.running': '*',
  'status.success': '+',
  'status.failure': 'x',
  'status.skipped': '-',
  'status.warn': '!',
  'status.queued': 'o',
  'status.unknown': '.',
  'rail.vertical': '|',
  'rail.branch': '+',
  'rail.last': '\\',
  'rail.space': ' ',
  'tool.prefix': '|',
  'busy.static': '*',
  'process.running': '*',
  'process.done': '+',
  'process.failed': 'x',
  'process.killed': 'x',
  'process.lost': '?',
  'agent.running': '*',
  'agent.queued': 'o',
  'agent.dispatched': 'o',
  'agent.finalizing': 'o',
  'agent.completed': '+',
  'agent.interrupted': '#',
  'agent.cancelled': '#',
  'agent.rejected': '!',
  'agent.failed': 'x',
  'agent.timeout': 'T',
  'agent.error': '!'
}

export const GLYPH_TABLES: Record<GlyphPreset, GlyphTable> = {
  ascii: ASCII,
  nerd: NERD,
  unicode: UNICODE
}

export const CHROME_GLYPH_KEYS = Object.keys(UNICODE) as ChromeGlyphKey[]

const PRESET_SET: ReadonlySet<GlyphPreset> = new Set(GLYPH_PRESETS)

export const normalizeGlyphPreset = (raw: unknown): GlyphPreset => {
  if (typeof raw !== 'string') {
    return DEFAULT_GLYPH_PRESET
  }

  const v = raw.trim().toLowerCase() as GlyphPreset

  return PRESET_SET.has(v) ? v : DEFAULT_GLYPH_PRESET
}

/** True iff every code point is printable ASCII (0x20–0x7E). */
export const isAsciiChrome = (s: string): boolean => {
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i)
    if (c < 0x20 || c > 0x7e) {
      return false
    }
  }

  return true
}

export const chromeGlyph = (key: ChromeGlyphKey, preset: GlyphPreset = getActiveGlyphPreset()): string =>
  GLYPH_TABLES[preset][key]

/** Snapshot helper for width-matrix smoke: one line of covered chrome. */
export const chromeSampleRow = (preset: GlyphPreset): string => {
  const g = (k: ChromeGlyphKey) => chromeGlyph(k, preset)

  return [
    g('disclosure.collapsed'),
    g('disclosure.expanded'),
    g('status.running'),
    g('status.success'),
    g('status.failure'),
    g('status.skipped'),
    g('rail.vertical'),
    g('rail.branch'),
    g('rail.last'),
    g('tool.prefix'),
    g('busy.static'),
    g('process.running'),
    g('process.done'),
    g('agent.completed'),
    g('agent.failed')
  ].join(' ')
}
