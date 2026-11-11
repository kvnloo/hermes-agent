'use client'

import { useAuiState } from '@assistant-ui/react'
import { useMemo, useRef } from 'react'

import type { RichFenceProps } from '@/components/assistant-ui/embeds/types'

import { EPHEMERAL_LIFETIME_MS, parseEphemeralFence } from './model'
import { EphemeralCardSlot } from './tool-card'

const FENCE_FRESH_MS = 30_000

/** Same fence text, same card: a re-mount (history refresh, stored-turn bind) keeps its phase. */
function fenceId(code: string): string {
  let hash = 0x811c9dc5

  for (let index = 0; index < code.length; index++) {
    hash = Math.imul(hash ^ code.charCodeAt(index), 0x01000193)
  }

  return `fence:${(hash >>> 0).toString(36)}:${code.length}`
}

/**
 * A card the agent chose to show (an `ephemeral-ui` fence): a cached kit card, or one it wrote. It
 * lives like a tool card: on screen while the turn runs, then its ring runs out and it dissolves into
 * a receipt unless the reader pins it. Anything that doesn't parse shows as the fence's source.
 */
export default function EphemeralFence({ code, source, streaming }: RichFenceProps) {
  const match = useMemo(() => (streaming ? null : parseEphemeralFence(code)), [code, streaming])
  const running = useAuiState(s => s.thread.isRunning)
  // The reply re-mounts when its stream is stored, so a ref alone forgets it was live: a fence in the
  // latest reply, written moments ago, is born live too (the same window a tool card gets).
  const recent = useAuiState(s => s.message.isLast && Date.now() - (s.message.createdAt?.getTime() ?? 0) < FENCE_FRESH_MS)
  const sawLive = useRef(false)
  sawLive.current ||= Boolean(streaming) || running || recent

  if (streaming) {
    return <div aria-hidden="true" className="my-2 h-24 animate-pulse rounded-xl border border-(--ui-stroke-tertiary) bg-muted/20 motion-reduce:animate-none" data-ephemeral-loading="" />
  }

  if (!match) {
    return <>{source}</>
  }

  return <EphemeralCardSlot born={sawLive.current} id={fenceId(code)} lifetimeMs={running ? null : EPHEMERAL_LIFETIME_MS} match={match} />
}
