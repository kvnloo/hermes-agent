import type { EvalCell, EvalView, EvalWork } from '@hermes/shared/gateway-events'
import { type JSX, node } from '@stencil-hq/tern'

import { evalOutputParts } from '../eval.js'
import type { ToolCall } from '../model.js'
import { record } from '../transcript.js'

import { outputLineCount, runBox, type RunBoxInput, runState, type RunState } from './runbox.js'

const CELL_STATE: Record<EvalCell['status'], RunState> = {
  pending: 'unknown', running: 'running', done: 'ok', error: 'error',
  cancelled: 'cancelled', timeout: 'timeout', background: 'background'
}

export function evalRunState(call: ToolCall): RunState | undefined {
  const outer = runState(call, record(call.result))

  if (['error', 'timeout', 'exit', 'cancelled'].includes(outer)) { return outer }

  const cells = call.eval?.cells ?? []

  // A finished outer invocation can still own background work or a failed cell.
  const outcome = (['error', 'timeout', 'cancelled', 'running', 'background', 'pending'] as const)
    .find(status => cells.some(cell => cell.status === status))

  return outcome ? CELL_STATE[outcome] : undefined
}

function printedView(view: EvalView): JSX.Element {
  const builders: Record<EvalView['kind'], () => JSX.Element> = {
    markdown: () => <md key={view.id} role="omp.tool.eval.markdown">{view.printed}</md>,
    json: () => <code key={view.id} lang="json" role="omp.tool.eval.json" text={view.printed} wrap />,
    table: () => node('table', {
      key: view.id, role: 'omp.tool.eval.table',
      cols: (view.columns ?? []).map((head, i) => ({ id: `c${i}`, head })),
      rows: (view.rows ?? []).map((cells, i) => ({ id: `r${i}`, cells: Object.fromEntries(cells.map((text, c) => [`c${c}`, text])) }))
    })
  }

  return builders[view.kind]()
}

/** Every observed state remains outside output folding; parent links never infer new work. */
function workNodes(events: readonly EvalWork[]): JSX.Element[] {
  const byId = new Map(events.map(event => [event.id, event]))
  const children = new Map<string, EvalWork[]>()
  const roots: EvalWork[] = []

  for (const event of events) {
    let parent = event.parent_id && byId.has(event.parent_id) ? event.parent_id : undefined
    let ancestor = parent
    const seen = new Set([event.id])

    while (ancestor) {
      if (seen.has(ancestor)) { parent = undefined;

 break }

      seen.add(ancestor)
      ancestor = byId.get(ancestor)?.parent_id ?? undefined
    }

    if (parent) { children.set(parent, [...(children.get(parent) ?? []), event]) }
    else { roots.push(event) }
  }

  const render = (event: EvalWork): JSX.Element => <col gap="none" key={event.id} role="omp.tool.eval.status.event">
    <text key="state" role="omp.tool.eval.status" spans={[
      { s: event.status === 'error' ? 'error' : event.status === 'running' ? 'pending' : 'muted', t: `${event.tool} · ${event.status}` }
    ]} wrap="word" />
    {event.preview ? <text key="preview" text={event.preview} wrap="word" /> : null}
    {(children.get(event.id) ?? []).map(render)}
  </col>

  return roots.map(render)
}

export function evalRuns(call: ToolCall, literalOutput: string | undefined, presentation: Pick<RunBoxInput, 'collapsed' | 'onToggle'>): JSX.Element[] | undefined {
  const cells = call.eval?.cells

  if (!cells?.length) { return undefined }

  // Captures can be clipped/rewritten after the producer emitted its companion.
  // Never use a rich copy to restore missing stdout or silently discard retained text.
  const matched = call.status === 'running' || cells.map(cell => cell.output ?? '').join('') === (literalOutput ?? '')
  const result = record(call.result)

  return cells.map((cell, i) => {
    const output = matched ? cell.output ?? '' : i === 0 ? literalOutput ?? '' : ''
    const views = matched || cells.length === 1 ? cell.views ?? [] : []
    const lines = outputLineCount(output)
    const error = cell.error ?? (i === 0 && typeof result?.error === 'string' ? result.error : undefined)

    return runBox({
      ...presentation, runKey: cell.id, command: cell.code, language: cell.language,
      output, error, state: CELL_STATE[cell.status], truncated: lines > 8,
      previewLines: 8, previewSide: 'first',
      captureTruncated: result?.stdout_truncated === true || output.includes('[tool result truncated]'),
      captureNote: output.includes('[tool result truncated]') ? 'display truncated: retained output only' : undefined,
      background: cell.status === 'background',
      statusNodes: [
        ...(cell.status === 'pending' ? [<text key="pending" role="omp.tool.eval.status" text="pending" />] : []),
        ...workNodes(cell.events ?? [])
      ],
      renderOutput: visible => evalOutputParts(visible, views).map(part => part.kind === 'view'
        ? printedView(part.view)
        : <code key={part.key} lang="text" role="omp.run.output" text={part.text} wrap />)
    })
  })
}
