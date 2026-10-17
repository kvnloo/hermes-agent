import type { JSX } from '@stencil-hq/tern'

import { displayText } from '../display-text.js'
import { fileHref } from '../links.js'

function count(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : undefined
}

/** Counts refer to the source result, not the native card's folded viewport. */
export function resultCounts(result: Record<string, unknown> | undefined, returned: number, unit: string): string[] {
  const total = count(result?.total_count) ?? returned
  const lowerBound = result?.total_count_is_lower_bound === true
  const omitted = Math.max(0, total - returned)

  return [
    `${returned} ${unit} returned`,
    `${lowerBound ? '≥' : ''}${total} total`,
    `${lowerBound ? '≥' : ''}${omitted} omitted`,
    ...(result?.truncated === true ? ['source truncated'] : [])
  ]
}

/** Only explicit tool-owned descriptors create artifact actions, never guessed cache names. */
export function outputArtifacts(result: Record<string, unknown> | undefined, cwd: string, key = 'full-output'): JSX.Element[] {
  const paths = [result?.full_output_path, result?.stdout_spill_path]
    .filter((path): path is string => typeof path === 'string' && path.length > 0)

  return [...new Set(paths)].map((path, i) => {
    const href = fileHref(path, cwd)

    return <text href={href} key={`${key}-${i}`} role="omp.tool.artifact"
      text={`${href ? 'Open full output' : 'Full output path (not locally linkable)'}: ${displayText(path)}`} wrap="word" />
  })
}

export function captureFacts(result: Record<string, unknown> | undefined): string[] {
  const captured = count(result?.stdout_bytes_captured)
  const total = count(result?.stdout_bytes_total)
  const omitted = count(result?.stdout_bytes_omitted)
  const chars = count(result?.output_total_chars)

  return [
    ...(captured === undefined ? [] : [`${captured} bytes returned`]),
    ...(total === undefined ? [] : [`${total} bytes total`]),
    ...(omitted === undefined ? [] : [`${omitted} bytes omitted`]),
    ...(chars === undefined ? [] : [`${chars} chars total`])
  ]
}

/** web_extract currently emits its stored result descriptor in this exact footer. */
export function fetchArtifact(content: string): Record<string, unknown> | undefined {
  const footer = content.slice(content.lastIndexOf('──────── [TRUNCATED] ────────'))
  const path = /^Full text saved to: (.+)$/m.exec(footer)?.[1]

  return path ? { full_output_path: path } : undefined
}
