// Request-owned questions: clarify and approvals use the nonmodal dock;
// masked values (sudo, secrets, vault prompts) preempt them in a modal layer.
// OMP ask vocabulary, with distinct clarify and approval response schemas.

import type { ClarifyResult } from '@hermes/shared/gateway-events'
import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import type { JSX, Key } from '@stencil-hq/tern'

import { actionHint } from '../actions.js'
import { Composer } from '../composer.js'
import { maskedOffset, maskOf, unmaskEdit } from '../mask.js'
import type { Overlay, OverlayHost } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'

import { approvalPrompt, type PromptHost } from './approval.js'
import { clarifyNoteOf, ClarifyNotes, clarifyTimer } from './clarify-notes.js'

/** Strips the backend's `(Recommended)` suffix from clarify's first choice. */
const RECOMMENDED = /\s*\(recommended\)\s*$/i

interface Option {
  id: string
  label: string
  detail?: string
  recommended?: boolean
  checked?: boolean
  /** `omp.ask.option` (radio), `omp.ask.check` (checkbox) or `omp.ask.other`. */
  role?: string
}

interface Button {
  key: string
  label: string
  keys: string[]
  hint: string
  primary?: boolean
  onClick(): void
}

const str = (v: unknown): string => (typeof v === 'string' ? v : '')

function actionsRow(buttons: Button[]): JSX.Element {
  return (
    <row align="center" gap="sm" key="actions" role="omp.actions">
      <spacer grow={1} key="fill" />
      {buttons.map(b => (
        <ActionButton
          align="center"
          gap="xs"
          key={b.key}
          onClick={b.onClick}
          role="omp.btn"
          title={`${b.label}  ${b.hint}`}
          tone={b.primary ? 'accent' : undefined}
        >
          <text key="label" text={b.label} />
          <kbd key="keys" keys={b.keys} />
        </ActionButton>
      ))}
    </row>
  )
}

function optionList(
  listKey: string,
  id: string,
  options: Option[],
  selected: number,
  select: (i: number) => void,
  pick: (i: number) => void,
  question: string
): JSX.Element {
  const at = (item: string) => options.findIndex(o => `${id}.${o.id}` === item)

  return (
    <list
      aria={`Answer choices: ${question}`}
      key={listKey}
      max={{ lines: 6 }}
      onActivate={ev => {
        const i = at(ev.item)

        if (i >= 0) {
          pick(i)
        }
      }}
      onSelect={ev => {
        const i = at(ev.item)

        if (i >= 0) {
          select(i)
        }
      }}
      role="omp.ask.options"
      selected={options[selected] ? `${id}.${options[selected].id}` : undefined}
    >
      {options.map(o => (
        <item
          detail={o.detail ? [o.role === 'omp.ask.other' ? { s: 'dim', t: o.detail } : { t: o.detail }] : undefined}
          icon={o.checked ? 'check' : undefined}
          key={o.id}
          label={[{ t: o.label }]}
          role={o.role ?? 'omp.ask.option'}
          tone={o.checked ? 'success' : undefined}
          value={o.recommended ? [{ s: 'accent', t: 'Recommended' }] : undefined}
        />
      ))}
    </list>
  )
}

/** ↑/↓ (⌃P/⌃N) through `count` rows, wrapping; undefined when `key` isn't a move. */
function moved(key: Key, at: number, count: number): number | undefined {
  if (key.name === 'up' || (key.ctrl && key.name === 'p')) {
    return (at - 1 + count) % count
  }

  if (key.name === 'down' || (key.ctrl && key.name === 'n')) {
    return (at + 1) % count
  }

  return undefined
}

/** The overlay for a server request, or null for a method this frontend can't answer. */
export function promptOverlay(host: PromptHost, req: ServerRequest): Overlay | null {
  switch (req.method) {
    case 'approval':
      return approvalPrompt(host, req)

    case 'clarify':
      if (!questionsOf(req.params.questions).length) {
        // Nothing to ask: answer at once (the first answer wins, so the caller's decline is a no-op).
        req.respond({})

        return null
      }

      return clarifyOverlay(host, req)

    case 'sudo':

    case 'secret':

    case 'vault.unlock_prompt':

    case 'vault.code':

    case 'vault.save_login':
      return maskedOverlay(host, req)

    default:
      return null
  }
}

