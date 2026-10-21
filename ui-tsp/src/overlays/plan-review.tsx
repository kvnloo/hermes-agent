import type { RpcMethods } from '@hermes/shared/gateway-events'

import { matchesAction, PLAN_ACTIONS, REPORT_ACTIONS } from '../actions.js'
import { Composer } from '../composer.js'
import { editTextExternal } from '../external-editor.js'
import type { Overlay } from '../overlay.js'
import { type Plan, type PlanStatus, reviewPlanText } from '../plan.js'
import { ActionButton } from '../view/action-button.js'

import { Sheet, type SheetHost } from './sheet.js'

interface PlanHost extends SheetHost {
  owns(overlay: Overlay): boolean
  submit(text: string): void
  request<M extends keyof RpcMethods>(method: M, params: RpcMethods[M]['params']): Promise<RpcMethods[M]['result']>
  sessionId: string
}

export function openPlanReview(host: PlanHost, plan: Plan | undefined, status: PlanStatus | undefined) {
  let selected = 0
  let refining = false
  let submitted = false
  let pending = false
  let error = ''
  let editing: 'refine' | 'annotation' | 'plan' = 'refine'
  let annotationSection = 0

  const update = (next: PlanStatus) => {
    status = next
    plan = next.plan ? reviewPlanText(next.plan.text) : undefined
    selected = Math.min(selected, Math.max(0, (plan?.sections.length ?? 1) - 1))
    host.changed()
  }

  const target = () =>
    status?.plan ? { session_id: host.sessionId, plan_id: status.plan.id, revision: status.plan.revision } : undefined

  const transact = async (run: () => Promise<PlanStatus>, close = false) => {
    if (pending || submitted || !host.owns(sheet)) {
      return
    }

    pending = true
    error = ''
    host.changed()

    try {
      const next = await run()

      if (!host.owns(sheet)) {
        return
      }

      update(next)
      refining = false

      if (close) {
        submitted = true
        host.close(sheet)
      }
    } catch (cause) {
      error = cause instanceof Error ? cause.message : String(cause)
    } finally {
      pending = false
      host.changed()
    }
  }

  const drafts = { refine: new Composer(), annotation: new Composer(), plan: new Composer() }
  const note = () => drafts[editing]

  const choose = (index: number) => {
    if (!plan?.sections[index]) {
      return
    }

    selected = index
    host.changed()
    host.scroll(sheet, 'start')
  }

  const decide = (text: string) => {
    if (!plan || status?.enabled || status?.plan || submitted || pending || !host.owns(sheet)) {
      return
    }

    submitted = true
    host.close(sheet)
    host.submit(text)
  }

  const refine = () => {
    editing = 'refine'
    refining = true
    host.changed()
  }

  const sendNote = (revision = target()) => {
    if (revision?.revision !== target()?.revision || revision?.plan_id !== target()?.plan_id) {
      return
    }

    const text = note().text.trim()

    if (revision) {
      if (editing === 'annotation') {
        void transact(() => host.request('plan.annotate', { ...revision, section: annotationSection, text }))
      } else if (editing === 'plan') {
        if (text) {
          void transact(() => host.request('plan.edit', { ...revision, text: note().text }))
        }
      } else if (text || status?.plan?.annotations.length) {
        void transact(() => host.request('plan.decide', { ...revision, intent: 'refine', feedback: text }), true)
      }
    } else if (text) {
      decide(`Refine the plan: ${text}`)
    }
  }

  const commands = {
    close: () => host.close(sheet),
    previous: () => choose(selected - 1),
    next: () => choose(selected + 1),
    approve: (revision = target()) => {
      if (revision?.revision !== target()?.revision || revision?.plan_id !== target()?.plan_id) {
        return
      }

      if (revision) {
        void transact(() => host.request('plan.decide', { ...revision, intent: 'approve', feedback: '' }), true)
      } else {
        decide('Approved — proceed with the plan.')
      }
    },
    refine,
    submit: () => {
      if (refining) {
        sendNote()
      }
    }
  }

  const sheet: Overlay = {
    key: 'plan',
    modal: true,
    focus: id => (refining ? `${id}.body.note` : null),
    node: id => {
      const renderedTarget = target()

      return (
        <Sheet id={id} role="omp.overlay.plan" title="Plan review">
          <text
            key="authority"
            text={
              status
                ? `Plan mode ${status.enabled ? 'ON · execution blocked' : 'OFF'} · ${status.generating ? 'Generating — no decision available' : status.plan ? `${status.plan.id} · revision ${status.plan.revision} · ${status.plan.decision}` : 'No authoritative plan'}`
                : 'Plan authority unavailable. Markdown review only; Continue sends an ordinary prompt, not plan approval.'
            }
            wrap="word"
          />
          {status ? (
            <ActionButton
              key="mode"
              onClick={() => {
                const enabled = !status?.enabled
                void transact(() => host.request('plan.mode', { session_id: host.sessionId, enabled }))
              }}
              role="omp.btn"
            >
              <text key="label" text={status.enabled ? 'Disable plan mode' : 'Enable plan mode'} />
            </ActionButton>
          ) : null}
          {error ? <text key="error" text={error} tone="danger" wrap="word" /> : null}
          {pending ? <text key="pending" text="Waiting for plan operation…" /> : null}
          {status?.plan?.annotations
            .filter(annotation => annotation.section === selected)
            .map(annotation => (
              <text
                key={`annotation-${annotation.section}`}
                role="omp.plan.annotation"
                text={`Note: ${annotation.text}`}
                wrap="word"
              />
            ))}
          {status?.enabled && status.plan?.decision === 'pending' && !refining ? (
            <row gap="sm" key="tools" role="omp.plan.tools">
              <ActionButton
                key="annotate"
                onClick={() => {
                  editing = 'annotation'
                  annotationSection = selected
                  note().set(status?.plan?.annotations.find(annotation => annotation.section === selected)?.text ?? '')
                  refining = true
                  host.changed()
                }}
                role="omp.btn"
              >
                <text key="label" text="Annotate section" />
              </ActionButton>
              <ActionButton
                key="edit-plan"
                onClick={() => {
                  editing = 'plan'
                  note().set(plan?.text ?? '')
                  refining = true
                  host.changed()
                }}
                role="omp.btn"
              >
                <text key="label" text="Edit plan" />
              </ActionButton>
              <ActionButton
                key="external-editor"
                onClick={() => {
                  const revision = renderedTarget
                  const initial = plan?.text

                  if (!revision || initial === undefined) {
                    return
                  }

                  void transact(async () => {
                    const text = await editTextExternal(initial)

                    if (!host.owns(sheet)) {
                      throw new Error('Plan review changed; external edit was not applied.')
                    }

                    return host.request('plan.edit', { ...revision, text })
                  })
                }}
                role="omp.btn"
              >
                <text key="label" text="Edit in $EDITOR" />
              </ActionButton>
            </row>
          ) : null}
          {plan && !refining ? (
            <col gap="sm" key="contents" role="omp.plan.contents">
              <text
                key="hint"
                text={`Section ${selected + 1}/${plan.sections.length} · Up/Down jumps sections · Page Up/Down scrolls`}
              />
              {plan.sections.map((section, index) => (
                <ActionButton
                  key={`section-${index}`}
                  onClick={() => choose(index)}
                  role="omp.btn"
                  tone={selected === index ? 'accent' : undefined}
                >
                  <text key="label" text={`${'  '.repeat(section.level - 1)}${section.title}`} />
                </ActionButton>
              ))}
            </col>
          ) : null}
          {refining ? (
            <text
              key="refine-hint"
              text={`${editing === 'plan' ? 'Shift+Enter inserts a line; Enter saves. ' : ''}${editing === 'annotation' ? 'Annotate the selected section.' : editing === 'plan' ? 'Edit the full plan; saving creates a new revision and clears section notes.' : 'Describe what should change in the plan.'} Your original composer draft is preserved.`}
              wrap="word"
            />
          ) : (
            <md key="markdown" role="omp.plan.body">
              {plan
                ? `${selected === 0 ? plan.preamble : ''}${plan.sections[selected]?.text ?? ''}`
                : 'No heading-structured assistant plan found. Ask Hermes for a plan first.'}
            </md>
          )}
          {plan && refining ? (
            <editor
              aria={editing === 'annotation' ? 'Section annotation' : editing === 'plan' ? 'Plan revision' : 'Plan refinement'}
              cursor={note().cursor}
              key="note"
              maxLines={editing === 'plan' ? 10 : 4}
              onEdit={ev => {
                note().edit(ev)
                host.changed()
              }}
              onUndo={() => {
                note().undo()
                host.changed()
              }}
              placeholder="How should the plan change?"
              role="omp.ask.input"
              text={note().text}
            />
          ) : null}
          <row align="center" gap="sm" key="actions" role="omp.actions">
            {refining ? (
              <ActionButton
                key="review"
                onClick={() => {
                  refining = false
                  host.changed()
                }}
                role="omp.btn"
                title="Back to plan"
              >
                <text key="label" text="Back to plan" />
              </ActionButton>
            ) : null}
            {plan && (!status?.plan || (status.enabled && status.plan.decision === 'pending')) && !refining ? (
              <ActionButton key="approve" onClick={() => commands.approve(renderedTarget)} role="omp.btn" title="Approve  alt+a">
                <text
                  key="label"
                  text={status?.plan ? 'Approve exact revision (no automatic execution)' : 'Continue (ordinary prompt)'}
                />
              </ActionButton>
            ) : null}
            {plan && (!status?.plan || (status.enabled && status.plan.decision === 'pending')) ? (
              <ActionButton
                key="refine"
                onClick={() => (refining ? sendNote(renderedTarget) : refine())}
                role="omp.btn"
                title={refining ? 'Send refinement  enter' : 'Refine  alt+r'}
              >
                <text
                  key="label"
                  text={refining ? (editing === 'refine' ? 'Send refinement' : 'Save revision') : 'Refine'}
                />
              </ActionButton>
            ) : null}
            <spacer grow={1} key="fill" />
            <ActionButton key="close" onClick={commands.close} role="omp.btn" title="Close  escape">
              <text key="label" text="Close" />
            </ActionButton>
          </row>
        </Sheet>
      )
    },
    onKey: key => {
      const action = PLAN_ACTIONS.find(action => matchesAction(action, key))?.action

      if (refining && action !== 'close') {
        // Only note submission can decide from the editor; Alt+A must not approve by accident.
        if (note().key(key) === 'submit') {
          sendNote()
        }
      } else if (action) {
        commands[action]()
      } else {
        const scroll = REPORT_ACTIONS.find(action => matchesAction(action, key))?.intent

        if (scroll?.kind === 'scroll') {
          host.scroll(sheet, scroll.to)
        }
      }

      return true
    }
  }

  host.open(sheet)
}
