import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { BargeMonitorCallbacks } from '@/lib/voice-barge-in'
import type { SpeechStreamSession } from '@/lib/voice-playback'

import type { MicRecording } from './use-mic-recorder'
import { useVoiceConversation } from './use-voice-conversation'

// The full-duplex contract: the barge monitor is live across the WHOLE agent
// turn — generation (thinking) and playback (speaking) — so speaking over the
// model interrupts it mid-generation instead of the mic being deaf until TTS
// starts (the Windows report: interruption "never works" because the deaf
// window covered generation, and playback bleed made the old monitor's
// trigger unreachable).

const monitorCalls: BargeMonitorCallbacks[] = []
const monitorStops: Array<ReturnType<typeof vi.fn>> = []

vi.mock('@/lib/voice-barge-in', () => ({
  monitorSpeechDuringPlayback: (callbacks: BargeMonitorCallbacks) => {
    const stop = vi.fn()

    monitorCalls.push(callbacks)
    monitorStops.push(stop)

    return stop
  }
}))

const markVoicePlaybackInterrupted = vi.fn()
const startSpeechStream = vi.fn<() => Promise<SpeechStreamSession | null>>(async () => null)
const stopVoicePlayback = vi.fn()

vi.mock('@/lib/voice-playback', () => ({
  markVoicePlaybackInterrupted: () => markVoicePlaybackInterrupted(),
  playSpeechText: vi.fn(async () => true),
  startSpeechStream: () => startSpeechStream(),
  stopVoicePlayback: () => stopVoicePlayback()
}))

vi.mock('@/lib/thinking-sound', () => ({
  startThinkingSound: vi.fn(),
  stopThinkingSound: vi.fn()
}))

const micHandle = {
  cancel: vi.fn(),
  start: vi.fn<(options?: { onSilence?: () => void }) => Promise<void>>(),
  stop: vi.fn<() => Promise<MicRecording | null>>()
}

let onMicSilence: () => void = () => undefined

vi.mock('./use-mic-recorder', () => ({
  useMicRecorder: () => ({ handle: micHandle, level: 0, recording: false })
}))

vi.mock('@/i18n', () => ({
  useI18n: () => ({
    t: {
      notifications: {
        voice: {
          configureSpeechToText: 'configure STT',
          couldNotStartSession: 'could not start',
          microphoneFailed: 'mic failed',
          playbackFailed: 'playback failed',
          transcriptionFailed: 'transcription failed',
          unavailable: 'unavailable'
        }
      }
    }
  })
}))

vi.mock('@/store/notifications', () => ({
  notify: vi.fn(),
  notifyError: vi.fn()
}))

interface HookProps {
  busy: boolean
}

function renderConversation(
  overrides: {
    onInterrupt?: () => void
    onSubmit?: () => Promise<void>
    pendingResponse?: () => { id: string; pending: boolean; text: string } | null
    transcript?: string | Promise<string> | ((index: number) => string | Promise<string>)
  } = {}
) {
  const onInterrupt = overrides.onInterrupt ?? vi.fn()

  // Mirrors the real app: submitting a turn makes the agent busy.
  const onBusyChange: { current: (busy: boolean) => void } = { current: () => undefined }

  const onSubmit = vi.fn(async () => {
    if (overrides.onSubmit) {
      await overrides.onSubmit()

      return
    }

    onBusyChange.current(true)
  })

  const onStopWord = vi.fn()

  // First transcription is the turn that starts the conversation; subsequent
  // ones are barge captures (the overridable transcript).
  let transcriptions = 0

  const onTranscribeAudio = vi.fn(async () => {
    const index = transcriptions++

    if (typeof overrides.transcript === 'function') {
      return await overrides.transcript(index)
    }

    return index === 0 ? 'kick off the task' : await (overrides.transcript ?? 'and another thing')
  })

  const hook = renderHook(
    ({ busy }: HookProps) =>
      useVoiceConversation({
        busy,
        consumePendingResponse: vi.fn(),
        enabled: true,
        onInterrupt,
        onStopWord,
        onSubmit,
        onTranscribeAudio,
        pendingResponse: overrides.pendingResponse ?? (() => null)
      }),
    { initialProps: { busy: false } }
  )

  onBusyChange.current = busy => hook.rerender({ busy })

  return { hook, onInterrupt, onStopWord, onSubmit, onTranscribeAudio }
}

