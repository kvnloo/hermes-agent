// The frontend consumes #457's prepared data; it does not become a generator,
// validator, approval owner, or Luau plugin installer.
import { constants } from 'node:fs'
import { open, realpath } from 'node:fs/promises'
import { isAbsolute, join } from 'node:path'
import { pathToFileURL } from 'node:url'

export interface VisualSession {
  sid: string | null
  storedSid: string | null
  info: { branch?: string | null } | null
}

interface RepositoryNode {
  children: readonly RepositoryNode[]
}

export interface VisualBundle {
  id: string
  selection: {
    view: { mode: 'code' | 'churn'; metrics: readonly ('files' | 'code' | 'churn')[] }
  }
  artifact: {
    document: { title: string; root: RepositoryNode & { code: number; churn: number } }
  }
}

export interface VisualSummary {
  id: string
  title: string
  mode: 'code' | 'churn'
  metrics: readonly { key: string; label: string; value: number }[]
}

export interface PreparedVisual extends VisualSummary {
  path: string
  href: string
}

/** Matches the existing bundle's opaque scope without ambiguous delimiters. */
export function visualScope(session: VisualSession): string | undefined {
  if (!session.sid) return undefined
  const scope = JSON.stringify([session.storedSid || session.sid, session.info?.branch ?? ''])
  return scope.length <= 256 ? scope : undefined
}

/** Project once after validation, not on every native frame or keypress. */
export function summarizeVisual(bundle: VisualBundle): VisualSummary {
  const { document } = bundle.artifact
  const { metrics, mode } = bundle.selection.view
  let files = 0
  if (metrics.includes('files')) {
    const stack = [...document.root.children]
    while (stack.length) {
      const node = stack.pop()!
      if (node.children.length) stack.push(...node.children)
      else files++
    }
  }
  const values = {
    files: { label: 'Files', value: files },
    code: { label: 'Text lines', value: document.root.code },
    churn: { label: 'File touches', value: document.root.churn }
  }
  return Object.freeze({
    id: bundle.id,
    title: document.title,
    mode,
    metrics: Object.freeze(metrics.map(key => Object.freeze({ key, ...values[key] })))
  })
}

/** Bound the read itself, including a file growing after stat; never block on a FIFO. */
export async function readVisualFile(path: string, maxBytes: number, signal?: AbortSignal) {
  signal?.throwIfAborted()
  if (!isAbsolute(path) || !path.endsWith('.hvisual.json') || /[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]/u.test(path)) {
    throw new Error('Use an absolute path to a prepared .hvisual.json file.')
  }
  const canonical = await realpath(path)
  if (!canonical.endsWith('.hvisual.json')) throw new Error('The resolved file must end in .hvisual.json.')
  const file = await open(canonical, constants.O_RDONLY | constants.O_NONBLOCK | constants.O_NOFOLLOW)
  try {
    signal?.throwIfAborted()
    const stat = await file.stat()
    if (!stat.isFile() || stat.size > maxBytes) throw new Error('Preview must be a bounded regular file.')
    const bytes = Buffer.alloc(maxBytes + 1)
    let used = 0
    for (;;) {
      signal?.throwIfAborted()
      const { bytesRead } = await file.read(bytes, used, bytes.length - used, null)
      used += bytesRead
      if (used > maxBytes) throw new Error('Preview exceeds the bundle size limit.')
      if (!bytesRead) break
    }
    signal?.throwIfAborted()
    return { path: canonical, input: JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes.subarray(0, used))) }
  } finally {
    await file.close()
  }
}

/** Import the reviewed checkout module, not a bundled copy with broken source fingerprints. */
export async function readPreparedVisual(path: string, scope: string, signal?: AbortSignal): Promise<PreparedVisual> {
  const root = process.env.HERMES_PYTHON_SRC_ROOT
  if (!root || !isAbsolute(root)) throw new Error('The source-checkout launcher must set HERMES_PYTHON_SRC_ROOT.')
  signal?.throwIfAborted()
  const url = pathToFileURL(join(root, 'ui-tsp/experiments/openui-preview/src/bundle.mjs')).href
  const tools = await import(/* @vite-ignore */ url)
  signal?.throwIfAborted()
  const loaded = await readVisualFile(path, tools.MAX_BYTES, signal)
  const bundle = tools.validateBundle(loaded.input)
  const current = await tools.fingerprints()
  signal?.throwIfAborted()
  tools.assertCurrent(bundle, scope, current)
  return Object.freeze({ ...summarizeVisual(bundle), path: loaded.path, href: pathToFileURL(loaded.path).href })
}
