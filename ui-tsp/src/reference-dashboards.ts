// Read-only reference dashboards for the native Tern presentation layer.
// Graphify-Labs graph.json and HANCORE-inspired machine reports remain external data,
// never agent authority. A view read launches no tool, model, package manager or poller.
import { constants } from 'node:fs'
import { lstat, open, realpath } from 'node:fs/promises'
import { join, sep } from 'node:path'

export type Snapshot<T> =
  | { status: 'ready'; value: T }
  | { status: 'missing' | 'invalid' | 'unsafe' | 'oversize'; note: string }

const MAX_BYTES = 16 * 1024 * 1024
const MAX_NODES = 30_000
const MAX_LINKS = 90_000
const MAX_MACHINE_BYTES = 512 * 1024

export interface CodeNode {
  id: string
  label: string
  sourceFile: string
  community: string
  degree: number
}
export interface CodeLink {
  source: string
  target: string
  relation: string
  confidence: 'EXTRACTED' | 'INFERRED' | 'AMBIGUOUS' | 'UNKNOWN'
  sourceFile: string
}
export interface CodeGraph {
  nodes: CodeNode[]
  links: CodeLink[]
  /** All valid nodes indexed by id; the UI only renders a bounded subset. */
  byId: Map<string, CodeNode>
}
export interface MachineUpdate {
  package: string
  from: string
  to: string
  risk: 'high' | 'medium' | 'low' | 'unclassified'
}
export interface MachineProblem {
  subject: string
  count: number
  kind: 'error' | 'crash' | 'unknown'
}
export interface MachineEvent {
  time: string
  source: string
  message: string
}
export interface MachineSnapshot {
  capturedAt: string
  machine: string
  os: string
  availableGiB: number | null
  diskPercent: number | null
  installedPackages: number | null
  updates: MachineUpdate[]
  problems: MachineProblem[]
  events: MachineEvent[]
  /** Whether incident history was actually queried. False means *unknown*, not zero. */
  problemsChecked: boolean
  updatesChecked: boolean
}
const str = (v: unknown, max = 160) =>
  (typeof v === 'string' || typeof v === 'number' ? String(v) : '')
    .replace(/[\x00-\x1f\x7f]/g, ' ')
    .trim().slice(0, max)
const obj = (v: unknown): Record<string, unknown> | null =>
  v !== null && typeof v === 'object' && !Array.isArray(v) ? v as Record<string, unknown> : null
const arr = (v: unknown): unknown[] => Array.isArray(v) ? v : []
const nonneg = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) && v >= 0 ? v : null
const finiteCount = (v: unknown) => Math.min(1_000_000, Math.max(0, Math.floor(nonneg(v) ?? 0)))
const idOf = (v: unknown) => str(obj(v)?.id ?? v, 400)

/** Reject escaping symlinks, including parent folders, and cap actual bytes read. */
async function readLocal(project: string, parts: readonly string[], maximum: number): Promise<Snapshot<unknown>> {
  try {
    const root = await realpath(project)
    let path = root
    for (const segment of parts) {
      path = join(path, segment)
      if ((await lstat(path)).isSymbolicLink()) {
        return { status: 'unsafe', note: 'Symlinked dashboard paths are not read.' }
      }
    }
    const canonical = await realpath(path)
    if (!canonical.startsWith(root + sep)) {
      return { status: 'unsafe', note: 'Dashboard path escapes this project.' }
    }
    const source = await open(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0))
    let raw: Buffer
    try {
      const stat = await source.stat()
      if (!stat.isFile()) {
        return { status: 'invalid', note: 'Dashboard source is not a regular file.' }
      }
      if (stat.size > maximum) {
        return { status: 'oversize', note: 'Dashboard file exceeds the bounded preview size.' }
      }
      // A file can grow after stat: cap the *actual* read rather than readFile().
      raw = Buffer.alloc(maximum + 1)
      let used = 0
      while (used < raw.length) {
        const { bytesRead } = await source.read(raw, used, raw.length - used, null)
        if (!bytesRead) { break }
        used += bytesRead
      }
      if (used > maximum) {
        return { status: 'oversize', note: 'Dashboard file exceeds the bounded preview size.' }
      }
      raw = raw.subarray(0, used)
    } finally {
      await source.close()
    }
    return { status: 'ready', value: JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw)) as unknown }
  } catch (error) {
    if (obj(error)?.code === 'ENOENT') {
      return { status: 'missing', note: 'No snapshot found in this project.' }
    }
    return { status: 'invalid', note: 'Dashboard source is unreadable or invalid JSON.' }
  }
}

