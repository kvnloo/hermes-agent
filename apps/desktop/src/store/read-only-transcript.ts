/**
 * Read-only stored-transcript resume — the no-owner recovery path (#94724).
 *
 * The fail-closed owner ladder is correct: a session-scoped RPC whose owner
 * nobody can name must NOT ride the ambient socket. But "fail closed" must
 * not mean "locked out of your own history": the transcripts of legacy
 * unowned rows sit fully intact in state.db, reachable over the id-only REST
 * read that needs no live-session routing at all.
 *
 * `resumeWithStoredTranscriptFallback` wraps a live `session.resume` dispatch
 * with exactly that recovery: when — and only when — the resume fails with
 * `SessionOwnerResolutionError` (owner genuinely unresolvable under registry
 * topology), it opens the stored transcript read-only instead of dead-ending.
 * Every other failure keeps its existing semantics. Rows whose owner IS
 * resolvable never take this path, and a later successful live resume (e.g.
 * after the single-match owner backfill stamps the row) clears the flag.
 */
import { atom } from 'nanostores'

import type { SessionOwnerResolutionError } from './session-owner-resolution'
import { isSessionOwnerResolutionError } from './session-owner-resolution'

/** Stored session ids currently open as read-only stored transcripts. The
 *  composer/submit surfaces consult this to refuse writes into a session
 *  that has no routable live runtime. */
export const $readOnlyStoredTranscripts = atom<ReadonlySet<string>>(new Set())

/** Bumped per stored id by every successful live resume (see
 *  `clearStoredTranscriptReadOnly`). A no-owner recovery snapshots it when its
 *  resume attempt starts; once it moved, the session was proven routable while
 *  the recovery was pending, so the recovery must not open it read-only. */
const liveResumeGenerationByStoredSessionId = new Map<string, number>()

export function liveResumeGeneration(storedSessionId: string): number {
  return liveResumeGenerationByStoredSessionId.get(storedSessionId.trim()) ?? 0
}

export function markStoredTranscriptReadOnly(storedSessionId: string): void {
  const id = storedSessionId.trim()

  if (!id || $readOnlyStoredTranscripts.get().has(id)) {
    return
  }

  $readOnlyStoredTranscripts.set(new Set([...$readOnlyStoredTranscripts.get(), id]))
}

export function clearStoredTranscriptReadOnly(storedSessionId: string): void {
  const id = storedSessionId.trim()

  if (!id) {
    return
  }

  // A live success counts even when the latch is not set yet: a recovery
  // that is still pending must not latch over it.
  liveResumeGenerationByStoredSessionId.set(id, liveResumeGeneration(id) + 1)

  if (!$readOnlyStoredTranscripts.get().has(id)) {
    return
  }

  const next = new Set($readOnlyStoredTranscripts.get())

  next.delete(id)
  $readOnlyStoredTranscripts.set(next)
}

export function isStoredTranscriptReadOnly(storedSessionId: null | string | undefined): boolean {
  return Boolean(storedSessionId && $readOnlyStoredTranscripts.get().has(storedSessionId.trim()))
}

/** Synthetic runtime-id namespace for read-only tiles: a stored transcript
 *  opened without a live runtime still needs a state-cache key, and this
 *  prefix guarantees it can never collide with (or be mistaken for) a real
 *  gateway runtime id. */
export const READ_ONLY_RUNTIME_ID_PREFIX = 'read-only:'

export function readOnlyRuntimeIdFor(storedSessionId: string): string {
  return `${READ_ONLY_RUNTIME_ID_PREFIX}${storedSessionId}`
}

export function isReadOnlyRuntimeId(runtimeId: null | string | undefined): boolean {
  return Boolean(runtimeId?.startsWith(READ_ONLY_RUNTIME_ID_PREFIX))
}

export type StoredTranscriptResumeOutcome<TResumed, TTranscript> =
  | { mode: 'live'; resumed: TResumed }
  | { error: SessionOwnerResolutionError; mode: 'read-only'; transcript: TTranscript }

/**
 * Dispatch a live resume, recovering into a read-only stored-transcript open
 * when the owner is unresolvable. `fetchStoredTranscript` must be an id-only
 * stored read (REST `/api/sessions/:id/messages`) that performs NO gateway
 * routing — that is the whole point of the recovery path.
 *
 * When even the stored read fails, the ORIGINAL owner-resolution error is
 * rethrown: the caller's existing error UX (retry latch, stranded screen)
 * stays authoritative and no misleading transport error replaces the real
 * diagnosis.
 *
 * `liveResumesAtStart` is the `liveResumeGeneration` snapshot taken when the
 * caller's attempt began (default: now). A caller that awaits before calling
 * (e.g. owner resolution) passes its own earlier snapshot.
 */
export async function resumeWithStoredTranscriptFallback<TResumed, TTranscript>(
  storedSessionId: string,
  resume: () => Promise<TResumed>,
  fetchStoredTranscript: () => Promise<TTranscript>,
  liveResumesAtStart = liveResumeGeneration(storedSessionId)
): Promise<StoredTranscriptResumeOutcome<TResumed, TTranscript>> {
  try {
    const resumed = await resume()

    // A live resume proves the owner is routable again (the backfill stamped
    // the row, or a topology change resolved it) — drop the read-only latch.
    clearStoredTranscriptReadOnly(storedSessionId)

    return { mode: 'live', resumed }
  } catch (error) {
    if (!isSessionOwnerResolutionError(error)) {
      throw error
    }

    let transcript: TTranscript

    try {
      transcript = await fetchStoredTranscript()
    } catch {
      throw error
    }

    // A live resume of this id succeeded while this attempt was pending: the
    // session is routable, so this stale recovery must not latch it.
    if (liveResumeGeneration(storedSessionId) === liveResumesAtStart) {
      markStoredTranscriptReadOnly(storedSessionId)
    }

    return { error, mode: 'read-only', transcript }
  }
}