/** Drive the hook into the generation phase (turn submitted, model working). */
async function enterThinking(hook: ReturnType<typeof renderConversation>['hook']) {
  await act(async () => {
    await hook.result.current.start()
  })
  await waitFor(() => expect(hook.result.current.status).toBe('listening'))

  micHandle.stop.mockResolvedValueOnce({
    audio: new Blob(['q'], { type: 'audio/webm' }),
    durationMs: 900,
    heardSpeech: true
  })

  await act(async () => {
    hook.result.current.stopTurn()
  })
  await waitFor(() => expect(hook.result.current.status).toBe('thinking'))
}

describe('useVoiceConversation full-duplex barge-in', () => {
  beforeEach(() => {
    monitorCalls.length = 0
    monitorStops.length = 0
    onMicSilence = () => undefined
    vi.clearAllMocks()
    micHandle.start.mockImplementation(async options => {
      onMicSilence = options?.onSilence ?? (() => undefined)
    })
    micHandle.stop.mockResolvedValue(null)
  })

  afterEach(cleanup)

  it('arms the barge monitor during generation (before any reply audio exists)', async () => {
    const { hook } = renderConversation()

    await act(async () => {
      await hook.result.current.start()
    })
    await enterThinking(hook)

    await waitFor(() => expect(hook.result.current.status).toBe('thinking'))
    // busy=true + thinking → the full-duplex monitor must be live.
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))
  })

  it('interrupts the in-flight turn when speech trips mid-generation', async () => {
    const { hook, onInterrupt } = renderConversation()

    await act(async () => {
      await hook.result.current.start()
    })
    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    act(() => {
      monitorCalls.at(-1)?.onSpeech()
    })

    expect(onInterrupt).toHaveBeenCalledTimes(1)
    expect(markVoicePlaybackInterrupted).toHaveBeenCalled()
    expect(stopVoicePlayback).toHaveBeenCalled()
  })

  it('submits the captured interruption once the interrupt settles (busy clears)', async () => {
    const { hook, onSubmit } = renderConversation({ transcript: 'no, do it differently' })

    await act(async () => {
      await hook.result.current.start()
    })
    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    const monitor = monitorCalls.at(-1)

    act(() => {
      monitor?.onSpeech()
    })

    // Interrupt lands → the turn ends → busy flips false.
    hook.rerender({ busy: false })

    await act(async () => {
      monitor?.onUtterance?.(new Blob(['x'], { type: 'audio/webm' }))
    })

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith('no, do it differently'))
  })

  it('does not interrupt when speech trips during playback (turn already done)', async () => {
    let responseAvailable = false

    const { hook, onInterrupt } = renderConversation({
      pendingResponse: () => (responseAvailable ? { id: 'reply', pending: false, text: 'Here is the answer.' } : null)
    })

    startSpeechStream.mockResolvedValueOnce({
      append: vi.fn(),
      done: new Promise(() => undefined),
      finish: vi.fn()
    })

    await act(async () => {
      await hook.result.current.start()
    })
    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    // Turn finished; playback phase.
    responseAvailable = true
    await act(async () => hook.rerender({ busy: false }))
    act(() => {
      monitorCalls.at(-1)?.onSpeech()
    })

    expect(onInterrupt).not.toHaveBeenCalled()
    expect(stopVoicePlayback).toHaveBeenCalled()
  })

  it('a spoken stop command in the barge capture ends the conversation instead of submitting', async () => {
    const { hook, onStopWord, onSubmit } = renderConversation({ transcript: 'stop' })

    await act(async () => {
      await hook.result.current.start()
    })
    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    const monitor = monitorCalls.at(-1)

    act(() => {
      monitor?.onSpeech()
    })
    hook.rerender({ busy: false })

    await act(async () => {
      monitor?.onUtterance?.(new Blob(['s'], { type: 'audio/webm' }))
    })

    await waitFor(() => expect(onStopWord).toHaveBeenCalledTimes(1))
    // Only the kickoff turn was submitted — the "stop" capture never was.
    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).not.toHaveBeenCalledWith('stop')
  })

  it('re-arms a single monitor per turn (idempotent ensure)', async () => {
    const { hook } = renderConversation()

    await act(async () => {
      await hook.result.current.start()
    })
    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    const armed = monitorCalls.length

    // Effect re-runs (busy toggles, status changes) must not open more mics.
    hook.rerender({ busy: true })
    hook.rerender({ busy: true })

    expect(monitorCalls.length).toBe(armed)
  })

  it('does not submit a transcript that resolves after the voice hook unmounts', async () => {
    let resolveTranscript: (text: string) => void = () => undefined

    const onSubmit = vi.fn()

    const onTranscribeAudio = vi.fn(
      () =>
        new Promise<string>(resolve => {
          resolveTranscript = resolve
        })
    )

    const hook = renderHook(
      ({ enabled }) =>
        useVoiceConversation({
          busy: false,
          consumePendingResponse: vi.fn(),
          enabled,
          onSubmit,
          onTranscribeAudio,
          pendingResponse: () => null
        }),
      { initialProps: { enabled: true } }
    )

    await act(async () => {
      await hook.result.current.start()
    })
    await waitFor(() => expect(hook.result.current.status).toBe('listening'))

    micHandle.stop.mockResolvedValueOnce({
      audio: new Blob(['q'], { type: 'audio/webm' }),
      durationMs: 900,
      heardSpeech: true
    })

    act(() => hook.result.current.stopTurn())
    await waitFor(() => expect(onTranscribeAudio).toHaveBeenCalledTimes(1))

    hook.unmount()

    await act(async () => resolveTranscript('stale request'))

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('does not let a stale turn release a newer turn closing lock', async () => {
    let resolveFirst!: (transcript: string) => void
    let resolveSecond!: (transcript: string) => void

    const firstTranscript = new Promise<string>(resolve => {
      resolveFirst = resolve
    })

    const secondTranscript = new Promise<string>(resolve => {
      resolveSecond = resolve
    })

    const { hook, onTranscribeAudio } = renderConversation({
      transcript: index => (index === 0 ? firstTranscript : secondTranscript)
    })

    await act(async () => hook.result.current.start())
    await waitFor(() => expect(hook.result.current.status).toBe('listening'))
    micHandle.stop.mockResolvedValueOnce({
      audio: new Blob(['first'], { type: 'audio/webm' }),
      durationMs: 900,
      heardSpeech: true
    })
    act(() => hook.result.current.stopTurn())
    await waitFor(() => expect(onTranscribeAudio).toHaveBeenCalledTimes(1))

    await act(async () => hook.result.current.end())
    await act(async () => hook.result.current.start())
    await waitFor(() => expect(hook.result.current.status).toBe('listening'))
    micHandle.stop.mockResolvedValueOnce({
      audio: new Blob(['second'], { type: 'audio/webm' }),
      durationMs: 900,
      heardSpeech: true
    })
    act(() => hook.result.current.stopTurn())
    await waitFor(() => expect(onTranscribeAudio).toHaveBeenCalledTimes(2))
    const stopCalls = micHandle.stop.mock.calls.length

    await act(async () => resolveFirst('stale'))
    act(() => onMicSilence())

    expect(micHandle.stop).toHaveBeenCalledTimes(stopCalls)
    await act(async () => resolveSecond('active'))
  })

  it('releases an aborted closing lock when mute starts a fresh turn', async () => {
    let resolveFirst!: (transcript: string) => void

    const firstTranscript = new Promise<string>(resolve => {
      resolveFirst = resolve
    })

    const { hook, onTranscribeAudio } = renderConversation({
      transcript: index => (index === 0 ? firstTranscript : 'active')
    })

    await act(async () => hook.result.current.start())
    await waitFor(() => expect(hook.result.current.status).toBe('listening'))
    micHandle.stop.mockResolvedValueOnce({
      audio: new Blob(['first'], { type: 'audio/webm' }),
      durationMs: 900,
      heardSpeech: true
    })
    act(() => hook.result.current.stopTurn())
    await waitFor(() => expect(onTranscribeAudio).toHaveBeenCalledTimes(1))

    act(() => hook.result.current.toggleMute())
    await waitFor(() => expect(hook.result.current.muted).toBe(true))
    act(() => hook.result.current.toggleMute())
    await waitFor(() => expect(hook.result.current.status).toBe('listening'))

    micHandle.stop.mockResolvedValueOnce({
      audio: new Blob(['second'], { type: 'audio/webm' }),
      durationMs: 900,
      heardSpeech: true
    })
    act(() => onMicSilence())

    await waitFor(() => expect(onTranscribeAudio).toHaveBeenCalledTimes(2))
    await act(async () => resolveFirst('stale'))
  })

  it('disposes the barge monitor when muted', async () => {
    const { hook } = renderConversation()

    await act(async () => hook.result.current.start())
    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))
    const monitor = monitorCalls.at(-1)
    const stopMonitor = monitorStops.at(-1)

    stopVoicePlayback.mockClear()
    act(() => hook.result.current.toggleMute())

    expect(stopMonitor).toHaveBeenCalledOnce()
    act(() => monitor?.onSpeech())
    expect(stopVoicePlayback).not.toHaveBeenCalled()

    act(() => hook.result.current.toggleMute())
    expect(monitorCalls).toHaveLength(2)
  })

  it('resumes normal listening when an old awaiting response is no longer active', async () => {
    const { hook } = renderConversation({ onSubmit: async () => Promise.reject(new Error('failed')) })

    await act(async () => hook.result.current.start())
    micHandle.stop.mockResolvedValueOnce({
      audio: new Blob(['q'], { type: 'audio/webm' }),
      durationMs: 900,
      heardSpeech: true
    })
    await act(async () => hook.result.current.stopTurn())
    await waitFor(() => expect(hook.result.current.status).toBe('listening'))
    const starts = micHandle.start.mock.calls.length

    act(() => hook.result.current.toggleMute())
    act(() => hook.result.current.toggleMute())

    await waitFor(() => expect(micHandle.start).toHaveBeenCalledTimes(starts + 1))
    expect(monitorCalls).toHaveLength(0)
  })

  it('does not submit a captured interruption that resolves after the conversation ends', async () => {
    let resolveTranscript: (text: string) => void = () => undefined

    const transcript = new Promise<string>(resolve => {
      resolveTranscript = resolve
    })

    const { hook, onSubmit, onTranscribeAudio } = renderConversation({ transcript })

    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    const monitor = monitorCalls.at(-1)

    act(() => monitor?.onSpeech())
    hook.rerender({ busy: false })
    act(() => monitor?.onUtterance?.(new Blob(['x'], { type: 'audio/webm' })))
    await waitFor(() => expect(onTranscribeAudio).toHaveBeenCalledTimes(2))

    await act(async () => hook.result.current.end())
    await act(async () => resolveTranscript('stale interruption'))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).not.toHaveBeenCalledWith('stale interruption')

    await act(async () => monitor?.onUtterance?.(new Blob(['late'], { type: 'audio/webm' })))
    expect(onTranscribeAudio).toHaveBeenCalledTimes(2)
  })

  it('disposes the barge monitor and ignores retained callbacks after unmount', async () => {
    const { hook, onSubmit, onTranscribeAudio } = renderConversation()

    await enterThinking(hook)
    await waitFor(() => expect(monitorCalls.length).toBeGreaterThan(0))

    const monitor = monitorCalls.at(-1)
    const stopMonitor = monitorStops.at(-1)

    hook.unmount()

    expect(stopMonitor).toHaveBeenCalledTimes(1)

    await act(async () => monitor?.onUtterance?.(new Blob(['x'], { type: 'audio/webm' })))

    expect(onTranscribeAudio).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })
})
