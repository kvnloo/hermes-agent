import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type * as HermesModule from '@/hermes'
import { $connectionsRegistry } from '@/store/connections'
import { $profiles } from '@/store/profile'
import { isStoredTranscriptReadOnly, resetLiveResumeGenerations } from '@/store/read-only-transcript'
import { setSessionOwnerHint, setSessions } from '@/store/session'
import { sessionTileDelegate } from '@/store/session-states'
import type { SessionInfo } from '@/types/hermes'

import { clearSingleFlightSessionResumeState } from '../../session/hooks/use-prompt-actions/single-flight-resume'

import { useSessionTileDelegate } from './use-session-tile-delegate'

vi.mock('@/hermes', async importActual => ({
  ...(await importActual<typeof HermesModule>()),
  fetchStoredTranscriptAcrossBackends: vi.fn(async () => ({ messages: [], session_id: '' })),
  getLatestSessionMessages: vi.fn(async () => ({ messages: [], session_id: '' })),
  getSession: vi.fn(async () => {
    throw new Error('not found')
  })
}))
vi.mock('@/store/gateway', async importActual => ({
  ...(await importActual<Record<string, unknown>>()),
  requestGatewayForAgent: vi.fn(),
  requestGatewayForProfile: vi.fn()
}))

const { fetchStoredTranscriptAcrossBackends, getLatestSessionMessages, getSession } = await import('@/hermes')
const { requestGatewayForAgent, requestGatewayForProfile } = await import('@/store/gateway')

const row = (over: Partial<SessionInfo>): SessionInfo =>
  ({
    ended_at: null,
    id: 'live',
    input_tokens: 0,
    is_active: false,
    last_active: 0,
    message_count: 1,
    model: null,
    output_tokens: 0,
    preview: null,
    profile: 'default',
    source: null,
    started_at: 0,
    title: null,
    ...over
  }) as SessionInfo

function renderTile(
  requestGateway: ReturnType<typeof vi.fn>,
  refs?: {
    runtimeIdByStoredSessionIdRef?: { current: Map<string, string> }
    sessionStateByRuntimeIdRef?: { current: Map<string, unknown> }
    updateSessionState?: ReturnType<typeof vi.fn>
  }
) {
  renderHook(() =>
    useSessionTileDelegate({
      archiveSession: vi.fn(async () => undefined),
      branchStoredSession: vi.fn(async () => undefined),
      executeSlashCommand: vi.fn(async () => undefined) as never,
      removeSession: vi.fn(async () => undefined),
      requestGateway: requestGateway as never,
      runtimeIdByStoredSessionIdRef: (refs?.runtimeIdByStoredSessionIdRef ?? { current: new Map() }) as never,
      sessionStateByRuntimeIdRef: (refs?.sessionStateByRuntimeIdRef ?? { current: new Map() }) as never,
      updateSessionState: (refs?.updateSessionState ?? vi.fn()) as never
    })
  )
}