// ── Clarify ────────────────────────────────────────────────────────────

interface Question {
  qid: string
  question: string
  choices: string[]
  multi: boolean
}

/** One question's answer state, kept while the user moves between questions. */
interface Draft {
  selected: number
  picked: Set<number>
  typing: boolean
  other: Composer
}

function questionsOf(raw: unknown): Question[] {
  if (!Array.isArray(raw)) {
    return []
  }

  return raw.flatMap((q: unknown): Question[] => {
    if (!q || typeof q !== 'object' || !('qid' in q) || !('question' in q)) {
      return []
    }

    const choices = 'choices' in q && Array.isArray(q.choices) ? q.choices.filter(c => typeof c === 'string') : []
    const question = str(q.question).trim()

    return question
      ? [{ choices, multi: 'multi_select' in q && q.multi_select === true, qid: str(q.qid), question }]
      : []
  })
}

/** The first few words of a question, for its tab. */
function tabLabel(question: string): string {
  const words = question.replace(/[?.!:]+$/, '').split(/\s+/)

  return words.length > 4 ? `${words.slice(0, 4).join(' ')}…` : words.join(' ')
}

export interface ClarifyPrompt extends Overlay {
  readonly placement: 'dock'
  readonly hidden: boolean
  toggle(): void
}

export function isClarifyPrompt(overlay: Overlay): overlay is ClarifyPrompt {
  return (
    overlay.placement === 'dock' &&
    'hidden' in overlay &&
    typeof overlay.hidden === 'boolean' &&
    'toggle' in overlay &&
    typeof overlay.toggle === 'function'
  )
}

function clarifyAnswers(raw: unknown, questions: Question[]): Record<string, string | null> {
  const answers: Record<string, string | null> = {}

  if (raw && typeof raw === 'object') {
    for (const q of questions) {
      const value: unknown = Reflect.get(raw, q.qid)

      if (typeof value === 'string' || value === null) {
        answers[q.qid] = value
      }
    }
  }

  return answers
}

function clarifyDraft(question: Question, answer: string | null | undefined): Draft {
  const draft: Draft = { other: new Composer(), picked: new Set(), selected: 0, typing: false }

  if (!answer) {
    return draft
  }

  let values: unknown = [answer]

  if (question.multi) {
    try {
      values = JSON.parse(answer)
    } catch {
      values = [answer]
    }
  }

  const choices = question.choices.map(choice => choice.replace(RECOMMENDED, ''))
  const other: string[] = []

  for (const value of Array.isArray(values) ? values : [answer]) {
    if (typeof value !== 'string') {
      continue
    }

    const index = choices.indexOf(value)

    if (index >= 0) {
      draft.selected = index
      draft.picked.add(index)
    } else {
      other.push(value)
    }
  }

  if (other.length) {
    draft.other.set(other.join('\n'))
    draft.typing = true
    draft.selected = choices.length
  }

  return draft
}

function optionsOf(q: Question, d: Draft): Option[] {
  return [
    ...q.choices.map((c, i) => ({
      checked: q.multi && d.picked.has(i),
      id: `option:${i}`,
      label: c.replace(RECOMMENDED, ''),
      recommended: RECOMMENDED.test(c),
      role: q.multi ? 'omp.ask.check' : 'omp.ask.option'
    })),
    { detail: d.other.text || 'Type your own answer', id: 'other', label: 'Other…', role: 'omp.ask.other' }
  ]
}

