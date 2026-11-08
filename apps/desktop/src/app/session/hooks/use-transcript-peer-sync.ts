import { type MutableRefObject, useEffect, useRef } from 'react'

import {
  hydrateStoredSessionTranscript,
  profileScopeForTranscriptSession,
  resolveActiveTranscriptSession
} from '@/app/contrib/hooks/use-background-sync'
import type { ClientSessionState } from '@/app/types'
import { $sessionTiles } from '@/store/session-states'
import { onTranscriptChanged } from '@/store/transcript-sync'

interface TranscriptPeerSyncOptions {
  activeSessionIdRef: MutableRefObject<string | null>
  busyRef: MutableRefObject<boolean>
  selectedStoredSessionIdRef: MutableRefObject<string | null>
  updateSessionState: (
    sessionId: string,
    updater: (state: ClientSessionState) => ClientSessionState,
    storedSessionId?: string | null
  ) => ClientSessionState
}

/**
 * When another window finishes a turn on a stored session this window is
 * showing, re-pull that transcript. The completing window does not receive
 * its own broadcast. Submit still refuses if this pull has not landed yet.
 */
export function useTranscriptPeerSync({
  activeSessionIdRef,
  busyRef,
  selectedStoredSessionIdRef,
  updateSessionState
}: TranscriptPeerSyncOptions): void {
  // Multiple completed-turn broadcasts can arrive before the first persisted
  // transcript read returns. Keep only the newest snapshot per runtime: an
  // earlier response would otherwise overwrite the later one on arrival.
  const refreshSequenceByRuntimeRef = useRef(new Map<string, number>())
  // A peer notification may wait for foreground hydration before touching its
  // tiles. Give it a generation at receipt, before any asynchronous reads.
  const peerBroadcastSequenceRef = useRef(0)

  useEffect(() => {
    let cancelled = false

    const latestRefresh = (runtimeId: string, sequence: number) => {
      const previous = refreshSequenceByRuntimeRef.current.get(runtimeId) ?? 0

      if (sequence > previous) {
        refreshSequenceByRuntimeRef.current.set(runtimeId, sequence)
      }

      return () => !cancelled && refreshSequenceByRuntimeRef.current.get(runtimeId) === sequence
    }

    const unsubscribe = onTranscriptChanged(payload => {
      const storedSessionId = payload.sessionId

      if (!storedSessionId) {
        return
      }

      const sequence = ++peerBroadcastSequenceRef.current
      void (async () => {
        const selected = selectedStoredSessionIdRef.current
        const runtimeId = activeSessionIdRef.current

        if (!cancelled && selected === storedSessionId && runtimeId && !busyRef.current) {
          await hydrateStoredSessionTranscript({
            attempts: 1,
            isCurrent: latestRefresh(runtimeId, sequence),
            runtimeSessionId: runtimeId,
            storedProfile: profileScopeForTranscriptSession(resolveActiveTranscriptSession(storedSessionId, runtimeId)),
            storedSessionId,
            updateSessionState
          })
        }

        if (cancelled) {
          return
        }

        for (const tile of $sessionTiles.get()) {
          if (tile.storedSessionId !== storedSessionId || !tile.runtimeId || tile.runtimeId === runtimeId) {
            continue
          }

          const owner = tile.ownerRoute
            ? { ownerRoute: tile.ownerRoute, profile: tile.ownerProfile ?? tile.ownerRoute.profile }
            : tile.ownerProfile
              ? { profile: tile.ownerProfile }
              : resolveActiveTranscriptSession(storedSessionId, tile.runtimeId)

          await hydrateStoredSessionTranscript({
            attempts: 1,
            isCurrent: latestRefresh(tile.runtimeId, sequence),
            runtimeSessionId: tile.runtimeId,
            storedProfile: profileScopeForTranscriptSession(owner),
            storedSessionId,
            updateSessionState
          })

          if (cancelled) {
            return
          }
        }
      })()
    })

    return () => {
      cancelled = true
      unsubscribe()
    }
  }, [activeSessionIdRef, busyRef, selectedStoredSessionIdRef, updateSessionState])
}