describe('useSessionTileDelegate resumeTile', () => {
  beforeEach(() => {
    setSessions([])
    vi.mocked(getLatestSessionMessages).mockClear()
  })

  afterEach(() => {
    setSessions([])
  })

  it('carries the owning profile into a cold tile resume so it cannot fork profiles', async () => {
    // A tile opens a session owned by another profile. Resuming without the
    // profile lets the gateway fall back to the launch-profile DB and clone the
    // conversation into the wrong profile (#67603). The owning profile must ride
    // both the transcript prefetch and the resume RPC.
    setSessions([row({ id: 'stored-x', profile: 'ai-engineer' })])

    const requestGateway = vi.fn(async (method: string) =>
      method === 'session.resume' ? ({ session_id: 'runtime-1' } as never) : ({} as never)
    )

    vi.mocked(requestGatewayForProfile).mockResolvedValueOnce({ session_id: 'runtime-1' } as never)

    renderTile(requestGateway)
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-x')

    expect(runtimeId).toBe('runtime-1')
    expect(getLatestSessionMessages).toHaveBeenCalledWith('stored-x', 'ai-engineer')
    expect(requestGatewayForProfile).toHaveBeenCalledWith(
      'ai-engineer',
      'session.resume',
      {
        session_id: 'stored-x',
        cols: 96,
        profile: 'ai-engineer',
        omit_messages: true
      },
      undefined,
      undefined
    )
    expect(requestGateway).not.toHaveBeenCalled()
  })

  it('resolves and carries a default-profile session explicitly', async () => {
    setSessions([row({ id: 'stored-y', profile: 'default' })])

    const requestGateway = vi.fn(async () => ({}) as never)

    // #92961: a known owner is ALWAYS routed through the profile router —
    // even 'default' — never dispatched on the ambient socket.
    vi.mocked(requestGatewayForProfile).mockResolvedValueOnce({ session_id: 'runtime-2' } as never)

    renderTile(requestGateway)
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-y')

    expect(runtimeId).toBe('runtime-2')
    expect(requestGatewayForProfile).toHaveBeenCalledWith(
      'default',
      'session.resume',
      {
        session_id: 'stored-y',
        cols: 96,
        profile: 'default',
        omit_messages: true
      },
      undefined,
      undefined
    )
    expect(requestGateway).not.toHaveBeenCalled()
  })

  it('carries a session row connection owner into a same-named tile resume', async () => {
    setSessions([row({ connection_id: 'source-b', id: 'stored-shared', profile: 'default' })])

    const ambientRequest = vi.fn(async () => ({}) as never)
    vi.mocked(requestGatewayForAgent).mockResolvedValueOnce({ session_id: 'runtime-shared' } as never)

    renderTile(ambientRequest)
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-shared')

    expect(runtimeId).toBe('runtime-shared')
    expect(requestGatewayForAgent).toHaveBeenCalledWith('source-b', 'default', 'session.resume', {
      session_id: 'stored-shared',
      cols: 96,
      omit_messages: true,
      profile: 'default'
    })
    expect(ambientRequest).not.toHaveBeenCalled()
  })

  it('routes a Bot tile prefetch and resume through its exact connection owner', async () => {
    const route = {
      connectionId: 'barry',
      mode: 'remote' as const,
      profile: 'oxcoder',
      targetProfile: 'backend-oxcoder'
    }

    setSessionOwnerHint('stored-remote', route)
    vi.mocked(requestGatewayForAgent).mockResolvedValueOnce({ session_id: 'runtime-remote' } as never)
    const ambientRequest = vi.fn(async () => ({}) as never)

    renderTile(ambientRequest)
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-remote')

    expect(runtimeId).toBe('runtime-remote')
    expect(getLatestSessionMessages).toHaveBeenCalledWith('stored-remote', {
      connectionId: 'barry',
      profile: 'backend-oxcoder'
    })
    expect(requestGatewayForAgent).toHaveBeenCalledWith('barry', 'oxcoder', 'session.resume', {
      session_id: 'stored-remote',
      cols: 96,
      omit_messages: true,
      profile: 'backend-oxcoder'
    })
    expect(ambientRequest).not.toHaveBeenCalled()
  })

  it('reuses a warm binding that still carries a transcript', async () => {
    const stateA = { busy: false, messages: [{ id: 'm1' }], storedSessionId: 'stored-a' }
    const runtimeIdByStoredSessionIdRef = { current: new Map([['stored-a', 'runtime-a']]) }
    const sessionStateByRuntimeIdRef = { current: new Map([['runtime-a', stateA]]) }
    const requestGateway = vi.fn(async () => ({}) as never)

    renderTile(requestGateway, { runtimeIdByStoredSessionIdRef, sessionStateByRuntimeIdRef })
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-a')

    expect(runtimeId).toBe('runtime-a')
    expect(requestGateway).not.toHaveBeenCalled()
    expect(getLatestSessionMessages).not.toHaveBeenCalled()
  })

  it('merges persisted messages into a warm tile on explicit reopen (#96183)', async () => {
    const stateA = {
      busy: false,
      messages: [{ id: 'm1', parts: [{ type: 'text', text: 'old' }], role: 'user' }],
      storedSessionId: 'stored-a'
    }

    const runtimeIdByStoredSessionIdRef = { current: new Map([['stored-a', 'runtime-a']]) }
    const sessionStateByRuntimeIdRef = { current: new Map([['runtime-a', stateA]]) }
    const updateSessionState = vi.fn((_id, updater) => updater(stateA))
    const requestGateway = vi.fn(async () => ({}) as never)

    vi.mocked(getLatestSessionMessages).mockResolvedValueOnce({
      messages: [
        { id: 'm1', content: 'old', role: 'user' },
        { id: 'm2', content: 'cron delivery', role: 'user' }
      ],
      session_id: 'stored-a'
    } as never)

    renderTile(requestGateway, { runtimeIdByStoredSessionIdRef, sessionStateByRuntimeIdRef, updateSessionState })
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-a', { refreshTranscript: true })

    expect(runtimeId).toBe('runtime-a')
    expect(requestGateway).not.toHaveBeenCalled()
    expect(getLatestSessionMessages).toHaveBeenCalled()
    expect(updateSessionState).toHaveBeenCalled()

    const updater = updateSessionState.mock.calls[0][1] as (state: typeof stateA) => {
      messages: Array<{ parts?: Array<{ text?: string }> }>
    }

    const next = updater(stateA)
    const texts = next.messages.flatMap(message => (message.parts ?? []).map(part => part.text ?? ''))

    expect(texts.some(text => text.includes('cron delivery'))).toBe(true)
  })

  it('falls through to a real resume when the warm binding has no transcript (post-wake empty tile)', async () => {
    // Sleep/wake regression: a released/stale cached state (messages: []) must
    // NOT satisfy the warm path — reusing it re-bound the tile to a dead
    // runtime id and painted the pane permanently empty.
    setSessions([row({ id: 'stored-b', profile: 'default' })])

    const staleState = { busy: false, messages: [], storedSessionId: 'stored-b' }
    const runtimeIdByStoredSessionIdRef = { current: new Map([['stored-b', 'runtime-dead']]) }
    const sessionStateByRuntimeIdRef = { current: new Map([['runtime-dead', staleState]]) }

    const requestGateway = vi.fn(async () => ({}) as never)

    vi.mocked(requestGatewayForProfile).mockResolvedValueOnce({ session_id: 'runtime-fresh' } as never)

    renderTile(requestGateway, { runtimeIdByStoredSessionIdRef, sessionStateByRuntimeIdRef })
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-b')

    expect(runtimeId).toBe('runtime-fresh')
    expect(requestGatewayForProfile).toHaveBeenCalledWith(
      'default',
      'session.resume',
      {
        session_id: 'stored-b',
        cols: 96,
        profile: 'default',
        omit_messages: true
      },
      undefined,
      undefined
    )
  })

  it('hydrates the tile model and provider from resume info', async () => {
    setSessions([row({ id: 'stored-model', profile: 'default' })])

    const updateSessionState = vi.fn()

    vi.mocked(requestGatewayForProfile).mockResolvedValueOnce({
      info: { fast: true, model: 'gpt-5', provider: 'openai', reasoning_effort: 'high', running: false },
      session_id: 'runtime-model'
    } as never)

    renderTile(vi.fn(), { updateSessionState })
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-model')

    expect(runtimeId).toBe('runtime-model')
    expect(updateSessionState).toHaveBeenCalled()

    const updater = updateSessionState.mock.calls[0][1] as (state: { messages: unknown[] }) => Record<string, unknown>
    const next = updater({ messages: [] })

    expect(next.model).toBe('gpt-5')
    expect(next.provider).toBe('openai')
    expect(next.reasoningEffort).toBe('high')
    expect(next.fast).toBe(true)
  })

  it('invalidateRuntimeBindings clears the stored→runtime map so tiles re-resume after reconnect', async () => {
    setSessions([row({ id: 'stored-c', profile: 'default' })])

    const liveState = { busy: false, messages: [{ id: 'm1' }], storedSessionId: 'stored-c' }
    const runtimeIdByStoredSessionIdRef = { current: new Map([['stored-c', 'runtime-dead']]) }
    const sessionStateByRuntimeIdRef = { current: new Map([['runtime-dead', liveState]]) }

    const requestGateway = vi.fn(async () => ({}) as never)

    vi.mocked(requestGatewayForProfile).mockResolvedValueOnce({ session_id: 'runtime-fresh' } as never)

    renderTile(requestGateway, { runtimeIdByStoredSessionIdRef, sessionStateByRuntimeIdRef })

    // Gateway reconnect (what resetTileRuntimeBindings calls on wake):
    sessionTileDelegate()!.invalidateRuntimeBindings!()
    expect(runtimeIdByStoredSessionIdRef.current.size).toBe(0)

    // The next resume goes cold instead of reusing the dead binding.
    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-c')
    expect(runtimeId).toBe('runtime-fresh')
  })
})

