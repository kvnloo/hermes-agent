// An ephemeral projection of Hermes's existing notification.show/clear events.
// Keys, expiration and limits live here; gateway settings and transcript remain authoritative.

import type { NotificationShowPayload } from '@hermes/shared/gateway-events'

export interface Dispatch {
  key: string
  serial: number
  text: string
  level: 'info' | 'warn' | 'error' | 'success'
  expiresAt: number | null
}

const DEFAULT_TTL_MS = 6_000
const MAX_TTL_MS = 60_000
const MAX_DISPATCHES = 8

/** Keyed notices; sticky entries survive until cleared, timed entries expire without user input. */
export class Dispatches {
  readonly #items = new Map<string, Dispatch>()
  readonly #held = new Map<string, NotificationShowPayload>()
  #serial = 0

  show(payload: NotificationShowPayload, now = Date.now(), hidden = false): void {
    const text = payload.text.trim()

    if (!text) {
      return
    }

    const key = payload.key?.trim() || payload.id?.trim() || `anonymous:${++this.#serial}`
    // A hidden pane must not lose a short notice before its user returns.
    // Hold only the latest value per key, bounded like the visible projection.
    if (hidden) {
      this.#items.delete(key)
      this.#held.delete(key)
      this.#held.set(key, { ...payload, key })
      while (this.#held.size > MAX_DISPATCHES) {
        this.#held.delete(this.#held.keys().next().value!)
      }

      return
    }

    this.#held.delete(key)
    const existing = this.#items.get(key)
    const ttl =
      typeof payload.ttl_ms === 'number' && Number.isFinite(payload.ttl_ms) && payload.ttl_ms > 0
        ? Math.min(payload.ttl_ms, MAX_TTL_MS)
        : DEFAULT_TTL_MS
    const note: Dispatch = {
      key,
      serial: existing?.serial ?? ++this.#serial,
      text,
      level: payload.level === 'warn' || payload.level === 'error' || payload.level === 'success' ? payload.level : 'info',
      expiresAt: payload.kind === 'sticky' ? null : now + ttl
    }

    this.#items.delete(key)
    this.#items.set(key, note)
    this.#prune(now)

    while (this.#items.size > MAX_DISPATCHES) {
      this.#items.delete(this.#items.keys().next().value!)
    }
  }

  clear(key: string): void {
    this.#items.delete(key)
    this.#held.delete(key)
  }

  /** Release deferred notices with fresh display TTL, only when Tern reports this pane visible. */
  resume(now = Date.now()): void {
    const held = [...this.#held.values()]
    this.#held.clear()

    for (const notice of held) {
      this.show(notice, now)
    }
  }

  reset(): void {
    this.#items.clear()
    this.#held.clear()
  }

  active(now = Date.now()): Dispatch[] {
    this.#prune(now)

    return [...this.#items.values()]
  }

  nextExpiry(now = Date.now()): number | null {
    this.#prune(now)
    let next: number | null = null

    for (const note of this.#items.values()) {
      if (note.expiresAt !== null && (next === null || note.expiresAt < next)) {
        next = note.expiresAt
      }
    }

    return next
  }

  #prune(now: number): void {
    for (const [key, note] of this.#items) {
      if (note.expiresAt !== null && note.expiresAt <= now) {
        this.#items.delete(key)
      }
    }
  }
}
