// Result keys are owned by tools/browser_tool.py, browser_tool_vision.py and
// vision_tools.py. Native envelopes carry text_summary, not an auxiliary answer.
import { type JSX } from '@stencil-hq/tern'

import { fileHref } from '../links.js'
import type { ToolCall } from '../model.js'
import { readMedia } from '../read-media.js'
import { record } from '../transcript.js'

import type { Card } from './tools.js'

const str = (value: unknown): string | undefined => (typeof value === 'string' && value ? value : undefined)
const excerpt = (text: string): string => (text.length > 4000 ? `${text.slice(0, 4000)}\n…` : text)

function webHref(value: string | undefined): string | undefined {
  try {
    const url = new URL(value ?? '')

    return url.protocol === 'https:' || url.protocol === 'http:' ? value : undefined
  } catch {
    return undefined
  }
}

function analysisBody(
  call: ToolCall,
  result: Record<string, unknown> | undefined,
  fallback: JSX.Element[]
): JSX.Element[] {
  const question = str(call.args.question)
  const analysis = str(result?.analysis) ?? str(result?.text_summary)
  const error = str(result?.error)

  return [
    ...(question ? [<text key="question" role="omp.tool.context" text={question} wrap="word" />] : []),
    ...(analysis ? [<md key="analysis">{excerpt(analysis)}</md>] : fallback),
    ...(error ? [<text key="error" role="omp.tool.notice" spans={[{ s: 'error', t: error }]} wrap="word" />] : [])
  ]
}

export function browserCard(
  call: ToolCall,
  result: Record<string, unknown> | undefined,
  cwd: string,
  fallback: JSX.Element[]
): Card {
  const url = str(result?.url) ?? str(call.args.url)
  const title = str(result?.title)
  const meta = record(result?.meta)
  const path = str(result?.screenshot_path) ?? str(meta?.screenshot_path)

  const image =
    path && call.status === 'done' && result?.success !== false ? readMedia(path, cwd, undefined, false) : undefined

  const action = call.name
    .replace(/^browser_?/, '')
    .replace(/[_-]+/g, ' ')
    .trim()

  return {
    name: 'browser',
    title: action ? action.charAt(0).toUpperCase() + action.slice(1) : 'Browser',
    target: url ?? str(call.args.target) ?? str(call.args.query) ?? (call.context || undefined),
    targetKind: url || str(call.args.target) ? 'path' : str(call.args.query) ? 'query' : 'text',
    href: webHref(url),
    meta: [title, str(result?.error_kind) ? `Tern ${str(result?.error_kind)}` : undefined].filter(
      (value): value is string => Boolean(value)
    ),
    body: [...(image ? [image] : []), ...analysisBody(call, result, fallback)],
    folded: !image,
    frame: 'inline'
  }
}

export function visionCard(
  call: ToolCall,
  result: Record<string, unknown> | undefined,
  cwd: string,
  fallback: JSX.Element[]
): Card {
  // Use the full argument, not native meta.image_url (Python truncates it to 200 chars).
  const path = str(call.args.image_url)

  return {
    name: 'image',
    title: 'Vision',
    target: path,
    targetKind: 'path',
    href: path ? (webHref(path) ?? fileHref(path, cwd)) : undefined,
    body: analysisBody(call, result, fallback),
    folded: true,
    frame: 'inline'
  }
}
