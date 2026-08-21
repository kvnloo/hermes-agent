import { host } from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { type ReactElement, useState } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type * as KanbanApi from './api'
import { updateAttention } from './api'
import { AttentionControls, BoardAnnouncer, KanbanPageShell, useBoardAttentionAnnouncements, useKanbanPageAnnouncements } from './board'
import { formatLocalDateTime, parseLocalDateTime } from './datetime-local'
import type { AttentionReceipt, KanbanTask } from './types'
import { errText } from './ui'

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
  vi.restoreAllMocks()
  updateAttentionMock.mockReset()
  vi.spyOn(host, 'notify').mockImplementation(() => '')
})

describe('attention lifecycle controls', () => {
  it('extracts a message from structured conflict details', () => {
    expect(errText(new Error(`409: ${JSON.stringify({ detail: { attention: receipt('settled', 5), current_revision: 5, message: 'stale attention revision' } })}`))).toBe('stale attention revision')
  })

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

  it.each([
    ['Settle', 'active', 'settled', 'Attention settled'],
    ['1 hr', 'active', 'snoozed', 'Task snoozed'],
    ['Wake', 'settled', 'active', 'Task awake']
  ] as const)('keeps repeated stale %s attempts distinct across filter reconciliation and permits success afterward', async (actionLabel, initialState, successState, successMessage) => {
    const attemptIds: string[] = []
    updateAttentionMock
      .mockRejectedValueOnce(new Error('409 stale attention revision'))
      .mockRejectedValueOnce(new Error('409 stale attention revision'))
      .mockResolvedValueOnce(response(successState, 2))

    function ReconciledControl() {
      const attention = useBoardAttentionAnnouncements()
      const [visible, setVisible] = useState(true)

      return (
        <div>
          <BoardAnnouncer announcement={attention.announcement} />
          <header data-testid="board-focus" ref={attention.focusTarget} tabIndex={-1}>Board context</header>
          {visible ? (
            <AttentionControls
              nextAttemptId={attention.nextAttemptId}
              onAnnouncement={next => {
                attemptIds.push(next.attemptId)
                attention.announce(next)

                if (next.stale) {
                  setVisible(false)
                }
              }}
              task={{ ...baseTask, attention: receipt(initialState, 1) }}
            />
          ) : (
            <div>
              <div data-testid="authoritative-lane">Filtered by authoritative receipt</div>
              <button onClick={() => setVisible(true)} type="button">Reconcile task</button>
            </div>
          )}
        </div>
      )
    }

    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } })}><ReconciledControl /></QueryClientProvider>)
    const runAction = () => {
      if (actionLabel === '1 hr') {
        fireEvent.click(screen.getByRole('button', { name: 'Snooze…' }))
      }

      fireEvent.click(screen.getByRole('button', { name: actionLabel }))
    }

    runAction()
    await waitFor(() => expect(screen.getByTestId('authoritative-lane')).toBeTruthy())
    expect(screen.getAllByRole('status')).toHaveLength(1)
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe('This task changed elsewhere. Your action was not applied.'))
    expect(document.body.textContent?.split('This task changed elsewhere. Your action was not applied.')).toHaveLength(2)
    await waitFor(() => expect(document.activeElement).toBe(screen.getByTestId('board-focus')))
    expect(updateAttentionMock).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Reconcile task' }))
    runAction()
    await waitFor(() => expect(screen.getByTestId('authoritative-lane')).toBeTruthy())
    expect(updateAttentionMock).toHaveBeenCalledTimes(2)
    expect(new Set(attemptIds.slice(0, 2)).size).toBe(2)

    fireEvent.click(screen.getByRole('button', { name: 'Reconcile task' }))
    runAction()
    await waitFor(() => expect(screen.getByRole('status').textContent).toBe(successMessage))
    expect(updateAttentionMock).toHaveBeenCalledTimes(3)
  })

  it('commits an empty frame for repeated text and ignores duplicate attempt ids', async () => {
    let nextFrame: FrameRequestCallback | undefined
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(callback => {
      nextFrame = callback

      return 42
    })
    const first = { attemptId: 'attempt-1', message: 'Task awake' }
    const { rerender } = render(<BoardAnnouncer announcement={first} />)
    expect(screen.getByRole('status').textContent).toBe('Task awake')

    rerender(<BoardAnnouncer announcement={first} />)
    expect(screen.getByRole('status').textContent).toBe('Task awake')

    rerender(<BoardAnnouncer announcement={{ attemptId: 'attempt-2', message: 'Task awake' }} />)
    expect(screen.getByRole('status').textContent).toBe('')
    act(() => nextFrame?.(0))
    expect(screen.getByRole('status').textContent).toBe('Task awake')
    expect(screen.getAllByRole('status')).toHaveLength(1)
  })

  it('keeps the page-shell host outside a replaced interactive board', () => {
    const { rerender } = render(
      <KanbanPageShell>
        <div data-testid="board-mount">board one</div>
      </KanbanPageShell>
    )

    const hostNode = screen.getByRole('status')

    expect(hostNode.closest('[data-kanban-interactive-root]')).toBeNull()
    rerender(
      <KanbanPageShell>
        <div data-testid="board-mount">board two</div>
      </KanbanPageShell>
    )
    expect(screen.getByRole('status')).toBe(hostNode)
    expect(screen.getByTestId('board-mount').textContent).toBe('board two')
  })

  it('announces a stale modal action after the interactive board is reconciled away', async () => {
    updateAttentionMock.mockRejectedValueOnce(new Error('409 stale attention revision'))

    function ReplaceableBoard() {
      const attention = useKanbanPageAnnouncements()
      const [visible, setVisible] = useState(true)

      return visible ? (
        <AttentionControls
          nextAttemptId={attention.nextAttemptId}
          onAnnouncement={announcement => {
            attention.announce(announcement)
            setVisible(false)
          }}
          task={{ ...baseTask, attention: receipt('active', 3) }}
        />
      ) : <div data-testid="reconciled-board">Authoritative board</div>
    }

    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } })}>
        <KanbanPageShell><ReplaceableBoard /></KanbanPageShell>
      </QueryClientProvider>
    )

    const hostNode = screen.getByRole('status')

    fireEvent.click(screen.getByRole('button', { name: 'Snooze…' }))
    fireEvent.click(screen.getByRole('button', { name: '1 hr' }))

    await waitFor(() => expect(screen.getByTestId('reconciled-board')).toBeTruthy())
    expect(screen.getByRole('status')).toBe(hostNode)
    await waitFor(() => expect(hostNode.textContent).toBe('This task changed elsewhere. Your action was not applied.'))
    expect(hostNode.closest('[inert], [aria-hidden="true"]')).toBeNull()
  })

  it('shows the compact presets and restores trigger focus on Escape and Cancel', async () => {
    render(view({ ...baseTask, attention: receipt('active', 0) }))
    const trigger = screen.getByRole('button', { name: 'Snooze…' })
    expect(screen.getByRole('button', { name: 'Settle' }).classList.contains('min-h-11')).toBe(true)
    expect(trigger.classList.contains('min-h-11')).toBe(true)
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