describe('useSessionTileDelegate retireBusyClaim', () => {
  it('retires a stale busy claim through the session-state write path (#93059)', () => {
    const busyState = { awaitingResponse: true, busy: true, messages: [{ id: 'm1' }], storedSessionId: 'stored-d' }
    const sessionStateByRuntimeIdRef = { current: new Map([['runtime-dead', busyState]]) }
    const updateSessionState = vi.fn()

    renderTile(
      vi.fn(async () => ({}) as never),
      { sessionStateByRuntimeIdRef, updateSessionState }
    )

    expect(sessionTileDelegate()!.retireBusyClaim!('runtime-dead')).toBe(true)
    expect(updateSessionState).toHaveBeenCalledWith('runtime-dead', expect.any(Function))

    // The updater is the downgrade: busy/awaiting off, everything else intact.
    const updater = updateSessionState.mock.calls[0][1] as (state: typeof busyState) => typeof busyState

    expect(updater(busyState)).toEqual({ ...busyState, awaitingResponse: false, busy: false })
  })

  it('reports a miss instead of minting a cache entry for a runtime it never held', () => {
    // No phantoms: updateSessionState mints a state for any id it is handed,
    // and prune never collects a transcript-less entry — so a miss must not
    // reach the write path; the store retires its own mirror instead.
    const idle = { awaitingResponse: false, busy: false, messages: [{ id: 'm1' }], storedSessionId: 'stored-e' }
    const sessionStateByRuntimeIdRef = { current: new Map([['runtime-idle', idle]]) }
    const updateSessionState = vi.fn()

    renderTile(
      vi.fn(async () => ({}) as never),
      { sessionStateByRuntimeIdRef, updateSessionState }
    )

    expect(sessionTileDelegate()!.retireBusyClaim!('runtime-unknown')).toBe(false)
    expect(sessionTileDelegate()!.retireBusyClaim!('runtime-idle')).toBe(false)
    expect(updateSessionState).not.toHaveBeenCalled()
  })
})

