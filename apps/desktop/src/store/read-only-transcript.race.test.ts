import { beforeEach, describe, expect, it } from 'vitest'

import { $connectionsRegistry } from './connections'
import { $profiles } from './profile'
import {
  $readOnlyStoredTranscripts,
  clearStoredTranscriptReadOnly,
  isStoredTranscriptReadOnly,
  markStoredTranscriptReadOnly,
  resetLiveResumeGenerations,
  resumeWithStoredTranscriptFallback
} from './read-only-transcript'
import { assertSessionOwnerResolved } from './session-owner-resolution'

const registry = (...ids: string[]) =>
  ({
    connections: ids.map(id => ({ id })),
    lastUsed: ids[0] ?? null,
    launchMode: 'primary',
    primary: ids[0] ?? null
  }) as never

beforeEach(() => {
  $connectionsRegistry.set(null)
  $profiles.set([])
  $readOnlyStoredTranscripts.set(new Set())
  resetLiveResumeGenerations()
})

describe('read-only stored-transcript race (#94724 stale no-owner recovery after a later live resume)', () => {
  it('does NOT mark read-only after a concurrent live resume proved the session routable', async () => {
    $connectionsRegistry.set(registry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }, { name: 'researcher' }] as never)

    // Call A's stored read is deferred so a later live resume can interleave.
    let resolveStored!: (value: { messages: unknown[] }) => void

    const storedRead = new Promise<{ messages: unknown[] }>(resolve => {
      resolveStored = resolve
    })

    const transcript = { messages: [{ content: 'intact history', role: 'user' }] }

    // Call A: owner unresolvable under registry topology -> SessionOwnerResolutionError
    // (REAL fail-closed gate, same as the existing test at read-only-transcript.test.ts:50).
    const callA = resumeWithStoredTranscriptFallback(
      'legacy-1',
      async () => {
        assertSessionOwnerResolved(undefined, { method: 'session.resume', sessionId: 'legacy-1' })

        return { session_id: 'runtime-A' }
      },
      () => storedRead
    )

    // Let Call A reach the catch and start awaiting the deferred stored read.
    await Promise.resolve()
    await Promise.resolve()
    expect(isStoredTranscriptReadOnly('legacy-1')).toBe(false) // flag still false at catch entry

    // A LATER live resume for the same id now proves routability. Its success
    // path calls clearStoredTranscriptReadOnly — which bumps the generation
    // (even though the latch was never set).
    clearStoredTranscriptReadOnly('legacy-1')
    expect(isStoredTranscriptReadOnly('legacy-1')).toBe(false)

    // The stale stored read resolves last.
    resolveStored!(transcript)
    const outcomeA = await callA
    expect(outcomeA.mode).toBe('read-only')

    // CONTRACT: a live resume has already proved this session routable; the
    // stale recovery must not latch it read-only over the live outcome.
    expect(isStoredTranscriptReadOnly('legacy-1')).toBe(false)
  })

  it('marks read-only for a LEGITIMATE first-time recovery when no live resume interleaves', async () => {
    $connectionsRegistry.set(registry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }, { name: 'researcher' }] as never)

    const transcript = { messages: [{ content: 'history', role: 'user' }] }

    const outcome = await resumeWithStoredTranscriptFallback(
      'legit-1',
      async () => {
        assertSessionOwnerResolved(undefined, { method: 'session.resume', sessionId: 'legit-1' })

        return { session_id: 'runtime-1' }
      },
      async () => transcript
    )

    expect(outcome.mode).toBe('read-only')
    // No interleaving live resume -> generation unchanged -> the mark applies.
    expect(isStoredTranscriptReadOnly('legit-1')).toBe(true)
  })

  it('lets a later live resume clear a PRIOR read-only latch (the live-upgrade path)', async () => {
    $connectionsRegistry.set(registry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }] as never)

    // First open: owner unresolvable (NULL-owner legacy row) -> read-only.
    markStoredTranscriptReadOnly('upgrade-1')
    expect(isStoredTranscriptReadOnly('upgrade-1')).toBe(true)

    // The backfill stamps the row; a later live resume succeeds and clears.
    const outcome = await resumeWithStoredTranscriptFallback(
      'upgrade-1',
      async () => {
        assertSessionOwnerResolved('default', { method: 'session.resume', sessionId: 'upgrade-1' })

        return { session_id: 'runtime-upgrade' }
      },
      async () => {
        throw new Error('stored read must not run on the live path')
      }
    )

    expect(outcome.mode).toBe('live')
    expect(isStoredTranscriptReadOnly('upgrade-1')).toBe(false)
  })

  it("suppresses a stale mark when the helper's OWN concurrent live resume clears mid-flight", async () => {
    $connectionsRegistry.set(registry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }, { name: 'researcher' }] as never)

    // Call A: owner unresolvable -> catch -> awaits a deferred stored read.
    let resolveStored!: (value: { messages: unknown[] }) => void

    const storedRead = new Promise<{ messages: unknown[] }>(resolve => {
      resolveStored = resolve
    })

    const callA = resumeWithStoredTranscriptFallback(
      'shared-1',
      async () => {
        assertSessionOwnerResolved(undefined, { method: 'session.resume', sessionId: 'shared-1' })

        return { session_id: 'runtime-A' }
      },
      () => storedRead
    )

    // Let Call A reach the catch.
    await Promise.resolve()
    await Promise.resolve()

    // Call B: a LATER live resume for the same id succeeds through the SAME
    // helper. Its success path calls clearStoredTranscriptReadOnly internally,
    // bumping the generation.
    const callB = resumeWithStoredTranscriptFallback(
      'shared-1',
      async () => ({ session_id: 'runtime-B' }),
      async () => {
        throw new Error('stored read must not run on the live path')
      }
    )

    const outcomeB = await callB
    expect(outcomeB.mode).toBe('live')

    // Call A's stale stored read resolves last.
    resolveStored!({ messages: [{ content: 'stale', role: 'user' }] })
    const outcomeA = await callA
    expect(outcomeA.mode).toBe('read-only')

    // The latch must NOT be set: the helper's own live-success clear proved
    // the session routable while Call A's stored read was still in flight.
    expect(isStoredTranscriptReadOnly('shared-1')).toBe(false)
  })

  it('does not bump the generation on a read-only-only flow (mark is not a live signal)', async () => {
    $connectionsRegistry.set(registry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }, { name: 'researcher' }] as never)

    await resumeWithStoredTranscriptFallback(
      'gen-1',
      async () => {
        assertSessionOwnerResolved(undefined, { method: 'session.resume', sessionId: 'gen-1' })

        return { session_id: 'runtime-1' }
      },
      async () => ({ messages: [] })
    )

    expect(isStoredTranscriptReadOnly('gen-1')).toBe(true)

    // A SUBSEQUENT legit recovery for the SAME id (generation untouched by the
    // prior read-only flow) still marks when no live resume interleaves — the
    // generation counter only moves on a real live-resume success signal.
    await resumeWithStoredTranscriptFallback(
      'gen-1',
      async () => {
        assertSessionOwnerResolved(undefined, { method: 'session.resume', sessionId: 'gen-1' })

        return { session_id: 'runtime-2' }
      },
      async () => ({ messages: [] })
    )

    expect(isStoredTranscriptReadOnly('gen-1')).toBe(true)
  })
})
