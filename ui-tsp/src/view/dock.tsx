// The `dock` region: the working row while a turn runs, queued prompts, and
// the glass composer (omp.editor) with its model chip, effort, context
// hairline and session cost. Roles match omp's so Tern's composer sheets apply.

import type { EditEvent, ImageProps, JSX, SendEvent } from '@stencil-hq/tern'

import { type Action, actionHint } from '../actions.js'
import type { Attachment } from '../attachments.js'
import type { Dispatch } from '../attention.js'
import type { Composer } from '../composer.js'
import type { Dictation } from '../dictation.js'
import type { LiveVoice } from '../live-voice.js'
import type { Todo } from '../model.js'
import type { ReportNotice } from '../reports.js'

import { ActionButton } from './action-button.js'
import { composerAttachments } from './attachments.js'
import { age, compact } from './time.js'
import { checklistNode } from './tools.js'

function voiceSendDisabled(cx: DockContext) {
  const reason = cx.liveVoice?.blocked ? 'live voice active' : cx.dictation?.blocked ? 'dictation active' : ''

  return reason ? <text key="send-disabled" role="omp.composer.send.disabled" text={`Send disabled: ${reason}`} tone="muted" /> : null
}

/** What the dock shows. */
export interface DockContext {
  actions?: readonly Action[]
  profile?: string
  composer: Composer
  attachments?: readonly Attachment[]
  onAttachmentRemove?(id: string): void
  onAttachmentRetry?(id: string): void
  dictation?: Dictation
  liveVoice?: LiveVoice
  onDictation?(): void
  approval?: JSX.Element
  approvalQueued?: number
  /** The `editor` node's full id, for the caret overlay and focus. */
  inputId: string
  placeholder: string
  /** The agent accepts prompts (for Tern's `send`). */
  ready: boolean
  busy?: { since: object; startedAt: number; label: string }
  busyMode?: 'queue' | 'steer'
  queued: readonly string[]
  /** One current gateway-sourced plan for the visible session. */
  todos: readonly Todo[]
  todoExpanded: boolean
  onTodoToggle(): void
  dispatches: readonly Dispatch[]
  reports?: readonly ReportNotice[]
  onReportView?(id: string): void
  onReportDismiss?(id: string): void
  model: string
  /** Hermes's reasoning effort (`none` = off); empty hides the chip. */
  effort: string
  /** Working directory, already shortened for display. */
  cwd: string
  branch: string
  jobs: number
  onJobs(): void
  context?: { used: number; max: number }
  cost?: number
  ghost?: string
  now: number
  orb?: ImageProps
  onInterrupt(): void
  onSubmit(): void
  /** Tern submitted text into the composer (`send` feature). */
  onSend(ev: SendEvent): void
  /** Native editing: Tern replaced a range of the composer's text. */
  onEdit(ev: EditEvent): void
  onUndo(): void
  onModel(): void
  onEffort(): void
  onSettings(): void
  onDismiss(key: string): void
  /** Pull the oldest queued prompt back into the composer. */
  onQueueEdit(): void
  onContext(): void
}

