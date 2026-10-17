import type { JSX } from '@stencil-hq/tern'

import { fileHref } from '../links.js'
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
      ? [<text key="lsp" role="omp.tool.notice" spans={[{ s: 'muted', t: legacy }]} wrap="word" />]
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
              <text href={fileHref(file.path, cwd)} key="path" spans={[{ s: 'path', t: file.path }]} />
              <text key="count" role="omp.tool.chip" text={String(file.diagnostics.length)} />
            </row>
            {file.diagnostics.map((diagnostic, j) => {
              const look = severities[diagnostic.severity]
              const href = fileHref(file.path, cwd, { col: diagnostic.col, line: diagnostic.line })

              return (
                <row href={href} key={`d${j}`} role="omp.tool.diagnostic">
                  <text key="severity" role={`omp.tool.diagnostic.${diagnostic.severity}`} spans={[{ s: look.style, t: look.marker }]} title={look.label} />
                  <text href={href} key="location" spans={[{ s: 'muted mono', t: `${diagnostic.line}:${diagnostic.col}` }]} />
                  <text key="message" text={diagnostic.message} wrap="word" />
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
    <text key={`lsp-unavailable-${i}`} role="omp.tool.diagnostics.unavailable" spans={[{ s: 'muted', t: `${note.path}: ${note.message}` }]} wrap="word" />
  )))

  return body
}
