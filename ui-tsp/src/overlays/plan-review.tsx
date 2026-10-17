import { matchesAction, PLAN_ACTIONS, REPORT_ACTIONS } from '../actions.js'
import { Composer } from '../composer.js'
import type { Overlay } from '../overlay.js'
import type { Plan } from '../plan.js'

import { Sheet, type SheetHost } from './sheet.js'

interface PlanHost extends SheetHost {
  owns(overlay: Overlay): boolean
  submit(text: string): void
}

// TODO: annotations are deliberately excluded from this read-only review.
export function openPlanReview(host: PlanHost, plan: Plan | undefined) {
  let selected = 0
  let refining = false
  let submitted = false
  const note = new Composer()

  const choose = (index: number) => {
    if (!plan?.sections[index]) {
      return
    }

    selected = index
    host.changed()
    host.scroll(sheet, 'start')
  }

  const decide = (text: string) => {
    if (!plan || submitted || !host.owns(sheet)) {
      return
    }

    submitted = true
    host.close(sheet)
    host.submit(text)
  }

  const refine = () => {
    refining = true
    host.changed()
  }

  const sendNote = () => {
    const text = note.text.trim()

    if (text) {
      decide(`Refine the plan: ${text}`)
    }
  }

  const commands = {
    close: () => host.close(sheet),
    previous: () => choose(selected - 1),
    next: () => choose(selected + 1),
    approve: () => decide('Approved — proceed with the plan.'),
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
    node: id => (
      <Sheet id={id} role="omp.overlay.plan" title="Plan review">
        {plan ? (
          <col gap="sm" key="contents" role="omp.plan.contents">
            <text
              key="hint"
              text={`Section ${selected + 1}/${plan.sections.length} · Up/Down jumps sections · Page Up/Down scrolls`}
            />
            {plan.sections.map((section, index) => (
              <row
                key={`section-${index}`}
                onClick={() => choose(index)}
                role="omp.btn"
                tone={selected === index ? 'accent' : undefined}
              >
                <text key="label" text={`${'  '.repeat(section.level - 1)}${section.title}`} />
              </row>
            ))}
          </col>
        ) : null}
        <md key="markdown" role="omp.plan.body">
          {plan
            ? `${selected === 0 ? plan.preamble : ''}${plan.sections[selected]?.text ?? ''}`
            : 'No heading-structured assistant plan found. Ask Hermes for a plan first.'}
        </md>
        {plan && refining ? (
          <input
            cursor={note.cursor}
            key="note"
            onEdit={ev => {
              note.edit(ev)
              host.changed()
            }}
            onUndo={() => {
              note.undo()
              host.changed()
            }}
            placeholder="How should the plan change?"
            role="omp.ask.input"
            text={note.text}
          />
        ) : null}
        <row align="center" gap="sm" key="actions" role="omp.actions">
          {plan && !refining ? (
            <row key="approve" onClick={commands.approve} role="omp.btn" title="Approve  alt+a">
              <text key="label" text="Approve" />
            </row>
          ) : null}
          {plan ? (
            <row
              key="refine"
              onClick={refining ? sendNote : refine}
              role="omp.btn"
              title={refining ? 'Send refinement  enter' : 'Refine  alt+r'}
            >
              <text key="label" text={refining ? 'Send refinement' : 'Refine'} />
            </row>
          ) : null}
          <spacer grow={1} key="fill" />
          <row key="close" onClick={commands.close} role="omp.btn" title="Close  escape">
            <text key="label" text="Close" />
          </row>
        </row>
      </Sheet>
    ),
    onKey: key => {
      const action = PLAN_ACTIONS.find(action => matchesAction(action, key))?.action

      if (refining && action !== 'close') {
        // Only note submission can decide from the editor; Alt+A must not approve by accident.
        if (note.key(key) === 'submit') {
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
