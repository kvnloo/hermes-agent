// The native dock is a projection of Hermes's latest todo.updated events.
// Keep one current plan per stored conversation; never mutate historical tool cards.

import type { Todo } from './model.js'

const MAX_CACHED_SESSIONS = 24

export class TodoHud {
  #active: string | null = null
  expanded = false
  readonly #plans = new Map<string, readonly Todo[]>()

  /** A new or resumed session selects its own last plan, never another session's. */
  adopt(key: string | null): void {
    if (this.#active !== key) {
      this.expanded = false
    }

    this.#active = key
  }

  /** The gateway remains authoritative; old tool-card snapshots are untouched. */
  update(todos: readonly Todo[]): void {
    const key = this.#active

    if (!key) {
      return
    }

    // Preserve the last event's ordering while bounding historical projection memory.
    this.#plans.delete(key)
    this.#plans.set(key, todos)

    while (this.#plans.size > MAX_CACHED_SESSIONS) {
      this.#plans.delete(this.#plans.keys().next().value!)
    }
  }

  /** Completed plans leave the dock after a turn; tool transcript keeps its history. */
  visible(turnRunning: boolean): readonly Todo[] {
    if (!this.#active) {
      return []
    }

    const plan = this.#plans.get(this.#active) ?? []

    if (!plan.length || (!turnRunning && plan.every(todo => todo.status === 'completed'))) {
      return []
    }

    return plan
  }
}
