import type { ProcessRow } from '../app/processRoster.js'
import type { Theme } from '../theme.js'

import { chromeGlyph, DEFAULT_GLYPH_PRESET, getActiveGlyphPreset, type ChromeGlyphKey, type GlyphPreset } from './glyphPreset.js'

// Status→glyph lookup for background-process rows; the docked panel and the
// /agents overlay render identical glyphs so the two never drift apart.
// Glyphs resolve through the shared `display.tui_glyph_preset` table.

const PROCESS_KEY: Record<ProcessRow['status'], ChromeGlyphKey> = {
  running: 'process.running',
  done: 'process.done',
  failed: 'process.failed',
  killed: 'process.killed',
  lost: 'process.lost'
}

const PROCESS_COLOR: Record<ProcessRow['status'], (t: Theme) => string> = {
  running: t => t.color.accent,
  done: t => t.color.statusGood,
  failed: t => t.color.error,
  killed: t => t.color.warn,
  lost: t => t.color.muted
}

/** Unicode-preset snapshot kept for call sites / tests that still import the
 * static map. Prefer `processGlyph(..., preset)`. */
export const PROCESS_GLYPH: Record<ProcessRow['status'], { color: (t: Theme) => string; glyph: string }> = {
  running: { color: PROCESS_COLOR.running, glyph: chromeGlyph('process.running', DEFAULT_GLYPH_PRESET) },
  done: { color: PROCESS_COLOR.done, glyph: chromeGlyph('process.done', DEFAULT_GLYPH_PRESET) },
  failed: { color: PROCESS_COLOR.failed, glyph: chromeGlyph('process.failed', DEFAULT_GLYPH_PRESET) },
  killed: { color: PROCESS_COLOR.killed, glyph: chromeGlyph('process.killed', DEFAULT_GLYPH_PRESET) },
  lost: { color: PROCESS_COLOR.lost, glyph: chromeGlyph('process.lost', DEFAULT_GLYPH_PRESET) }
}

export const processGlyph = (
  status: ProcessRow['status'],
  t: Theme,
  preset: GlyphPreset = getActiveGlyphPreset()
): { color: string; glyph: string } => ({
  color: PROCESS_COLOR[status](t),
  glyph: chromeGlyph(PROCESS_KEY[status], preset)
})
