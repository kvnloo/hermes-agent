import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { atom } from 'nanostores'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'
import { CONVERSATION_LEASE, resetTtsLeasesForTests } from '@/lib/tts-lease'
import { $voiceLiveStatus } from '@/store/voice-live'
import { $autoSpeakReplies, $voiceStopPhrase } from '@/store/voice-prefs'

import type { ComposerTarget } from '../focus'
import { ComposerScopeProvider, MAIN_COMPOSER_SCOPE } from '../scope'

import { useComposerVoice } from './use-composer-voice'

const boundary = vi.hoisted(() => ({ lease: vi.fn(async () => ({ ok: true })), end: vi.fn() }))
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
// Substitute audio/provider engines, not the consumer hook or its lease effects.
vi.mock('./use-voice-conversation', () => ({
  useVoiceConversation: () => ({
    end: boundary.end,
    level: 0,
    muted: false,
    start: vi.fn(),
    status: 'listening',
    stopTurn: vi.fn(),
    toggleMute: vi.fn()
  })
}))
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
    onSubmit: vi.fn(),
    onTranscribeAudio: vi.fn(),
    sessionId: target,
    target
  })
  return (
    <button onClick={voice.voiceConversationActive ? voice.endConversation : voice.startConversation}>
      {voice.voiceConversationActive ? 'End' : 'Start'} {target}
    </button>
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
  resetTtsLeasesForTests()
  boundary.lease.mockClear()
  boundary.end.mockClear()
  $autoSpeakReplies.set(false)
  $voiceStopPhrase.set(null)
  $voiceLiveStatus.set(null)
})
afterEach(async () => {
  cleanup()
  await flushLease()
  resetTtsLeasesForTests()
  $voiceStopPhrase.set('stop')
})

it('keeps the real main hook lease across idle tile mount/unmount, then releases on owner End', async () => {
  const view = render(<App />)
  fireEvent.click(screen.getByRole('button', { name: 'Start main' }))
  await flushLease()
  expect(boundary.lease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
  view.rerender(<App tile />)
  await flushLease()
  view.rerender(<App />)
  await flushLease()
  expect(boundary.lease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
  fireEvent.click(screen.getByRole('button', { name: 'End main' }))
  await flushLease()
  expect(boundary.end).toHaveBeenCalledTimes(1)
  expect(boundary.lease.mock.calls).toEqual([
    [CONVERSATION_LEASE, true],
    [CONVERSATION_LEASE, false]
  ])
})

it('lets the real tile hook own the lease until unmount despite an idle main composer', async () => {
  const view = render(<App main={false} tile />)
  fireEvent.click(screen.getByRole('button', { name: 'Start tile:test' }))
  await flushLease()
  expect(boundary.lease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
  view.rerender(<App tile />)
  await flushLease()
  view.rerender(<App main={false} tile />)
  await flushLease()
  expect(boundary.lease.mock.calls).toEqual([[CONVERSATION_LEASE, true]])
  view.unmount()
  await flushLease()
  expect(boundary.lease.mock.calls).toEqual([
    [CONVERSATION_LEASE, true],
    [CONVERSATION_LEASE, false]
  ])
})
