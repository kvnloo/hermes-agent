// Incremental main children over public SDK primitives. See RETENTION.md.
import {
  type Dispatch,
  Node,
  node,
  type Op,
  Surface,
  Tree,
  type TspEvent,
  View,
  type ViewInput
} from '@stencil-hq/tern'

import type { Entry } from './model.js'
import type { Transcript } from './transcript.js'
import { entryNode, forgetEntryNode, type TranscriptContext } from './view/transcript.js'

export const RETAIN_TURNS = 20
export const RELOAD_PAGE = 40
const LOAD_ID = 'main.retention-load'

interface RetainedEntry {
  entry: Entry
  index: number
  settled: boolean
  evicted: boolean
  tree?: Tree
}

/** No terminal reload/scroll event exists in SDK 0.1; reload is an explicit intent. */
export class Retention {
  readonly #entries = new Map<string, RetainedEntry>()
  readonly #hot = new Set<RetainedEntry>()
  #structure = -1
  #context = ''
  readonly #evicted = new Set<RetainedEntry>()
  /** The requested page must survive the budget pass that evicted it in the first place. */
  #reading = new Set<RetainedEntry>()
  #loadShown = false
  #reload = false
  #reveal = false
  #cx: TranscriptContext | undefined
  #transcript: Transcript | undefined
  #chromeOps: readonly Op[] = []
  readonly #chrome = new Surface(
    {
      send: message => {
        if (message.verb === 'f') {
          this.#chromeOps = message.body.ops
        }
      },
      credits: () => 1,
      dropped() {}
    },
    'hermes',
    { listen: false }
  )

  /** Build chrome through the SDK, then send history and chrome atomically under real credits. */
  paint(surface: Surface, view: ViewInput, history: readonly Op[]): void {
    this.#chromeOps = []
    this.#chrome.render(view)
    const ops = [...this.#chromeOps, ...history]

    if (ops.length) {
      surface.send(ops)
    }
  }

  request(reveal = false): void {
    this.#reload = true
    this.#reveal ||= reveal
  }

  invalidate(id: string): void {
    const item = this.#entries.get(`main.${id}`)

    if (item) {
      this.#hot.add(item)
    }
  }

  gone(event: TspEvent, surface: string): void {
    if (event.ev !== 'gone' || event.sf !== surface) {
      return
    }

    for (const id of event.ids) {
      const item = this.#entries.get(id)

      if (!item?.settled) {
        continue
      }

      item.evicted = true
      this.#evicted.add(item)
      item.tree = undefined
      forgetEntryNode(item.entry)
    }
  }

  /** Main routing is rebuilt on gestures, never kept in a historical closure cache. */
  dispatch(event: TspEvent, surface: string, changed: () => void): Dispatch | undefined {
    if (!('sf' in event) || event.sf !== surface) {
      return
    }

    if (!('id' in event) || !event.id?.startsWith('main.')) {
      return this.#chrome.dispatch(event)
    }

    if (event.id === LOAD_ID && event.ev === 'action' && event.act === 'click') {
      return () => {
        this.request()
        changed()
      }
    }

    if (event.ev !== 'action') {
      return
    }

    const id = event.id.split('.').slice(0, 2).join('.')
    const item = this.#entries.get(id)

    if (!item || item.evicted || !this.#cx) {
      return
    }

    return () => {
      if (
        this.#entries.get(id) !== item ||
        item.evicted ||
        !this.#cx ||
        !this.#transcript?.entries.includes(item.entry)
      ) {
        return
      }

      const router = new Surface({ send() {}, credits: () => 1, dropped() {} }, surface, { listen: false })
      router.render({ main: [entryNode(item.entry, id, this.#cx)] })
      const action = router.dispatch(event)

      if (item.settled) {
        forgetEntryNode(item.entry)
      }

      return action?.()
    }
  }

  /** Called once per permitted App build; returned ops share Surface's ACK queue. */
  render(transcript: Transcript, cx: TranscriptContext, hold: boolean): Op[] {
    this.#cx = cx
    this.#transcript = transcript
    const ops: Op[] = []
    const context = `${cx.cwd}:${cx.media}`
    const structural = this.#structure !== transcript.structureRev

    if (structural) {
      const current = new Set(transcript.entries)

      for (const [id, item] of this.#entries) {
        if (current.has(item.entry)) {
          continue
        }

        if (!item.evicted) {
          ops.push(['del', id])
        }

        forgetEntryNode(item.entry)
        this.#hot.delete(item)
        this.#evicted.delete(item)
        this.#reading.delete(item)
        this.#entries.delete(id)
      }

      transcript.entries.forEach((entry, index) => {
        const id = `main.${entry.id}`
        let item = this.#entries.get(id)

        if (!item) {
          item = { entry, index, settled: false, evicted: false }
          this.#entries.set(id, item)
        }

        item.index = index
      })
      this.#structure = transcript.structureRev
    }

    // Completion/structure work is linear once per turn, not once per token.
    const boundary = structural ? coldBoundary(transcript.entries) : undefined

    if (boundary !== undefined || context !== this.#context) {
      for (const item of this.#entries.values()) {
        if (!item.settled || item.index >= (boundary ?? 0) || !safeEntry(item.entry) || context !== this.#context) {
          this.#hot.add(item)
        }
      }
    }

    this.#context = context

    for (const entry of transcript.changedEntries) {
      const item = this.#entries.get(`main.${entry.id}`)

      if (item) {
        this.#hot.add(item)
      }
    }

    transcript.changedEntries.clear()

    // A page request adds only evicted entries; resident history is untouched.
    const reload = this.#reload ? [...this.#evicted].sort((a, b) => a.index - b.index).slice(-RELOAD_PAGE) : []

    this.#reload = false

    if (reload.length) {
      for (const item of this.#reading) {this.#hot.add(item)}
      this.#reading = new Set(reload)
    }

    for (const item of reload) {
      item.evicted = false
      this.#evicted.delete(item)
      this.#hot.add(item)
    }

    const cold = boundary ?? this.#boundary
    this.#boundary = cold
    const work = [...this.#hot].sort((a, b) => b.index - a.index)
    const restored = new Set(reload)

    for (const item of work) {
      const entry = item.entry
      const id = `main.${entry.id}`
      const settle = !hold && !this.#reading.has(item) && item.index < cold && safeEntry(entry) && safePrompt(item.index, transcript.entries)

      if (item.evicted && settle) {
        this.#hot.delete(item)

        continue
      }

      const wasEvicted = item.evicted
      item.evicted = false
      this.#evicted.delete(item)
      const element = entryNode(entry, id, cx)

      if (!(element instanceof Node)) {
        continue
      }

      const tree = new Tree(id, element)

      if (item.tree && !wasEvicted && !restored.has(item)) {
        ops.push(...new View([item.tree]).ops(new View([tree]), 'main'))
      } else {
        if (item.settled && !wasEvicted && !restored.has(item)) {
          ops.push(['del', id])
        }

        const before = this.#nextResident(item.index)
        ops.push(['add', id, 'main', before, tree.wire()])
      }

      item.tree = tree
      item.settled = settle

      if (settle) {
        ops.push(['settle', id])
        item.tree = undefined
        forgetEntryNode(entry)
        this.#hot.delete(item)
      }
    }

    const missing = this.#evicted.size > 0

    if (missing !== this.#loadShown) {
      if (missing) {
        const load = new Tree(
          LOAD_ID,
          node('text', {
            key: 'retention-load',
            role: 'omp.history.load',
            text: 'Load older history · Ctrl+Home',
            actions: { click: 'click' }
          })
        )

        const before = this.#firstResident()
        ops.push(['add', LOAD_ID, 'main', before, load.wire()])
      } else {
        ops.push(['del', LOAD_ID])
      }

      this.#loadShown = missing
    }

    if (this.#reveal) {
      ops.push(reload.length ? ['reveal', `main.${reload[0]!.entry.id}`, 'start'] : ['scroll', 'main', 'start'])
    }

    this.#reveal = false

    return ops
  }

  #boundary = 0

  #nextResident(index: number): string | null {
    const entries = this.#transcript?.entries ?? []

    for (let i = index + 1; i < entries.length; i++) {
      const id = `main.${entries[i]!.id}`

      if (!this.#entries.get(id)?.evicted) {
        return id
      }
    }

    return null
  }

  #firstResident(): string | null {
    return this.#nextResident(-1)
  }
}

function safeEntry(entry: Entry): boolean {
  if (entry.kind === 'welcome') {
    return false
  }

  if (entry.kind === 'notice') {
    return entry.tone !== 'error' && entry.tone !== 'warning'
  }

  if (entry.kind !== 'turn') {
    return true
  }

  return (
    entry.status === 'done' &&
    entry.blocks.every(
      block =>
        block.kind !== 'tool' ||
        ((block.call.status === 'done' || block.call.status === 'cancelled') &&
          (block.call.subagents ?? []).every(agent => agent.status === 'done' || agent.status === 'cancelled'))
    )
  )
}

function safePrompt(index: number, entries: readonly Entry[]): boolean {
  if (entries[index]?.kind !== 'user') {
    return true
  }

  for (let i = index + 1; i < entries.length; i++) {
    const next = entries[i]!

    if (next.kind === 'user') {
      return true
    }

    if (next.kind === 'turn') {
      return safeEntry(next)
    }
  }

  return false
}

function coldBoundary(entries: readonly Entry[]): number {
  let completed = 0

  for (let i = entries.length - 1; i >= 0; i--) {
    const entry = entries[i]!

    if (entry.kind === 'turn' && entry.status !== 'live' && ++completed === RETAIN_TURNS) {
      return entries[i - 1]?.kind === 'user' ? i - 1 : i
    }
  }

  return 0
}
