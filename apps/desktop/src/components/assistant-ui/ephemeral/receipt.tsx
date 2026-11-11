'use client'

import type { FC } from 'react'

import { cn } from '@/lib/utils'

import type { EphemeralMatch } from './model'

/** Readable ink on a brand colour (the kit's monogram tiles use the same split). */
function inkOn(hex: string | null): string {
  if (!hex) {
    return 'currentColor'
  }

  const n = Number.parseInt(hex.slice(1), 16)
  const [r, g, b] = [(n >> 16) & 255, (n >> 8) & 255, n & 255]

  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 150 ? '#111' : '#fff'
}

/** The app's monogram tile, in its brand colour (the kit ships monograms, not logos). */
export const EphemeralMark: FC<{ card: Pick<EphemeralMatch, 'appName' | 'hex'>; size?: number }> = ({ card, size = 16 }) => (
  <span
    aria-hidden="true"
    className={cn('inline-grid shrink-0 place-items-center rounded-[5px] font-semibold', !card.hex && 'bg-muted text-muted-foreground')}
    style={{
      width: size,
      height: size,
      fontSize: Math.round(size * 0.55),
      ...(card.hex ? { background: card.hex, color: inkOn(card.hex) } : {})
    }}
  >
    {card.appName.slice(0, 1)}
  </span>
)

interface EphemeralReceiptProps {
  card: Pick<EphemeralMatch, 'appName' | 'hex' | 'kind'> & { summary: string }
  note?: string
  action?: string
  onAction?: () => void
}

/** What a card leaves behind once it dissolves: one line, with a way to show the card again. */
export const EphemeralReceipt: FC<EphemeralReceiptProps> = ({ card, note, action, onAction }) => (
  <div
    className="inline-flex max-w-full items-center gap-2 rounded-full bg-muted/60 py-1 pr-1 pl-2 text-xs text-muted-foreground"
    data-ephemeral-receipt={card.kind}
  >
    <EphemeralMark card={card} />
    <span className="min-w-0 truncate">{card.summary}</span>
    {note && <span className="shrink-0 text-muted-foreground/80">· {note}</span>}
    {action && onAction && (
      <button className="shrink-0 rounded-full px-2 py-0.5 text-foreground hover:bg-accent" onClick={onAction} type="button">
        {action}
      </button>
    )}
  </div>
)
