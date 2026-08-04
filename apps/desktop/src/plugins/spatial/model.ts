/** Discover project-scope docs and rank them for the Spatial desk. */

export type CardKind = 'note' | 'sticky' | 'webclip' | 'metric'
export type DocType =
  | 'prd'
  | 'frd'
  | 'roadmap'
  | 'timeline'
  | 'epic'
  | 'sprint'
  | 'spec'
  | 'decision'
  | 'doc'
  | 'context'

export interface DeskCard {
  id: string
  title: string
  summary: string
  type: DocType
  kind: CardKind
  status: string
  tags: string[]
  priority: number
  sourcePath?: string
  x: number
  y: number
  rotation: number
  width: number
  height: number
  accent: string
}

export interface DeskStack {
  id: string
  name: string
  x: number
  y: number
  rotation: number
  width: number
  height: number
  folderColor: string
  collapsed: boolean
  /** Max priority among cards — drives left-to-right order. */
  priority: number
  cards: DeskCard[]
}

export interface Desk {
  width: number
  height: number
  /** Default pan so the highest-priority stack is in view. */
  defaultPan: { x: number; y: number }
  defaultScale: number
  stacks: DeskStack[]
  scannedFrom: string[]
}

export interface FoundDoc {
  path: string
  name: string
  rel: string
  mtimeMs?: number
  bytes?: number
}

type Rule = {
  re: RegExp
  type: DocType
  priority: number
  stack: string
  accent: string
  kind?: CardKind
}