function clarifyOverlay(host: PromptHost, req: ServerRequest): ClarifyPrompt {
  const questions = questionsOf(req.params.questions)
  const answers = clarifyAnswers(req.params.answers, questions)
  const drafts = questions.map(q => clarifyDraft(q, answers[q.qid]))

  const notes = questions.map(
    q =>
      new ClarifyNotes(
        host,
        str(req.params.session_id),
        req.params.supports_notes === true,
        req.params.supports_image_refs === true,
        clarifyNoteOf(req.params.notes, q.qid)
      )
  )

  let hidden = false
  let settled = false
  let locking = false
  const live = () => !settled && host.owns(overlay)

  const finish = (result: ClarifyResult) => {
    if (live()) {
      req.respond({ ...result })
      host.close(overlay)
    }
  }

  let step = Math.max(
    0,
    questions.findIndex(q => !(q.qid in answers))
  )

  /** Records the current question's answer and moves to the next unanswered one, or submits. */
  const commit = async (answer: string | null) => {
    if (locking || !live() || notes.some(note => note.images?.blocked)) {
      if (live()) {
        host.notice('Wait for note images; retry or remove failed attachments before answering.')
      }

      return
    }

    const q = questions[step]

    if (!q) {
      return
    }

    const last = questions.every(other => other.qid === q.qid || other.qid in answers)

    if (!last && host.lockClarify) {
      locking = true
      host.changed()

      try {
        const ack = await host.lockClarify(req.id, q.qid, answer, notes[step]?.result())

        if (settled) {
          return
        }

        if (ack.status === 'expired' || ack.remaining?.length === 0) {
          host.close(overlay)

          return
        }
      } catch (error) {
        if (!settled) {
          host.notice(`Could not save clarification: ${error instanceof Error ? error.message : String(error)}`)
        }

        return
      } finally {
        locking = false
        host.changed()
      }
    }

    answers[q.qid] = answer

    const next = questions.findIndex((other, i) => i > step && !(other.qid in answers))
    const first = questions.findIndex(other => !(other.qid in answers))

    if (next >= 0 || first >= 0) {
      step = next >= 0 ? next : first
      host.changed()

      return
    }

    const extra = Object.fromEntries(
      questions.flatMap((question, i) => {
        const note = notes[i]?.result()

        return note ? [[question.qid, note]] : []
      })
    )

    finish(Object.keys(extra).length ? { answers, notes: extra } : { answers })
  }

  /** The answer the current question would get from Enter / Submit. */
  const submit = () => {
    const q = questions[step]
    const d = drafts[step]

    if (!q || !d) {
      return
    }

    const typed = d.other.text.trim()

    if (!q.choices.length) {
      return commit(typed || null)
    }

    if (!q.multi) {
      return commit(d.typing ? typed || null : (q.choices[d.selected]?.replace(RECOMMENDED, '') ?? null))
    }

    const picked = [...d.picked].sort((a, b) => a - b).map(i => q.choices[i]?.replace(RECOMMENDED, '') ?? '')

    // Nothing checked: Enter takes the highlighted row, as a single pick would.
    if (!picked.length && !typed && d.selected < q.choices.length) {
      picked.push(q.choices[d.selected]?.replace(RECOMMENDED, '') ?? '')
    }

    const values = typed ? [...picked, typed] : picked

    commit(values.length ? JSON.stringify(values) : null)
  }

  /** A click or Enter on row `i`: a radio answers, a checkbox toggles, Other starts typing. */
  const activate = (i: number) => {
    const q = questions[step]
    const d = drafts[step]

    if (!q || !d) {
      return
    }

    d.selected = i

    if (i >= q.choices.length) {
      d.typing = true
    } else if (q.multi && d.picked.has(i)) {
      d.picked.delete(i)
    } else if (q.multi) {
      d.picked.add(i)
    } else {
      d.typing = false

      return submit()
    }

    host.changed()
  }

  const go = (to: number) => {
    if (locking) {
      return
    }

    step = (to + questions.length) % questions.length
    host.changed()
  }

  const overlay: ClarifyPrompt = {
    key: `prompt:${req.id}`,
    placement: 'dock',
    get inputRevision() {
      return step * 2 + Number(hidden)
    },
    get hidden() {
      return hidden
    },
    toggle: () => {
      if (live()) {
        hidden = !hidden
        host.changed()
      }
    },
    onClose: () => {
      settled = true

      for (const note of notes) {
        note.images?.clear()
      }
    },
    get focus() {
      return hidden
        ? undefined
        : (id: string) => {
            if (notes[step]?.active) {
              return `${id}.body.notes.input`
            }

            const q = questions[step]
            const d = drafts[step]

            return q && d && (d.typing || !q.choices.length) ? `${id}.body.answer` : null
          }
    },
    node: id =>
      clarifyNode(id, {
        questions,
        drafts,
        answers,
        notes,
        step,
        hidden,
        locking,
        req,
        host,
        overlay,
        optionsOf,
        submit,
        commit,
        finish,
        activate,
        go
      }),
    onKey: k => {
      if (!live() || hidden) {
        return false
      }

      if (locking) {
        return true
      }

      const note = notes[step]!

      if (k.name === 'paste' && k.text && note.paste(k.text)) {
        return true
      }

      if (note.active && k.name !== 'enter' && k.name !== 'tab') {
        note.key(k)
        host.changed()

        return true
      }

      const q = questions[step]
      const d = drafts[step]

      if (!q || !d) {
        return true
      }

      const typing = d.typing || !q.choices.length
      const count = q.choices.length + 1

      if (k.name === 'tab' && questions.length > 1) {
        go(step + (k.shift ? -1 : 1))
      } else if (k.name === 'escape' && typing && q.choices.length) {
        // Leave the Other field first; Esc on the list skips the question.
        d.typing = false
      } else if (k.name === 'escape') {
        commit(null)
      } else if (k.name === 'enter' && (typing || (q.multi && d.selected < q.choices.length))) {
        submit()
      } else if (k.name === 'enter') {
        activate(d.selected)
      } else if (typing) {
        const to = q.choices.length ? moved(k, d.selected, count) : undefined

        if (to !== undefined) {
          d.typing = false
          d.selected = to
        } else if (k.name !== 'up' && k.name !== 'down') {
          d.other.key(k)
        }
      } else {
        const to = moved(k, d.selected, count)
        const n = Number.parseInt(k.name, 10)

        if (to !== undefined) {
          d.selected = to
        } else if (k.name === 'space' && q.multi) {
          activate(d.selected)
        } else if (n >= 1 && n <= count) {
          activate(n - 1)
        } else if (k.text && !k.ctrl && !k.meta && k.name !== 'space') {
          // Typing on the list starts the Other answer.
          d.selected = q.choices.length
          d.typing = true
          d.other.key(k)
        }
      }

      return true
    }
  }

  return overlay
}

