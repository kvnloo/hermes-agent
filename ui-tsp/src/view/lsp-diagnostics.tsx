import type { LspSymbol } from '@hermes/shared/gateway-events'
import type { JSX, TreeItem } from '@stencil-hq/tern'

import { displayText } from '../display-text.js'
import { fileHref } from '../links.js'
import { parseLspResult } from '../lsp-result.js'
import { record } from '../transcript.js'

const severities = {
  error: { label: 'error', marker: '●', style: 'error' },
  warn: { label: 'warning', marker: '▲', style: 'warning' },
  info: { label: 'info', marker: 'ℹ', style: 'muted' },
  hint: { label: 'hint', marker: '·', style: 'dim' }
}

type Severity = keyof typeof severities

interface Diagnostic {
  severity: Severity
  line: number
  col: number
  message: string
}

interface FileDiagnostics {
  path: string
  diagnostics: Diagnostic[]
  omitted: number
}

interface Unavailable {
  path: string
  message: string
}

interface Diagnostics {
  files: FileDiagnostics[]
  unavailable: Unavailable[]
}

function severity(value: unknown): Severity | undefined {
  switch (value) {
    case 'error':

    case 'warn':

    case 'info':

    case 'hint':
      return value

    default:
      return undefined
  }
}

function positive(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value > 0
}

/** Validate the Python companion field once; malformed/old payloads keep the legacy text. */
function parse(value: unknown): Diagnostics | undefined {
  if (!Array.isArray(value)) {return undefined}
  const files = new Map<string, FileDiagnostics>()
  const unavailable: Unavailable[] = []

  for (const item of value) {
    const file = record(item)

    if (!file || typeof file.path !== 'string') {return undefined}

    if (file.status === 'unavailable' && typeof file.message === 'string') {
      unavailable.push({ message: file.message, path: file.path })

      continue
    }

    if (file.status !== 'ok' || !Array.isArray(file.diagnostics)) {return undefined}
    const group = files.get(file.path) ?? { diagnostics: [], omitted: 0, path: file.path }

    for (const item of file.diagnostics) {
      const row = record(item)
      const tone = severity(row?.severity)

      if (!row || !tone || !positive(row.line) || !positive(row.col) || typeof row.message !== 'string') {
        return undefined
      }

      group.diagnostics.push({ col: row.col, line: row.line, message: row.message, severity: tone })
    }

    group.omitted += positive(file.omitted) ? file.omitted : 0
    files.set(file.path, group)
  }

  return { files: [...files.values()], unavailable }
}

function summary(rows: Diagnostic[]): string {
  const counts: Record<Severity, number> = { error: 0, hint: 0, info: 0, warn: 0 }

  for (const row of rows) {counts[row.severity]++}

  return (Object.keys(severities).filter((key): key is Severity => key in counts))
    .filter(key => counts[key] > 0)
    .map(key => `${counts[key]} ${severities[key].label}${counts[key] === 1 ? '' : 's'}`)
    .join(' · ')
}

/** Native sections own click-to-expand; no frontend store or idle work is needed. */
export function lspDiagnostics(result: Record<string, unknown> | undefined, cwd: string): JSX.Element[] {
  const parsed = parse(result?.lsp_diagnostics_data)

  if (!parsed) {
    const legacy = result?.lsp_diagnostics

    return typeof legacy === 'string' && legacy
      ? [<text key="lsp" role="omp.tool.notice" spans={[{ s: 'muted', t: displayText(legacy) }]} wrap="word" />]
      : []
  }

  const rows = parsed.files.flatMap(file => file.diagnostics)
  const body: JSX.Element[] = []

  if (rows.length || parsed.files.some(file => file.omitted)) {
    body.push(
      <section collapsed={rows.length > 8} collapsible head={[{ s: 'chip', t: summary(rows) || 'LSP diagnostics' }]} key="lsp" role="omp.tool.diagnostics">
        {parsed.files.filter(file => file.diagnostics.length || file.omitted).map((file, i) => (
          <col key={`f${i}`} role="omp.tool.diagnostics.file">
            <row key="head" role="omp.tool.file">
              <text href={fileHref(file.path, cwd)} key="path" spans={[{ s: 'path', t: displayText(file.path) }]} />
              <text key="count" role="omp.tool.chip" text={String(file.diagnostics.length)} />
            </row>
            {file.diagnostics.map((diagnostic, j) => {
              const look = severities[diagnostic.severity]
              const href = fileHref(file.path, cwd, { col: diagnostic.col, line: diagnostic.line })

              return (
                <row href={href} key={`d${j}`} role="omp.tool.diagnostic">
                  <text key="severity" role={`omp.tool.diagnostic.${diagnostic.severity}`} spans={[{ s: look.style, t: look.marker }]} title={look.label} />
                  <text href={href} key="location" spans={[{ s: 'muted mono', t: `${diagnostic.line}:${diagnostic.col}` }]} />
                  <text key="message" text={displayText(diagnostic.message)} wrap="word" />
                </row>
              )
            })}
            {file.omitted ? <text key="omitted" role="omp.tool.notice" spans={[{ s: 'muted', t: `${file.omitted} additional diagnostics omitted` }]} /> : null}
          </col>
        ))}
      </section>
    )
  }

  body.push(...parsed.unavailable.map((note, i) => (
    <text key={`lsp-unavailable-${i}`} role="omp.tool.diagnostics.unavailable" spans={[{ s: 'muted', t: displayText(`${note.path}: ${note.message}`) }]} wrap="word" />
  )))

  return body
}