/** The `dock` region's nodes: the working row, the queued prompts and the composer. */
export function dockNodes(cx: DockContext): JSX.Element[] {
  const nodes: JSX.Element[] = []

  if (cx.todos.length > 5) {
    // Count only completed tasks: Tern's native HUD also counts dropped items.
    const done = cx.todos.filter(todo => todo.status === 'completed').length
    const active = cx.todos.find(todo => todo.status === 'in_progress')
    nodes.push(
      <ActionButton
        key="plan-summary"
        onClick={cx.onTodoToggle}
        role="omp.todo.summary"
        text={`${done}/${cx.todos.length} done${active ? ` · now: ${active.content}` : ''}`}
        title={cx.todoExpanded ? 'Collapse current plan' : 'Expand current plan'}
        wrap="none"
      />
    )
  }

  if (cx.todos.length && (cx.todos.length <= 5 || cx.todoExpanded)) {
    nodes.push(checklistNode(cx.todos, 'full', 'current-plan'))
  }

  if (cx.busy) {
    nodes.push(
      <col key="hud" role="omp.hud.status">
        {workingNode(cx)}
      </col>
    )
  }

  if (cx.dispatches.length) {
    nodes.push(
      <col gap="xs" key="dispatches" role="omp.dispatches">
        {cx.dispatches.map(note => (
          <row align="center" gap="xs" key={`note.${note.serial}`} role="omp.dispatch">
            <icon key="glyph" name="info" />
            <text grow={1} key="text" role="omp.dispatch.message" text={note.text} />
            <ActionButton
              aria="Dismiss notice"
              key="dismiss"
              onClick={() => cx.onDismiss(note.key)}
              role="omp.dispatch.dismiss"
              text="×"
              title="Dismiss notice"
            />
          </row>
        ))}
      </col>
    )
  }

  for (const report of cx.reports ?? []) {
    nodes.push(
      <row align="center" gap="xs" key={`report.${report.id}`} role="omp.report.notice">
        <text key="label" text={`${report.label} ·`} tone={report.failed ? 'error' : 'muted'} />
        <ActionButton key="view" onClick={() => cx.onReportView?.(report.id)} role="omp.report.view" text="View" title={`View report: ${report.title}`} />
        <spacer grow={1} key="fill" />
        <ActionButton key="dismiss" onClick={() => cx.onReportDismiss?.(report.id)} role="omp.dispatch.dismiss" text="×" title="Dismiss report" />
      </row>
    )
  }

  if (cx.queued.length) {
    nodes.push(
      <col gap="xs" key="queue" role="omp.queue">
        {cx.queued.map((text, i) => (
          <row align="center" gap="sm" key={`q${i}`} role="omp.queue.item" title="Queued">
            <icon key="icon" name="corner-down-right" />
            <text grow={1} key="text" text={text.replace(/\s*\r?\n\s*/g, ' ↵ ')} truncate="end" wrap="none" />
            {i === 0 && cx.queued.length > 1 ? (
              <badge key="count" role="omp.queue.count" text={`${cx.queued.length}`} />
            ) : null}
            <ActionButton align="center" gap="xs" key="edit" onClick={cx.onQueueEdit} role="omp.queue.edit" title={`Edit  ${actionHint('app.message.dequeue', cx.actions)}`}>
              <kbd key="k" keys={actionHint('app.message.dequeue', cx.actions).split('+').filter(Boolean)} />
              <text key="t" text="Edit" />
            </ActionButton>
          </row>
        ))}
      </col>
    )
  }

  if (cx.approval) {
    nodes.push(cx.approval)

    if (cx.approvalQueued) {
      nodes.push(<text key="approval-queued" role="omp.editor.ask.approval.queued" text={`${cx.approvalQueued} more`} />)
    }
  }

  nodes.push(composerNode(cx))

  return nodes
}

function workingNode(cx: DockContext): JSX.Element {
  const busy = cx.busy!

  return (
    // Same order as omp's describeWorkingRow: spinner, elapsed, divider, intent.
    // The orb is an extra; this spinner is the indicator every Tern client draws.
    <row align="center" gap="sm" key="working" role="omp.working">
      <spinner key="spinner" style="starburst" tone="accent" />
      <elapsed age={age(busy.since, busy.startedAt, cx.now)} format="short" key="elapsed" />
      <text key="sep" role="omp.working.sep" text="·" />
      <shimmer
        key="label"
        mode="classic"
        palette={{ high: 'accent', low: 'dim', mid: 'muted' }}
        role="omp.working.label"
        spans={[{ s: 'muted', t: busy.label }]}
      />
      <row grow={1} key="fill" />
      <ActionButton align="center" gap="xs" key="stop" onClick={cx.onInterrupt} role="omp.working.stop" title={`Stop  ${actionHint('app.interrupt', cx.actions)}`}>
        <kbd key="k" keys={actionHint('app.interrupt', cx.actions).split('+').filter(Boolean)} />
        <text key="t" text="Stop" />
      </ActionButton>
    </row>
  )
}

