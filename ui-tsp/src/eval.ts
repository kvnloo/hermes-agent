import type { EvalCell, EvalDisplay, EvalView, EvalWork } from '@hermes/shared/gateway-events'

import { record } from './transcript.js'

const states = new Set(['pending', 'running', 'done', 'error', 'cancelled', 'timeout', 'background'])
const stringList = (v: unknown): v is string[] => Array.isArray(v) && v.every(item => typeof item === 'string')

function work(value: unknown): EvalWork | undefined {
  const r = record(value)

  if (!r || typeof r.id !== 'string' || !r.id || typeof r.tool !== 'string' ||
    typeof r.status !== 'string' || r.status === 'pending' || !states.has(r.status) ||
    (r.parent_id != null && typeof r.parent_id !== 'string') ||
    (r.preview !== undefined && typeof r.preview !== 'string')) { return undefined }

  return r as unknown as EvalWork // The wire discriminant and every consumed field were checked above.
}

function view(value: unknown): EvalView | undefined {
  const r = record(value)

  if (!r || typeof r.id !== 'string' || !r.id || typeof r.printed !== 'string' || !r.printed ||
    typeof r.start !== 'number' || !Number.isSafeInteger(r.start) || r.start < 0 ||
    !['json', 'markdown', 'table'].includes(String(r.kind))) { return undefined }

  if (r.kind === 'table' && (!stringList(r.columns) || !r.columns.length || !Array.isArray(r.rows) ||
    !r.rows.every(row => stringList(row) && row.length === (r.columns as string[]).length))) { return undefined }

  if (r.kind === 'json') {
    try { JSON.parse(r.printed) } catch { return undefined }
  }

  return r as unknown as EvalView
}

/** Optional companions are untrusted on history too; invalid entries leave literal output intact. */
export function evalCell(value: unknown): EvalCell | undefined {
  const r = record(value)

  if (!r || typeof r.id !== 'string' || !r.id || typeof r.code !== 'string' ||
    typeof r.status !== 'string' || !states.has(r.status) ||
    (r.output !== undefined && typeof r.output !== 'string') ||
    (r.language !== undefined && typeof r.language !== 'string') ||
    (r.error != null && typeof r.error !== 'string')) { return undefined }

  return {
    id: r.id, code: r.code, status: r.status as EvalCell['status'],
    output: typeof r.output === 'string' ? r.output : '',
    language: typeof r.language === 'string' ? r.language : 'python',
    error: typeof r.error === 'string' ? r.error : undefined,
    events: unique((Array.isArray(r.events) ? r.events : []).map(work).filter(e => e !== undefined)),
    views: unique((Array.isArray(r.views) ? r.views : []).map(view).filter(e => e !== undefined))
  }
}

export function evalDisplay(value: unknown): EvalDisplay | undefined {
  const r = record(value)

  if (!r || r.version !== 1 || !Array.isArray(r.cells)) { return undefined }

  const cells = r.cells.map(evalCell)

  if (cells.some(cell => !cell)) { return undefined }

  return { version: 1, cells: unique(cells.filter(cell => cell !== undefined)) }
}

function unique<T extends { id: string }>(items: T[]): T[] {
  const seen = new Set<string>()

  return items.filter(item => {
    if (seen.has(item.id)) { return false }
    seen.add(item.id)

    return true
  })
}

export type EvalOutputPart = { kind: 'text'; text: string; key: string } | { kind: 'view'; view: EvalView; key: string }

/** No substring search: repeated text must not steal another print's view. */
export function evalOutputParts(output: string, views: readonly EvalView[]): EvalOutputPart[] {
  const points = Array.from(output)
  const parts: EvalOutputPart[] = []
  let cursor = 0

  for (const entry of [...views].sort((a, b) => a.start - b.start)) {
    const end = entry.start + Array.from(entry.printed).length

    if (entry.start < cursor || points.slice(entry.start, end).join('') !== entry.printed ||
      entry.printed.includes('[tool result truncated]')) { continue }

    if (entry.start > cursor) { parts.push({ kind: 'text', text: points.slice(cursor, entry.start).join(''), key: `text-${cursor}` }) }
    parts.push({ kind: 'view', view: entry, key: entry.id })
    cursor = end
  }

  if (cursor < points.length) { parts.push({ kind: 'text', text: points.slice(cursor).join(''), key: `text-${cursor}` }) }

  return parts
}
