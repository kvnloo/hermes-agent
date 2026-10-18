import { BTW_ACTIONS, matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { BtwReports } from '../btw.js'
import { copyToClipboard } from '../clipboard.js'
import type { Overlay } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

import { Sheet } from './sheet.js'

/** Independent history/reader panes, with one unsent composer per selected thread. */
export function openBtwSheet(model: BtwReports): Overlay {
  const host = model.host
  let focus: 'history' | 'reader' | 'composer' = 'reader'
  let message = ''

  const choose = (id: string | null) => {
    model.selected = id
    focus = 'composer'
    host.changed()
  }

  const move = (delta: number) => {
    const index = model.threads.findIndex(thread => thread.id === model.selected)
    const thread = model.threads[index + delta]

    if (thread) {
      choose(thread.id)
    }
  }

  const copy = () => {
    try {
      copyToClipboard(model.thread?.turns.map(turn => `${turn.question}\n\n${turn.answer}`).join('\n\n') ?? '')
      message = 'Report sent to the terminal clipboard (OSC 52).'
    } catch {
      message = 'Could not copy the report to the clipboard.'
    }

    host.changed()
  }

  const commands = {
    close: () => host.close(sheet),
    focus: () => {
      focus = ({ history: 'reader', reader: 'composer', composer: 'history' } as const)[focus]
      host.changed()
    },
    next: () => move(1),
    previous: () => move(-1),
    send: () => {
      void model.submit()
    },
    cancel: () => {
      void model.cancel()
    },
    copy
  }

  const sheet: Overlay = {
    key: 'report',
    modal: true,
    focus: id => (focus === 'composer' ? `${id}.body.followup` : null),
    node: id => (
      <Sheet id={id} role="omp.overlay.report" title="/btw">
        <text
          key="hint"
          text="Tab: history / reader / composer · Ctrl+N/P: select · Alt+Enter: send · Ctrl+X: stop side turn"
          wrap="word"
        />
        <row key="panes" role="omp.btw.body">
          <col key="history" role="omp.btw.history">
            <ActionButton key="new" onClick={() => choose(null)} role="omp.btn">
              <text key="label" text="New side question" />
            </ActionButton>
            {model.threads.map(thread => (
              <ActionButton
                key={thread.id}
                onClick={() => choose(thread.id)}
                role="omp.btn"
                tone={thread.id === model.selected ? 'accent' : undefined}
              >
                <text
                  key="label"
                  text={`${thread.turns[0]?.question ?? 'Side question'} · ${thread.turns.at(-1)?.state ?? 'pending'}`}
                  wrap="word"
                />
              </ActionButton>
            ))}
          </col>
          <col grow={1} key="reader" role="omp.btw.reader">
            {model.thread?.turns.map(turn => (
              <col key={turn.id} role="omp.btw.turn">
                <md key="question" role="omp.btw.question">
                  {turn.question}
                </md>
                <text
                  key="state"
                  role="omp.btw.meta"
                  text={turn.state}
                  tone={turn.state === 'error' ? 'error' : undefined}
                />
                <md key="answer" role="omp.btw.answer" stream={turn.state === 'running'}>
                  {turn.answer || (turn.state === 'running' ? 'Waiting for answer…' : 'No answer text.')}
                </md>
                {turn.error ? (
                  <text key="error" role="omp.btw.error" text={turn.error} tone="error" wrap="word" />
                ) : null}
              </col>
            )) ?? <text key="empty" text="No side question selected. Ask here or use /btw <question>." wrap="word" />}
          </col>
        </row>
        <text
          key="pending"
          role="omp.btw.pending"
          text={
            model.state === 'idle'
              ? ''
              : model.state === 'loading'
                ? 'Loading side threads…'
                : 'Submitting side question…'
          }
        />
        {model.error ? <text key="error" role="omp.btw.error" text={model.error} tone="error" wrap="word" /> : null}
        <input
          cursor={model.draft.cursor}
          key="followup"
          onEdit={ev => {
            model.draft.edit(ev)
            focus = 'composer'
            host.changed()
          }}
          onUndo={() => {
            model.draft.undo()
            host.changed()
          }}
          placeholder={model.selected ? 'Follow up in this side thread' : 'New side question'}
          role="omp.ask.input"
          text={model.draft.text}
        />
        {message ? <text key="notice" role="omp.report.notice" text={message} wrap="word" /> : null}
        <row gap="sm" key="actions" role="omp.actions">
          <ActionButton key="send" onClick={commands.send} role="omp.btn">
            <text key="label" text="Send side question" />
          </ActionButton>
          {model.thread?.turns.at(-1)?.state === 'running' ? (
            <ActionButton key="cancel" onClick={commands.cancel} role="omp.btn">
              <text key="label" text="Stop side turn" />
            </ActionButton>
          ) : null}
          <ActionButton key="copy" onClick={copy} role="omp.btn">
            <text key="label" text="Copy" />
          </ActionButton>
          <ActionButton key="close" onClick={commands.close} role="omp.btn">
            <text key="label" text="Return to main draft" />
          </ActionButton>
        </row>
      </Sheet>
    ),
    onKey: key => {
      const action = BTW_ACTIONS.find(action => matchesAction(action, key))

      if (action) {
        commands[action.action]()
      } else if (focus === 'composer') {
        if (model.draft.key(key) === 'submit') {
          void model.submit()
        }

        host.changed()
      } else {
        const scroll = REPORT_ACTIONS.find(action => matchesAction(action, key))?.intent

        if (scroll?.kind === 'scroll') {
          host.scrollOverlay(sheet, `body.panes.${focus}`, scroll.to)
        }
      }

      return true
    }
  }

  host.open(sheet)

  return sheet
}
