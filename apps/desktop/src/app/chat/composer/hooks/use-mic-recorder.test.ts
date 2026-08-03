import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { type MicRecorderErrorCopy, useMicRecorder } from './use-mic-recorder'

const copy: MicRecorderErrorCopy = {
  microphoneAccessDenied: 'access denied',
  microphoneConstraintsUnsupported: 'constraints unsupported',
  microphoneInUse: 'in use',
  microphonePermissionDenied: 'permission denied',
  microphoneStartFailed: 'start failed',
  microphoneUnsupported: 'unsupported',
  noMicrophone: 'not found'
}

describe('useMicRecorder adaptive endpointing', () => {
  let level = 0
  let now = 0
  let nextFrame: FrameRequestCallback | null = null
  let recorderConstructions = 0

  const analyser = {
    fftSize: 0,
    getByteTimeDomainData(data: Uint8Array) {
      data.fill(128 + Math.round(level * 42))
    }
  }

  const track = { stop: vi.fn() }
  const stream = { getTracks: () => [track] } as unknown as MediaStream

  class FakeAudioContext {
    close = vi.fn(async () => undefined)
    createAnalyser = () => analyser
    createMediaStreamSource = () => ({ connect: vi.fn() })
  }

  class FakeMediaRecorder {
    static isTypeSupported = () => true

    mimeType = 'audio/webm'
    ondataavailable: ((event: BlobEvent) => void) | null = null
    onerror: ((event: Event) => void) | null = null
    onstop: ((event: Event) => void) | null = null
    state: RecordingState = 'inactive'

    constructor() {
      recorderConstructions += 1
    }

    start() {
      this.state = 'recording'
    }

    stop() {
      this.state = 'inactive'
      this.onstop?.(new Event('stop'))
    }
  }

  const frame = (at: number, nextLevel: number) => {
    now = at
    level = nextLevel
    const callback = nextFrame

    nextFrame = null
    act(() => callback?.(at))
  }

  beforeEach(() => {
    level = 0.1
    now = 0
    nextFrame = null
    recorderConstructions = 0
    track.stop.mockClear()
    vi.spyOn(Date, 'now').mockImplementation(() => now)
    vi.stubGlobal('AudioContext', FakeAudioContext)
    vi.stubGlobal('MediaRecorder', FakeMediaRecorder)
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(callback => {
      nextFrame = callback

      return 1
    })
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => undefined)
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => stream) }
    })
    Object.defineProperty(window, 'hermesDesktop', {
      configurable: true,
      value: { requestMicrophoneAccess: vi.fn(async () => true) }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    Reflect.deleteProperty(navigator, 'mediaDevices')
    Reflect.deleteProperty(window, 'hermesDesktop')
  })

  it('learns elevated ambience without treating it as speech', async () => {
    const onSilence = vi.fn()
    const hook = renderHook(() => useMicRecorder(copy))

    await act(async () => {
      await hook.result.current.handle.start({
        idleSilenceMs: 12_000,
        onSilence,
        silenceLevel: 0.075,
        silenceMs: 1_250
      })
    })

    frame(200, 0.1)
    frame(400, 0.1)
    frame(2_000, 0.1)
    expect(onSilence).not.toHaveBeenCalled()

    frame(2_100, 0.5)
    frame(2_200, 0.1)
    frame(3_500, 0.1)
    expect(onSilence).toHaveBeenCalledTimes(1)

    act(() => hook.unmount())
  })

  it('preserves speech that ends during floor calibration', async () => {
    const onSilence = vi.fn()
    const hook = renderHook(() => useMicRecorder(copy))

    await act(async () => {
      await hook.result.current.handle.start({
        idleSilenceMs: 12_000,
        onSilence,
        silenceLevel: 0.075,
        silenceMs: 1_250
      })
    })

    frame(100, 0.5)
    frame(200, 0.5)
    frame(400, 0.02)
    frame(1_700, 0.02)
    expect(onSilence).toHaveBeenCalledTimes(1)

    act(() => hook.unmount())
  })

  it('releases a microphone acquired after its turn is aborted', async () => {
    let resolveStream: (value: MediaStream) => void = () => undefined

    const getUserMedia = vi.fn(
      () =>
        new Promise<MediaStream>(resolve => {
          resolveStream = resolve
        })
    )

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia }
    })

    const controller = new AbortController()
    const hook = renderHook(() => useMicRecorder(copy))
    const started = hook.result.current.handle.start({ signal: controller.signal })

    await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1))
    controller.abort()

    await act(async () => {
      resolveStream(stream)
      await started
    })

    expect(track.stop).toHaveBeenCalledTimes(1)
    expect(recorderConstructions).toBe(0)
    expect(hook.result.current.recording).toBe(false)

    act(() => hook.unmount())
  })

  it('releases a microphone acquired after the recorder unmounts without a caller signal', async () => {
    let resolveStream: (value: MediaStream) => void = () => undefined

    const getUserMedia = vi.fn(
      () =>
        new Promise<MediaStream>(resolve => {
          resolveStream = resolve
        })
    )

    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia }
    })

    const hook = renderHook(() => useMicRecorder(copy))
    const started = hook.result.current.handle.start()

    await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1))
    hook.unmount()
    resolveStream(stream)
    expect(await started).toBe(false)

    expect(track.stop).toHaveBeenCalledOnce()
    expect(recorderConstructions).toBe(0)
  })
})
