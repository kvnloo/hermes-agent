import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { CONVERSATION_LEASE, resetTtsLeasesForTests } from '@/lib/tts-lease'

import { markActiveComposer, requestVoiceToggle } from '../focus'
import { ComposerScopeProvider, ComposerSurfaceProvider, MAIN_COMPOSER_SCOPE } from '../scope'

import { useComposerVoice } from './use-composer-voice'

// Every mounted composer (the main chat bar and each session tile) runs
// useComposerVoice against the SAME per-renderer conversation lease, deduped by
// the real tts-lease module. Only the wire call is stubbed here.
const mocks = vi.hoisted(() => ({
  setTtsLease: vi.fn(async (_lease: string, _active: boolean) => ({ ok: true }))
}))

vi.mock('@/hermes', async importOriginal => ({
  ...(await importOriginal<Record<string, unknown>>()),
  setTtsLease: (lease: string, active: boolean) => mocks.setTtsLease(lease, active)
}))

vi.mock('./use-voice-recorder', () => ({
  useVoiceRecorder: () => ({
    dictate: vi.fn(),
    voiceActivityState: { elapsedSeconds: 0, level: 0, status: 'idle' },
    voiceStatus: 'idle'
  })
}))

vi.mock('./use-voice-conversation', () => ({
  useVoiceConversation: () => ({ end: vi.fn(async () => undefined), start: vi.fn(), status: 'idle' })
}))

vi.mock('./use-voice-live-conversation', () => ({
  useVoiceLiveConversation: () => ({ end: vi.fn(async () => undefined), start: vi.fn(), status: 'idle' })
}))

vi.mock('./use-auto-speak-replies', () => ({ useAutoSpeakReplies: vi.fn() }))

vi.mock('@/i18n', () => ({
  useI18n: () => ({
    t: {
      notifications: { voice: {} },
      assistant: { thread: { readAloudFailed: '' } },
      settings: { config: { autosaveFailed: '' } }
    }
  })
}))

vi.mock('@/lib/haptics', () => ({ triggerHaptic: vi.fn() }))
vi.mock('@/lib/spoken-reply', () => ({
  adoptSpokenReplySession: vi.fn(),
  markAssistantIdSpoken: vi.fn(),
  resolveSpokenReply: vi.fn(() => null)
}))
vi.mock('@/lib/wake-indicator', () => ({ clearWakeIndicator: vi.fn(), syncWakeIndicatorWithVoice: vi.fn() }))
vi.mock('@/lib/voice-live', () => ({ toLiveHistory: vi.fn(() => []) }))
vi.mock('@/store/notifications', () => ({ notify: vi.fn(), notifyError: vi.fn() }))
vi.mock('@/store/voice-live', async () => {
  const { atom } = await import('nanostores')

  return {
    $voiceLiveStatus: atom(null),
    refreshVoiceLiveStatus: vi.fn(async () => undefined),
    selectedVoiceChatMode: vi.fn(() => 'chained')
  }
})
vi.mock('@/store/voice-prefs', async () => {
  const { atom } = await import('nanostores')

  return {
    $autoSpeakReplies: atom(false),
    $voiceStopPhrase: atom(null),
    setAutoSpeakReplies: vi.fn(async () => undefined)
  }
})
vi.mock('@/store/gateway', async () => {
  const { atom } = await import('nanostores')

  return { $gateway: atom(null) }
})
vi.mock('@/store/composer-input-history', () => ({ resetBrowseState: vi.fn() }))
vi.mock('@/store/wake-word', () => ({ resumeWakeAfterVoice: vi.fn(async () => undefined) }))
vi.mock('../floating-target', () => ({ pinFloatingComposerCapture: vi.fn(() => undefined) }))

function Composer({ target }: { target: string }) {
  useComposerVoice({
    busy: false,
    clearDraft: vi.fn(),
    disabled: false,
    focusInput: vi.fn(),
    insertText: vi.fn(),
    maxRecordingSeconds: 60,
    onSubmit: vi.fn(async () => true),
    onTranscribeAudio: vi.fn(async () => 'spoken text'),
    sessionId: null,
    target
  })

  return null
}

function Composers({ targets }: { targets: string[] }) {
  return (
    <>
      {targets.map(target => (
        <ComposerScopeProvider key={target} value={{ ...MAIN_COMPOSER_SCOPE, target }}>
          <ComposerSurfaceProvider value={`${target}-surface`}>
            <div data-composer-target={target}>
              <Composer target={target} />
            </div>
          </ComposerSurfaceProvider>
        </ComposerScopeProvider>
      ))}
    </>
  )
}

// Effects run inside act; the lease's wire call lands one task later.
async function settle(action: () => void = () => undefined) {
  await act(async () => {
    action()
    await new Promise(resolve => window.setTimeout(resolve, 0))
  })
}

beforeEach(() => {
  resetTtsLeasesForTests()
  mocks.setTtsLease.mockClear()
})

afterEach(() => {
  cleanup()
  resetTtsLeasesForTests()
  markActiveComposer('main')
})

describe('useComposerVoice conversation lease ownership', () => {
  it('keeps the main conversation lease held while a session tile mounts and unmounts', async () => {
    const view = render(<Composers targets={['main']} />)

    await settle(() => requestVoiceToggle('main'))
    expect(mocks.setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    view.rerender(<Composers targets={['main', 'tile:a']} />)
    await settle()
    view.rerender(<Composers targets={['main']} />)
    await settle()
    expect(mocks.setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    // The owner's own end-of-conversation release still reaches the backend.
    await settle(() => requestVoiceToggle('main'))
    expect(mocks.setTtsLease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  })

  it('releases the lease when the owning composer unmounts mid-conversation', async () => {
    const view = render(<Composers targets={['main', 'tile:a']} />)

    await settle(() => requestVoiceToggle('tile:a'))
    expect(mocks.setTtsLease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])

    view.rerender(<Composers targets={['main']} />)
    await settle()
    expect(mocks.setTtsLease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  })
})
