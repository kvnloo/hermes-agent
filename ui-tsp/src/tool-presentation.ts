import type { Entry, ToolCall } from './model.js'
import { record } from './transcript.js'
import { runState } from './view/runbox.js'
import { toolFoldState } from './view/tools.js'

/** Only successful, fully settled work may disappear or enter a host work fold. */
export function settledTool(call: ToolCall): boolean {
  return runState(call, record(call.result)) === 'ok' && call.status === 'done' && (call.subagents ?? []).every(agent => agent.status === 'done')
}

/** Presentation intents, never a second copy of gateway tool data. */
export class ToolPresentation {
  readonly #folds = new Map<string, boolean>()
  readonly #revisions = new Map<string, number>()
  #expanded = false
  hidden = false
  revision = 0

  reset(): void {
    this.#folds.clear()
    this.#revisions.clear()
  }

  foldRevision(turn: string): number {
    return this.revision + (this.#revisions.get(turn) ?? 0)
  }

  collapsed(turn: string, call: string): boolean | undefined {
    return this.#folds.get(`${turn}:${call}`) ?? (this.#expanded ? false : undefined)
  }

  mirror(turn: string, call: string, collapsed: boolean): void {
    this.#folds.set(`${turn}:${call}`, collapsed)
    this.#revisions.set(turn, (this.#revisions.get(turn) ?? 0) + 1)
  }

  toggle(turn: string, call: ToolCall, cwd: string, media: boolean): void {
    this.mirror(turn, call.id, !(this.collapsed(turn, call.id) ?? toolFoldState(call, cwd, media).collapsed))
  }

  expand(entries: readonly Entry[], cwd: string, media: boolean): void {
    const calls = entries.flatMap(entry => entry.kind === 'turn'
      ? entry.blocks.flatMap(block => block.kind === 'tool' && toolFoldState(block.call, cwd, media).collapsible
        ? [{ turn: entry.id, call: block.call }] : []) : [])

    // Mixed pointer folds expand together; the next invocation collapses together.
    const expand = calls.length ? calls.some(({ turn, call }) => this.collapsed(turn, call.id) ?? toolFoldState(call, cwd, media).collapsed) : !this.#expanded
    this.#expanded = expand
    this.#folds.clear()

    for (const { turn, call } of calls) {
      this.#folds.set(`${turn}:${call.id}`, !expand)
    }

    this.revision++
  }

  toggleVisibility(): void {
    this.hidden = !this.hidden
    this.revision++
  }
}
