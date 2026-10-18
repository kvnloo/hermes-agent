import type { BtwListResult, BtwSubmitResult, BtwThread } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { Composer } from './composer.js'
import type { Overlay } from './overlay.js'
import { openBtwSheet } from './overlays/btw-sheet.js'
import type { ReportNotice } from './reports.js'

type BtwHost = Pick<App, 'sid' | 'gw' | 'open' | 'close' | 'owns' | 'changed' | 'scrollOverlay'>

/** A projection and unsent drafts only. Hermes owns ids, turns, history and cancellation. */
export class BtwReports {
  threads: BtwThread[] = []
  selected: string | null = null
  state: 'idle' | 'loading' | 'submitting' = 'idle'
  error = ''
  #sid: string | null = null
  #epoch = 0
  #drafts = new Map<string, Composer>()
  #dismissed = new Set<string>()
  #noticed = new Set<string>()
  #sheet: Overlay | undefined

  constructor(readonly host: BtwHost) {}

  adopt(sid: string | null) {
    if (this.#sid === sid) {
      return
    }

    if (this.#sheet) {
      this.host.close(this.#sheet)
    }

    this.#sid = sid
    this.#epoch++
    this.threads = []
    this.selected = null
    this.state = 'idle'
    this.error = ''
    this.#drafts.clear()
    this.#dismissed.clear()
    this.#noticed.clear()
  }

  get thread() {
    return this.threads.find(thread => thread.id === this.selected)
  }
  get draft(): Composer {
    const key = this.selected ?? 'new'
    let draft = this.#drafts.get(key)

    if (!draft) {
      draft = new Composer()
      this.#drafts.set(key, draft)
    }

    return draft
  }

  update(thread: BtwThread, notice = false) {
    if (notice) {
      this.#noticed.add(thread.id)
    }

    const index = this.threads.findIndex(item => item.id === thread.id)

    if (index < 0) {
      this.threads.push(thread)
    } else if (this.threads[index]!.revision < thread.revision) {
      this.threads[index] = thread
    }

    this.host.changed()
  }

  get notices(): ReportNotice[] {
    return this.threads
      .filter(thread => this.#noticed.has(thread.id) && !this.#dismissed.has(thread.id))
      .map(thread => {
        const turn = thread.turns.at(-1)

        return {
          id: `btw:${thread.id}`,
          title: '/btw',
          text: turn?.answer ?? '',
          label: `Side question ${turn?.state ?? 'pending'}`,
          failed: turn?.state === 'error'
        }
      })
  }

  dismiss(id: string) {
    this.#dismissed.add(id.slice('btw:'.length))
    this.host.changed()
  }

  async show(question = '', selected?: string) {
    const sid = this.host.sid

    if (!sid) {
      return
    }

    this.adopt(sid)
    const epoch = ++this.#epoch
    this.selected = selected ?? this.selected
    this.#sheet = openBtwSheet(this)
    this.state = 'loading'
    this.error = ''
    this.host.changed()

    try {
      const result = await this.host.gw.request<BtwListResult>('btw.list', { session_id: sid })

      if (this.host.sid !== sid || this.#epoch !== epoch) {
        return
      }

      for (const thread of result.threads) {
        this.update(thread)
      }

      this.selected ??= this.threads.at(-1)?.id ?? null
      this.state = 'idle'

      if (question) {
        this.selected = null
        this.draft.set(question)
        await this.submit()
      }
    } catch (error) {
      if (this.host.sid === sid && this.#epoch === epoch) {
        this.error = error instanceof Error ? error.message : String(error)
        this.state = 'idle'
      }
    }

    this.host.changed()
  }

  async submit() {
    const sid = this.host.sid
    const text = this.draft.text.trim()

    if (!sid || sid !== this.#sid || this.state !== 'idle' || !text || this.thread?.turns.at(-1)?.state === 'running') {
      return
    }

    const epoch = this.#epoch
    const threadId = this.selected
    const draft = this.draft
    const rev = draft.rev
    this.state = 'submitting'
    this.error = ''
    this.host.changed()

    try {
      const result = await this.host.gw.request<BtwSubmitResult>('btw.submit', {
        session_id: sid,
        text,
        ...(threadId ? { thread_id: threadId } : {})
      })

      if (this.host.sid !== sid || this.#epoch !== epoch) {
        return
      }

      // A completion event can beat the RPC acknowledgement; revision fences both.
      this.update(result.thread, true)

      if (this.selected === threadId) {
        this.selected = result.thread.id
      }

      this.#dismissed.delete(result.thread.id)

      if (draft.rev === rev) {
        draft.set('')
      }
    } catch (error) {
      if (this.host.sid === sid && this.#epoch === epoch) {
        this.error = error instanceof Error ? error.message : String(error)
      }
    } finally {
      if (this.host.sid === sid && this.#epoch === epoch) {
        this.state = 'idle'
        this.host.changed()
      }
    }
  }

  async cancel() {
    const sid = this.host.sid
    const thread = this.thread
    const turn = thread?.turns.at(-1)
    const epoch = this.#epoch

    if (!sid || !thread || turn?.state !== 'running') {
      return
    }

    try {
      const result = await this.host.gw.request<BtwSubmitResult>('btw.cancel', {
        session_id: sid,
        thread_id: thread.id,
        turn_id: turn.id
      })

      if (this.host.sid === sid && this.#epoch === epoch) {
        this.update(result.thread)
      }
    } catch (error) {
      if (this.host.sid === sid && this.#epoch === epoch) {
        this.error = error instanceof Error ? error.message : String(error)
        this.host.changed()
      }
    }
  }
}
