// Presentation snapshots only. The gateway remains the owner of jobs and output.

import type { JobsCancelResult, JobsListResult, JobSnapshot, JobsTailResult } from '@hermes/shared/gateway-events'
import type { JSX, Key } from '@stencil-hq/tern'

import { jobsKeyAction } from '../actions.js'
import type { App } from '../app.js'
import type { Overlay } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

import { openAgentHub } from './agent-hub.js'
import { agentSelectionForJob, openAgentInspector } from './agent-inspector.js'
import { confirmOverlay } from './prompts.js'

const STATE_EVENTS = new Set([
  'jobs.changed', 'tool.complete', 'background.complete', 'terminal.close', 'subagent.start', 'subagent.complete', 'subagent.spawn_requested'
])

const OUTPUT_EVENTS = new Set(['agent.terminal.output', 'subagent.progress', 'subagent.tool', 'subagent.thinking'])
const running = (job: JobSnapshot) => job.state === 'running' || job.state === 'queued' || job.state === 'pending'

// Colour confirms only the backend's actual job state; never estimate progress.
function jobStateTone(state: JobSnapshot['state']) {
  if (state === 'failed') {
    return 'error'
  }

  if (state === 'completed') {
    return 'success'
  }

  if (state === 'queued' || state === 'pending') {
    return 'warning'
  }

  if (state === 'cancelled') {
    return 'muted'
  }

  return undefined
}

/** Master/detail sheet plus its event-fed dock snapshot. No idle polling. */
export class JobsSheet implements Overlay {
  readonly key = 'jobs'
  readonly modal = true
  #sid: string | null = null
  #jobs: JobSnapshot[] = []
  #selected = ''
  #tail: JobsTailResult | null = null
  #error = ''
  #notice = ''
  #loading = false
  #open = false
  #generation = 0
  #selection = 0
  #visit = 0
  #lastRead = -Infinity
  #timer: ReturnType<typeof setTimeout> | undefined
  #reading = false
  #dirty = false
  #cancelling = false

  constructor(readonly app: App) {}

  get count(): number {
    return this.#sid === this.app.sid ? this.#jobs.filter(running).length : 0
  }

  adopt(sid: string | null) {
    if (sid === this.#sid) {
      return
    }

    this.app.close(this)
    this.#generation++
    this.#sid = sid
    this.#jobs = []
    this.#selected = ''
    this.#tail = null
    this.#reading = false
    this.#dirty = false
    this.#error = ''
    this.#notice = ''

    if (sid) {
      void this.#read()
    }
  }

  show() {
    if (!this.app.sid) {
      return
    }

    // Opening manually also works before the first session adoption callback.
    if (this.#sid !== this.app.sid) {
      this.adopt(this.app.sid)
    }

    this.app.open(this)
    this.#open = true
    this.#error = ''

    if (!this.#reading) {
      this.#invalidate()
    }
  }

  onClose() {
    this.#open = false
    this.#visit++
    this.#selection++
    this.#dirty = false
    this.#clearTimer()
  }

  event(type: string) {
    if (STATE_EVENTS.has(type) || (this.#open && OUTPUT_EVENTS.has(type))) {
      this.#invalidate()
    }
  }

  #clearTimer() {
    clearTimeout(this.#timer)
    this.#timer = undefined
  }

  #invalidate() {
    if (!this.#sid || this.#sid !== this.app.sid) {
      return
    }

    if (this.#reading) {
      this.#dirty = true

      return
    }

    const delay = 1000 - (Date.now() - this.#lastRead)

    if (this.#open && delay > 0) {
      this.#timer ??= setTimeout(() => {
        this.#timer = undefined
        void this.#read()
      }, delay)

      return
    }