describe('useSessionTileDelegate interruptSession', () => {
  beforeEach(() => {
    setSessions([])
  })

  afterEach(async () => {
    setSessions([])
    const { clearSessionRecentlyInterrupted } = await import('../../session/hooks/use-prompt-actions/utils')
    clearSessionRecentlyInterrupted()
  })

  it('marks the session recently interrupted so a quick tile edit/resend still interrupt-firsts (#83855)', async () => {
    const { isSessionRecentlyInterrupted } = await import('../../session/hooks/use-prompt-actions/utils')

    const requestGateway = vi.fn(async () => ({}) as never)

    renderTile(requestGateway)
    await sessionTileDelegate()!.interruptSession('runtime-tile-1')

    expect(requestGateway).toHaveBeenCalledWith('session.interrupt', { session_id: 'runtime-tile-1' })
    // Same 3s cooldown the primary chat's Stop sets: busy reads false while the
    // gateway winds down, so the rewind path must still interrupt-first.
    expect(isSessionRecentlyInterrupted('runtime-tile-1')).toBe(true)
  })
})

const tileRegistry = (...ids: string[]) =>
  ({
    connections: ids.map(id => ({ id })),
    lastUsed: ids[0] ?? null,
    launchMode: 'primary',
    primary: ids[0] ?? null
  }) as never

