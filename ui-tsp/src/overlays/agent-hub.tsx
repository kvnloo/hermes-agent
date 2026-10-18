import type { AgentControlResult, AgentHubResult, AgentHubRow, AgentTranscriptResult } from '@hermes/shared/gateway-events'
import type { Key } from '@stencil-hq/tern'

import { jobsKeyAction, matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { App } from '../app.js'
import { Composer } from '../composer.js'
import type { Overlay } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

interface Selection {
  childSessionId?: string
  subagentId?: string
}

/** Event-driven presentation snapshots only; canonical pages and authority stay in Python. */
export class AgentHubSheet implements Overlay {
  readonly key: string
  readonly modal = true
  readonly #sid: string | null
  readonly #draft = new Composer()
  #agents: AgentHubRow[] = []
  #selected = ''
  #page: AgentTranscriptResult | undefined
  #offset = 0
  #error = ''
  #notice = ''
  #closed = false
  #reading = false
  #dirty = false
  #busy = false
  #version = 0

  constructor(readonly app: App, readonly initial?: Selection) {
    this.key = initial ? 'agent-inspector' : 'agent-hub'
    this.#sid = app.sid
  }

  #current() { return !this.#closed && this.app.sid === this.#sid }
  #agent() { return this.#agents.find(row => row.id === this.#selected) }

  show() {
    if (!this.#sid) {
      return
    }

    this.app.open(this)
    this.app.gw.on('event', this.#event)
    void this.#read()
  }

  readonly #event = (event: { session_id?: string | null; type: string }) => {
    if (event.session_id === this.#sid && ['subagent.start', 'subagent.spawn_requested', 'subagent.tool', 'subagent.progress', 'subagent.complete', 'jobs.changed', 'message.complete'].includes(event.type)) {
      void this.#read()
    }
  }

  onClose() {
    this.#closed = true
    this.#version++
    this.app.gw.off('event', this.#event)
  }

  async #read() {
    if (!this.#current()) {
      return
    }

    if (this.#reading) {
      this.#dirty = true

      return
    }

    this.#reading = true

    try {
      const result = await this.app.gw.request<AgentHubResult>('subagent.hub', { session_id: this.#sid })

      if (!this.#current()) {
        return
      }

      this.#agents = result.agents

      if (!this.#selected) {
        this.#selected = this.#agents.find(row => row.child_session_id === this.initial?.childSessionId ||
          (this.initial?.subagentId !== undefined && row.subagent_id === this.initial.subagentId))?.id ??
          (this.initial ? '' : this.#agents[0]?.id ?? '')
      }

      await this.#readPage()
      this.#error = ''
    } catch (error) {
      if (this.#current()) {
        this.#error = error instanceof Error ? error.message : String(error)
      }
    } finally {
      this.#reading = false
      this.app.changed()

      if (this.#dirty) {
        this.#dirty = false
        void this.#read()
      }
    }
  }

  async #readPage() {
    const row = this.#agent()
    const version = ++this.#version

    if (!row?.actions.transcript || !row.child_session_id) {
      this.#page = undefined

      return
    }

    const page = await this.app.gw.request<AgentTranscriptResult>('subagent.transcript', {
      child_session_id: row.child_session_id, limit: 50, offset: this.#offset, session_id: this.#sid
    })

    if (this.#current() && version === this.#version && this.#agent()?.id === row.id) {
      this.#page = page
      this.app.changed()
    }
  }

  #select(id: string) {
    if (!this.#current() || !this.#agents.some(row => row.id === id) || id === this.#selected) {
      return
    }

    this.#selected = id
    this.#version++
    this.#offset = 0
    this.#page = undefined
    this.#draft.set('')
    this.#notice = ''
    void this.#read()
    this.app.changed()
  }

  #pageTo(offset: number) {
    this.#version++
    this.#offset = offset
    this.#page = undefined
    void this.#read()
    this.app.changed()
  }

  async #control(stop: boolean) {
    const row = this.#agent()
    const text = this.#draft.text

    if (!this.#current() || !this.app.owns(this) || this.#busy || !row?.actions[stop ? 'stop' : 'send'] ||
        !row.child_session_id || !row.subagent_id || (!stop && !text.trim())) {
      return
    }

    this.#busy = true
    this.app.changed()

    try {
      const result = await this.app.gw.request<AgentControlResult>(stop ? 'subagent.stop' : 'subagent.message', {
        child_session_id: row.child_session_id, session_id: this.#sid, subagent_id: row.subagent_id,
        ...(!stop ? { text } : {})
      })

      if (this.#current() && this.#selected === row.id) {
        this.#notice = {
          cancel_requested: 'Cancellation requested — waiting for terminal status.',
          queued: 'Steering queued, not yet delivered. A final-boundary race is reported as missed_steer.',
          rejected: 'Rejected: this child no longer supports that action. Your draft was kept.'
        }[result.status]

        if (result.status === 'queued' && this.#draft.text === text) {
          this.#draft.set('')
        }
      }

      await this.#read()
    } catch (error) {
      if (this.#current()) {
        this.#error = error instanceof Error ? error.message : String(error)
      }
    } finally {
      this.#busy = false
      this.app.changed()
    }
  }

  focus(id: string) {
    return this.#current() && this.#agent()?.actions.send ? `${id}.body.detail.message` : null
  }

  onKey(key: Key) {
    const report = REPORT_ACTIONS.find(action => matchesAction(action, key))?.intent

    if (report?.kind === 'close') {
      this.app.close(this)
    } else if (report?.kind === 'scroll') {
      this.app.scrollOverlay(this, 'body.detail.transcript', report.to)
    } else if (!this.#agent()?.actions.send) {
      const action = jobsKeyAction(key)
      const at = this.#agents.findIndex(row => row.id === this.#selected)
      const delta = action === 'next' ? 1 : action === 'previous' ? -1 : 0

      if (delta) {
        this.#select(this.#agents[(at + delta + this.#agents.length) % this.#agents.length]?.id ?? '')
      }
    }

    return true
  }

  node(id: string) {
    const row = this.#current() ? this.#agent() : undefined
    const agents = this.#current() ? this.#agents : []
    const page = row && this.#page?.child_session_id === row.child_session_id ? this.#page : undefined
    const choose = (item: string) => this.#select(this.#agents.find(row => `${id}.body.roster.${row.id}` === item)?.id ?? '')

    return (
      <overlay anchor="center" head="Agents · owned hub" key={id.slice('layer.'.length)} modal role={this.initial ? 'omp.overlay.agent-inspector' : 'omp.overlay.agent-hub'} size="lg">
        <col gap="md" key="body">
          <row gap="sm" key="actions">
            <ActionButton key="refresh" onClick={() => void this.#read()} role="omp.btn" text="Refresh" />
            <ActionButton key="close" onClick={() => this.app.close(this)} role="omp.btn" text="Close  escape" />
          </row>
          {this.#error ? <text key="error" text={this.#error} tone="error" /> : null}
          {this.#reading && !this.#agents.length ? <text key="loading" text="Loading agents…" /> : null}
          <list key="roster" onActivate={ev => choose(ev.item)} onSelect={ev => choose(ev.item)} role="omp.agents.roster" selected={row ? `${id}.body.roster.${row.id}` : undefined}>
            {agents.map(agent => <item detail={[{ t: `${agent.status} · ${agent.parent_id ? `parent ${agent.parent_id}` : 'parent not reported'}` }]} key={agent.id} label={[{ t: agent.goal }]} role="omp.agents.item" tone={['failed', 'cancelled', 'aborted'].includes(agent.status) ? 'error' : undefined} />)}
          </list>
          <col gap="sm" key="detail" role="omp.agent.details">
            {row ? <text key="identity" text={`${row.subagent_id ?? row.id} · session ${row.child_session_id ?? 'not reported'}`} tone="muted" /> : null}
            <text key="status" text={row ? `Status: ${row.status} · Model: ${row.model ?? 'not reported'}` : 'This agent is unavailable in the current session.'} />
            {row?.last_tool ? <text key="activity" role="omp.agent.activity" text={`Last started tool: ${row.last_tool}`} /> : null}
            <text key="capabilities" text={`Supported actions: ${row?.actions.send ? 'send steering' : 'send unavailable'} · ${row?.actions.stop ? 'stop' : 'stop unavailable'} · ${row?.actions.transcript ? 'paged transcript (read-only)' : 'transcript unavailable'}`} tone="muted" />
            <row gap="sm" key="pages">
              {this.#offset > 0 ? <ActionButton key="previous" onClick={() => this.#pageTo(Math.max(0, this.#offset - 50))} role="omp.btn" text="Previous page" /> : null}
              {page?.next_offset != null ? <ActionButton key="next" onClick={() => this.#pageTo(page.next_offset!)} role="omp.btn" text="Next page" /> : null}
            </row>
            {row?.actions.send ? <input cursor={this.#draft.cursor} key="message" onEdit={ev => {
              if (this.app.owns(this) && this.#current()) {
                this.#draft.edit(ev)
                this.app.changed()
              }
            }} placeholder="Steer this child (queued, not a restart)" role="omp.agent.input" text={this.#draft.text} /> : null}
            <row gap="sm" key="controls">
              {row?.actions.send ? <ActionButton key="send" onClick={() => void this.#control(false)} role="omp.btn" text={this.#busy ? 'Working…' : 'Send steering'} /> : null}
              {row?.actions.stop ? <ActionButton key="stop" onClick={() => void this.#control(true)} role="omp.btn" text="Stop agent" tone="error" /> : null}
            </row>
            {this.#notice ? <text key="notice" text={this.#notice} /> : null}
            <col gap="sm" key="transcript" role="omp.agent.transcript">
              {page?.messages.map((message, at) => <col key={String(at)} role={message.role === 'tool' ? 'omp.agent.tool' : 'omp.agent.message'}>
                <text key="role" text={`${typeof message.role === 'string' ? message.role : 'message'}${typeof message.tool_name === 'string' ? ` · ${message.tool_name}` : ''}`} tone="muted" />
                <code key="content" text={typeof message.content === 'string' ? message.content : JSON.stringify(message.content ?? '', null, 2)} />
                {message.tool_calls ? <code key="calls" text={JSON.stringify(message.tool_calls, null, 2)} /> : null}
                {message.reasoning || message.reasoning_content ? <code key="reasoning" text={String(message.reasoning || message.reasoning_content)} /> : null}
              </col>)}
              {page && !page.messages.length ? <text key="empty" text="No persisted messages yet. Live activity may precede a transcript flush." /> : null}
            </col>
          </col>
        </col>
      </overlay>
    )
  }
}

export function openAgentHub(app: App, initial?: Selection) {
  new AgentHubSheet(app, initial).show()
}
