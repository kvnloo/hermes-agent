/**
 * Layout gate for the Ctrl+T / /agents roster (#113241).
 *
 * Normal terminals keep the parent transcript mounted under a
 * context-preserving overlay. Small terminals fall back to the existing
 * full-height swap so worker controls stay usable. Explicit expand always
 * forces full-height.
 */

export type AgentsLayoutMode = 'full' | 'overlay'

/** Rows below this cannot host a useful overlay + recognizable parent. */
export const AGENTS_OVERLAY_MIN_ROWS = 24

/** Columns below this clip worker controls / steer form. */
export const AGENTS_OVERLAY_MIN_COLS = 40

/** Fraction of terminal rows the context overlay claims (clamped). */
export const AGENTS_OVERLAY_HEIGHT_RATIO = 0.4

/** Floor rows reserved for recognizable parent transcript above the overlay. */
export const AGENTS_OVERLAY_PARENT_RESERVE = 6

export const overlayLayoutDecision = (
  rows: number,
  cols: number,
  expanded = false
): AgentsLayoutMode => {
  if (expanded) {
    return 'full'
  }

  if (rows < AGENTS_OVERLAY_MIN_ROWS || cols < AGENTS_OVERLAY_MIN_COLS) {
    return 'full'
  }

  return 'overlay'
}

/** Deterministic overlay card height for a terminal that passed the gate. */
export const agentsOverlayHeight = (rows: number): number => {
  const target = Math.floor(rows * AGENTS_OVERLAY_HEIGHT_RATIO)
  const max = Math.max(10, rows - AGENTS_OVERLAY_PARENT_RESERVE)

  return Math.max(10, Math.min(target, max))
}