type TileStoredTranscript = { messages: unknown[]; session_id: string }

describe('useSessionTileDelegate resumeTile stale-recovery race (#94724)', () => {
  beforeEach(() => {
    setSessions([])
    clearSingleFlightSessionResumeState()
    resetLiveResumeGenerations()
    vi.mocked(getLatestSessionMessages).mockClear()
    vi.mocked(fetchStoredTranscriptAcrossBackends).mockClear()
    vi.mocked(requestGatewayForAgent).mockClear()
    vi.mocked(requestGatewayForProfile).mockClear()
  })

  afterEach(() => {
    $connectionsRegistry.set(null)
    $profiles.set([])
    setSessions([])
    clearSingleFlightSessionResumeState()
    resetLiveResumeGenerations()
    // Restore the default hermes mock implementations the other suites rely on
    // (mockReset clears impl + once-queues, then re-arm the file-level defaults).
    vi.mocked(getLatestSessionMessages).mockReset()
    vi.mocked(getLatestSessionMessages).mockImplementation(async () => ({ messages: [], session_id: '' }))
    vi.mocked(fetchStoredTranscriptAcrossBackends).mockReset()
    vi.mocked(fetchStoredTranscriptAcrossBackends).mockImplementation(async () => ({ messages: [], session_id: '' }))
    vi.mocked(requestGatewayForAgent).mockReset()
    vi.mocked(requestGatewayForProfile).mockReset()
  })

  it('does NOT repoint the binding onto a stale read-only id after a later live resumeTile (#94724)', async () => {
    // Registry topology + 2 profiles: assertSessionOwnerResolved throws for an
    // unknown owner (the ambient gateway does not own every session).
    $connectionsRegistry.set(tileRegistry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }, { name: 'researcher' }] as never)

    // Call A opens before the owner backfill stamps the row: the row exists but
    // carries no owning profile, so assertSessionOwnerResolved throws under
    // registry topology (the real fail-closed gate, same as read-only-transcript
    // tests). The ambient prefetch misses (rejects -> null) so the helper's
    // stored read falls through to fetchStoredTranscriptAcrossBackends, which
    // is deferred so Call B can interleave.
    setSessions([row({ id: 'stored-race', profile: undefined })])
    vi.mocked(getLatestSessionMessages).mockRejectedValue(new Error('404'))
    let resolveStored!: (value: TileStoredTranscript) => void

    const storedRead = new Promise<TileStoredTranscript>(resolve => {
      resolveStored = resolve
    })

    vi.mocked(fetchStoredTranscriptAcrossBackends).mockImplementation(() => storedRead as never)

    // Call B's later live resume returns a real runtime id through the profile
    // router (the row's owner is resolvable once the backfill stamps it).
    vi.mocked(requestGatewayForProfile).mockResolvedValueOnce({ session_id: 'runtime-live' } as never)

    const requestGateway = vi.fn(async () => ({}) as never)

    const runtimeIdByStoredSessionIdRef = { current: new Map<string, string>() }
    const sessionStateByRuntimeIdRef = { current: new Map<string, unknown>() }

    // Mirror the real ensureSessionState: side-effect the stored->runtime
    // binding so Call A's stale call-site guard can observe Call B's binding.
    const updateSessionState = vi.fn(
      (id: string, updater: (state: { messages: unknown[] }) => { messages: unknown[] }, stored?: string) => {
        const prev = (sessionStateByRuntimeIdRef.current.get(id) ?? { messages: [] }) as { messages: unknown[] }
        const next = updater(prev)
        sessionStateByRuntimeIdRef.current.set(id, next)

        if (stored) {
          runtimeIdByStoredSessionIdRef.current.set(stored, id)
        }

        return next
      }
    ) as never

    renderTile(requestGateway, { runtimeIdByStoredSessionIdRef, sessionStateByRuntimeIdRef, updateSessionState })

    const delegate = sessionTileDelegate()!

    // Call A: owner unresolvable -> SessionOwnerResolutionError -> catch ->
    // awaits the deferred cross-backend stored read.
    const callA = delegate.resumeTile('stored-race')

    // Let Call A reach the catch and start awaiting the deferred stored read
    // (drain the owner-resolution microtask chain).
    await new Promise(resolve => setTimeout(resolve, 0))

    // The owner backfill stamps the row; Call B now resolves a routable owner.
    setSessions([row({ id: 'stored-race', profile: 'default' })])

    // Call B: live resume succeeds, clears the latch (no-op), and binds the
    // stored->runtime mapping to the live runtime id.
    const callB = delegate.resumeTile('stored-race')
    const runtimeIdB = await callB
    expect(runtimeIdB).toBe('runtime-live')
    expect(runtimeIdByStoredSessionIdRef.current.get('stored-race')).toBe('runtime-live')

    // Call A's stale stored read resolves last. The helper skips the latch
    // (generation moved), and the call-site staleness guard discards the stale
    // read-only outcome WITHOUT repointing the binding onto read-only:stored-race.
    resolveStored!({ messages: [{ content: 'stale history', role: 'user' }], session_id: 'stored-race' })
    const runtimeIdA = await callA

    // The stale call returns the live binding (not a synthetic read-only id),
    // and the stored->runtime binding still points at the live runtime.
    expect(runtimeIdA).toBe('runtime-live')
    expect(runtimeIdByStoredSessionIdRef.current.get('stored-race')).toBe('runtime-live')

    // No read-only tile state was painted for the stale outcome:
    // updateSessionState was never called with a read-only:* id.
    const readOnlyPaints = (updateSessionState as ReturnType<typeof vi.fn>).mock.calls.filter(
      ([id]: unknown[]) => typeof id === 'string' && id.startsWith('read-only:')
    )

    expect(readOnlyPaints).toHaveLength(0)

    // The latch is NOT set: the helper skipped the mark because a live resume
    // bumped the generation during Call A's stored read.
    expect(isStoredTranscriptReadOnly('stored-race')).toBe(false)
  })

  it('still paints read-only for a LEGITIMATE no-owner tile recovery when no live resume interleaves', async () => {
    $connectionsRegistry.set(tileRegistry('gw-a', 'gw-b'))
    $profiles.set([{ name: 'default' }, { name: 'researcher' }] as never)

    setSessions([row({ id: 'stored-lone', profile: undefined })])

    // Prefetch misses -> the cross-backend stored read carries the transcript.
    vi.mocked(getLatestSessionMessages).mockRejectedValue(new Error('404'))
    vi.mocked(fetchStoredTranscriptAcrossBackends).mockResolvedValueOnce({
      messages: [{ content: 'intact history', role: 'user' }],
      session_id: 'stored-lone'
    } as never)

    const runtimeIdByStoredSessionIdRef = { current: new Map<string, string>() }
    const sessionStateByRuntimeIdRef = { current: new Map<string, unknown>() }

    const updateSessionState = vi.fn(
      (id: string, updater: (state: { messages: unknown[] }) => { messages: unknown[] }, stored?: string) => {
        const prev = (sessionStateByRuntimeIdRef.current.get(id) ?? { messages: [] }) as { messages: unknown[] }
        const next = updater(prev)
        sessionStateByRuntimeIdRef.current.set(id, next)

        if (stored) {
          runtimeIdByStoredSessionIdRef.current.set(stored, id)
        }

        return next
      }
    ) as never

    renderTile(
      vi.fn(async () => ({}) as never),
      {
        runtimeIdByStoredSessionIdRef,
        sessionStateByRuntimeIdRef,
        updateSessionState
      }
    )

    const runtimeId = await sessionTileDelegate()!.resumeTile('stored-lone')

    // The synthetic read-only id is returned and bound, and the latch is set:
    // no live resume proved this session routable, so read-only is correct.
    expect(runtimeId).toBe('read-only:stored-lone')
    expect(runtimeIdByStoredSessionIdRef.current.get('stored-lone')).toBe('read-only:stored-lone')
    expect(isStoredTranscriptReadOnly('stored-lone')).toBe(true)
  })
})
