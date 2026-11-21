'use client'

import { type ToolCallMessagePartProps, useAuiState } from '@assistant-ui/react'
import { useStore } from '@nanostores/react'
import { type FC, type ReactNode, useEffect, useLayoutEffect, useRef, useState } from 'react'

import { requestComposerInsertAcked } from '@/app/chat/composer/focus'
import { useSessionView } from '@/app/chat/session-view'
import { ToolFallback } from '@/components/assistant-ui/tool/fallback'
import { toolCallFailed } from '@/components/assistant-ui/tool/fallback-model'
import { Button } from '@/components/ui/button'
import { useI18n } from '@/i18n/context'

import { EphemeralCardFrame } from './card-frame'
import { EPHEMERAL_LIFETIME_MS, ephemeralContextLine, type EphemeralIntent, type EphemeralMatch, type EphemeralMessage, ephemeralReceipt } from './model'
import { EphemeralReceipt } from './receipt'
import {
  $ephemeralCards,
  dissolveEphemeralCard,
  noteEphemeralCard,
  noteEphemeralSummary,
  pinEphemeralCard,
  reopenEphemeralCard
} from './store'

type ToolCallProps = ToolCallMessagePartProps & { completedAt?: number; timestamp?: number }

/** A call that returned this recently still grows a live card even if the turn already ended. */
const FRESH_MS = 30_000

const reducedMotion = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/**
 * A tool call on a known app's MCP server: the usual tool row, then the app's card growing out of it.
 * The card stays while its task runs. Once the agent moves on (a later tool call, or the turn ends)
 * its ring starts; when it runs out the card dissolves into a one-line receipt. Pinning moves it to
 * the input bar instead.
 */
export const EphemeralToolCall: FC<ToolCallProps & { match: EphemeralMatch; row?: ReactNode }> = ({ match, row, ...props }) => {
  const id = props.toolCallId
  // Interim text seals each step into its own assistant message, so liveness is the thread's.
  const running = useAuiState(s => s.thread.isRunning)

  // The agent moved on once anything follows this call: a later part here, or a later message.
  const movedOn = useAuiState(s => {
    if (!s.message.isLast) {
      return true
    }

    const parts = s.message.content as readonly { type: string; toolCallId?: string }[]
    const index = parts.findIndex(part => part.type === 'tool-call' && part.toolCallId === id)

    return index >= 0 && parts.slice(index + 1).some(part => part.type === 'tool-call' || part.type === 'text')
  })

  const settled = props.result !== undefined && !toolCallFailed(props)

  // A card is born when its call returns: live while the turn runs or just after (the last step can
  // land with the final reply), a receipt when the call is history.
  const completedAt = props.completedAt
  const fresh = typeof completedAt === 'number' && Date.now() - completedAt * 1000 < FRESH_MS

  // The tool's usual row (the connector row when the gateway labelled the call).
  const toolRow = row ?? <ToolFallback {...props} />

  if (!settled) {
    return toolRow
  }

  return (
    <>
      {toolRow}
      <EphemeralCardSlot born={running || fresh} id={id} lifetimeMs={running && !movedOn ? null : EPHEMERAL_LIFETIME_MS} match={match} />
    </>
  )
}

/**
 * One card's place in the transcript, keyed by `id` (a tool call, or an agent-written fence): the live
 * card while its task runs, then the receipt chip it dissolves into. `born` = first seen during a live
 * turn (history starts as a receipt); `lifetimeMs` null keeps the ring waiting.
 */
export const EphemeralCardSlot: FC<{ id: string; match: EphemeralMatch; born: boolean; lifetimeMs: number | null }> = ({ id, match, born, lifetimeMs }) => {
  const { t } = useI18n()
  const view = useSessionView()
  const sessionId = useStore(view.$runtimeId)
  const record = useStore($ephemeralCards)[id]

  useEffect(() => {
    noteEphemeralCard(id, match, sessionId, born)
  }, [born, id, match, sessionId])

  if (!record) {
    return null
  }

  return (
    <div className="mt-1.5 min-w-0" data-ephemeral-call={match.kind} data-ephemeral-phase={record.phase}>
      {record.phase === 'live' ? (
        <LiveCard lifetimeMs={lifetimeMs} match={match} toolCallId={id} />
      ) : (
        <EphemeralReceipt
          action={record.phase === 'receipt' ? t.openui.kitShow : undefined}
          card={record}
          note={record.phase === 'pinned' ? t.openui.kitPinned : undefined}
          onAction={() => reopenEphemeralCard(id)}
        />
      )}
    </div>
  )
}

type AddState = 'idle' | 'added' | 'missing'

const LiveCard: FC<{ match: EphemeralMatch; toolCallId: string; lifetimeMs: number | null }> = ({ match, toolCallId, lifetimeMs }) => {
  const { t } = useI18n()
  const shell = useRef<HTMLDivElement>(null)
  const [intent, setIntent] = useState<EphemeralIntent | null>(null)
  const [added, setAdded] = useState<AddState>('idle')

  // Container transform: the card grows down out of the tool row above it.
  useLayoutEffect(() => {
    if (!reducedMotion()) {
      shell.current?.animate(
        [
          { clipPath: 'inset(0 0 100% 0 round 12px)', transform: 'translateY(-6px)', opacity: 0.4 },
          { clipPath: 'inset(0 0 0 0 round 12px)', transform: 'none', opacity: 1 }
        ],
        { duration: 420, easing: 'cubic-bezier(.2,.8,.2,1)' }
      )
    }
  }, [])

  const pin = () => {
    const box = shell.current?.getBoundingClientRect()
    pinEphemeralCard(toolCallId, box && { left: box.left, top: box.top, width: box.width, height: box.height })
  }

  const onMessage = (message: EphemeralMessage) => {
    if (message.type === 'dissolved') {
      dissolveEphemeralCard(toolCallId)
    } else if (message.type === 'intent' && message.intent.action === 'pin') {
      pin()
    } else if (message.type === 'intent' && message.intent.action !== 'unpin') {
      setIntent(message.intent)
      setAdded('idle')
      noteEphemeralSummary(toolCallId, ephemeralReceipt(match, message.intent.label || message.intent.action))
    }
  }

  const addToChat = async () => {
    if (intent) {
      const line = ephemeralContextLine(match, intent.label || intent.action, intent.ids)
      setAdded((await requestComposerInsertAcked(line, { mode: 'block', target: 'main' })) ? 'added' : 'missing')
    }
  }

  return (
    <div className="min-w-0 space-y-1" ref={shell}>
      <EphemeralCardFrame lifetimeMs={lifetimeMs} match={match} onMessage={onMessage} title={`${match.appName} card`} />
      <div aria-live="polite" className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-muted-foreground">
        <p className="min-w-0 flex-1">
          {intent ? t.openui.kitPicked.replace('{what}', intent.label || intent.action) : t.openui.kitIdle}
          {added === 'added' && <> · {t.openui.kitAdded}</>}
          {added === 'missing' && <> · {t.openui.kitNoComposer}</>}
        </p>
        {intent && added !== 'added' && (
          <Button onClick={() => void addToChat()} size="sm" variant="outline">
            {t.openui.kitAddToChat}
          </Button>
        )}
        <Button onClick={pin} size="sm" variant="ghost">
          {t.openui.kitPin}
        </Button>
      </div>
    </div>
  )
}
