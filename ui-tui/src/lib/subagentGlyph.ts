import type { Theme } from '../theme.js'
import type { SubagentProgress } from '../types.js'

import { chromeGlyph, DEFAULT_GLYPH_PRESET, getActiveGlyphPreset, type GlyphPreset, type ChromeGlyphKey } from './glyphPreset.js'

// Shared status→glyph lookup for the subagent surfaces. Extracted so the
// docked agents panel and the full /agents overlay render identical glyphs
// and colours — a single source of truth prevents visual drift between them.
// Glyphs resolve through the shared `display.tui_glyph_preset` table.

export type SubagentStatus = SubagentProgress['status']

/** Background async delegations carry their own lifecycle vocabulary
 * (`dispatched → running → finalizing → completed|error`, plus `rejected`
 * when the capacity gate refuses one). They render through the same table so
 * a background row never falls through to the unknown-status glyph. */
export type AgentStatus = 'cancelled' | 'dispatched' | 'finalizing' | 'rejected' | SubagentStatus

const AGENT_KEY: Record<AgentStatus, ChromeGlyphKey> = {
  running: 'agent.running',
  queued: 'agent.queued',
  dispatched: 'agent.dispatched',
  finalizing: 'agent.finalizing',
  completed: 'agent.completed',
  interrupted: 'agent.interrupted',
  cancelled: 'agent.cancelled',
  rejected: 'agent.rejected',
  failed: 'agent.failed',
  timeout: 'agent.timeout',
  error: 'agent.error'
}

const AGENT_COLOR: Record<AgentStatus, (t: Theme) => string> = {
  running: t => t.color.accent,
  queued: t => t.color.muted,
  dispatched: t => t.color.muted,
  finalizing: t => t.color.accent,
  completed: t => t.color.statusGood,
  interrupted: t => t.color.warn,
  cancelled: t => t.color.warn,
  rejected: t => t.color.warn,
  failed: t => t.color.error,
  timeout: t => t.color.warn,
  error: t => t.color.error
}

/** Legacy export: unicode-preset snapshot of the table (tests / call sites
 * that still import the static map). Prefer `statusGlyph(..., preset)`. */
export const STATUS_GLYPH: Record<AgentStatus, { color: (t: Theme) => string; glyph: string }> =
  Object.fromEntries(
    (Object.keys(AGENT_KEY) as AgentStatus[]).map(status => [
      status,
      { color: AGENT_COLOR[status], glyph: chromeGlyph(AGENT_KEY[status], DEFAULT_GLYPH_PRESET) }
    ])
  ) as Record<AgentStatus, { color: (t: Theme) => string; glyph: string }>

/** Neutral fallback for a status this build has never heard of (an older or
 * newer daemon on the other end of the socket). Deliberately not the `error`
 * glyph: an unknown status is not a failure, and painting it red made healthy
 * rows look broken. */
const unknownGlyph = (preset: GlyphPreset) => ({
  color: (t: Theme) => t.color.muted,
  glyph: chromeGlyph('status.unknown', preset)
})

/** Resolve a status to its glyph + theme colour, with a defensive fallback for
 * cross-version snapshots carrying an unknown status. */
export const statusGlyph = (
  status: string,
  t: Theme,
  preset: GlyphPreset = getActiveGlyphPreset()
): { color: string; glyph: string } => {
  const key = AGENT_KEY[status as AgentStatus]
  if (!key) {
    const g = unknownGlyph(preset)

    return { color: g.color(t), glyph: g.glyph }
  }

  return { color: AGENT_COLOR[status as AgentStatus](t), glyph: chromeGlyph(key, preset) }
}
