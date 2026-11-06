import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SessionInfo } from '@/types/hermes'

import { listEveryArchivedSession } from './sidebar-archive'

const listAllProfileSessions = vi.hoisted(() => vi.fn())

vi.mock('@/api/sessions', () => ({ listAllProfileSessions }))

const archivedPage = (offset: number, count = 500): SessionInfo[] =>
  Array.from({ length: count }, (_, i) =>
    ({ id: `archive-${offset + i}`, archived: true, profile: 'default' }) as SessionInfo
  )

const livePin = { id: 'pinned', archived: false, profile: 'default', pinned: true } as SessionInfo

beforeEach(() => listAllProfileSessions.mockReset())

describe('archived page publication', () => {
  it('keeps 2500 completed rows when the sixth page times out, preserving offsets and the original error', async () => {
    const timeout = new Error('Timed out connecting to Hermes backend after 60000ms')
    let rejectSixth!: (reason?: unknown) => void
    const sixth = new Promise<never>((_, reject) => { rejectSixth = reject })

    listAllProfileSessions.mockImplementation((...args: unknown[]) => {
      const offset = Number(args[6])

      return offset === 2500
        ? sixth
        : Promise.resolve({ sessions: [...archivedPage(offset), livePin], total: 3000 })
    })

    const snapshots: SessionInfo[][] = []
    const done = listEveryArchivedSession({ onPage: rows => snapshots.push(rows) })

    await vi.waitFor(() => expect(listAllProfileSessions).toHaveBeenCalledTimes(6))
    expect(snapshots).toHaveLength(5)
    expect(snapshots.map(rows => rows.filter(row => row.archived).length)).toEqual([500, 1000, 1500, 2000, 2500])
    expect(snapshots[4].filter(row => row.id === 'pinned')).toHaveLength(1)
    expect(listAllProfileSessions.mock.calls.map(args => args[6])).toEqual([0, 500, 1000, 1500, 2000, 2500])

    const failure = expect(done).rejects.toBe(timeout)
    rejectSixth(timeout)
    await failure
    expect(snapshots[4].filter(row => row.archived)).toHaveLength(2500)
  })

  it('publishes successful sibling profiles but rejects a partial-profile response', async () => {
    listAllProfileSessions.mockResolvedValue({
      sessions: archivedPage(0, 1),
      total: 1,
      errors: [{ profile: 'work', error: 'profile read failed' }]
    })
    const onPage = vi.fn()

    await expect(listEveryArchivedSession({ onPage })).rejects.toThrow('profile read failed')
    expect(onPage).toHaveBeenCalledWith(archivedPage(0, 1))
  })

  it('stops the next page after cancellation during a completed-page callback', async () => {
    listAllProfileSessions.mockResolvedValue({ sessions: archivedPage(0), total: 1000 })
    const controller = new AbortController()

    await expect(listEveryArchivedSession({
      signal: controller.signal,
      onPage: () => controller.abort()
    })).rejects.toMatchObject({ name: 'AbortError' })

    expect(listAllProfileSessions).toHaveBeenCalledTimes(1)
  })

  it('does not request a page for an already-cancelled scope', async () => {
    const controller = new AbortController()
    controller.abort()

    await expect(listEveryArchivedSession({ signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' })
    expect(listAllProfileSessions).not.toHaveBeenCalled()
  })
})
