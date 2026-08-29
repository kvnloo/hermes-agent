import { useState } from 'react'
import { ThinkingOrb } from 'thinking-orbs'

import { formatElapsed } from '@/components/chat/activity-timer'
import { DisclosureCaret } from '@/components/ui/disclosure-caret'
import { prefersReducedMotion } from '@/hooks/use-media-query'
import { useI18n } from '@/i18n'
import {
  type MoaAdvisorSlot,
  type MoaOrchestrationState,
  moaStatusAnnouncement,
  thinkingOrbStateFor
} from '@/lib/moa-orchestration'
import { cn } from '@/lib/utils'

const ADVISOR_ORB_SIZE = 20

function terminalFor(slot: MoaAdvisorSlot): MoaAdvisorSlot['status'] {
  return slot.status
}

function AdvisorMarker({
  reducedMotion,
  slot,
  theme
}: {
  reducedMotion: boolean
  slot: MoaAdvisorSlot
  theme: 'dark' | 'light'
}) {
  const terminal = terminalFor(slot)

  const clip =
    typeof slot.outputProgress === 'number'
      ? { clipPath: `inset(${Math.round((1 - Math.min(1, Math.max(0, slot.outputProgress))) * 100)}% 0 0 0)` }
      : undefined

  return (
    <span
      className={cn(
        'relative inline-flex size-5 items-center justify-center',
        terminal === 'complete' && 'text-emerald-500',
        terminal === 'failed' && 'text-red-500',
        terminal === 'interrupted' && 'text-amber-500',
        terminal === 'queued' && 'text-(--ui-text-tertiary)'
      )}
      data-terminal={terminal}
      style={clip}
    >
      <ThinkingOrb
        paused={reducedMotion}
        size={ADVISOR_ORB_SIZE}
        state={thinkingOrbStateFor({ kind: 'advisor', status: slot.status })}
        theme={theme}
      />
      {(terminal === 'complete' || terminal === 'failed' || terminal === 'interrupted') && (
        <span aria-hidden className="pointer-events-none absolute inset-0 grid place-items-center">
          <span className="size-2 rounded-full bg-current" />
        </span>
      )}
    </span>
  )
}

export function MoaThinkingOrbs({
  elapsedSeconds,
  reducedMotion,
  state,
  theme = 'dark'
}: {
  elapsedSeconds?: number
  reducedMotion?: boolean
  state: MoaOrchestrationState
  theme?: 'dark' | 'light'
}) {
  const { t } = useI18n()
  const copy = t.assistant.thread.moa
  const [open, setOpen] = useState(false)
  const [openSlotId, setOpenSlotId] = useState<string | null>(null)
  const reduceMotion = reducedMotion ?? prefersReducedMotion()
  const elapsed = elapsedSeconds ?? state.elapsedSeconds
  const announcement = moaStatusAnnouncement(state)

  const phaseOrb = thinkingOrbStateFor(
    state.phase === 'aggregating'
      ? { kind: 'aggregator', status: 'acting' }
      : state.aggregatorStatus === 'waiting'
        ? { kind: 'advisor', status: 'queued' }
        : { kind: 'planning' }
  )

  const phaseCopy =
    state.phase === 'settled'
      ? copy.settled(state.refsTotal || state.slots.length, state.aggregatorLabel ?? 'aggregator')
      : state.phase === 'aggregating'
        ? copy.aggregating
        : state.phase === 'reused'
          ? copy.reused
          : copy.waiting

  if (state.phase === 'idle') {
    return null
  }

  return (
    <div
      className="text-[length:var(--conversation-tool-font-size)] text-(--conversation-scaffold-text)"
      data-completion-bounce={reduceMotion ? 'off' : 'on'}
      data-conversation-scaffold=""
      data-footprint="inline"
      data-ink={theme === 'dark' ? 'light' : 'dark'}
      data-line-height="scaffold"
      data-slot="moa-thinking-orbs"
      data-testid="moa-thinking-orbs"
    >
      <div className="flex h-(--conversation-line-height) min-w-0 items-center gap-1.5">
        <button
          aria-expanded={open}
          aria-label={open ? copy.collapse : copy.expand}
          className="flex min-w-0 max-w-fit items-center gap-1.5 text-left hover:text-foreground"
          onClick={() => setOpen(value => !value)}
          type="button"
        >
          <span className="shrink-0 font-medium">{copy.label}</span>
          {state.parallel && <span>{copy.parallel}</span>}
          <span className="tabular-nums">{copy.advisors(state.refsDone, state.refsTotal)}</span>
          <span className="inline-flex items-center gap-px" data-testid="moa-advisor-markers">
            {state.slots.map(slot => (
              <AdvisorMarker key={slot.id} reducedMotion={reduceMotion} slot={slot} theme={theme} />
            ))}
          </span>
          <span aria-hidden>→</span>
          <ThinkingOrb paused={reduceMotion} size={ADVISOR_ORB_SIZE} state={phaseOrb} theme={theme} />
          <span className="min-w-0 truncate">{phaseCopy}</span>
          {elapsed !== undefined && state.phase !== 'settled' && (
            <span className="shrink-0 text-[0.625rem] tabular-nums text-(--conversation-scaffold-meta)">
              {formatElapsed(Math.round(elapsed))}
            </span>
          )}
          <DisclosureCaret open={open} />
        </button>
      </div>
      <span aria-live="polite" className="sr-only" role="status">
        {announcement}
      </span>
      {open && (
        <div className="mt-0.5 flex flex-col gap-0.5" data-testid="moa-thinking-orbs-details">
          {state.slots.map(slot => {
            const label = slot.label ?? `#${slot.index}`
            const expanded = openSlotId === slot.id

            return (
              <div key={slot.id}>
                <button
                  className="flex w-full items-center gap-1.5 text-left text-[0.7rem]"
                  onClick={() => setOpenSlotId(expanded ? null : slot.id)}
                  type="button"
                >
                  <span className="truncate">{label}</span>
                  <span className="text-(--conversation-scaffold-meta)">{slot.status}</span>
                </button>
                {expanded && slot.output && (
                  <pre className="mt-0.5 whitespace-pre-wrap text-[0.65rem]" data-testid="moa-advisor-output">
                    {slot.output}
                  </pre>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
