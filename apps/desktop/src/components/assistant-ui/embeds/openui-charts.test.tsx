import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { inspectOpenUiBoard } from './openui-catalog'
import { RichCodeBlock } from './registry'

const source = (code: string) => <pre data-testid="original-chart-source"><code>{code}</code></pre>
const embedded = (code: string) => (
  <RichCodeBlock code={code} fallback={source(code)} language="openui-v2" />
)

// Actual model-file and container sizes from the T3 eebe70d411 regression fixture.
const diskCode = [
  'root = Board("Disk report", "", [disk])',
  'disk = Treemap("Disk usage", "MB", "MB", [' +
    '{path: "home/kvn/models/qwen3-32b.gguf", size: 19800, color: 19800}, ' +
    '{path: "home/kvn/.cache/pnpm/store", size: 6100, color: 6100}, ' +
    '{path: "var/lib/docker/overlay2", size: 15600, color: 15600}, ' +
    '{path: "var/log/journal", size: 1200, color: 1200}, ' +
    '{path: "opt/cuda", size: 5400, color: 5400}])'
].join('\n')

const heatmapCode = (width: 12 | 24 | 48, shortenLast = false) => {
  const halfHourly = width === 48
  const columns = Array.from({ length: width }, (_, index) =>
    String(Math.floor(index / (halfHourly ? 2 : 1))).padStart(2, '0') +
    (halfHourly && index % 2 ? ':30' : ':00')
  )
  const counts = [
    columns.map((_, index) => index % 7),
    columns.map((_, index) => index === 0 ? 3 : 0)
  ]
  if (shortenLast) counts[1]!.pop()
  return [
    'root = Board("Activity", "", [activity])',
    'activity = Heatmap("Hourly usage", "turns", ["Mon", "Tue"], ' +
      JSON.stringify(columns) + ', ' + JSON.stringify(counts) + ')'
  ].join('\n')
}

afterEach(cleanup)

describe('OpenUI treemap board', () => {
  it('renders real-world disk sizes, folded folder labels and keyboard drilldown', async () => {
    expect(inspectOpenUiBoard(diskCode)).toEqual({ kind: 'ready' })
    const { container } = render(embedded(diskCode))
    await waitFor(() => expect(screen.getByRole('group', { name: 'Disk usage treemap' })).toBeTruthy())
    const home = screen.getByRole('button', { name: /home\/kvn · 25,900 MB/ })
    expect(home).toBeTruthy()
    expect(screen.getByRole('button', { name: /var · 16,800 MB/ })).toBeTruthy()
    fireEvent.keyDown(home, { key: 'Enter' })
    expect(screen.getByRole('button', { name: /models\/qwen3-32b\.gguf · 19,800 MB/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /\.cache\/pnpm\/store · 6,100 MB/ })).toBeTruthy()

    const file = screen.getByRole('button', { name: /models\/qwen3-32b\.gguf · 19,800 MB/ })
    fireEvent.click(file)
    expect(container.querySelector('p[aria-live="polite"]')?.textContent)
      .toBe('home/kvn/models/qwen3-32b.gguf · 19,800 MB')
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByRole('button', { name: /opt\/cuda · 5,400 MB/ })).toBeTruthy()
    expect(container.querySelector('p[aria-live="polite"]')?.textContent)
      .toBe('Disk usage · 48,100 MB')
  })

  it('rejects file/folder conflicts, duplicate aliases and empty normalized paths', () => {
    const board = 'root = Board("Paths", "", [p])\n'
    const panel = (rows: string) => 'p = Treemap("Paths", "LOC", "commits", [' + rows + '])'
    const row = (path: string) => '{path: "' + path + '", size: 1, color: 1}'
    for (const rows of [
      row('src') + ', ' + row('src/file.ts'),
      row('src/file.ts') + ', ' + row('src'),
      row('src//file.ts') + ', ' + row('src/file.ts'),
      row('///')
    ]) {
      expect(inspectOpenUiBoard(board + panel(rows))).toEqual({ kind: 'invalid', reason: 'invalid' })
    }
    expect(inspectOpenUiBoard(board + panel(row('src') + ', ' + row('src-file.ts'))))
      .toEqual({ kind: 'ready' })
  })
})

