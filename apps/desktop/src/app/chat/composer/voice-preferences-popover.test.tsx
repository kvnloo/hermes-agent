import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import type { HermesConfigRecord } from '@/types/hermes'

class TestResizeObserver {
  disconnect() {}
  observe() {}
  unobserve() {}
}

beforeAll(() => {
  vi.stubGlobal('ResizeObserver', TestResizeObserver)
})

const mocks = vi.hoisted(() => ({
  activeProfile: 'default',
  getConfig: vi.fn(),
  getVoices: vi.fn(),
  notify: vi.fn(),
  notifyError: vi.fn(),
  playSpeechText: vi.fn(),
  profileSwitch: null as null | (() => void),
  saveConfig: vi.fn()
}))

vi.mock('@/app/hooks/use-on-profile-switch', () => ({
  useOnProfileSwitch: (callback: () => void) => {
    mocks.profileSwitch = callback
  }
}))
vi.mock('@/hermes', () => ({
  getElevenLabsVoices: mocks.getVoices,
  getHermesConfigRecord: mocks.getConfig,
  saveHermesConfig: mocks.saveConfig
}))
vi.mock('@/lib/voice-playback', () => ({ playSpeechText: mocks.playSpeechText }))
vi.mock('@/store/notifications', () => ({ notify: mocks.notify, notifyError: mocks.notifyError }))
vi.mock('@/i18n', () => ({
  useI18n: () => ({
    t: {
      composer: {
        voicePreferences: {
          description: 'Choose conversation speech and appearance.',
          loadFailed: 'Could not load voice preferences',
          loading: 'Loading voice preferences…',
          nextTurn: 'The next assistant turn will use this voice.',
          preview: 'Preview voice',
          previewFailed: 'Could not preview voice',
          previewing: 'Previewing…',
          previewPhrase: 'Hello from Hermes.',
          provider: 'Provider',
          providers: { edge: 'Edge', elevenlabs: 'ElevenLabs', openai: 'OpenAI' },
          save: 'Save voice',
          saveFailed: 'Could not save voice preferences',
          saved: 'Voice saved',
          title: 'Voice preferences',
          visualizer: 'Visualizer',
          visualizers: { minimal: 'Minimal', orb: 'Orb', pill: 'Pill', waveform: 'Waveform' },
          voice: 'Voice'
        }
      }
    }
  })
}))

import { VoicePreferencesPopover } from './voice-preferences-popover'

const initialConfigs: Record<string, HermesConfigRecord> = {
  default: {
    tts: { edge: { voice: 'en-US-AriaNeural' }, openai: { voice: 'alloy' }, provider: 'edge' },
    voice: { desktop_visualizer: 'orb' }
  },
  work: {
    tts: { edge: { voice: 'en-US-GuyNeural' }, openai: { voice: 'echo' }, provider: 'openai' },
    voice: { desktop_visualizer: 'minimal' }
  }
}
let configs: Record<string, HermesConfigRecord> = structuredClone(initialConfigs)

async function openPicker() {
  fireEvent.click(screen.getByRole('button', { name: 'Voice preferences' }))
  await screen.findByRole('combobox', { name: 'Provider' })
}

afterEach(cleanup)

beforeEach(() => {
  vi.clearAllMocks()
  configs = structuredClone(initialConfigs)
  mocks.activeProfile = 'default'
  mocks.profileSwitch = null
  mocks.getConfig.mockImplementation(async () => structuredClone(configs[mocks.activeProfile]))
  mocks.getVoices.mockResolvedValue({ available: true, voices: [{ label: 'Rachel', name: 'Rachel', voice_id: 'rachel' }] })
  mocks.playSpeechText.mockResolvedValue(true)
  mocks.saveConfig.mockImplementation(async (config: HermesConfigRecord) => {
    configs[mocks.activeProfile] = structuredClone(config)
    return { ok: true }
  })
})

describe('VoicePreferencesPopover', () => {
  it('keeps provider and voice unsaved, previews that candidate, then persists only on Save', async () => {
    render(<VoicePreferencesPopover onVariantChange={vi.fn()} status="listening" />)
    await openPicker()

    fireEvent.change(screen.getByRole('combobox', { name: 'Provider' }), { target: { value: 'openai' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Voice' }), { target: { value: 'nova' } })

    expect(mocks.saveConfig).not.toHaveBeenCalled()
    expect(configs.default.tts).toMatchObject({ provider: 'edge' })

    fireEvent.click(screen.getByRole('button', { name: 'Preview voice' }))
    await waitFor(() =>
      expect(mocks.playSpeechText).toHaveBeenCalledWith('Hello from Hermes.', {
        preview: { provider: 'openai', voice: 'nova' },
        source: 'voice-conversation'
      })
    )
    expect(mocks.saveConfig).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: 'Save voice' }))
    await waitFor(() => expect(mocks.saveConfig).toHaveBeenCalledTimes(1))
    expect(configs.default.tts).toMatchObject({ openai: { voice: 'nova' }, provider: 'openai' })
    expect(mocks.notify).toHaveBeenCalledWith(expect.objectContaining({ message: expect.stringMatching(/next assistant turn/i) }))
  })

  it('drops unsaved candidates on profile switch and writes only the active profile', async () => {
    render(<VoicePreferencesPopover onVariantChange={vi.fn()} status="idle" />)
    await openPicker()
    fireEvent.change(screen.getByRole('combobox', { name: 'Provider' }), { target: { value: 'openai' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Voice' }), { target: { value: 'nova' } })

    const readsBeforeSwitch = mocks.getConfig.mock.calls.length
    mocks.activeProfile = 'work'
    mocks.profileSwitch?.()

    await waitFor(() => expect(mocks.getConfig.mock.calls.length).toBeGreaterThan(readsBeforeSwitch))
    await openPicker()
    expect((screen.getByRole('combobox', { name: 'Provider' }) as HTMLSelectElement).value).toBe('openai')
    expect((screen.getByRole('combobox', { name: 'Voice' }) as HTMLSelectElement).value).toBe('echo')

    fireEvent.change(screen.getByRole('combobox', { name: 'Voice' }), { target: { value: 'shimmer' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save voice' }))
    await waitFor(() => expect(mocks.saveConfig).toHaveBeenCalledTimes(1))

    expect(configs.work.tts).toMatchObject({ openai: { voice: 'shimmer' }, provider: 'openai' })
    expect(configs.default.tts).toMatchObject({ edge: { voice: 'en-US-AriaNeural' }, provider: 'edge' })
  })

  it('is keyboard operable and exposes names for trigger, fields, and actions', async () => {
    render(<VoicePreferencesPopover onVariantChange={vi.fn()} status="idle" />)
    const trigger = screen.getByRole('button', { name: 'Voice preferences' })
    trigger.focus()
    expect(document.activeElement).toBe(trigger)
    // A native button maps keyboard activation to click; jsdom does not synthesize
    // that browser default, so drive the resulting activation directly.
    fireEvent.click(trigger)
    await screen.findByRole('combobox', { name: 'Provider' })

    expect(screen.getByRole('combobox', { name: 'Voice' })).toBeTruthy()
    expect(screen.getByRole('combobox', { name: 'Visualizer' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Preview voice' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Save voice' })).toBeTruthy()
  })
})
