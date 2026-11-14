import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { cancelRecording, notifyError, playSpeechText, startRecording, stopRecording, VoiceAudioPlaybackError, VoiceSynthesisError } = vi.hoisted(() => ({
  startRecording: vi.fn(),
  stopRecording: vi.fn(),
  cancelRecording: vi.fn(),
  notifyError: vi.fn(),
  playSpeechText: vi.fn(),
  VoiceAudioPlaybackError: class VoiceAudioPlaybackError extends Error {},
  VoiceSynthesisError: class VoiceSynthesisError extends Error {}
}))

vi.mock('./use-mic-recorder', () => ({
  useMicRecorder: () => ({
    handle: { cancel: cancelRecording, start: startRecording, stop: stopRecording },
    level: 0.4
  })
}))
vi.mock('@/lib/voice-playback', () => ({
  playSpeechText,
  stopVoicePlayback: vi.fn(),
  VoiceAudioPlaybackError,
  VoiceSynthesisError
}))
vi.mock('@/store/native-notifications', () => ({ setVoiceTurnNotificationHold: vi.fn() }))
vi.mock('@/store/notifications', () => ({ notify: vi.fn(), notifyError }))
vi.mock('@/i18n', () => ({
  useI18n: () => ({
    t: {
      notifications: {
        voice: {
          configureSpeechToText: 'configure stt', couldNotStartSession: 'start failed', microphoneFailed: 'mic failed',
          modelFailed: 'model failed', noSpeechDetected: 'no speech', playbackFailed: 'playback failed',
          submissionFailed: 'submission failed', synthesisFailed: 'synthesis failed', transcriptionFailed: 'stt failed', unavailable: 'unavailable'
        }
      }
    }
  })
}))

import { useVoiceConversation } from './use-voice-conversation'

describe('useVoiceConversation stage recovery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    stopRecording.mockResolvedValue({ audio: new Blob(['audio']), durationMs: 125, heardSpeech: true })
    startRecording.mockResolvedValue(undefined)
    playSpeechText.mockResolvedValue(true)
  })

  it('surfaces STT separately, preserves capture latency, and retries the failed stage', async () => {
    const transcribe = vi.fn().mockRejectedValueOnce(new Error('network down')).mockResolvedValueOnce('hello')
    const submit = vi.fn().mockResolvedValue(undefined)
    const { result } = renderHook(() =>
      useVoiceConversation({
        busy: false,
        consumePendingResponse: vi.fn(),
        enabled: true,
        onSubmit: submit,
        onTranscribeAudio: transcribe,
        pendingResponse: () => null
      })
    )

    await act(async () => result.current.start())
    act(() => result.current.stopTurn())
    await waitFor(() => expect(result.current.error?.stage).toBe('stt'))
    expect(result.current.latency.captureMs).toBe(125)

    act(() => result.current.retry())
    await waitFor(() => expect(submit).toHaveBeenCalledWith('hello'))
    expect(transcribe).toHaveBeenCalledTimes(2)
    expect(result.current.status).toBe('thinking')
  })

  it('uses the saved backend voice on the next turn and retries a synthesis error', async () => {
    const response = { id: 'assistant-1', pending: false, text: 'The saved voice is active.' }
    const submit = vi.fn().mockResolvedValue(undefined)
    playSpeechText
      .mockRejectedValueOnce(new VoiceSynthesisError('provider unavailable'))
      .mockResolvedValueOnce(true)

    const { result } = renderHook(() =>
      useVoiceConversation({
        busy: false,
        consumePendingResponse: vi.fn(),
        enabled: true,
        onSubmit: submit,
        onTranscribeAudio: vi.fn().mockResolvedValue('hello'),
        pendingResponse: () => response
      })
    )

    await act(async () => result.current.start())
    act(() => result.current.stopTurn())
    await waitFor(() => expect(result.current.error?.stage).toBe('tts'))

    const options = playSpeechText.mock.calls[0]?.[1]
    expect(options).toMatchObject({ source: 'voice-conversation' })
    expect(options).not.toHaveProperty('preview')

    act(() => result.current.retry())
    await waitFor(() => expect(playSpeechText).toHaveBeenCalledTimes(2))
    expect(playSpeechText.mock.calls[1]?.[0]).toBe('The saved voice is active.')
  })
})