/** Typed semantic results come only from Hermes; old/foreign result prose stays on the generic card. */
export function lspResult(value: unknown, cwd: string, hostLocal: boolean): JSX.Element[] | undefined {
  const result = parseLspResult(value)

  if (!result) { return undefined }

  const link = (path: string, span?: { start: { line: number; col: number }; end: { line: number; col: number } }) => hostLocal
    ? fileHref(path, cwd, span ? { line: span.start.line, col: span.start.col, endLine: span.end.line } : undefined)
    : undefined

  const body: JSX.Element[] = [
    <text href={link(result.path)} key="path" role="omp.tool.file" text={result.path} wrap="word" />,
    <text key="server" role="omp.tool.context" text={`Server: ${result.server ?? 'unavailable'} · UTF-16 positions`} wrap="word" />
  ]

  switch (result.kind) {
    case 'references': {
      const groups = new Map<string, typeof result.locations>()

      for (const location of result.locations) {
        const rows = groups.get(location.path) ?? []
        rows.push(location)
        groups.set(location.path, rows)
      }

      body.push(<text key="summary" role="omp.tool.lsp.summary" text={result.locations.length ? `${result.locations.length} references · ${groups.size} files` : 'No references found (checked)'} wrap="word" />)
      body.push(...[...groups].map(([path, locations], i) => (
        <col key={`f${i}`} role="omp.tool.references.file">
          <text href={link(path)} key="path" role="omp.tool.file" text={`${path} · ${locations.length}`} wrap="word" />
          {locations.map((location, j) => (
            <text href={link(path, location.range)} key={`r${j}`} role="omp.tool.reference"
              text={`${location.range.start.line}:${location.range.start.col}–${location.range.end.line}:${location.range.end.col}`} wrap="word" />
          ))}
        </col>
      )))

      break
    }

    case 'symbols': {
      // The SDK tree's stable item ids and linked label spans survive stored-result replay.
      const item = (symbol: LspSymbol): TreeItem => ({
        id: symbol.id,
        label: [{ s: 'accent', t: symbol.name, href: link(symbol.location.path, symbol.selection) },
          { s: 'muted', t: ` · kind ${symbol.kind} · ${symbol.selection.start.line}:${symbol.selection.start.col}` }],
        open: true,
        children: symbol.children.map(item)
      })

      const locations = (symbols: LspSymbol[]): JSX.Element[] => symbols.flatMap(symbol => [
        <text href={link(symbol.location.path, symbol.selection)} key={`s${symbol.id}`} role="omp.tool.symbol.location"
          text={`${symbol.name} · ${symbol.location.path} · ${symbol.location.range.start.line}:${symbol.location.range.start.col}–${symbol.location.range.end.line}:${symbol.location.range.end.col}`} wrap="word" />,
        ...locations(symbol.children)
      ])

      body.push(result.symbols.length
        ? <col key="symbol-view"><tree key="symbols" nodes={result.symbols.map(item)} role="omp.tool.symbols" />{locations(result.symbols)}</col>
        : <text key="empty" role="omp.tool.lsp.summary" text="No symbols found (checked)" wrap="word" />)

      break
    }

    case 'hover':
      if (result.range) {
        body.push(<text href={link(result.path, result.range)} key="range" role="omp.tool.hover.range"
          text={`${result.range.start.line}:${result.range.start.col}–${result.range.end.line}:${result.range.end.col}`} wrap="word" />)
      }

      body.push(...result.contents.map((content, i) => content.format === 'markdown'
        ? <md key={`h${i}`} role="omp.tool.hover">{content.text}</md>
        : content.format === 'code'
          ? <code key={`h${i}`} lang={content.language ?? undefined} role="omp.tool.hover" text={content.text} wrap />
          : <text key={`h${i}`} role="omp.tool.hover" text={content.text} wrap="word" />))

      if (!result.contents.length) {
        body.push(<text key="empty" role="omp.tool.lsp.summary" text="No hover information (checked)" wrap="word" />)
      }

      break

    case 'error':

    case 'unavailable':
      body.push(<text key="failure" role={`omp.tool.lsp.${result.kind}`} text={`${result.operation}: ${result.message}`} tone={result.kind === 'error' ? 'error' : 'muted'} wrap="word" />)

      break
    default: {
      const exhaustive: never = result

      return exhaustive
    }
  }

  if (!hostLocal) {
    body.push(<text key="remote" role="omp.tool.notice" text="File targets are not confirmed host-local; links disabled." wrap="word" />)
  }

  return body
}
