import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { RoadmapProjection } from './types'

const fetchRoadmap = vi.fn()

vi.mock('./api', () => ({
  fetchRoadmap: () => fetchRoadmap(),
  roadmapKey: (slug: string) => ['kanban', 'roadmap', slug]
}))

import { RoadmapView } from './roadmap'

const projection: RoadmapProjection = {
  board: 'public-example',
  capability: true,
  contract_version: 1,
  freshness: { latest_event_id: 17, observed_at: 1_700_000_000 },
  scopes: [
    {
      board_bound: false,
      id: 'company',
      name: 'Public Example',
      parent_id: null,
      provenance: { board: 'public-example', latest_event_id: 17, source_revision: 'abc123def456' },
      rollup: {
        blocker_task_ids: ['t_blocked'],
        critical_path: { state: 'ok', task_ids: ['t_plan', 't_build'] },
        outcome_event_ids: [14],
        status_counts: { blocked: 1, done: 1 },
        task_count: 2,
        verified_outcomes: 1,
        volume_score: 0
      },
      type: 'company'
    },
    {
      board_bound: true,
      id: 'project',
      name: 'Roadmap',
      parent_id: 'company',
      provenance: { board: 'public-example', latest_event_id: 17, source_revision: 'abc123def456' },
      rollup: {
        blocker_task_ids: [],
        critical_path: { state: 'ok', task_ids: ['t_build'] },
        outcome_event_ids: [14],
        status_counts: { done: 1 },
        task_count: 1,
        verified_outcomes: 1,
        volume_score: 0
      },
      type: 'project'
    }
  ],
  source_revision: 'abc123def456',
  state: 'ready',
  warnings: []
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderRoadmap() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  return render(
    <QueryClientProvider client={client}>
      <RoadmapView onReturnToBoard={vi.fn()} slug="public-example" />
    </QueryClientProvider>
  )
}

describe('RoadmapView', () => {
  it('renders the hierarchy and restores row focus after Escape', async () => {
    fetchRoadmap.mockResolvedValue(projection)
    renderRoadmap()

    const row = await screen.findByRole('treeitem', { name: /Roadmap/i })
    row.focus()
    fireEvent.click(row)

    const dialog = await screen.findByRole('dialog', { name: 'Roadmap details' })
    const close = screen.getByRole('button', { name: 'Close details' })
    expect(document.activeElement).toBe(close)
    fireEvent.keyDown(window, { key: 'Tab' })
    expect(document.activeElement).toBe(close)
    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true })
    expect(document.activeElement).toBe(close)
    expect(dialog.getAttribute('aria-modal')).toBe('true')
    fireEvent.keyDown(window, { key: 'Escape' })
    await vi.waitFor(() => expect(document.activeElement).toBe(row))
  })

  it('fails closed when the catalog is invalid', async () => {
    fetchRoadmap.mockResolvedValue({ ...projection, scopes: [], state: 'invalid', warnings: ['scope cycle'] })
    renderRoadmap()

    expect(await screen.findByText('scope cycle')).toBeTruthy()
    expect(screen.queryByRole('tree')).toBeNull()
  })
})
