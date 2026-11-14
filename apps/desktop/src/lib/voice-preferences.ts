import type { VoiceVisualizerVariant } from '@/app/chat/composer/voice-visualizer'
import type { ElevenLabsVoice, HermesConfigRecord } from '@/types/hermes'

export type ConversationVoiceProvider = 'edge' | 'elevenlabs' | 'openai'

export interface ConversationVoiceOption {
  id: string
  label: string
}

export const CONVERSATION_VOICE_PROVIDERS: readonly ConversationVoiceProvider[] = ['edge', 'elevenlabs', 'openai']
export const VOICE_VISUALIZER_VARIANTS: readonly VoiceVisualizerVariant[] = ['pill', 'orb', 'waveform', 'minimal']

// A compact useful catalog; settings still accepts any Edge voice identifier.
const EDGE_VOICES: readonly ConversationVoiceOption[] = [
  { id: 'en-US-AriaNeural', label: 'Aria · US English' },
  { id: 'en-US-GuyNeural', label: 'Guy · US English' },
  { id: 'en-US-JennyNeural', label: 'Jenny · US English' },
  { id: 'en-GB-SoniaNeural', label: 'Sonia · UK English' },
  { id: 'en-GB-RyanNeural', label: 'Ryan · UK English' },
  { id: 'en-AU-NatashaNeural', label: 'Natasha · Australian English' },
  { id: 'ja-JP-NanamiNeural', label: 'Nanami · Japanese' },
  { id: 'zh-CN-XiaoxiaoNeural', label: 'Xiaoxiao · Mandarin' }
]

const OPENAI_VOICES: readonly ConversationVoiceOption[] = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'].map(
  id => ({ id, label: id[0].toUpperCase() + id.slice(1) })
)

const VOICE_KEY: Record<ConversationVoiceProvider, string> = {
  edge: 'voice',
  elevenlabs: 'voice_id',
  openai: 'voice'
}

export function voiceOptionsForProvider(
  provider: ConversationVoiceProvider,
  elevenLabsVoices: ElevenLabsVoice[]
): ConversationVoiceOption[] {
  if (provider === 'edge') {
    return [...EDGE_VOICES]
  }
  if (provider === 'openai') {
    return [...OPENAI_VOICES]
  }

  return elevenLabsVoices.map(voice => ({ id: voice.voice_id, label: voice.name || voice.label || voice.voice_id }))
}

export function selectedVoice(config: HermesConfigRecord, provider: ConversationVoiceProvider): string {
  const tts = config.tts
  if (!tts || typeof tts !== 'object' || Array.isArray(tts)) {
    return ''
  }
  const providerConfig = (tts as Record<string, unknown>)[provider]
  if (!providerConfig || typeof providerConfig !== 'object' || Array.isArray(providerConfig)) {
    return ''
  }
  return String((providerConfig as Record<string, unknown>)[VOICE_KEY[provider]] ?? '')
}

export function selectedProvider(config: HermesConfigRecord): ConversationVoiceProvider {
  const provider =
    config.tts && typeof config.tts === 'object' && !Array.isArray(config.tts)
      ? (config.tts as Record<string, unknown>).provider
      : undefined
  return CONVERSATION_VOICE_PROVIDERS.includes(provider as ConversationVoiceProvider)
    ? (provider as ConversationVoiceProvider)
    : 'edge'
}

export function selectedVoiceVisualizerVariant(config: HermesConfigRecord): VoiceVisualizerVariant {
  const variant =
    config.voice && typeof config.voice === 'object' && !Array.isArray(config.voice)
      ? (config.voice as Record<string, unknown>).desktop_visualizer
      : undefined
  return VOICE_VISUALIZER_VARIANTS.includes(variant as VoiceVisualizerVariant)
    ? (variant as VoiceVisualizerVariant)
    : 'orb'
}

export function applyVoiceVisualizerVariant(
  config: HermesConfigRecord,
  variant: VoiceVisualizerVariant
): HermesConfigRecord {
  const voice = config.voice && typeof config.voice === 'object' && !Array.isArray(config.voice) ? config.voice : {}
  return { ...config, voice: { ...(voice as Record<string, unknown>), desktop_visualizer: variant } }
}

/** Immutable update. Config records deliberately contain no secret material in
 * normal API responses; regardless, this helper never enumerates or renders any
 * unrelated values and preserves them byte-for-value in the outgoing record. */
export function applyVoiceSelection(
  config: HermesConfigRecord,
  provider: ConversationVoiceProvider,
  voice: string
): HermesConfigRecord {
  const tts = config.tts && typeof config.tts === 'object' && !Array.isArray(config.tts) ? config.tts : {}
  const providerConfig =
    (tts as Record<string, unknown>)[provider] &&
    typeof (tts as Record<string, unknown>)[provider] === 'object' &&
    !Array.isArray((tts as Record<string, unknown>)[provider])
      ? ((tts as Record<string, unknown>)[provider] as Record<string, unknown>)
      : {}

  return {
    ...config,
    tts: {
      ...(tts as Record<string, unknown>),
      provider,
      [provider]: { ...providerConfig, [VOICE_KEY[provider]]: voice }
    }
  }
}
