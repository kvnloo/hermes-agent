import { describe, expect, it } from 'vitest'

import {
  buildTreemap,
  findTreemapNode,
  fitTreemapLabel,
  heatmapDensity,
  layoutTreemap,
  shade,
  validHeatmapCounts,
  validTreemapPaths,
  type TreemapRow
} from './openui-chart-layout'

// Disk-usage fixture from T3 Code's eebe70d411 readability regression.
const disk: TreemapRow[] = [
  { path: 'home/kvn/models/qwen3-32b.gguf', size: 19800, color: 19800 },
  { path: 'home/kvn/.cache/pnpm/store', size: 6100, color: 6100 },
  { path: 'var/lib/docker/overlay2', size: 15600, color: 15600 },
  { path: 'var/log/journal', size: 1200, color: 1200 },
  { path: 'opt/cuda', size: 5400, color: 5400 }
]

describe('OpenUI treemap arithmetic and folding', () => {
  it('folds no-choice folders, retains full paths and sums actual file values', () => {
    expect(validTreemapPaths(disk)).toBe(true)
    const root = buildTreemap(disk)
    expect(root.size).toBe(48100)
    expect(root.color).toBe(48100)
    expect(root.children.map(child => child.name).sort()).toEqual(['home/kvn', 'opt/cuda', 'var'])
    const home = findTreemapNode(root, 'home/kvn')
    expect(home.size).toBe(25900)
    expect(home.children.map(child => child.name).sort()).toEqual(['.cache/pnpm/store', 'models/qwen3-32b.gguf'])
    expect(findTreemapNode(root, 'home/kvn/models/qwen3-32b.gguf').size).toBe(19800)
    expect(findTreemapNode(root, 'home')).toBe(root)
    expect(findTreemapNode(root, 'var/lib/docker/overlay2').parent).toBe(findTreemapNode(root, 'var'))
    expect(findTreemapNode(root, 'no/such/file')).toBe(root)
  })

  it('adopts a common root folder and preserves navigation for two files', () => {
    const root = buildTreemap([
      { path: 'apps/mobile/src/a.ts', size: 2, color: 1 },
      { path: 'apps/mobile/src/b.ts', size: 3, color: 1 }
    ])
    expect(root.path).toBe('apps/mobile/src')
    expect(root.children.map(child => child.name)).toEqual(['a.ts', 'b.ts'])
    expect(root.children.every(child => child.parent === root)).toBe(true)
    expect(findTreemapNode(root, '')).toBe(root)
  })

  it('gives files proportional tile area without mutating the folder order', () => {
    const root = buildTreemap(disk)
    const before = root.children.map(child => child.path)
    const tiles = layoutTreemap(root, 600, 260)
    expect(root.children.map(child => child.path)).toEqual(before)
    expect(tiles).toHaveLength(3)
    expect(tiles.reduce((sum, tile) => sum + tile.width * tile.height, 0)).toBeCloseTo(600 * 260, 6)
    for (const tile of tiles) {
      expect(tile.width * tile.height / (600 * 260)).toBeCloseTo(tile.node.size / 48100, 8)
      expect(tile.x).toBeGreaterThanOrEqual(0)
      expect(tile.y).toBeGreaterThanOrEqual(0)
      expect(tile.x + tile.width).toBeLessThanOrEqual(600.00001)
      expect(tile.y + tile.height).toBeLessThanOrEqual(260.00001)
    }
    expect(layoutTreemap(root, 0, 260)).toEqual([])
    expect(layoutTreemap(buildTreemap([{ path: 'empty', size: 0, color: 0 }]), 600, 260)).toEqual([])
  })

  it('rejects empty, duplicate and file-as-folder paths, including normalized aliases', () => {
    expect(validTreemapPaths([{ path: 'src', size: 1, color: 1 }, { path: 'src/a.ts', size: 2, color: 2 }])).toBe(false)
    expect(validTreemapPaths([{ path: 'src/a.ts', size: 2, color: 2 }, { path: 'src', size: 1, color: 1 }])).toBe(false)
    expect(validTreemapPaths([{ path: 'src//a.ts', size: 1, color: 1 }, { path: 'src/a.ts', size: 2, color: 2 }])).toBe(false)
    expect(validTreemapPaths([{ path: '///', size: 1, color: 1 }])).toBe(false)
    expect(validTreemapPaths([{ path: 'src', size: 1, color: 1 }, { path: 'src-a.ts', size: 2, color: 2 }])).toBe(true)
  })

  it('truncates tiny tiles and preserves intact names that fit', () => {
    expect(fitTreemapLabel('tokens.ts', 9, 9)).toBe('…')
    expect(fitTreemapLabel('tokens.ts', 4, 9)).toBe('')
    expect(fitTreemapLabel('qwen3-32b.gguf', 60, 9)).toBe('qwen3…')
    expect(fitTreemapLabel('models/', 100, 9)).toBe('models/')
  })
})

describe('OpenUI heatmap shape and density', () => {
  it('accepts exact 24- and 48-column grids including explicit zero counts', () => {
    for (const width of [24, 48]) {
      const columns = Array.from({ length: width }, (_, i) => String(i))
      const rows = ['Mon', 'Tue']
      const counts = [columns.map((_, i) => i), columns.map(() => 0)]
      expect(validHeatmapCounts(rows, columns, counts)).toBe(true)
      expect(validHeatmapCounts(rows, columns, [counts[0]!, counts[1]!.slice(1)])).toBe(false)
      expect(validHeatmapCounts(rows, columns, [counts[0]!])).toBe(false)
      expect(validHeatmapCounts(rows, columns, [counts[0]!, [...counts[1]!, 0]])).toBe(false)
    }
  })

  it('keeps sparse headers and exact intensity for real dense displays', () => {
    expect(heatmapDensity(5)).toEqual({ dense: false, labelEvery: 1 })
    expect(heatmapDensity(12)).toEqual({ dense: false, labelEvery: 1 })
    expect(heatmapDensity(24)).toEqual({ dense: true, labelEvery: 3 })
    expect(heatmapDensity(48)).toEqual({ dense: true, labelEvery: 6 })
    expect(shade(0, 9)).toBe(0)
    expect(shade(9, 9)).toBe(1)
    expect(shade(3, 0)).toBe(0)
  })
})
