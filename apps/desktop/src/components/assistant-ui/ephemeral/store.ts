import { atom } from 'nanostores'

import { EPHEMERAL_PIN_LIMIT, type EphemeralMatch, ephemeralReceipt } from './model'

// Where each tool call's card is in its life. Keyed by tool call id and kept for the window's
// lifetime, so a turn that re-mounts (stored-turn bind, history refresh) shows the same phase
// instead of replaying the card.
//   live     the card is on screen under its tool row
//   receipt  its ring ran out (or the turn came from history): a one-line chip remains
//   pinned   the reader pinned it to the input bar: a chip there opens the card in a popup

export type EphemeralPhase = 'live' | 'receipt' | 'pinned'

export interface EphemeralCardRecord extends EphemeralMatch {
  id: string
  sessionId: string | null
  phase: EphemeralPhase
  summary: string
  pinnedAt: number
}

/** Where a card was on screen when it was pinned: the input bar chip grows from there. */
export interface PinOrigin {
  id: string
  rect: { left: number; top: number; width: number; height: number }
}

export const $ephemeralCards = atom<Record<string, EphemeralCardRecord>>({})
export const $pinOrigin = atom<PinOrigin | null>(null)
/** The pinned card whose popup is open on the input bar, if any. */
export const $openPin = atom<string | null>(null)

function update(id: string, patch: Partial<EphemeralCardRecord>): void {
  const current = $ephemeralCards.get()[id]

  if (current) {
    $ephemeralCards.set({ ...$ephemeralCards.get(), [id]: { ...current, ...patch } })
  }
}

/** First sight of a finished tool call that grows a card. A live turn starts it live; history starts as a receipt. */
export function noteEphemeralCard(id: string, match: EphemeralMatch, sessionId: string | null, live: boolean): void {
  if ($ephemeralCards.get()[id]) {
    return
  }

  $ephemeralCards.set({
    ...$ephemeralCards.get(),
    [id]: { ...match, id, sessionId, phase: live ? 'live' : 'receipt', summary: ephemeralReceipt(match), pinnedAt: 0 }
  })
}

export const noteEphemeralSummary = (id: string, summary: string) => summary && update(id, { summary })

export const dissolveEphemeralCard = (id: string) => update(id, { phase: 'receipt' })

/** Show a receipt's card again; it stays until the reader pins it or the ring runs out again. */
export const reopenEphemeralCard = (id: string) => update(id, { phase: 'live' })

export function pinEphemeralCard(id: string, origin?: PinOrigin['rect']): void {
  const card = $ephemeralCards.get()[id]

  if (!card || card.phase === 'pinned') {
    return
  }

  // A session keeps at most EPHEMERAL_PIN_LIMIT pins; the oldest goes back to being a receipt.
  const pinned = Object.values($ephemeralCards.get())
    .filter(entry => entry.phase === 'pinned' && entry.sessionId === card.sessionId)
    .sort((a, b) => a.pinnedAt - b.pinnedAt)

  for (const old of pinned.slice(0, Math.max(0, pinned.length - EPHEMERAL_PIN_LIMIT + 1))) {
    update(old.id, { phase: 'receipt' })
  }

  $pinOrigin.set(origin ? { id, rect: origin } : null)
  update(id, { phase: 'pinned', pinnedAt: Date.now() })
}

export function unpinEphemeralCard(id: string): void {
  if ($openPin.get() === id) {
    $openPin.set(null)
  }

  update(id, { phase: 'receipt' })
}

export function pinnedEphemeralCards(cards: Record<string, EphemeralCardRecord>, sessionId: string | null): EphemeralCardRecord[] {
  return Object.values(cards)
    .filter(card => card.phase === 'pinned' && card.sessionId === sessionId)
    .sort((a, b) => a.pinnedAt - b.pinnedAt)
}