/** Higher priority = more important; shown first (left / expanded). */
const RULES: Rule[] = [
  { re: /(^|\/)(prd|product[-_ ]?requirements?)(\.|$)/i, type: 'prd', priority: 100, stack: 'Scope', accent: '#0a84ff' },
  { re: /(^|\/)(frd|functional[-_ ]?requirements?)(\.|$)/i, type: 'frd', priority: 96, stack: 'Scope', accent: '#0a84ff' },
  { re: /(north[-_ ]?star|vision|product[-_ ]?brief)/i, type: 'prd', priority: 94, stack: 'Scope', accent: '#0a84ff' },
  { re: /roadmap/i, type: 'roadmap', priority: 90, stack: 'Plan', accent: '#30d158' },
  { re: /timeline|milestones?/i, type: 'timeline', priority: 86, stack: 'Plan', accent: '#30d158' },
  { re: /\bepics?\b/i, type: 'epic', priority: 82, stack: 'Plan', accent: '#30d158' },
  { re: /\bsprints?\b/i, type: 'sprint', priority: 78, stack: 'Plan', accent: '#30d158' },
  { re: /(adr|decision|decisions?[-_ ]?log|rfc)/i, type: 'decision', priority: 88, stack: 'Decisions', accent: '#ffd60a', kind: 'sticky' },
  { re: /(architecture|spec|design[-_ ]?doc|contract)/i, type: 'spec', priority: 84, stack: 'Specs', accent: '#bf5af2' },
  { re: /(^|\/)(agents|claude|cursor|hermes)\.md$/i, type: 'context', priority: 72, stack: 'Context', accent: '#8e8e93' },
  { re: /(^|\/)readme(\.mdx?)?$/i, type: 'doc', priority: 68, stack: 'Context', accent: '#8e8e93' },
  { re: /\/docs\//i, type: 'doc', priority: 55, stack: 'Docs', accent: '#8e8e93' },
  { re: /\.(md|mdx)$/i, type: 'doc', priority: 30, stack: 'Docs', accent: '#8e8e93' }
]

const STACK_META: Record<string, { color: string; order: number }> = {
  Scope: { color: '#0a84ff', order: 0 },
  Plan: { color: '#30d158', order: 1 },
  Decisions: { color: '#ffd60a', order: 2 },
  Specs: { color: '#bf5af2', order: 3 },
  Context: { color: '#8e8e93', order: 4 },
  Docs: { color: '#8e8e93', order: 5 }
}

const SKIP_DIR = new Set([
  '.git',
  'node_modules',
  '.venv',
  'venv',
  'dist',
  'build',
  '.next',
  'coverage',
  '__pycache__',
  '.tox',
  'target',
  '.cache',
  'vendor',
  '.turbo'
])

export function classifyDoc(relOrName: string): { type: DocType; priority: number; stack: string; accent: string; kind: CardKind } {
  const s = relOrName.replace(/\\/g, '/')
  for (const rule of RULES) {
    if (rule.re.test(s)) {
      return { type: rule.type, priority: rule.priority, stack: rule.stack, accent: rule.accent, kind: rule.kind ?? 'note' }
    }
  }
  return { type: 'doc', priority: 20, stack: 'Docs', accent: '#9a8f84', kind: 'note' }
}

export function titleFromPath(name: string): string {
  return name
    .replace(/\.(md|mdx|txt)$/i, '')
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function hashRot(id: string): number {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0
  return ((h % 50) - 25) / 10 // -2.5 .. 2.4
}

/** Surface budget: only the most important papers start expanded. */
export const SURFACE_CARD_CAP = 12
export const SURFACE_STACK_CAP = 3

export function layoutDesk(docs: FoundDoc[], roots: string[] = []): Desk {
  const ranked = docs
    .map(doc => {
      const cls = classifyDoc(doc.rel || doc.name)
      return {
        doc,
        ...cls,
        title: titleFromPath(doc.name),
        summary: doc.rel || doc.path
      }
    })
    .sort((a, b) => b.priority - a.priority || a.title.localeCompare(b.title))

  const byStack = new Map<string, typeof ranked>()
  for (const item of ranked) {
    const list = byStack.get(item.stack) ?? []
    list.push(item)
    byStack.set(item.stack, list)
  }

  // Stacks ordered by their best card priority (desc), then canonical order.
  const stackNames = [...byStack.keys()].sort((a, b) => {
    const pa = Math.max(...(byStack.get(a)?.map(x => x.priority) ?? [0]))
    const pb = Math.max(...(byStack.get(b)?.map(x => x.priority) ?? [0]))
    if (pb !== pa) return pb - pa
    return (STACK_META[a]?.order ?? 9) - (STACK_META[b]?.order ?? 9)
  })

  let surfaceLeft = SURFACE_CARD_CAP
  const stacks: DeskStack[] = stackNames.slice(0, 8).map((name, si) => {
    const items = byStack.get(name) ?? []
    const meta = STACK_META[name] ?? { color: '#9a8f84', order: 9 }
    const stackPriority = items[0]?.priority ?? 0
    // High-priority left expanded; long-tail collapsed piles with peeks.
    const collapse = si >= SURFACE_STACK_CAP || stackPriority < 70 || surfaceLeft <= 0
    const take = collapse ? Math.min(items.length, 5) : Math.min(items.length, Math.max(3, Math.min(7, surfaceLeft)))
    if (!collapse) surfaceLeft -= take

    const cards: DeskCard[] = items.slice(0, take).map((item, ci) => {
      const id = item.doc.path
      const sticky = item.kind === 'sticky'
      // Freeform fan: slight column drift + organic offsets (not a rigid grid).
      const col = ci % 3
      const row = Math.floor(ci / 3)
      const drift = (ci % 2 === 0 ? -1 : 1) * (6 + (ci % 5) * 2)
      return {
        id,
        title: item.title,
        summary: item.summary,
        type: item.type,
        kind: item.kind,
        status: item.priority >= 80 ? 'focus' : item.priority >= 50 ? 'active' : 'ref',
        tags: [item.stack.toLowerCase()],
        priority: item.priority,
        sourcePath: item.doc.path,
        x: sticky ? 36 + (ci % 2) * 138 + drift : col * 248 + drift + row * 12,
        y: 108 + row * (sticky ? 132 : 172) + (col === 1 ? -14 : col === 2 ? 10 : 0),
        rotation: hashRot(id),
        width: sticky ? 168 : 228,
        height: sticky ? 118 : 156,
        accent: item.accent
      }
    })

    return {
      id: name.toLowerCase(),
      name,
      x: 140 + si * 560 + (si % 2) * 30,
      y: 160 + (si % 3) * 70,
      rotation: ((si % 5) - 2) * 0.85,
      width: 272,
      height: 78,
      folderColor: meta.color,
      collapsed: collapse,
      priority: stackPriority,
      cards
    }
  })

  return {
    width: Math.max(2800, 280 + stacks.length * 600),
    height: 1800,
    defaultPan: { x: 0, y: 0 },
    defaultScale: 0.75,
    stacks,
    scannedFrom: roots
  }
}

export function filterDesk(desk: Desk, query: string): Desk {
  const q = query.trim().toLowerCase()
  if (!q) return desk
  return {
    ...desk,
    stacks: desk.stacks
      .map(stack => ({
        ...stack,
        cards: stack.cards.filter(c =>
          [c.title, c.summary, c.type, c.status, stack.name, c.sourcePath ?? '', ...c.tags]
            .join(' ')
            .toLowerCase()
            .includes(q)
        )
      }))
      .filter(s => s.cards.length > 0)
  }
}

export function cardCount(desk: Desk): number {
  return desk.stacks.reduce((n, s) => n + s.cards.length, 0)
}

/** Demo desk when a repo has no scannable docs. */
export function seedDesk(): Desk {
  return layoutDesk(
    [
      { path: 'docs/PRD.md', name: 'PRD.md', rel: 'docs/PRD.md' },
      { path: 'docs/FRD.md', name: 'FRD.md', rel: 'docs/FRD.md' },
      { path: 'docs/ROADMAP.md', name: 'ROADMAP.md', rel: 'docs/ROADMAP.md' },
      { path: 'docs/decisions/ADR-001.md', name: 'ADR-001.md', rel: 'docs/decisions/ADR-001.md' },
      { path: 'docs/specs/interaction.md', name: 'interaction.md', rel: 'docs/specs/interaction.md' },
      { path: 'AGENTS.md', name: 'AGENTS.md', rel: 'AGENTS.md' },
      { path: 'README.md', name: 'README.md', rel: 'README.md' },
      { path: 'docs/notes/misc.md', name: 'misc.md', rel: 'docs/notes/misc.md' }
    ],
    ['(seed)']
  )
}

export function shouldSkipDir(name: string): boolean {
  return SKIP_DIR.has(name) || name.startsWith('.')
}

export function isDocFile(name: string): boolean {
  return /\.(md|mdx|txt)$/i.test(name)
}

/** Pure BFS planner used by the async walker (testable without FS). */
export function planWalk(entries: Array<{ name: string; isDirectory: boolean; path: string }>, depth: number, maxDepth: number) {
  const docs: string[] = []
  const dirs: string[] = []
  for (const e of entries) {
    if (e.isDirectory) {
      if (depth < maxDepth && !shouldSkipDir(e.name)) dirs.push(e.path)
    } else if (isDocFile(e.name)) {
      docs.push(e.path)
    }
  }
  return { docs, dirs }
}
