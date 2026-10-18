import type { LspHoverContent, LspLocation, LspQueryResult, LspRange, LspSymbol } from '@hermes/shared/gateway-events'

import { record } from './transcript.js'

type LspResult = LspQueryResult['lsp_result']

const positive = (value: unknown): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value > 0
const operation = (value: unknown): value is 'references' | 'symbols' | 'hover' => value === 'references' || value === 'symbols' || value === 'hover'

function range(value: unknown): LspRange | undefined {
  const row = record(value)
  const start = record(row?.start)
  const end = record(row?.end)

  if (!start || !end || !positive(start.line) || !positive(start.col) || !positive(end.line) || !positive(end.col) ||
      end.line < start.line || (end.line === start.line && end.col < start.col)) { return undefined }

  return { start: { line: start.line, col: start.col }, end: { line: end.line, col: end.col } }
}

function location(value: unknown): LspLocation | undefined {
  const row = record(value)
  const span = range(row?.range)

  return row && typeof row.path === 'string' && span ? { path: row.path, range: span } : undefined
}

function array<T>(value: unknown, parse: (item: unknown) => T | undefined): T[] | undefined {
  if (!Array.isArray(value)) { return undefined }
  const parsed: T[] = []

  for (const item of value) {
    const row = parse(item)

    if (row === undefined) { return undefined }
    parsed.push(row)
  }

  return parsed
}

function symbols(value: unknown, seen: Set<string>, depth = 0): LspSymbol[] | undefined {
  if (depth > 128) { return undefined }

  return array(value, item => {
    const row = record(item)
    const target = location(row?.location)
    const selection = range(row?.selection)

    if (!row || typeof row.id !== 'string' || !row.id || seen.has(row.id) || typeof row.name !== 'string' ||
        !positive(row.kind) || row.kind > 26 || !target || !selection) { return undefined }

    seen.add(row.id)
    const children = symbols(row.children, seen, depth + 1)

    return children ? { id: row.id, name: row.name, kind: row.kind, location: target, selection, children } : undefined
  })
}

function content(value: unknown): LspHoverContent | undefined {
  const row = record(value)

  if (!row || typeof row.text !== 'string' || (row.language !== null && row.language !== undefined && typeof row.language !== 'string')) { return undefined }

  if (row.format !== 'code' && row.format !== 'markdown' && row.format !== 'plaintext') { return undefined }

  return { format: row.format, text: row.text, language: row.language }
}

/** Stored and live results cross the same validation boundary; no parsing semantic data from prose. */
export function parseLspResult(value: unknown): LspResult | undefined {
  const row = record(value)

  if (!row || typeof row.path !== 'string' || (row.server !== null && typeof row.server !== 'string') || row.position_encoding !== 'utf-16') { return undefined }
  const base = { path: row.path, server: row.server, position_encoding: 'utf-16' as const }

  switch (row.kind) {
    case 'references': {
      const locations = array(row.locations, location)

      return locations ? { ...base, kind: row.kind, locations } : undefined
    }

    case 'symbols': {
      const parsed = symbols(row.symbols, new Set())

      return parsed ? { ...base, kind: row.kind, symbols: parsed } : undefined
    }

    case 'hover': {
      const contents = array(row.contents, content)
      const span = row.range === null ? null : range(row.range)

      return contents && span !== undefined ? { ...base, kind: row.kind, contents, range: span } : undefined
    }

    case 'error':

    case 'unavailable':
      return operation(row.operation) && typeof row.message === 'string'
        ? { ...base, kind: row.kind, operation: row.operation, message: row.message }
        : undefined

    default:
      return undefined
  }
}
