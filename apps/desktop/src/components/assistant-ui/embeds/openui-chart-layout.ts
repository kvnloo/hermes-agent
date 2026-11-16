/** Pure layout and validation for read-only OpenUI chart boards.
 * Ported behavior from kvnloo/t3code openUiCharts.ts (eebe70d411, be5e729379).
 */
export interface TreemapRow { path: string; size: number; color: number }
export interface TreemapNode {
  name: string
  path: string
  size: number
  color: number
  children: TreemapNode[]
  parent: TreemapNode | null
}
export interface TreemapTile {
  node: TreemapNode
  x: number
  y: number
  width: number
  height: number
}

const parts = (path: string) => path.split('/').filter(Boolean)
const normalized = (path: string) => parts(path).join('/')

/** File paths cannot duplicate each other or act as both files and folders. */
export function validTreemapPaths(rows: readonly TreemapRow[]): boolean {
  const paths = new Set<string>()
  for (const row of rows) {
    const path = normalized(row.path)
    if (!path || paths.has(path)) return false
    paths.add(path)
  }
  for (const path of paths) {
    const names = parts(path)
    for (let i = 1; i < names.length; i += 1) {
      if (paths.has(names.slice(0, i).join('/'))) return false
    }
  }
  return true
}

/** Positional cells must each have exactly one explicit count (including zero). */
export function validHeatmapCounts(
  rows: readonly string[],
  columns: readonly string[],
  counts: readonly (readonly number[])[]
): boolean {
  return counts.length === rows.length && counts.every(row => row.length === columns.length)
}

/** Build parent totals and fold no-choice single-child folders into their child. */
export function buildTreemap(rows: readonly TreemapRow[]): TreemapNode {
  const root: TreemapNode = { name: '', path: '', size: 0, color: 0, children: [], parent: null }
  for (const row of rows) {
    const names = parts(row.path)
    let node = root
    names.forEach((name, index) => {
      let child = node.children.find(candidate => candidate.name === name)
      if (!child) {
        child = {
          name,
          path: names.slice(0, index + 1).join('/'),
          size: 0,
          color: 0,
          children: [],
          parent: node
        }
        node.children.push(child)
      }
      node = child
    })
    node.size = row.size
    node.color = row.color
  }
  const total = (node: TreemapNode): void => {
    if (!node.children.length) return
    node.size = 0
    node.color = 0
    for (const child of node.children) {
      total(child)
      node.size += child.size
      node.color += child.color
    }
  }
  total(root)
  const fold = (node: TreemapNode): void => {
    node.children.forEach((child, index) => {
      let merged = child
      while (merged.children.length === 1) {
        const only = merged.children[0]!
        merged = { ...only, name: merged.name + '/' + only.name, parent: node }
      }
      for (const grandchild of merged.children) grandchild.parent = merged
      node.children[index] = merged
      fold(merged)
    })
  }
  fold(root)
  if (root.children.length === 1 && root.children[0]!.children.length > 0) {
    const only = root.children[0]!
    root.path = only.path
    root.children = only.children
    for (const child of root.children) child.parent = root
  }
  return root
}

/** Full-path lookup traverses folded nodes; unknown paths safely resolve to root. */
export function findTreemapNode(root: TreemapNode, path: string): TreemapNode {
  const target = normalized(path)
  let node = root
  while (node.path !== target) {
    const child = node.children.find(candidate => target === candidate.path || target.startsWith(candidate.path + '/'))
    if (!child) return root
    node = child
  }
  return node
}

/** Squarified tile layout; sort a copy, never use ES2023 toSorted/toReversed. */
export function layoutTreemap(node: TreemapNode, width: number, height: number): TreemapTile[] {
  const items = node.children.filter(child => child.size > 0).sort((a, b) => b.size - a.size)
  const total = items.reduce((sum, item) => sum + item.size, 0)
  if (total <= 0 || width <= 0 || height <= 0) return []
  const scale = width * height / total
  const tiles: TreemapTile[] = []
  let x = 0
  let y = 0
  let w = width
  let h = height
  const worst = (row: readonly TreemapNode[], side: number) => {
    const areas = row.map(item => item.size * scale)
    const sum = areas.reduce((acc, area) => acc + area, 0)
    return Math.max(...areas.map(area => Math.max(
      side * side * area / (sum * sum),
      sum * sum / (side * side * area)
    )))
  }
  const place = (row: readonly TreemapNode[]) => {
    const sum = row.reduce((acc, item) => acc + item.size * scale, 0)
    if (w >= h) {
      const columnWidth = sum / h
      let offset = y
      for (const item of row) {
        const tileHeight = item.size * scale / columnWidth
        tiles.push({ node: item, x, y: offset, width: columnWidth, height: tileHeight })
        offset += tileHeight
      }
      x += columnWidth
      w -= columnWidth
    } else {
      const rowHeight = sum / w
      let offset = x
      for (const item of row) {
        const tileWidth = item.size * scale / rowHeight
        tiles.push({ node: item, x: offset, y, width: tileWidth, height: rowHeight })
        offset += tileWidth
      }
      y += rowHeight
      h -= rowHeight
    }
  }
  let row: TreemapNode[] = []
  for (const item of items) {
    const side = Math.min(w, h)
    if (!row.length || worst([...row, item], side) <= worst(row, side)) {
      row.push(item)
    } else {
      place(row)
      row = [item]
    }
  }
  if (row.length) place(row)
  return tiles
}

export function shade(value: number, max: number): number {
  return max > 0 ? Math.min(1, Math.max(0, value / max)) : 0
}

export function heatmapDensity(columns: number): { dense: boolean; labelEvery: number } {
  const dense = columns > 12
  return { dense, labelEvery: dense ? Math.ceil(columns / 8) : 1 }
}

export function fitTreemapLabel(label: string, width: number, charWidth: number): string {
  const max = Math.floor(width / charWidth)
  if (max <= 0) return ''
  const characters = Array.from(label)
  return characters.length <= max ? label : max === 1 ? '…' : characters.slice(0, max - 1).join('') + '…'
}
