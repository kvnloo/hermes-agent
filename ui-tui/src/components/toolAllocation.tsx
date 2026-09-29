import { Box, Text } from '@hermes/ink'

import { parseToolTrailResultLine, splitToolDuration } from '../lib/text.js'
import type { Theme } from '../theme.js'
import type { DetailsMode, Msg } from '../types.js'

export type ToolAllocationTone = 'error' | 'success'

export interface AllocatedToolBlock {
  rows: string[]
  tone: ToolAllocationTone
}

export const flattenToolHeader = (text: string): string => text.replace(/\s+/g, ' ').trim()

const detailLines = (text: string): string[] =>
  text
    .split('\n')
    .map(flattenToolHeader)
    .filter(Boolean)

export const allocateSettledToolTrailLine = (line: string, requestedRows: number): AllocatedToolBlock | null => {
  const parsed = parseToolTrailResultLine(line)

  if (!parsed) {
    return null
  }

  const tone: ToolAllocationTone = parsed.mark === '✗' ? 'error' : 'success'
  const minimumRows = tone === 'error' ? 1 : 0
  const budget = Math.max(minimumRows, Math.max(0, Math.trunc(requestedRows)))
  const { duration, label } = splitToolDuration(flattenToolHeader(parsed.call))
  const header = `${parsed.mark} ${label}${duration}`
  const details = detailLines(parsed.detail)

  if (budget === 0) {
    return { rows: [], tone }
  }

  if (budget === 1) {
    const preview = details[0]

    return { rows: [preview ? `${header} · ${preview}` : header], tone }
  }

  if (budget === 2) {
    const preview = details[0] ?? '(no output)'

    const suffix =
      details.length > 1
        ? ` · +${details.length - 1} line${details.length === 2 ? '' : 's'}`
        : ''

    return { rows: [`╭─ ${header}`, `╰─ ${preview}${suffix}`], tone }
  }

  const detailBudget = budget - 1
  let visible: string[]

  if (details.length > detailBudget) {
    const shown = details.slice(0, Math.max(0, detailBudget - 1))
    const omitted = details.length - shown.length
    visible = [...shown, `… ${omitted} more line${omitted === 1 ? '' : 's'}`]
  } else {
    visible = [...details]
  }

  if (visible.length === 0) {
    visible.push('(no output)')
  }

  return {
    rows: [
      `╭─ ${header}`,
      ...visible.map((detail, index) =>
        index === visible.length - 1 ? `╰─ ${detail}` : `│  ${detail}`
      )
    ],
    tone
  }
}

export const isSettledToolTrailCandidate = (lines: readonly string[]): boolean =>
  lines.length > 0 && lines.every(line => parseToolTrailResultLine(line) !== null)

const READ_FILE_PREFIX = 'Read File("'

const settledReadPath = (line: string): string | null => {
  const parsed = parseToolTrailResultLine(line)

  if (!parsed || parsed.mark !== '✓') {
    return null
  }

  const { label } = splitToolDuration(flattenToolHeader(parsed.call))

  if (!label.startsWith(READ_FILE_PREFIX) || !label.endsWith('")')) {
    return null
  }

  return label.slice(READ_FILE_PREFIX.length, -2)
}

export const isSettledReadGroupCandidate = (lines: readonly string[]): boolean =>
  lines.length >= 2 && lines.every(line => settledReadPath(line) !== null)

export const allocateSettledReadGroup = (
  lines: readonly string[],
  requestedRows: number
): AllocatedToolBlock | null => {
  if (!isSettledReadGroupCandidate(lines)) {
    return null
  }

  const paths = lines.map(line => settledReadPath(line)!)
  const budget = Math.max(0, Math.trunc(requestedRows))
  const header = `✓ Read ${paths.length} files`

  if (budget === 0) {
    return { rows: [], tone: 'success' }
  }

  if (budget === 1) {
    const shown = paths.slice(0, 2)
    const omitted = paths.length - shown.length
    const suffix = omitted > 0 ? ` · +${omitted} more` : ''

    return { rows: [`${header} · ${shown.join(' · ')}${suffix}`], tone: 'success' }
  }

  if (budget === 2) {
    const omitted = paths.length - 1
    const suffix = omitted > 0 ? ` · +${omitted} file${omitted === 1 ? '' : 's'}` : ''

    return { rows: [`╭─ ${header}`, `╰─ ${paths[0]}${suffix}`], tone: 'success' }
  }

  const detailBudget = budget - 1
  let visible: string[]

  if (paths.length > detailBudget) {
    const shown = paths.slice(0, Math.max(0, detailBudget - 1))
    const omitted = paths.length - shown.length
    visible = [...shown, `… +${omitted} file${omitted === 1 ? '' : 's'}`]
  } else {
    visible = [...paths]
  }

  return {
    rows: [
      `╭─ ${header}`,
      ...visible.map((path, index) => (index === visible.length - 1 ? `╰─ ${path}` : `│  ${path}`))
    ],
    tone: 'success'
  }
}

export const isSettledToolAllocationCandidate = (msg: Msg, toolsMode: DetailsMode): boolean => {
  const lines = msg.tools ?? []

  return (
    msg.kind === 'trail' &&
    !msg.isMoaReference &&
    !(msg.thinking?.trim()) &&
    toolsMode === 'collapsed' &&
    ((lines.length === 1 && isSettledToolTrailCandidate(lines)) || isSettledReadGroupCandidate(lines))
  )
}

export function AllocatedToolTrail({
  lines,
  rowsPerTool,
  t
}: {
  lines: readonly string[]
  rowsPerTool: number
  t: Theme
}) {
  const readGroup = allocateSettledReadGroup(lines, rowsPerTool)

  const blocks = readGroup
    ? readGroup.rows.length > 0
      ? [readGroup]
      : []
    : lines
        .map(line => allocateSettledToolTrailLine(line, rowsPerTool))
        .filter((block): block is AllocatedToolBlock => block !== null && block.rows.length > 0)

  if (!blocks.length) {
    return null
  }

  return (
    <Box flexDirection="column">
      {blocks.map((block, blockIndex) => (
        <Box flexDirection="column" key={blockIndex}>
          {block.rows.map((row, rowIndex) => (
            <Text
              color={block.tone === 'error' ? t.color.error : rowIndex === 0 ? t.color.text : t.color.muted}
              dim={block.tone !== 'error' && rowIndex > 0}
              key={rowIndex}
              wrap="truncate-end"
            >
              {row}
            </Text>
          ))}
        </Box>
      ))}
    </Box>
  )
}
