// Visible-branch traversal follows OMP's raw-ancestry/visible-target split
// (Can Bölük / Stencil, MIT). Hermes nodes are copied sessions, not entries.
import type { SessionTreeRow } from '@hermes/shared/gateway-events'

export interface SessionTreeEntry {
  row: SessionTreeRow
  depth: number
  branch: string
}

export interface SessionTreeProjection {
  entries: SessionTreeEntry[]
  branches: string[]
}

/** Keep raw ancestry even when a branch head is filtered out. */
export function projectSessionTree(rows: readonly SessionTreeRow[], visible: ReadonlySet<string>, active: string | null): SessionTreeProjection {
  const byId = new Map(rows.map(row => [row.id, row]))
  const parents = new Map(rows.map(row => [row.id, byId.has(row.parent_session_id ?? '') ? row.parent_session_id ?? null : null]))
  const checked = new Set<string>()

  // Sever one deterministic edge per corrupt cycle; iterative walks also
  // tolerate deeply nested sessions without overflowing the JS call stack.
  for (const row of rows) {
    const path: string[] = []
    const at = new Map<string, number>()
    let id: string | null = row.id

    while (id !== null && !checked.has(id)) {
      const cycle = at.get(id)

      if (cycle !== undefined) {
        const cut = path.slice(cycle).sort()[0]

        if (cut) {
          parents.set(cut, null)
        }

        break
      }

      at.set(id, path.length)
      path.push(id)
      id = parents.get(id) ?? null
    }

    path.forEach(id => checked.add(id))
  }

  const activePath = new Set<string>()
  let cursor = active

  while (cursor && byId.has(cursor) && !activePath.has(cursor)) {
    activePath.add(cursor)
    cursor = parents.get(cursor) ?? null
  }

  const children = new Map<string | null, SessionTreeRow[]>()

  for (const row of rows) {
    const parent = parents.get(row.id) ?? null
    const list = children.get(parent) ?? []
    list.push(row)
    children.set(parent, list)
  }

  for (const list of children.values()) {
    list.sort((a, b) => Number(activePath.has(b.id)) - Number(activePath.has(a.id)))
  }

  const entries: SessionTreeEntry[] = []
  const stack = [...(children.get(null) ?? [])].reverse().map(row => ({ branch: row.id, depth: 0, row }))

  while (stack.length) {
    const entry = stack.pop()!

    if (visible.has(entry.row.id)) {
      entries.push(entry)
    }

    for (const row of [...(children.get(entry.row.id) ?? [])].reverse()) {
      stack.push({ branch: row.edge_kind === 'continuation' ? entry.branch : row.id, depth: entry.depth + 1, row })
    }
  }

  const targets = new Map<string, string>()

  for (const entry of entries) {
    if (!targets.has(entry.branch)) {
      targets.set(entry.branch, entry.row.id)
    }
  }

  return { branches: [...targets.values()], entries }
}

/** Only move the highlight; activation remains a separate user intent. */
export function adjacentBranch(projection: SessionTreeProjection, selected: string | undefined, direction: -1 | 1): string | undefined {
  const branch = projection.entries.find(entry => entry.row.id === selected)?.branch
  const current = projection.branches.findIndex(id => projection.entries.find(entry => entry.row.id === id)?.branch === branch)
  const count = projection.branches.length

  return count ? projection.branches[(current < 0 ? direction > 0 ? 0 : count - 1 : (current + direction + count) % count)] : selected
}