interface ClarifyView {
  questions: Question[]
  drafts: Draft[]
  answers: Record<string, string | null>
  notes: ClarifyNotes[]
  step: number
  hidden: boolean
  locking: boolean
  req: ServerRequest
  host: PromptHost
  overlay: ClarifyPrompt
  optionsOf(q: Question, d: Draft): Option[]
  submit(): void
  commit(answer: string | null): Promise<void>
  finish(result: ClarifyResult): void
  activate(i: number): void
  go(to: number): void
}

function clarifyNode(id: string, cx: ClarifyView): JSX.Element {
  const {
    questions,
    drafts,
    answers,
    notes,
    step,
    hidden,
    locking,
    req,
    host,
    overlay,
    optionsOf,
    submit,
    commit,
    finish,
    activate,
    go
  } = cx

  const q = questions[step]
  const d = drafts[step]

  if (!q || !d) {
    return <col key={id.slice('dock.'.length)} role="omp.editor.ask" />
  }

  const freeText = !q.choices.length
  const last = questions.every((other, i) => i === step || other.qid in answers)
  const toggleHint = actionHint('app.clarify.toggle', host.bindings?.actions)

  if (hidden) {
    return (
      <col gap="xs" key={id.slice('dock.'.length)} role="omp.editor.ask">
        <text
          key="waiting"
          text={`Clarification waiting · ${Object.keys(answers).length}/${questions.length} answered`}
          tone="pending"
        />
        <text key="timer" role="omp.ask.timer" text={clarifyTimer(req.params.deadline_at)} />
        <ActionButton key="show" onClick={overlay.toggle} role="omp.btn" text={`Show question${toggleHint ? ` · ${toggleHint}` : ''}`} />
      </col>
    )
  }

  return (
    <col key={id.slice('dock.'.length)} role="omp.editor.ask">
      <col gap="md" key="body">
        <text key="timer" role="omp.ask.timer" text={clarifyTimer(req.params.deadline_at)} />
        {questions.length > 1 ? (
          <row align="center" gap="sm" key="head" role="omp.ask.head">
            <tabs
              active={String(step)}
              items={questions.map((other, i) => ({
                id: String(i),
                label: `${other.qid in answers ? '✓ ' : ''}${tabLabel(other.question)}`
              }))}
              key="tabs"
              onSelect={ev => {
                const to = Number(ev.item)

                if (Number.isInteger(to) && questions[to]) {
                  go(to)
                }
              }}
              role="omp.ask.questions"
            />
            <spacer grow={1} key="fill" />
            <text key="count" spans={[{ s: 'dim', t: `${step + 1} of ${questions.length}` }]} wrap="none" />
          </row>
        ) : null}
        <md key="question" role="omp.ask.question" text={q.question} />
        {locking ? <text key="saving" text="Saving answer…" tone="pending" /> : null}
        {freeText
          ? null
          : optionList(
              `q${step}`,
              `${id}.body.q${step}`,
              optionsOf(q, d),
              d.selected,
              i => {
                d.selected = i
                d.typing = i >= q.choices.length
                host.changed()
              },
              activate,
              q.question
            )}
        {freeText || d.typing ? (
          <input
            cursor={d.other.cursor}
            key="answer"
            onEdit={ev => {
              notes[step]!.active = false

              if (notes[step]?.paste(ev.text)) {
                host.changed()

                return
              }

              d.other.edit(ev)
              host.changed()
            }}
            onFocus={() => {
              notes[step]!.active = false
              host.changed()
            }}
            onUndo={() => {
              d.other.undo()
              host.changed()
            }}
            placeholder={freeText ? 'Type your answer' : 'Type your own answer'}
            role="omp.ask.input"
            text={d.other.text}
          />
        ) : null}
        {notes[step]?.node()}
        {actionsRow([
          { hint: toggleHint, key: 'hide', keys: toggleHint.split('+').filter(Boolean), label: 'Hide', onClick: overlay.toggle },
          { hint: '', key: 'cancel', keys: [], label: 'Cancel all', onClick: () => finish({}) },
          { hint: 'escape', key: 'skip', keys: ['escape'], label: 'Skip', onClick: () => commit(null) },
          {
            hint: `enter${q.multi && !d.typing ? ' · space toggles' : ''} · up/down move${questions.length > 1 ? ' · tab switches question' : ''}`,
            key: 'submit',
            keys: ['enter'],
            label: last ? 'Submit' : 'Next',
            onClick: submit,
            primary: true
          }
        ])}
      </col>
    </col>
  )
}

