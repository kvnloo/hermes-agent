import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { inspectOpenUiBoard } from './openui-catalog'
import { RICH_FENCE_LANGUAGES, RichCodeBlock } from './registry'

// Exact completed fence from T3 Code experiments/openui-lab/source-demo-fences.md,
// model-stacked-area, at 3cf6d0c655d22e249398fb7ea36198bf73b4e63d.
const SOURCE_FENCE = [
  'root = Board("Turns by model", "Wednesday had the most turns (16); Claude led on Tuesday.", [usage])',
  'usage = StackedArea("Turns by model", "turns", ["Mon", "Tue", "Wed"], [{name: "Codex", values: [8, 4, 10]}, {name: "Claude", values: [4, 10, 6]}])'
].join('\n')

const source = (code: string) => <pre data-testid="original-fence"><code>{code}</code></pre>
const embedded = (code: string, streaming = false) => (
  <RichCodeBlock code={code} fallback={source(code)} language="openui-v2" streaming={streaming} />
)

afterEach(cleanup)

describe('openui-v2 Desktop fence', () => {
  it('routes only the registered version through the lazy embed', async () => {
    expect(RICH_FENCE_LANGUAGES.has('openui-v2')).toBe(true)
    const { rerender } = render(
      <RichCodeBlock code={SOURCE_FENCE} fallback={source(SOURCE_FENCE)} language="openui-v3" />
    )
    expect(screen.getByTestId('original-fence').textContent).toBe(SOURCE_FENCE)
    rerender(embedded(SOURCE_FENCE))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Turns by model', level: 3 })).toBeTruthy())
  })

  it('renders a real lab board, its panel and raw values while streaming', async () => {
    expect(inspectOpenUiBoard(SOURCE_FENCE)).toEqual({ kind: 'ready' })
    render(embedded(SOURCE_FENCE, true))
    await waitFor(() => expect(screen.getByRole('img', { name: 'Turns by model, stacked values' })).toBeTruthy())
    expect(screen.getByRole('heading', { name: 'Turns by model', level: 3 })).toBeTruthy()
    expect(screen.getAllByText('Codex')).toBeTruthy()
    expect(screen.getAllByText('Claude')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Turns by model values' }).textContent).toContain('10')
  })

  it('shows the exact normal code fence when asked, then restores the board', async () => {
    render(embedded(SOURCE_FENCE))
    const button = await screen.findByRole('button', { name: 'Show source' })
    fireEvent.click(button)
    expect(screen.getByTestId('original-fence').textContent).toBe(SOURCE_FENCE)
    fireEvent.click(screen.getByRole('button', { name: 'Show board' }))
    expect(screen.getByRole('heading', { name: 'Turns by model', level: 3 })).toBeTruthy()
  })

  it('keeps malformed table source visible with a notice', async () => {
    const malformed = [
      'root = Board("Bad rows", "", [t])',
      't = Table("Runs", ["Suite", "Result"], [["Parser"]])'
    ].join('\n')
    expect(inspectOpenUiBoard(malformed)).toEqual({ kind: 'invalid', reason: 'rows' })
    render(embedded(malformed))
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('column'))
    expect(screen.getByTestId('original-fence').textContent).toBe(malformed)
    expect(screen.queryByRole('heading', { name: 'Bad rows' })).toBeNull()
  })

  it('rejects oversized, tool-bearing and misaligned series boards', () => {
    expect(inspectOpenUiBoard('x'.repeat(65_537))).toEqual({ kind: 'invalid', reason: 'oversized' })
    expect(inspectOpenUiBoard(SOURCE_FENCE + '\ndata = Query("read_file", {})').kind).not.toBe('ready')
    expect(
      inspectOpenUiBoard('root = Board("Bad", "", [s])\ns = LineChart("L", "", ["Mon", "Tue"], [{name: "A", values: [1]}])')
    ).toEqual({ kind: 'invalid', reason: 'series' })
  })

  it('supports stat, bar, stacked bar, line and table without actions', async () => {
    const code = [
      'root = Board("Metrics", "Read-only", [s, b, k, l, t])',
      's = Stat("Overview", [{label: "Runs", value: "12"}])',
      'b = BarChart("Throughput", "runs", [{label: "Monday", value: 5}])',
      'k = StackedBar("Workers", "runs", ["Mon", "Tue"], [{name: "A", values: [2, 3]}])',
      'l = LineChart("Trend", "runs", ["Mon", "Tue"], [{name: "B", values: [3, 4]}])',
      't = Table("Results", ["Suite", "Result"], [["Parser", "pass"]])'
    ].join('\n')
    expect(inspectOpenUiBoard(code)).toEqual({ kind: 'ready' })
    const { container } = render(embedded(code))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Metrics' })).toBeTruthy())
    for (const panel of ['Overview', 'Throughput', 'Workers', 'Trend', 'Results']) {
      expect(screen.getByRole('heading', { name: panel })).toBeTruthy()
    }
    expect(screen.getByText('pass')).toBeTruthy()
    expect(container.querySelector('a, [data-action], iframe')).toBeNull()
  })
})
