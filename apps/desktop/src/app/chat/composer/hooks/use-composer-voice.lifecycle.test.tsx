import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { atom } from 'nanostores'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'
import { clearVoiceClientConfigCache, transcribeAudioClientDirect } from '@/lib/voice-client-direct'
import { CONVERSATION_LEASE, resetTtsLeasesForTests } from '@/lib/tts-lease'
import { $voiceLiveStatus } from '@/store/voice-live'
import { $autoSpeakReplies, $voiceStopPhrase } from '@/store/voice-prefs'

import type { ComposerTarget } from '../focus'
import { ComposerScopeProvider, MAIN_COMPOSER_SCOPE } from '../scope'

import { useComposerVoice } from './use-composer-voice'

const boundary = vi.hoisted(() => ({
  lease: vi.fn(async () => ({ ok: true })),
  submit: vi.fn(),
  error: vi.fn(),
  mic: {
    start: vi.fn(async () => undefined),
    cancel: vi.fn(),
    stop: vi.fn(async () => ({ audio: new Blob(['fixture']), durationMs: 900, heardSpeech: true }))
  }
}))
vi.mock('@/hermes', async importOriginal => ({ ...(await importOriginal()), setTtsLease: boundary.lease }))
vi.mock('@/store/desktop-metrics', () => ({ recordFeatureUse: vi.fn() }))
vi.mock('@/store/voice-live', async importOriginal => ({
  ...(await importOriginal()),
  refreshVoiceLiveStatus: vi.fn(async () => null)
}))
vi.mock('@/store/wake-word', async importOriginal => ({
  ...(await importOriginal()),
  resumeWakeAfterVoice: vi.fn(async () => undefined)
}))
// Real chained conversation and transcription execute; hardware and sound do not.
vi.mock('./use-mic-recorder', () => ({ useMicRecorder: () => ({ handle: boundary.mic, level: 0, recording: false }) }))
vi.mock('@/lib/stt-lease', () => ({ syncSttLease: vi.fn(async () => undefined), VOICE_INPUT_LEASE: 'fixture-input' }))
vi.mock('@/lib/voice-barge-in', () => ({ monitorSpeechDuringPlayback: () => vi.fn() }))
vi.mock('@/lib/thinking-sound', () => ({ startThinkingSound: vi.fn(), stopThinkingSound: vi.fn() }))
vi.mock('@/store/notifications', () => ({ notify: vi.fn(), notifyError: boundary.error }))
vi.mock('./use-voice-live-conversation', () => ({
  useVoiceLiveConversation: () => ({
    end: vi.fn(),
    level: 0,
    muted: false,
    start: vi.fn(),
    status: 'idle',
    stopTurn: vi.fn(),
    toggleMute: vi.fn()
  })
}))
vi.mock('./use-voice-recorder', () => ({ useVoiceRecorder: () => ({ dictate: vi.fn(), voiceStatus: 'idle' }) }))
vi.mock('./use-auto-speak-replies', () => ({ useAutoSpeakReplies: vi.fn() }))

const messages = atom<never[]>([])
function Composer({ target }: { target: ComposerTarget }) {
  const voice = useComposerVoice({
    busy: false,
    clearDraft: vi.fn(),
    disabled: false,
    focusInput: vi.fn(),
    insertText: vi.fn(),
    maxRecordingSeconds: 60,
    onSubmit: boundary.submit,
    onTranscribeAudio: async (audio, owner) => (await transcribeAudioClientDirect(audio, owner)) ?? '',
    sessionId: target,
    target
  })
  return (
    <>
      <output aria-label="conversation status">{voice.conversation.status}</output>
      <button onClick={voice.voiceConversationActive ? voice.endConversation : voice.startConversation}>
        {voice.voiceConversationActive ? 'End' : 'Start'} {target}
      </button>
      <button onClick={voice.conversation.stopTurn}>Finish take {target}</button>
    </>
  )
}
function App({ main = true, tile = false }: { main?: boolean; tile?: boolean }) {
  return (
    <I18nProvider configClient={null} initialLocale="en">
      {main && (
        <ComposerScopeProvider key="main" value={{ ...MAIN_COMPOSER_SCOPE, $messages: messages }}>
          <Composer target="main" />
        </ComposerScopeProvider>
      )}
      {tile && (
        <ComposerScopeProvider key="tile" value={{ ...MAIN_COMPOSER_SCOPE, $messages: messages, target: 'tile:test' }}>
          <Composer target="tile:test" />
        </ComposerScopeProvider>
      )}
    </I18nProvider>
  )
}
async function flushLease() {
  await act(async () => {
    await Promise.resolve()
  })
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.clearAllMocks()
  resetTtsLeasesForTests()
  clearVoiceClientConfigCache()
  $autoSpeakReplies.set(false)
  $voiceStopPhrase.set(null)
  $voiceLiveStatus.set(null)
  Object.defineProperty(window, 'hermesDesktop', {
    configurable: true,
    value: {
      api: vi.fn(async () => ({
        ok: true,
        stt: {
          mode: 'direct',
          wire: 'xai-stt',
          provider: 'xai',
          base_url: 'https://stt.invalid/v1',
          api_key: 'fixture',
          model: 'grok-voice-transcribe-2.0',
          language: '',
          timeout_s: 1
        },
        tts: { mode: 'relay' }
      }))
    }
  })
})
afterEach(async () => {
  cleanup()
  await flushLease()
  resetTtsLeasesForTests()
  clearVoiceClientConfigCache()
  Reflect.deleteProperty(window, 'hermesDesktop')
  $voiceStopPhrase.set('stop')
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

it('recovers an active composer from a stalled transcription body and releases its lease on End', async () => {
  let requestSignal: AbortSignal | undefined
  let body: ReadableStreamDefaultController<Uint8Array> | undefined
  const fetch = vi.fn(async (_url: unknown, init?: RequestInit) => {
    const signal = init?.signal
    if (!signal) throw new Error('Expected transcription abort signal')
    requestSignal = signal
    return new Response(
      new ReadableStream<Uint8Array>({
        start(controller) {
          body = controller
          signal.addEventListener('abort', () => controller.error(new DOMException('Aborted', 'AbortError')), {
            once: true
          })
        }
      }),
      { headers: { 'Content-Type': 'application/json' } }
    )
  })
  vi.stubGlobal('fetch', fetch)
  const view = render(<App />)
  try {
    fireEvent.click(screen.getByRole('button', { name: 'Start main' }))
    await flushLease()
    expect(boundary.mic.start).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByRole('button', { name: 'Finish take main' }))
    await flushLease()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText('conversation status').textContent).toBe('transcribing')
    view.rerender(<App tile />)
    await flushLease()
    view.rerender(<App />)
    await flushLease()
    expect(boundary.lease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })
    expect(requestSignal?.aborted).toBe(true)
    expect(boundary.error).toHaveBeenCalledWith(
      expect.objectContaining({ message: expect.stringContaining('Transcription timed out') }),
      expect.any(String)
    )
    expect(screen.getByLabelText('conversation status').textContent).toBe('listening')
    expect(boundary.mic.start).toHaveBeenCalledTimes(2)
    expect(boundary.submit).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'End main' }))
    await flushLease()
    expect(screen.getByRole('button', { name: 'Start main' })).toBeTruthy()
    expect(boundary.lease.mock.calls).toEqual([
      [CONVERSATION_LEASE, true],
      [CONVERSATION_LEASE, false]
    ])
  } finally {
    // Settle the finite body even when the exact-source negative lacks a deadline.
    if (!requestSignal?.aborted) body?.error(new Error('fixture teardown'))
    view.unmount()
    await flushLease()
  }
})