// ── Masked values ──────────────────────────────────────────────────────

interface Field {
  id: string
  label: string
  masked: boolean
  value: Composer
}

function maskedOverlay(host: OverlayHost, req: ServerRequest): Overlay {
  const p = req.params
  const key = `prompt:${req.id}`
  const site = str(p.site) || str(p.origin)
  const login = req.method === 'vault.save_login'

  const fields: Field[] = login
    ? [
        { id: 'identifier', label: 'Username or email', masked: false, value: new Composer() },
        { id: 'password', label: 'Password', masked: true, value: new Composer() }
      ]
    : [{ id: 'value', label: 'Hidden while you type', masked: true, value: new Composer() }]

  let at = 0

  const title =
    req.method === 'sudo'
      ? 'Password for sudo'
      : req.method === 'secret'
        ? str(p.prompt) || `Value for ${str(p.env_var) || 'a secret'}`
        : req.method === 'vault.unlock_prompt'
          ? `Master password for ${str(p.display_name) || str(p.backend) || 'the password manager'}`
          : login
            ? `Save a login for ${site || 'this site'}`
            : `Code for ${site || 'this site'}`

  const note = req.method === 'secret' ? str(p.env_var) : req.method === 'vault.code' ? str(p.hint) : ''

  // `''` is the contract's "skipped / declined".
  const finish = (cancel: boolean) => {
    const [first, second] = fields
    req.respond({
      value: cancel
        ? ''
        : login
          ? JSON.stringify({ identifier: first?.value.text ?? '', password: second?.value.text ?? '' })
          : (first?.value.text ?? '')
    })
    host.close(overlay)
  }

  const overlay: Overlay = {
    key,
    modal: true,
    focus: id => `${id}.body.${fields[at]?.id ?? 'value'}`,
    node: id => (
      <overlay anchor="bottom" key={id.slice('layer.'.length)} modal role="omp.overlay.ask" size="md">
        <col gap="md" key="body">
          <md key="question" role="omp.ask.question" text={title} />
          {note ? (
            <text key="note" spans={[{ s: req.method === 'secret' ? 'mono dim' : 'muted', t: note }]} wrap="word" />
          ) : null}
          {str(p.command) ? <code key="command" lang="bash" text={str(p.command)} /> : null}
          {fields.map((f, i) => (
            <input
              aria={f.label}
              cursor={f.masked ? maskedOffset(f.value.text, f.value.cursor) : f.value.cursor}
              key={f.id}
              onEdit={ev => {
                at = i
                const edit = f.masked ? unmaskEdit(f.value.text, ev) : ev

                if (edit) {
                  f.value.edit(edit)
                }

                host.changed()
              }}
              onFocus={() => {
                // A click in the other field: the keys follow the caret there.
                at = i
                host.changed()
              }}
              placeholder={f.label}
              role="omp.ask.input"
              text={f.masked ? maskOf(f.value.text) : f.value.text}
            />
          ))}
          {actionsRow([
            { hint: 'escape', key: 'cancel', keys: ['escape'], label: 'Cancel', onClick: () => finish(true) },
            {
              hint: 'enter',
              key: 'ok',
              keys: ['enter'],
              label: login ? 'Save' : 'Submit',
              onClick: () => finish(false),
              primary: true
            }
          ])}
        </col>
      </overlay>
    ),
    onKey: k => {
      if (k.name === 'escape') {
        finish(true)
      } else if (k.name === 'tab' && fields.length > 1) {
        at = (at + 1) % fields.length
      } else if (k.name === 'enter' && at < fields.length - 1) {
        at += 1
      } else if (k.name === 'enter') {
        finish(false)
      } else if (k.name !== 'up' && k.name !== 'down') {
        fields[at]?.value.key(k)
      }

      return true
    }
  }

  return overlay
}

