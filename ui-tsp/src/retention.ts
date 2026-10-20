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
import { forgetView, SurfaceView } from './surface-protocol.js'
import type { Transcript } from './transcript.js'
import { forgetEntryNode, projectedEntryNodes, type TranscriptContext } from './view/transcript.js'

export const RETAIN_TURNS = 20
export const RELOAD_PAGE = 40
const LOAD_ID = 'main.retention-load'

interface RetainedEntry {
  entry: Entry
  index: number
  settled: boolean
  evicted: boolean
  trees?: Tree[]
  ids: string[]
  gone: Set<string>
}

/** No terminal reload/scroll event exists in SDK 0.1; reload is an explicit intent. */
export class Retention {
  readonly #entries = new Map<string, RetainedEntry>()
  /** Native action target roots; avoids scanning every retained turn for a click. */
  readonly #owners = new Map<string, RetainedEntry>()
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
  readonly #chrome = new SurfaceView()

  /** Build chrome through the SDK, then send history and chrome atomically under real credits. */
  paint(surface: Surface, view: ViewInput, history: readonly Op[]): void {
    this.#chrome.paint(surface, view, history)
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

    this.#chrome.forget(event.ids)

    if (event.ids.includes('main') || event.ids.includes(LOAD_ID)) {
      this.#loadShown = false
    }

    for (const item of this.#entries.values()) {
      const absent = item.ids.filter(id => event.ids.includes('main') || event.ids.includes(id))
      const affected = absent.length > 0 || item.ids.some(id => event.ids.some(gone => gone.startsWith(`${id}.`)))

      if (!affected) {
        continue
      }

      forgetEntryNode(item.entry)

      for (const id of absent) {
        item.gone.add(id)
      }

      if (absent.length) {
        item.evicted = true
        this.#evicted.add(item)
        item.trees = undefined
      } else if (item.trees) {
        item.trees = item.trees.flatMap(tree => {
          const resident = forgetView(new View([tree]), event.ids).regions[0]

          return resident ? [resident] : []
        })
      }

      // Settled roots stay cold. Active/error rows and partial subtrees are restored.
      if (!item.settled || !absent.length) {
        this.#hot.add(item)
      }
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

    const item = this.#ownerOf(event.id)

    if (!item || item.evicted || !this.#cx) {
      return
    }

    return () => {
      if (
        this.#entries.get(`main.${item.entry.id}`) !== item ||
        item.evicted ||
        !this.#cx ||
        !this.#transcript?.entries.includes(item.entry)
      ) {
        return
      }

      const router = new Surface({ send() {}, credits: () => 1, dropped() {} }, surface, { listen: false })
      router.render({ main: projectedEntryNodes(item.entry, `main.${item.entry.id}`, this.#cx) })
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
    const context = `${cx.cwd}:${cx.media}:${cx.hostLocal}:${cx.toolsHidden}:${cx.hour12 ?? false}:${cx.mediaRevision}:${cx.attachmentHostLocal}:${cx.gatewayRemote}:${cx.mediaHost}:${cx.charts?.revision ?? 0}`
    const structural = this.#structure !== transcript.structureRev

    if (structural) {
      const current = new Set(transcript.entries)

      for (const [id, item] of this.#entries) {
        if (current.has(item.entry)) {
          continue
        }

        for (const part of item.ids) {
          this.#owners.delete(part)

          if (!item.gone.has(part)) { ops.push(['del', part]) }
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
          item = { entry, index, settled: false, evicted: false, ids: [], gone: new Set() }
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
      for (const item of this.#reading) {
        this.#hot.add(item)
      }

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

      const settle =
        !hold &&
        !this.#reading.has(item) &&
        item.index < cold &&
        safeEntry(entry) &&
        safePrompt(item.index, transcript.entries)

      if (item.evicted && settle) {
        this.#hot.delete(item)

        continue
      }

      const wasEvicted = item.evicted
      item.evicted = false
      this.#evicted.delete(item)

      const trees = projectedEntryNodes(entry, id, cx).flatMap(element => element instanceof Node
        ? [new Tree(`main.${element.props.key}`, element)] : [])

      const before = this.#nextResident(item.index)

      if (item.trees && !wasEvicted && !restored.has(item)) {
        // Keep exact resident children: rebuilding from tree.node would resurrect evicted descendants.
        const resident = new class extends Tree {
          override readonly children = item.trees!
        }('main', node('col', {}))

        const changes = new View([resident]).ops(View.from({ main: trees.map(tree => tree.node) }), 'hermes')
        ops.push(...changes.map(op => (op[0] === 'add' || op[0] === 'move') && op[2] === 'main' && op[3] === null
          ? op[0] === 'add' ? ['add', op[1], op[2], before, op[4]] satisfies Op : ['move', op[1], op[2], before] satisfies Op : op))
      } else {
        for (const part of item.ids) {
          if (!item.gone.has(part)) { ops.push(['del', part]) }
        }

        for (const tree of trees) {
          ops.push(['add', tree.id, 'main', before, tree.wire()])
        }
      }

      for (const id of item.ids) { this.#owners.delete(id) }
      item.ids = trees.map(tree => tree.id)

      for (const id of item.ids) { this.#owners.set(id, item) }
      item.gone.clear()
      item.trees = trees
      item.settled = settle

      if (settle) {
        ops.push(...item.ids.map(part => ['settle', part] satisfies Op))
        item.trees = undefined
        forgetEntryNode(entry)
        this.#hot.delete(item)
      }
    }

    const missing = this.#evicted.size > 0

    if (missing !== this.#loadShown) {
      if (missing) {
        const load = new Tree(
          LOAD_ID,
          node('el', {
            tag: 'button',
            aria: 'Load older history',
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

  /** Resolve the deepest emitted native root, even when a tool id contains dots. */
  #ownerOf(target: string): RetainedEntry | undefined {
    let prefix = target

    while (prefix.startsWith('main.')) {
      const owner = this.#owners.get(prefix)

      if (owner) { return owner }
      const dot = prefix.lastIndexOf('.')

      if (dot <= 'main'.length) { return undefined }
      prefix = prefix.slice(0, dot)
    }

    return undefined
  }

  #nextResident(index: number): string | null {
    const entries = this.#transcript?.entries ?? []

    for (let i = index + 1; i < entries.length; i++) {
      const id = `main.${entries[i]!.id}`

      const item = this.#entries.get(id)
      const resident = item?.ids.find(part => !item.gone.has(part))

      if (resident) {
        return resident
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