/** The effort level as omp names it: hermes's `none` is `off`. */
function effortLabel(effort: string): string {
  return effort === 'none' ? 'off' : effort
}

/** A path dim up to its last component, like omp's path segment. */
function pathSpans(path: string): { s: string; t: string }[] {
  const slash = path.lastIndexOf('/', path.length - 2)

  if (slash < 0 || slash + 1 >= path.length) {
    return [{ s: 'statusLinePath strong', t: path }]
  }

  return [
    { s: 'statusLinePath dim', t: path.slice(0, slash + 1) },
    { s: 'statusLinePath strong', t: path.slice(slash + 1) }
  ]
}

function composerNode(cx: DockContext): JSX.Element {
  const { composer } = cx
  const ctx = cx.context
  const share = ctx && ctx.max > 0 ? ctx.used / ctx.max : undefined

  return (
    <col key="composer" role="omp.editor">
      {share === undefined ? null : (
        <meter
          aria="Context window usage"
          key="context"
          label={`${Math.round(share * 100)}%`}
          role="omp.composer.context"
          style="bar"
          thresholds={{ bad: 0.85, warn: 0.6 }}
          title={`Context ${Math.round(share * 100)}% used\n${compact(ctx!.used)} of ${compact(ctx!.max)} tokens`}
          total={compact(ctx!.max)}
          value={share}
        />
      )}
      {cx.liveVoice?.view()}
      {composerAttachments(cx.attachments ?? [], id => cx.onAttachmentRemove?.(id), id => cx.onAttachmentRetry?.(id))}
      {cx.dictation && cx.dictation.state !== 'idle' ? (
        <col key="dictation" role={`omp.composer.mic.${cx.dictation.state}`}>
          <text key="status" text={cx.dictation.label} tone={cx.dictation.state === 'error' ? 'error' : 'muted'} />
          {cx.dictation.partial ? <text key="partial" role="omp.composer.mic.partial" text={cx.dictation.partial} /> : null}
        </col>
      ) : null}
      <row align="start" gap="sm" key="line" role="omp.composer.line">
        {cx.orb ? <image key="orb" {...cx.orb} role="hermes.agent.orb" /> : null}
        <editor
          anchor={composer.vim.selection.anchor}
          cursor={composer.vim.selection.cursor}
          ghost={cx.ghost || undefined}
          key="input"
          maxLines={18}
          mode={composer.vim.nativeMode}
          onEdit={cx.onEdit}
          onSend={cx.onSend}
          onUndo={cx.onUndo}
          placeholder={cx.placeholder}
          sendable={cx.ready}
          text={composer.text}
        />
      </row>
      <row align="center" gap="sm" key="bar" role="omp.composer.bar">
        {/* Context/Settings must survive phone widths. The host retains at least
            the highest-priority segment, even if it is wider than the row, so
            the unbounded model name must never be that last survivor. */}
        <status basis={0} grow={1} key="hints" min={{ w: 0 }} role="omp.composer.extras" transparent>
          {composer.vim.enabled ? <seg key="vim" priority={110} role="omp.composer.vim" text={`${composer.vim.mode.toUpperCase()}${composer.vim.pending ? ` ${composer.vim.pending}` : ''}`} /> : null}
          {share === undefined ? null : (
            <seg key="context-details" priority={115}>
              <ActionButton aria="Show context window" key="action" onClick={cx.onContext} role="omp.composer.context.action" text="Context" title={actionHint('app.context', cx.actions)} />
            </seg>
          )}
          {cx.model ? (
            <seg key="model" priority={100}>
              <ActionButton
                align="center"
                gap="xs"
                key="model"
                onClick={cx.onModel}
                role="omp.composer.model"
                title={`Model: ${cx.model} · click to switch`}
              >
                <icon key="icon" name="model" />
                <text key="name" spans={[{ t: cx.model }]} wrap="none" />
                <icon key="chev" name="chev" />
              </ActionButton>
            </seg>
          ) : null}
          {cx.effort ? (
            <seg key="effort" priority={50}>
              <ActionButton
                align="center"
                gap="xs"
                key="effort"
                onClick={cx.onEffort}
                role="omp.composer.effort"
                title={`Reasoning effort: ${effortLabel(cx.effort)} · click to cycle  ${actionHint('app.thinking.cycle', cx.actions)}`}
              >
                <effort key="glyph" level={effortLabel(cx.effort)} />
                <text key="level" text={effortLabel(cx.effort)} wrap="none" />
              </ActionButton>
            </seg>
          ) : null}
          {cx.profile ? <seg key="profile" priority={30} role="omp.composer.profile" text={cx.profile} title={`Owning Hermes profile: ${cx.profile}`} /> : null}
          {cx.cwd ? (
            <seg
              icon="folder"
              key="cwd"
              priority={20}
              role="omp.composer.fact"
              spans={pathSpans(cx.cwd)}
              title={cx.cwd}
            />
          ) : null}
          {cx.branch ? (
            <seg
              icon="git-branch"
              key="git"
              priority={10}
              role="omp.composer.fact"
              spans={[{ s: 'statusLineGitClean', t: cx.branch }]}
              title={`Branch ${cx.branch}`}
            />
          ) : null}
          {cx.jobs > 0 ? (
            <seg key="jobs" priority={80}>
              <ActionButton aria="Background jobs" key="action" onClick={cx.onJobs} role="omp.composer.jobs" text={`${cx.jobs} ${cx.jobs === 1 ? 'job' : 'jobs'}`} />
            </seg>
          ) : null}
          {cx.dictation ? (
            <seg key="mic" priority={60}>
              <ActionButton key="action" onClick={cx.onDictation} role="omp.composer.mic" text={cx.dictation.state === 'recording' ? 'Finish dictation' : 'Mic'} title={`${cx.dictation.label} · ${actionHint('app.stt.toggle', cx.actions)}`} />
            </seg>
          ) : null}
          <seg key="help" priority={0} role="omp.composer.hint" text={cx.approval ? 'Enter deny and steer' : cx.busy ? `Enter ${cx.busyMode === 'steer' ? 'steer' : 'queue'} · ${actionHint('app.message.alternate', cx.actions) || '(unbound)'} ${cx.busyMode === 'steer' ? 'queue' : 'steer'}` : `${actionHint('app.help', cx.actions) || '/help'} help`} tone="muted" />
          <seg key="settings" priority={120}>
            <ActionButton align="center" gap="xs" key="action" onClick={cx.onSettings} role="omp.composer.settings" title="Open Hermes settings">
              <icon key="icon" name="settings" />
              <text key="label" text="Settings" wrap="none" />
            </ActionButton>
          </seg>
          {cx.cost ? (
            <seg
              key="usage"
              priority={40}
              role="omp.composer.usage"
              text={`$${cx.cost.toFixed(2)}`}
              title="Session cost"
            />
          ) : null}
        </status>
        {voiceSendDisabled(cx) ?? (cx.busy ? (
          <ActionButton
            key="stop"
            onClick={cx.onInterrupt}
            role="omp.composer.stop"
            text="Stop"
            title={`Stop  ${actionHint('app.interrupt', cx.actions)}`}
            tone="error"
          />
        ) : (
          <ActionButton disabled={!cx.ready} key="send" keys={['enter']} onClick={cx.onSubmit} role="omp.composer.send" title="Send  ⏎" />
        ))}
      </row>
    </col>
  )
}