describe('OpenUI dense heatmap board', () => {
  it('keeps one exact count per compact cell, including true zero', async () => {
    const code = heatmapCode(12)
    expect(inspectOpenUiBoard(code)).toEqual({ kind: 'ready' })
    render(embedded(code))
    const region = await screen.findByRole('region', { name: 'Hourly usage heatmap' })
    const buttons = within(region).getAllByRole('button')
    expect(buttons).toHaveLength(24)
    expect(buttons[0]?.textContent).toBe('0')
    expect(within(region).getByText('01:00')).toBeTruthy()
    fireEvent.click(within(region).getByRole('button', { name: 'Tue · 11:00 · 0 turns' }))
    expect(screen.getByText('Tue · 11:00 · 0 turns')).toBeTruthy()
  })

  it('renders a 24-column grid with sparse labels and selectable zero values', async () => {
    const code = heatmapCode(24)
    expect(inspectOpenUiBoard(code)).toEqual({ kind: 'ready' })
    render(embedded(code))
    const region = await screen.findByRole('region', { name: 'Hourly usage heatmap' })
    expect(within(region).getAllByRole('button')).toHaveLength(48)
    expect(within(region).getByText('00:00')).toBeTruthy()
    expect(within(region).queryByText('01:00')).toBeNull()
    fireEvent.click(within(region).getByRole('button', { name: 'Tue · 23:00 · 0 turns' }))
    expect(screen.getByText('Tue · 23:00 · 0 turns')).toBeTruthy()
  })

  it('renders all 96 cells at 48 columns without label collision or numeric placeholders', async () => {
    const code = heatmapCode(48)
    expect(inspectOpenUiBoard(code)).toEqual({ kind: 'ready' })
    render(embedded(code))
    const region = await screen.findByRole('region', { name: 'Hourly usage heatmap' })
    expect(within(region).getAllByRole('button')).toHaveLength(96)
    expect(within(region).getByText('00:00')).toBeTruthy()
    expect(within(region).queryByText('00:30')).toBeNull()
    fireEvent.click(within(region).getByRole('button', { name: 'Tue · 23:30 · 0 turns' }))
    expect(screen.getByText('Tue · 23:30 · 0 turns')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Show source' }))
    expect(screen.getByTestId('original-chart-source').textContent).toBe(code)
    fireEvent.click(screen.getByRole('button', { name: 'Show board' }))
    expect(screen.getByRole('region', { name: 'Hourly usage heatmap' })).toBeTruthy()
  })

  it('never fills missing cells or rows with fabricated zero values', async () => {
    const malformed = heatmapCode(24, true)
    expect(inspectOpenUiBoard(malformed)).toEqual({ kind: 'invalid', reason: 'invalid' })
    // A separate one-row count grid must not be accepted for two labels.
    const oneRow = [
      'root = Board("Activity", "", [activity])',
      'activity = Heatmap("Hourly usage", "turns", ["Mon", "Tue"], ["00:00"], [[0]])'
    ].join('\n')
    expect(inspectOpenUiBoard(oneRow)).toEqual({ kind: 'invalid', reason: 'invalid' })
    const extraCell = [
      'root = Board("Activity", "", [activity])',
      'activity = Heatmap("Hourly usage", "turns", ["Mon"], ["00:00"], [[0, 1]])'
    ].join('\n')
    expect(inspectOpenUiBoard(extraCell)).toEqual({ kind: 'invalid', reason: 'invalid' })
    render(embedded(malformed))
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    expect(screen.getByTestId('original-chart-source').textContent).toBe(malformed)
    expect(screen.queryByRole('region', { name: 'Hourly usage heatmap' })).toBeNull()
  })
})