    void this.#read()
  }

  async #read() {
    const sid = this.#sid
    const generation = this.#generation
    const current = () => sid !== null && this.app.sid === sid && generation === this.#generation

    if (!current()) {
      return
    }

    this.#reading = true
    this.#loading = this.#jobs.length === 0
    this.#lastRead = Date.now()
    this.app.changed()

    try {
      const result = await this.app.gw.request<JobsListResult>('jobs.list', { session_id: sid })

      if (!current()) {
        return
      }

      this.#jobs = result.jobs.filter(job => job.owner_session_id === sid)
      this.#selected = this.#jobs.some(job => job.id === this.#selected) ? this.#selected : this.#jobs[0]?.id ?? ''
      this.#error = ''

      if (this.#open) {
        await this.#readTail()
      }
    } catch (error) {
      if (current()) {
        this.#error = error instanceof Error ? error.message : String(error)
      }
    } finally {
      if (current()) {
        this.#loading = false
        this.#reading = false
        this.app.changed()

        if (this.#dirty) {
          this.#dirty = false
          this.#invalidate()
        }
      }
    }
  }

  async #readTail() {
    const sid = this.#sid
    const id = this.#selected
    const selection = ++this.#selection
    const generation = this.#generation

    if (!id || !this.#open || sid !== this.app.sid) {
      this.#tail = null

      return
    }

    const result = await this.app.gw.request<JobsTailResult>('jobs.tail', { job_id: id, lines: 100, session_id: sid })

    if (this.#open && this.app.sid === sid && generation === this.#generation && selection === this.#selection) {
      this.#tail = result
      this.app.changed()
    }
  }

  #select(id: string) {
    if (!this.#jobs.some(job => job.id === id) || id === this.#selected) {
      return
    }

    this.#selected = id
    this.#notice = ''
    this.#tail = null
    void this.#readTail().catch(error => {
      if (this.#open) {
        this.#error = String(error)
        this.app.changed()
      }
    })
    this.app.changed()
  }

  #inspect(job: JobSnapshot) {
    if (job.kind !== 'subagent' || job.owner_session_id !== this.app.sid) {
      return
    }

    const selection = agentSelectionForJob(this.app, job.id)
    this.app.close(this)

    if (selection) {
      openAgentInspector(this.app, selection)
    } else {
      openAgentHub(this.app, { subagentId: job.id })
    }
  }

  #askCancel(job: JobSnapshot) {
    const sid = this.#sid
    const generation = this.#generation
    const visit = this.#visit

    if (!this.#open || !job.can_cancel || !running(job) || job.owner_session_id !== this.app.sid || this.#cancelling) {
      return
    }

    this.app.open(confirmOverlay(this.app, {
      confirm: 'Cancel job',
      detail: `${job.title} · ${job.id} · owner session ${sid}`,
      onConfirm: () => {
        if (this.#open && !this.#cancelling && this.#visit === visit && this.app.sid === sid && generation === this.#generation &&
          this.#jobs.some(current => current.id === job.id && running(current))) {
          void this.#cancel(job, sid)
        }
      },
      title: 'Cancel this background job?'
    }))
  }

  async #cancel(job: JobSnapshot, sid: string | null) {
    this.#cancelling = true
    this.app.changed()

    try {
      const result = await this.app.gw.request<JobsCancelResult>('jobs.cancel', { job_id: job.id, session_id: sid })

      if (this.app.sid === sid) {
        this.#error = result.accepted ? '' : 'The job is no longer running or could not be cancelled.'
        this.#notice = result.accepted ? 'Cancellation requested; waiting for the next job status.' : ''
        this.#invalidate()
      }
    } catch (error) {
      if (this.app.sid === sid) {
        this.#error = error instanceof Error ? error.message : String(error)
      }
    } finally {
      this.#cancelling = false
      this.app.changed()
    }
  }

  onKey(key: Key): boolean {
    const action = jobsKeyAction(key)
    const at = this.#jobs.findIndex(job => job.id === this.#selected)

    const actions = {
      close: () => this.app.close(this),
      next: () => this.#select(this.#jobs[(at + 1) % this.#jobs.length]?.id ?? ''),
      previous: () => this.#select(this.#jobs[(at - 1 + this.#jobs.length) % this.#jobs.length]?.id ?? '')
    }

    if (action) {
      actions[action]()
    }

    return true
  }

  node(id: string): JSX.Element {
    const selected = this.#jobs.find(job => job.id === this.#selected)
    const inspectable = selected?.kind === 'subagent'
    const selectedId = selected ? `${id}.body.panes.list.${selected.id}` : undefined
    const choose = (item: string) => this.#select(this.#jobs.find(job => `${id}.body.panes.list.${job.id}` === item)?.id ?? '')

    const activate = (item: string) => {
      const job = this.#jobs.find(job => `${id}.body.panes.list.${job.id}` === item)

      if (job) {
        this.#select(job.id)
        this.#inspect(job)
      }
    }

    return (
      <overlay anchor="center" head="Background jobs" key={id.slice('layer.'.length)} modal role="omp.overlay.jobs" size="lg">
        <col gap="md" key="body">
          {this.#error ? <text key="error" text={this.#error} tone="error" /> : null}
          {this.#notice ? <text key="notice" text={this.#notice} /> : null}
          {this.#loading ? <text key="loading" text="Loading jobs…" /> : null}
          <row gap="md" key="panes">
            <list grow={1} key="list" onActivate={ev => activate(ev.item)} onSelect={ev => choose(ev.item)} role="omp.jobs.list" selected={selectedId}>
              {this.#jobs.map(job => (
                <item detail={[{ t: `${job.kind} · ${job.state}${job.parent_id ? ` · parent ${job.parent_id}` : ''}` }]}
                  key={job.id} label={[{ t: job.title }]} role="omp.jobs.item" />
              ))}
            </list>
            <col gap="sm" grow={2} key="detail" role="omp.jobs.detail">
              {selected ? (
                <row align="center" gap="xs" key="title-row">
                  <text key="title" text={selected.title} />
                  <badge key="state" role="omp.jobs.state" text={selected.state} tone={jobStateTone(selected.state)} />
                </row>
              ) : <text key="empty" text="No background jobs in this session." />}
              {selected ? <text key="owner" text={`${selected.id} · owner ${selected.owner_session_id} · started ${selected.started ? new Date(selected.started * 1000).toISOString() : 'unknown'}`} tone="muted" /> : null}
              {this.#tail && this.#tail.job_id === selected?.id ? <code key="output" text={this.#tail.text || (this.#tail.available ? 'No output yet.' : 'Live output unavailable.')} /> : null}
              {this.#tail?.truncated ? <text key="truncated" text="Showing the last 100 lines (up to 16 KiB)." tone="muted" /> : null}
              {selected && inspectable ? <ActionButton key="inspect" onClick={() => this.#inspect(selected)} role="omp.btn" text="Inspect agent" /> : null}
              {selected && selected.can_cancel && running(selected) && selected.owner_session_id === this.app.sid ? (
                <ActionButton key="cancel" onClick={() => this.#askCancel(selected)} role="omp.btn" text={this.#cancelling ? 'Cancelling…' : 'Cancel job'} tone="error" />
              ) : null}
            </col>
          </row>
          <row gap="sm" key="actions">
            <ActionButton key="refresh" onClick={() => this.#invalidate()} role="omp.btn" text="Refresh" />
            <ActionButton key="close" onClick={() => this.app.close(this)} role="omp.btn" text="Close" />
          </row>
        </col>
      </overlay>
    )
  }
}
