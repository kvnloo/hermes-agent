'use client'

import { useStore } from '@nanostores/react'
import { type FC, useLayoutEffect, useRef, useState } from 'react'

import { requestComposerInsertAcked } from '@/app/chat/composer/focus'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useI18n } from '@/i18n/context'

import { EphemeralCardFrame } from './card-frame'
import { ephemeralContextLine, type EphemeralIntent, type EphemeralMessage, ephemeralReceipt } from './model'
import { EphemeralMark } from './receipt'
import { $ephemeralCards, $openPin, $pinOrigin, type EphemeralCardRecord, noteEphemeralSummary, pinnedEphemeralCards, unpinEphemeralCard } from './store'

/**
 * Cards pinned to the input bar. Each collapses to a chip in the composer (app mark + its one-line
 * summary); clicking the chip opens the card in a popup above the bar. Renders nothing when empty.
 */
export const EphemeralPinnedBar: FC<{ sessionId: string | null }> = ({ sessionId }) => {
  const { t } = useI18n()
  const cards = pinnedEphemeralCards(useStore($ephemeralCards), sessionId)

  if (cards.length === 0) {
    return null
  }

  return (
    // The composer focuses its editor on any press inside it, which would close the chip's popup.
    <div
      aria-label={t.openui.kitPinnedBar}
      className="flex min-w-0 flex-wrap gap-1.5 px-2 pt-2"
      data-slot="ephemeral-pins"
      onPointerDown={event => event.stopPropagation()}
      role="toolbar"
    >
      {cards.map(card => (
        <PinnedChip card={card} key={card.id} />
      ))}
    </div>
  )
}

const PinnedChip: FC<{ card: EphemeralCardRecord }> = ({ card }) => {
  const { t } = useI18n()
  const chip = useRef<HTMLButtonElement>(null)
  // Held outside the component: the composer can re-mount its chrome while the popup is open.
  const open = useStore($openPin) === card.id
  const setOpen = (next: boolean) => $openPin.set(next ? card.id : $openPin.get() === card.id ? null : $openPin.get())
  const [intent, setIntent] = useState<EphemeralIntent | null>(null)
  const [added, setAdded] = useState<'idle' | 'added' | 'missing'>('idle')

  // The card collapses into its chip: a ghost of the card's box shrinks onto the chip.
  useLayoutEffect(() => {
    const origin = $pinOrigin.get()
    const to = chip.current?.getBoundingClientRect()

    if (!origin || origin.id !== card.id || !to) {
      return
    }

    $pinOrigin.set(null)

    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      return
    }

    const ghost = document.createElement('div')
    ghost.setAttribute('aria-hidden', 'true')
    ghost.style.cssText =
      `position:fixed;z-index:80;pointer-events:none;left:${origin.rect.left}px;top:${origin.rect.top}px;` +
      `width:${origin.rect.width}px;height:${origin.rect.height}px;border-radius:14px;` +
      'border:1px solid var(--ui-stroke-secondary);background:color-mix(in srgb,var(--ui-bg-elevated) 85%,transparent)'
    ghost.style.transformOrigin = '0 0'
    document.body.append(ghost)

    const move = ghost.animate(
      [
        { transform: 'none', opacity: 0.9 },
        {
          transform: `translate(${to.left - origin.rect.left}px, ${to.top - origin.rect.top}px) scale(${to.width / origin.rect.width}, ${to.height / origin.rect.height})`,
          opacity: 0.2
        }
      ],
      { duration: 460, easing: 'cubic-bezier(.3,.7,.2,1)', fill: 'forwards' }
    )

    move.onfinish = () => ghost.remove()
    chip.current?.animate([{ transform: 'scale(.85)' }, { transform: 'scale(1.06)', offset: 0.7 }, { transform: 'none' }], { delay: 380, duration: 260 })
  }, [card.id])

  const onMessage = (message: EphemeralMessage) => {
    if (message.type === 'intent' && message.intent.action === 'unpin') {
      setOpen(false)
      unpinEphemeralCard(card.id)
    } else if (message.type === 'intent' && message.intent.action !== 'pin') {
      setIntent(message.intent)
      setAdded('idle')
      noteEphemeralSummary(card.id, ephemeralReceipt(card, message.intent.label || message.intent.action))
    }
  }

  const addToChat = async () => {
    const line = ephemeralContextLine(card, intent ? intent.label || intent.action : card.summary, intent?.ids ?? [`card:${card.kind}`])
    setAdded((await requestComposerInsertAcked(line, { mode: 'block', target: 'main' })) ? 'added' : 'missing')
  }

  return (
    <Popover onOpenChange={setOpen} open={open}>
      <PopoverTrigger asChild>
        <button
          aria-label={`${card.appName}: ${card.summary}`}
          className="inline-flex max-w-64 items-center gap-1.5 rounded-full border border-(--ui-stroke-tertiary) bg-muted/50 py-0.5 pr-2.5 pl-1 text-xs text-foreground hover:bg-accent data-[state=open]:bg-accent"
          data-ephemeral-pin={card.kind}
          ref={chip}
          type="button"
        >
          <EphemeralMark card={card} size={18} />
          <span className="min-w-0 truncate">{card.summary}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-[min(28rem,calc(100vw-2rem))] space-y-1.5 p-2"
        // Add to chat focuses the composer; the card stays open until a click elsewhere or Escape.
        onFocusOutside={event => event.preventDefault()}
        side="top"
      >
        <EphemeralCardFrame app={card.app} kind={card.kind} onMessage={onMessage} pinned title={`${card.appName} card (pinned)`} />
        <div aria-live="polite" className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-muted-foreground">
          <p className="min-w-0 flex-1">
            {intent ? t.openui.kitPicked.replace('{what}', intent.label || intent.action) : t.openui.kitIdle}
            {added === 'added' && <> · {t.openui.kitAdded}</>}
            {added === 'missing' && <> · {t.openui.kitNoComposer}</>}
          </p>
          {added !== 'added' && (
            <Button onClick={() => void addToChat()} size="sm" variant="outline">
              {t.openui.kitAddToChat}
            </Button>
          )}
          <Button
            onClick={() => {
              setOpen(false)
              unpinEphemeralCard(card.id)
            }}
            size="sm"
            variant="ghost"
          >
            {t.openui.kitUnpin}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}
