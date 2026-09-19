/**
 * Forced wake-reconnect coalescing for Desktop (#94769 / #115701).
 *
 * Windows/macOS often fire power-resume and `window 'online'` seconds apart.
 * Each forced wake closes and re-probes secondary sockets, so an unthrottled
 * handler churns healthy connections. Main already coalesces power-resume
 * revalidation behind POWER_RESUME_REVALIDATION_HOLDOFF_MS; this is the
 * renderer twin.
 *
 * Required shape (leading edge + coalesced trailing edge):
 *
 *   first wake inside a quiet window
 *     → force recovery immediately
 *
 *   one or more additional wakes inside the holdoff
 *     → run the cheap nudge only
 *     → mark exactly one trailing forced recovery pending
 *
 *   holdoff expires
 *     → fire exactly one trailing forced recovery
 *
 * Dropping mid-holdoff wakes without a trailing edge strands a transport that
 * went half-open after the leading recovery succeeded.
 *
 * Pure and Electron-free so the boundaries are assertable with a fake clock.
 */

/** Renderer twin of main's POWER_RESUME_REVALIDATION_HOLDOFF_MS. */
export const WAKE_RECONNECT_HOLDOFF_MS = 15_000

export type WakeForcedReconnectDecision =
  | {
      /** Leading edge (or holdoff already expired): force open sockets now. */
      kind: 'force-now'
      /** Stamp this as lastForcedAt after dispatching. */
      nextLastForcedAt: number
      /** Clear any pending trailing timer — the leading edge absorbs it. */
      cancelTrailing: true
    }
  | {
      /** Inside holdoff: cheap nudge only; optionally arm one trailing force. */
      kind: 'nudge-only'
      scheduleTrailing: boolean
      /** Absolute time when the trailing force should fire (lastForcedAt + holdoff). */
      trailingDueAt: number
    }

export interface WakeForcedReconnectInput {
  now: number
  /** null when no forced wake has run yet in this boot (0 is a valid stamp). */
  lastForcedAt: number | null
  /** True when a trailing forced recovery is already armed. */
  trailingPending: boolean
  holdoffMs?: number
}

export function decideWakeForcedReconnect(input: WakeForcedReconnectInput): WakeForcedReconnectDecision {
  const holdoffMs = Math.max(0, Math.floor(input.holdoffMs ?? WAKE_RECONNECT_HOLDOFF_MS))
  const now = Number.isFinite(input.now) ? input.now : 0
  const lastForcedAt =
    input.lastForcedAt === null || !Number.isFinite(input.lastForcedAt)
      ? null
      : Math.max(0, input.lastForcedAt)
  const holdoffExpired = lastForcedAt === null || now - lastForcedAt >= holdoffMs

  if (holdoffExpired) {
    return {
      kind: 'force-now',
      nextLastForcedAt: now,
      cancelTrailing: true
    }
  }

  // Holdoff still open ⇒ lastForcedAt is a concrete stamp.
  return {
    kind: 'nudge-only',
    scheduleTrailing: !input.trailingPending,
    trailingDueAt: (lastForcedAt as number) + holdoffMs
  }
}

/**
 * Decision for a trailing timer that just fired. Always forces once; the
 * caller is responsible for clearing `trailingPending` and updating
 * `lastForcedAt`.
 */
export function decideTrailingWakeForcedReconnect(now: number): Extract<
  WakeForcedReconnectDecision,
  { kind: 'force-now' }
> {
  return {
    kind: 'force-now',
    nextLastForcedAt: Number.isFinite(now) ? now : 0,
    cancelTrailing: true
  }
}
