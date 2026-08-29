import { useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'

import type { MoaSlot, MoaState } from '@/lib/moa-orchestration'
import { thinkingOrbStateFor } from '@/lib/moa-orchestration'
import { cn } from '@/lib/utils'

const SIZE = 20

function Marker({ paused, slot }: { paused: boolean; slot: MoaSlot }) {
  return (
    <span
      className={cn(
        'relative inline-grid size-5 place-items-center',
        slot.status === 'queued' && 'text-gray-500',
        slot.status === 'complete' && 'text-emerald-500',
        slot.status === 'failed' && 'text-red-500',
        slot.status === 'interrupted' && 'text-amber-500'
      )}
      data-testid={`moa-marker-${slot.id}`}
    >
      <ThinkingOrb paused={paused} size={SIZE} state={thinkingOrbStateFor('advisor')} theme="auto" />
      {slot.status !== 'running' && slot.status !== 'queued' && (
        <span aria-hidden className="absolute size-1.5 rounded-full bg-current" />
      )}
    </span>
  )
}

export function MoaThinkingOrbs({ reducedMotion, state }: { reducedMotion: boolean; state: MoaState }) {
  const [open, setOpen] = useState(false)

  if (state.phase === 'idle') {
    return null
  }

  const settled = state.phase === 'settled'

  const summary = settled
    ? `${state.refsTotal} advisors → ${state.aggregatorLabel ?? 'aggregator'}`
    : `${state.refsDone}/${state.refsTotal} advisors → ${state.phase === 'aggregating' ? 'aggregating' : 'waiting'}`

  return (
    <div className="text-foreground" data-testid="moa-thinking-orbs">
      <div className="flex h-(--conversation-line-height) min-w-0 items-center gap-1.5 text-[length:var(--conversation-tool-font-size)]">
        <button
          aria-expanded={open}
          aria-label={`${open ? 'Collapse' : 'Expand'} MoA details`}
          className="flex min-w-0 items-center gap-1.5 text-left"
          onClick={() => setOpen(value => !value)}
          type="button"
        >
          <span className="font-medium">MoA</span>
          {!settled && (
            <span className="inline-flex gap-px" data-testid="moa-markers">
              {state.slots.map(slot => (
                <Marker key={slot.id} paused={reducedMotion} slot={slot} />
              ))}
            </span>
          )}
          <span aria-hidden>→</span>
          <ThinkingOrb
            paused={reducedMotion}
            size={SIZE}
            state={thinkingOrbStateFor(state.phase === 'aggregating' ? 'aggregator' : 'response')}
            theme="auto"
          />
          <span className="truncate">{summary}</span>
        </button>
      </div>
      <span aria-live="polite" className="sr-only" role="status">
        {`MoA ${state.refsDone} of ${state.refsTotal} advisors`}
      </span>
      {open && (
        <div className="ml-1 mt-0.5 text-xs" data-testid="moa-details">
          {state.slots.map(slot => (
            <div className="flex gap-2" key={slot.id}>
              <span>{slot.label ?? `advisor-${slot.id}`}</span>
              <span>{slot.status}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
