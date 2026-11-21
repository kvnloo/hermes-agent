// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { $apiRequestScope } from '@/api/client'
import { en } from '@/i18n/en'
import type { SessionInfo } from '@/types/hermes'

import { SessionsSettings } from './sessions-settings'

const listEveryArchivedSession = vi.hoisted(() => vi.fn())
const notifyError = vi.hoisted(() => vi.fn())

vi.mock('@/i18n', () => ({ useI18n: () => ({ t: en }) }))
vi.mock('@/store/sidebar-archive', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  listEveryArchivedSession
}))
vi.mock('@/store/notifications', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  notifyError
}))

const row = (id: string, profile = 'default'): SessionInfo =>
  ({
    archived: true,
    ended_at: null,
    id,
    input_tokens: 0,
    is_active: false,
    last_active: 1,
    message_count: 1,
    model: null,
    output_tokens: 0,
    preview: null,
    profile,
    source: 'desktop',
    started_at: 1,
    title: `${id}-${profile}`,
    tool_call_count: 0
  }) as SessionInfo

beforeEach(() => {
  $apiRequestScope.set({ connectionId: null, profile: null })
  listEveryArchivedSession.mockReset()
  notifyError.mockReset()
})

afterEach(() => cleanup())

describe('archived Settings incremental loading', () => {
  it('keeps an actionable completed row after a later timeout, then retries without an empty success', async () => {
    let publish!: (rows: SessionInfo[]) => void
    let rejectTail!: (reason?: unknown) => void
    const timeout = new Error('Timed out connecting to Hermes backend after 60000ms')

    listEveryArchivedSession.mockImplementationOnce((options: { onPage: typeof publish }) => {
      publish = options.onPage
      return new Promise<SessionInfo[]>((_, reject) => { rejectTail = reject })
    })
    listEveryArchivedSession.mockImplementationOnce(async (options: { onPage: typeof publish }) => {
      const rows = [row('first'), row('second')]
      options.onPage(rows)
      return rows
    })

    render(<SessionsSettings subpage="archived" />)
    await waitFor(() => expect(listEveryArchivedSession).toHaveBeenCalledTimes(1))

    await act(async () => publish([row('first')]))
    expect(screen.getByText('first-default')).toBeDefined()
    expect(screen.getByText(en.settings.sessions.loading)).toBeDefined()
    expect(screen.getByRole('button', { name: en.settings.sessions.unarchive })).toBeDefined()
    expect(screen.queryByText(en.settings.sessions.emptyArchivedTitle)).toBeNull()

    await act(async () => rejectTail(timeout))
    expect(screen.getByRole('alert').textContent).toContain(en.settings.sessions.failedLoad)
    expect(notifyError).toHaveBeenCalledWith(timeout, en.settings.sessions.failedLoad)
    expect(screen.getByText('first-default')).toBeDefined()
    expect(screen.queryByText(en.settings.sessions.emptyArchivedTitle)).toBeNull()

    await act(async () => fireEvent.click(screen.getByRole('button', { name: en.common.retry })))
    await waitFor(() => expect(screen.getByText('second-default')).toBeDefined())
    expect(listEveryArchivedSession).toHaveBeenCalledTimes(2)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  it('shows Retry, not a successful empty archive, if the first page fails', async () => {
    listEveryArchivedSession.mockRejectedValue(new Error('offline'))

    render(<SessionsSettings subpage="archived" />)
    await screen.findByRole('alert')

    expect(screen.getByRole('button', { name: en.common.retry })).toBeDefined()
    expect(screen.queryByText(en.settings.sessions.emptyArchivedTitle)).toBeNull()
  })

  it('aborts a previous backend scope and cannot paint its late pages into the next scope', async () => {
    let publishOld!: (rows: SessionInfo[]) => void
    let finishOld!: (rows: SessionInfo[]) => void

    listEveryArchivedSession.mockImplementationOnce((options: { onPage: typeof publishOld }) => {
      publishOld = options.onPage
      return new Promise<SessionInfo[]>(resolve => { finishOld = resolve })
    })
    listEveryArchivedSession.mockImplementationOnce(async (options: { onPage: (rows: SessionInfo[]) => void }) => {
      const rows = [row('new-scope')]
      options.onPage(rows)
      return rows
    })

    render(<SessionsSettings subpage="archived" />)
    await waitFor(() => expect(listEveryArchivedSession).toHaveBeenCalledTimes(1))
    const oldSignal = listEveryArchivedSession.mock.calls[0][0].signal as AbortSignal

    await act(async () => $apiRequestScope.setKey('connectionId', 'new-connection'))
    await waitFor(() => expect(screen.getByText('new-scope-default')).toBeDefined())
    expect(oldSignal.aborted).toBe(true)

    await act(async () => {
      publishOld([row('stale')])
      finishOld([row('stale')])
    })
    expect(screen.queryByText('stale-default')).toBeNull()
    expect(screen.getByText('new-scope-default')).toBeDefined()
  })
})
