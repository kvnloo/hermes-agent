import { describe, expect, it } from 'vitest'

import {
  applyVoiceSelection,
  applyVoiceVisualizerVariant,
  selectedProvider,
  selectedVoiceVisualizerVariant,
  voiceOptionsForProvider
} from './voice-preferences'

describe('voice preferences', () => {
  it('updates only provider and selected voice without exposing credentials', () => {
    const source = { api_key: 'do-not-touch', tts: { provider: 'edge', edge: { voice: 'old' } } }
    const next = applyVoiceSelection(source, 'openai', 'nova')

    expect(next).toMatchObject({ api_key: 'do-not-touch', tts: { provider: 'openai', openai: { voice: 'nova' } } })
    expect(source).toEqual({ api_key: 'do-not-touch', tts: { provider: 'edge', edge: { voice: 'old' } } })
  })

  it('provides built-in Edge and OpenAI catalogs', () => {
    expect(voiceOptionsForProvider('edge', [])).toContainEqual(expect.objectContaining({ id: 'en-US-AriaNeural' }))
    expect(voiceOptionsForProvider('openai', [])).toContainEqual(expect.objectContaining({ id: 'nova' }))
  })

  it('normalizes provider and visualizer values from malformed config', () => {
    expect(selectedProvider({ tts: { provider: 'openai' } })).toBe('openai')
    expect(selectedProvider({ tts: { provider: 'unknown' } })).toBe('edge')
    expect(selectedVoiceVisualizerVariant({ voice: { desktop_visualizer: 'waveform' } })).toBe('waveform')
    expect(selectedVoiceVisualizerVariant({ voice: { desktop_visualizer: 'unknown' } })).toBe('orb')
  })

  it('persists the visualizer without replacing other voice settings', () => {
    const source = { voice: { auto_tts: true } }
    expect(applyVoiceVisualizerVariant(source, 'minimal')).toEqual({
      voice: { auto_tts: true, desktop_visualizer: 'minimal' }
    })
    expect(source).toEqual({ voice: { auto_tts: true } })
  })
})
