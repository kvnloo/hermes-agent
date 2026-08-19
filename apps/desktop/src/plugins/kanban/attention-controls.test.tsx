import { host } from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { type ReactElement, useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type * as KanbanApi from './api'
import { updateAttention } from './api'
import { type AttentionAnnouncement, AttentionControls, BoardAnnouncer } from './board'
import { formatLocalDateTime, parseLocalDateTime } from './datetime-local'
import type { AttentionReceipt, KanbanTask } from './types'

vi.mock('./api', async importOriginal => {
  const actual = await importOriginal<typeof KanbanApi>()

  return { ...actual, updateAttention: vi.fn() }
})

const updateAttentionMock = vi.mocked(updateAttention)

const baseTask: KanbanTask = { id: 'task-safe', status: 'running', title: 'Privacy-safe evidence task' }
const receipt = (state: AttentionReceipt['state'], revision: number): AttentionReceipt => ({
  reason: 'receipt', revision, state, wake_at: state === 'snoozed' ? 1_800_000_000 : null
})
const response = (state: AttentionReceipt['state'], revision: number) => ({ attention: receipt(state, revision), idempotent: false })

function view(task: KanbanTask): ReactElement {
  return <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } })}><AttentionControls task={task} /></QueryClientProvider>
}

afterEach(cleanup)
beforeEach(() => {
  updateAttentionMock.mockReset()
  vi.spyOn(host, 'notify').mockImplementation(() => '')
})

describe('attention lifecycle controls', () => {
  it('locks duplicate actions and announces stale conflicts', async () => {
    let reject!: (reason: Error) => void
    updateAttentionMock.mockImplementationOnce(() => new Promise((_resolve, fail) => { reject = fail }))
    render(view({ ...baseTask, attention: receipt('active', 4) }))

    fireEvent.click(screen.getByRole('button', { name: 'Settle' }))
    await waitFor(() => expect((screen.getByRole('button', { name: 'Settle' }) as HTMLButtonElement).disabled).toBe(true))
    fireEvent.click(screen.getByRole('button', { name: 'Settle' }))
    expect(updateAttentionMock).toHaveBeenCalledTimes(1)
    reject(new Error('stale attention revision'))
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe('This task changed elsewhere. Your action was not applied.'))
    expect(screen.getByRole('status').getAttribute('aria-live')).toBe('polite')
    expect(screen.getByRole('status').getAttribute('aria-atomic')).toBe('true')
  })

  it('keeps a stale announcement through an authoritative receipt reconciliation', async () => {
    let reject!: (reason: Error) => void
    updateAttentionMock.mockImplementationOnce(() => new Promise((_resolve, fail) => { reject = fail }))

    function ReconciledControl() {
      const [announcement, setAnnouncement] = useState<AttentionAnnouncement | null>(null)
      const [visible, setVisible] = useState(true)

      return (
        <div>
          <BoardAnnouncer announcement={announcement} />
          {visible && (
            <AttentionControls
              onAnnouncement={next => {
                setAnnouncement(next)
                setVisible(false)
              }}
              task={{ ...baseTask, attention: receipt('active', 0) }}
            />
          )}
          {!visible && <div data-testid="authoritative-settled-lane">Settled elsewhere</div>}
        </div>
      )
    }

    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } })}><ReconciledControl /></QueryClientProvider>)
    fireEvent.click(screen.getByRole('button', { name: 'Settle' }))
    await waitFor(() => expect(updateAttentionMock).toHaveBeenCalledTimes(1))
    reject(new Error('409 stale attention revision'))

    await waitFor(() => expect(screen.getByTestId('authoritative-settled-lane')).toBeTruthy())
    expect(screen.queryByRole('button', { name: 'Settle' })).toBeNull()
    expect(screen.getAllByRole('status')).toHaveLength(1)
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe('This task changed elsewhere. Your action was not applied.'))
  })

  it('commits an empty frame for repeated text and ignores duplicate attempt ids', async () => {
    const first = { attemptId: 'attempt-1', message: 'Task awake' }
    const { rerender } = render(<BoardAnnouncer announcement={first} />)
    expect(screen.getByRole('status').textContent).toBe('Task awake')

    rerender(<BoardAnnouncer announcement={first} />)
    expect(screen.getByRole('status').textContent).toBe('Task awake')

    rerender(<BoardAnnouncer announcement={{ attemptId: 'attempt-2', message: 'Task awake' }} />)
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe('Task awake'))
    expect(screen.getAllByRole('status')).toHaveLength(1)
  })

  it('shows the compact presets and restores trigger focus on Escape and Cancel', async () => {
    render(view({ ...baseTask, attention: receipt('active', 0) }))
    const trigger = screen.getByRole('button', { name: 'Snooze…' })
    fireEvent.click(trigger)

    for (const label of ['1 hr', 'Tmrw 9am', '1 wk', '1 mo', 'Custom…']) {
      const classes = screen.getByRole('button', { name: label }).classList

      expect(classes.contains('min-h-11') && classes.contains('min-w-11')).toBe(true)
    }

    fireEvent.keyDown(screen.getByRole('dialog', { name: 'Snooze task' }), { key: 'Escape' })
    await waitFor(() => expect(document.activeElement).toBe(trigger))

    fireEvent.click(trigger)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitFor(() => expect(document.activeElement).toBe(trigger))
  })

  it('submits an exact local custom time at the current receipt revision', async () => {
    process.env.TZ = 'America/Chicago'
    updateAttentionMock.mockResolvedValueOnce(response('snoozed', 8))
    render(view({ ...baseTask, attention: receipt('active', 7) }))
    fireEvent.click(screen.getByRole('button', { name: 'Snooze…' }))
    fireEvent.change(screen.getByLabelText('Exact local date and time'), { target: { value: '2030-01-02T09:15' } })
    fireEvent.click(screen.getByRole('button', { name: 'Snooze' }))
    await waitFor(() => expect(updateAttentionMock).toHaveBeenCalledWith('task-safe', 'snooze', 7, 1_893_597_300))
    expect(screen.getByRole('status').textContent).toBe('Task snoozed')
  })
})

describe('attention local wake fields', () => {
  it.each([
    ['UTC', '2026-01-02T03:04'],
    ['America/Chicago', '2026-01-01T21:04'],
    ['Asia/Kathmandu', '2026-01-02T08:49']
  ])('formats local wall time in %s', (tz, expected) => {
    process.env.TZ = tz
    expect(formatLocalDateTime(new Date('2026-01-02T03:04:00Z'))).toBe(expected)
  })

  it('rejects normalized calendar values and DST gaps', () => {
    process.env.TZ = 'America/Chicago'
    expect(parseLocalDateTime('2026-02-30T09:00')).toBeNull()
    expect(parseLocalDateTime('2026-03-08T02:30')).toBeNull()
  })

  it('uses the earlier DST-fold occurrence and preserves its wall-clock field', () => {
    process.env.TZ = 'America/Chicago'
    const folded = parseLocalDateTime('2026-11-01T01:30')
    expect(folded).not.toBeNull()
    expect(formatLocalDateTime(folded!)).toBe('2026-11-01T01:30')
    expect(folded!.toISOString()).toBe('2026-11-01T06:30:00.000Z')
  })
})