/** A Graphify graph is code structure, not a Hermes agent/task graph. */
export function parseGraph(value: unknown): Snapshot<CodeGraph> {
  const data = obj(value)
  if (!Array.isArray(data?.nodes)) {
    return { status: 'invalid', note: 'Graphify graph.json needs a nodes array.' }
  }
  const rawLinks = data.links ?? data.edges ?? []
  if (!Array.isArray(rawLinks)) {
    return { status: 'invalid', note: 'Graphify graph.json needs a links/edges array.' }
  }
  if (data.nodes.length > MAX_NODES || rawLinks.length > MAX_LINKS) {
    return { status: 'oversize', note: 'Graphify node/edge limits exceeded; open graph.html instead.' }
  }
  const byId = new Map<string, CodeNode>()
  for (const item of data.nodes) {
    const row = obj(item), id = idOf(row?.id)
    if (!row || !id || byId.has(id)) { continue }
    byId.set(id, {
      id, label: str(row.label ?? id), sourceFile: str(row.source_file),
      community: str(row.community ?? row.community_id, 48), degree: 0
    })
  }
  const links: CodeLink[] = []
  for (const item of rawLinks) {
    const row = obj(item)
    if (!row) { continue }
    const source = idOf(row.source), target = idOf(row.target)
    if (!byId.has(source) || !byId.has(target)) { continue }
    const confidence = str(row.confidence, 24).toUpperCase()
    links.push({
      source, target, relation: str(row.relation ?? 'relates'),
      confidence: confidence === 'EXTRACTED' || confidence === 'INFERRED' || confidence === 'AMBIGUOUS'
        ? confidence : 'UNKNOWN',
      sourceFile: str(row.source_file)
    })
    byId.get(source)!.degree++
    byId.get(target)!.degree++
  }
  const nodes = [...byId.values()].sort((a, b) =>
    b.degree - a.degree || a.label.localeCompare(b.label) || a.id.localeCompare(b.id))
  return { status: 'ready', value: { nodes, links, byId } }
}

export function graphMatches(graph: CodeGraph, query: string, maximum = 14): CodeNode[] {
  const q = query.trim().toLowerCase()
  return graph.nodes.filter(n => !q ||
    n.label.toLowerCase().includes(q) || n.id.toLowerCase().includes(q) ||
    n.sourceFile.toLowerCase().includes(q)).slice(0, Math.max(0, maximum))
}
export function graphEdges(graph: CodeGraph, node: string, maximum = 12): Array<CodeLink & { direction: 'in' | 'out' }> {
  const edges: Array<CodeLink & { direction: 'in' | 'out' }> = []
  for (const link of graph.links) {
    if (link.source === node || link.target === node) {
      edges.push({ ...link, direction: link.source === node ? 'out' : 'in' })
    }
    if (edges.length >= maximum) { break }
  }
  return edges
}

export function parseMachine(value: unknown): Snapshot<MachineSnapshot> {
  const data = obj(value)
  if (!data || data.schema !== 1 || !str(data.captured_at)) {
    return { status: 'invalid', note: 'Machine snapshot requires schema=1 and captured_at.' }
  }
  if (!Array.isArray(data.updates) || !Array.isArray(data.problems) || !Array.isArray(data.events)) {
    return { status: 'invalid', note: 'Machine snapshot needs updates, problems, and events arrays.' }
  }
  if (data.updates.length > 5000 || data.problems.length > 5000 || data.events.length > 5000) {
    return { status: 'oversize', note: 'Machine snapshot item limits exceeded.' }
  }
  const updates = arr(data.updates).flatMap(item => {
    const r = obj(item)
    if (!r || !str(r.package)) { return [] }
    const risk = str(r.risk)
    return [{
      package: str(r.package, 100), from: str(r.from, 48), to: str(r.to, 48),
      risk: (['high', 'medium', 'low'].includes(risk) ? risk : 'unclassified') as MachineUpdate['risk']
    }]
  })
  const problems = arr(data.problems).flatMap(item => {
    const r = obj(item)
    if (!r || !str(r.subject)) { return [] }
    return [{ subject: str(r.subject), count: finiteCount(r.count),
      kind: (r.kind === 'error' || r.kind === 'crash' ? r.kind : 'unknown') as MachineProblem['kind'] }]
  })
  const events = arr(data.events).flatMap(item => {
    const r = obj(item)
    if (!r || !str(r.message)) { return [] }
    return [{ time: str(r.time, 50), source: str(r.source, 65), message: str(r.message, 240) }]
  })
  return { status: 'ready', value: {
    capturedAt: str(data.captured_at, 60), machine: str(data.machine, 100), os: str(data.os, 120),
    availableGiB: nonneg(data.available_gib), diskPercent: nonneg(data.disk_percent),
    installedPackages: nonneg(data.installed_packages),
    updates, problems, events, problemsChecked: data.problems_checked === true,
    updatesChecked: data.updates_checked === true
  } }
}

export async function readGraph(project = process.cwd()): Promise<Snapshot<CodeGraph>> {
  const loaded = await readLocal(project, ['graphify-out', 'graph.json'], MAX_BYTES)
  return loaded.status === 'ready' ? parseGraph(loaded.value) : loaded
}
export async function readMachine(project = process.cwd()): Promise<Snapshot<MachineSnapshot>> {
  const loaded = await readLocal(project, ['.hermes-dashboard', 'machine.json'], MAX_MACHINE_BYTES)
  return loaded.status === 'ready' ? parseMachine(loaded.value) : loaded
}