// ── Confirm ────────────────────────────────────────────────────────────

/** A yes/no sheet for a choice the frontend itself must confirm (an expensive model switch). */
export function confirmOverlay(
  host: OverlayHost,
  ask: { title: string; detail: string; confirm: string; onConfirm(): void; onCancel?(): void }
): Overlay {
  const key = `confirm:${ask.title}`

  const answer = (yes: boolean) => {
    host.close(overlay)

    if (yes) {
      ask.onConfirm()
    } else {
      ask.onCancel?.()
    }
  }

  const overlay: Overlay = {
    key,
    modal: true,
    node: id => (
      <overlay anchor="bottom" key={id.slice('layer.'.length)} modal role="omp.overlay.ask" size="md">
        <col gap="md" key="body">
          <md key="question" role="omp.ask.question" text={ask.title} />
          {ask.detail ? <text key="detail" text={ask.detail} wrap="word" /> : null}
          {actionsRow([
            {
              hint: 'enter · escape',
              key: 'cancel',
              keys: ['enter', 'escape'],
              label: 'Cancel (default)',
              onClick: () => answer(false),
              primary: true
            },
            {
              hint: 'y',
              key: 'ok',
              keys: ['y'],
              label: ask.confirm,
              onClick: () => answer(true),
              primary: false
            }
          ])}
        </col>
      </overlay>
    ),
    onKey: k => {
      if (k.name === 'y') {
        answer(true)
      } else if (k.name === 'enter' || k.name === 'escape' || k.name === 'n') {
        answer(false)
      }

      return true
    }
  }

  return overlay
}
