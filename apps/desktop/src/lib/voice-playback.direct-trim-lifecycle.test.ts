import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { startSpeechStream, stopVoicePlayback } from './voice-playback'

vi.mock('@/lib/voice-client-direct', () => ({
  directTtsConfig: vi.fn(async () => ({ min_len: 20 })),
  synthesizeSpeechClientDirect: vi.fn(async () => new ArrayBuffer(8))
}))

vi.mock('@/hermes', () => ({
  getApiRequestConnection: () => null,
  getApiRequestProfile: () => null,
  speakText: vi.fn()
}))

class PendingDecodeContext {
  static instances: PendingDecodeContext[] = []

  decodeAudioData = vi.fn(() => new Promise<AudioBuffer>(() => undefined))
  close = vi.fn(async () => undefined)

  constructor() {
    PendingDecodeContext.instances.push(this)
  }
}

describe('client-direct trim context lifetime', () => {
  beforeEach(() => {
    PendingDecodeContext.instances = []
    vi.stubGlobal('AudioContext', PendingDecodeContext)
  })

  afterEach(() => {
    stopVoicePlayback()
    vi.unstubAllGlobals()
  })

  it('closes the trim context on barge-in while a clip is decoding', async () => {
    const session = await startSpeechStream({ source: 'voice-conversation' })

    if (!session) {
      throw new Error('expected a client-direct speech session')
    }

    session.append('This complete sentence is ready for spoken playback.')
    session.finish()

    // Let the synthesized bytes reach decodeAudioData without completing decode.
    for (let tick = 0; tick < 8; tick += 1) {
      await Promise.resolve()
    }

    expect(PendingDecodeContext.instances).toHaveLength(1)
    const context = PendingDecodeContext.instances[0]

    expect(context.decodeAudioData).toHaveBeenCalledOnce()

    stopVoicePlayback()

    await expect(session.done).resolves.toBe('done')
    expect(context.close).toHaveBeenCalledOnce()
  })
})
