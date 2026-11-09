import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getUiState, resetUiState } from '../app/uiStore.js'
import { useSessionLifecycle } from '../app/useSessionLifecycle.js'
import type { Msg } from '../types.js'

// Drive the actual lifecycle callbacks without mounting an Ink terminal.
vi.mock('react', async importOriginal => ({
  ...(await importOriginal<typeof import('react')>()),
  useCallback: (callback: unknown) => callback,
  useEffect: () => undefined,
  useMemo: (factory: () => unknown) => factory(),
  useRef: (current: unknown) => ({ current })
}))
vi.mock('../app/sessionResumeView.js', () => ({
  refreshSessionView: vi.fn(),
  scheduleResumeScrollToBottom: () => () => undefined
}))

describe('live-session selection ordering', () => {
  beforeEach(() => resetUiState())

  it('does not replace the latest chat when an earlier activation resolves last', async () => {
    const pending = new Map<string, (value: unknown) => void>()
    const request = vi.fn((_method: string, params: { session_id: string }) =>
      new Promise<unknown>(resolve => pending.set(params.session_id, resolve))
    )
    let history: Msg[] = []
    const setHistoryItems = vi.fn((next: Msg[] | ((previous: Msg[]) => Msg[])) => {
      history = typeof next === 'function' ? next(history) : next
    })
    const lifecycle = useSessionLifecycle({
      colsRef: { current: 80 },
      composerActions: { setComposerTokens: vi.fn() },
      gw: { request },
      panel: vi.fn(),
      rpc: vi.fn(),
      scrollRef: { current: null },
      setHistoryItems,
      setLastUserMsg: vi.fn(),
      setSessionStartedAt: vi.fn(),
      setStickyPrompt: vi.fn(),
      setVoiceProcessing: vi.fn(),
      setVoiceRecording: vi.fn(),
      sys: vi.fn()
    } as any)

    lifecycle.activateLiveSession('older')
    lifecycle.activateLiveSession('newer')
    expect(request).toHaveBeenCalledTimes(2)

    pending.get('newer')?.({
      session_id: 'newer',
      session_key: 'newer',
      messages: [{ role: 'user', text: 'newer chat' }]
    })
    await Promise.resolve()
    expect(getUiState().sid).toBe('newer')

    pending.get('older')?.({
      session_id: 'older',
      session_key: 'older',
      messages: [{ role: 'user', text: 'older chat' }]
    })
    await Promise.resolve()

    expect(getUiState().sid).toBe('newer')
    expect(history).toEqual([{ role: 'user', text: 'newer chat' }])
  })
})
