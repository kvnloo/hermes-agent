import { matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { App } from '../app.js'
import type { Subagent } from '../model.js'
import type { Overlay } from '../overlay.js'
import { age, duration } from '../view/time.js'

export interface AgentSelection {
  /** Tool identity scopes legacy task-index ids to their exact delegation. */
  callId: string
  agentId: string
}

export function selectedAgent(app: App, selection: AgentSelection): Subagent | undefined {
  for (const entry of app.transcript.entries) {
    if (entry.kind !== 'turn') {
      continue
    }

    for (const block of entry.blocks) {
      if (block.kind === 'tool' && block.call.id === selection.callId) {
        return block.call.subagents?.find(agent => agent.id === selection.agentId)
      }
    }
  }

  return undefined
}

/** Jobs ids are canonical subagent ids; never guess from a title or task index. */
export function agentSelectionForJob(app: App, jobId: string): AgentSelection | undefined {
  for (const entry of app.transcript.entries) {
    if (entry.kind !== 'turn') {
      continue
    }

    for (const block of entry.blocks) {
      if (block.kind === 'tool') {
        const agent = block.call.subagents?.find(agent => agent.id === jobId)

        if (agent) {
          return { agentId: agent.id, callId: block.call.id }
        }
      }
    }
  }

  return undefined
}

/** Reads the existing event-folded transcript on every frame, including after completion. */
export function openAgentInspector(app: App, selection: AgentSelection) {
  if (!selectedAgent(app, selection)) {
    return
  }

  const sid = app.sid
  let clock = { at: 0 }

  const sheet: Overlay = {
    key: 'agent-inspector',
    modal: true,
    node: id => {
      const agent = app.sid === sid ? selectedAgent(app, selection) : undefined

      if (agent && clock.at !== agent.startedAt) {
        clock = { at: agent.startedAt }
      }

      return (
        <overlay anchor="center" head="Agent inspector · read-only" key={id.slice('layer.'.length)} modal role="omp.overlay.agent-inspector" size="lg">
          <col gap="md" key="body">
            {agent ? (
              <col gap="sm" key="details" role="omp.agent.details">
                <text key="identity" text={`${selection.callId} · ${selection.agentId}`} tone="muted" />
                <text key="goal" text={agent.goal} wrap="word" />
                <text key="model" text={`Model: ${agent.model ?? 'not reported'}`} />
                <text key="status" text={`Status: ${agent.status}`} tone={agent.status === 'failed' || agent.status === 'cancelled' ? 'error' : undefined} />
                <row gap="sm" key="elapsed">
                  <text key="label" text="Elapsed:" />
                  {agent.duration === undefined
                    ? <elapsed age={age(clock, agent.startedAt, Date.now())} format="short" key="age" />
                    : <text key="duration" text={duration(agent.duration)} />}
                </row>
                <text key="counts" text={`${agent.calls} requests · ${agent.tokens} tokens · ${agent.toolCount} tools`} />
              </col>
            ) : <text key="unavailable" text="This agent is no longer available in the current session." />}
            <col gap="sm" key="activity" role="omp.agent.activity">
              {(agent?.activity ?? []).map((event, index) => (
                <col gap="xs" key={String(index)} role={event.kind === 'tool' ? 'omp.agent.tool' : 'omp.agent.note'}>
                  <text key="label" text={event.kind === 'tool' ? event.tool ?? 'Tool' : 'Note'} tone="muted" />
                  <text key="text" text={event.text} wrap="word" />
                </col>
              ))}
              {agent && !agent.activity?.length ? <text key="empty" text="No tool calls or notes received yet." tone="muted" /> : null}
              {agent?.summary ? <md key="summary" role="omp.agent.summary">{agent.summary}</md> : null}
            </col>
            <text key="close" onClick={() => app.close(sheet)} role="omp.btn" text="Close  escape" />
          </col>
        </overlay>
      )
    },
    onKey: key => {
      const action = REPORT_ACTIONS.find(action => matchesAction(action, key))

      if (action?.intent.kind === 'close') {
        app.close(sheet)
      } else if (action?.intent.kind === 'scroll') {
        app.scrollOverlay(sheet, 'body.activity', action.intent.to)
      }

      return true
    }
  }

  // TODO(agent-inspector-controls): add stop/send intents only with supported backend contracts.
  app.open(sheet)
}
