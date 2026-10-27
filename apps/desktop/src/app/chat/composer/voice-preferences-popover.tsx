import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { useOnProfileSwitch } from '@/app/hooks/use-on-profile-switch'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { getElevenLabsVoices, getHermesConfigRecord, saveHermesConfig } from '@/hermes'
import { useI18n } from '@/i18n'
import { playSpeechText } from '@/lib/voice-playback'
import {
  applyVoiceSelection,
  applyVoiceVisualizerVariant,
  CONVERSATION_VOICE_PROVIDERS,
  type ConversationVoiceProvider,
  selectedProvider,
  selectedVoice,
  selectedVoiceVisualizerVariant,
  VOICE_VISUALIZER_VARIANTS,
  voiceOptionsForProvider
} from '@/lib/voice-preferences'
import { notify, notifyError } from '@/store/notifications'
import type { ElevenLabsVoice, HermesConfigRecord } from '@/types/hermes'

import type { ConversationStatus } from './hooks/use-voice-conversation'
import type { VoiceVisualizerVariant } from './voice-visualizer'

interface VoicePreferencesPopoverProps {
  onVariantChange: (variant: VoiceVisualizerVariant) => void
  status: ConversationStatus
}

export function VoicePreferencesPopover({ onVariantChange, status }: VoicePreferencesPopoverProps) {
  const { t } = useI18n()
  const copy = t.composer.voicePreferences
  const [open, setOpen] = useState(false)
  const [config, setConfig] = useState<HermesConfigRecord | null>(null)
  const [voices, setVoices] = useState<ElevenLabsVoice[]>([])
  const [candidateProvider, setCandidateProvider] = useState<ConversationVoiceProvider>('edge')
  const [candidateVoice, setCandidateVoice] = useState('')
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const generationRef = useRef(0)

  const load = useCallback(async () => {
    const generation = ++generationRef.current
    try {
      const [nextConfig, catalog] = await Promise.all([
        getHermesConfigRecord(),
        getElevenLabsVoices().catch(() => ({ available: false, voices: [] }))
      ])
      if (generation !== generationRef.current) {
        return
      }
      setConfig(nextConfig)
      setVoices(catalog.available ? catalog.voices : [])
      const nextProvider = selectedProvider(nextConfig)
      const nextVoices = catalog.available ? catalog.voices : []
      setCandidateProvider(nextProvider)
      setCandidateVoice(selectedVoice(nextConfig, nextProvider) || voiceOptionsForProvider(nextProvider, nextVoices)[0]?.id || '')
      onVariantChange(selectedVoiceVisualizerVariant(nextConfig))
    } catch (error) {
      if (generation === generationRef.current) {
        notifyError(error, copy.loadFailed)
      }
    }
  }, [copy.loadFailed, onVariantChange])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (open && !config) {
      void load()
    }
  }, [config, load, open])

  useOnProfileSwitch(() => {
    generationRef.current += 1
    setConfig(null)
    setVoices([])
    setOpen(false)
    void load()
  })

  const provider = candidateProvider
  const options = useMemo(() => voiceOptionsForProvider(provider, voices), [provider, voices])
  const voice = candidateVoice || options[0]?.id || ''
  const variant = config ? selectedVoiceVisualizerVariant(config) : 'orb'

  const save = async (update: (fresh: HermesConfigRecord) => HermesConfigRecord) => {
    const generation = generationRef.current
    setSaving(true)
    try {
      // Re-read immediately before the authoritative write so this compact
      // surface never overwrites edits made in Settings or another profile.
      const fresh = await getHermesConfigRecord()
      if (generation !== generationRef.current) {
        return
      }
      const next = update(fresh)
      await saveHermesConfig(next)
      if (generation !== generationRef.current) {
        return
      }
      setConfig(next)
      onVariantChange(selectedVoiceVisualizerVariant(next))
      notify({ kind: 'success', title: copy.saved, message: copy.nextTurn })
    } catch (error) {
      if (generation === generationRef.current) {
        notifyError(error, copy.saveFailed)
      }
      await load()
    } finally {
      if (generation === generationRef.current) {
        setSaving(false)
      }
    }
  }

  const chooseProvider = (next: ConversationVoiceProvider) => {
    const first = voiceOptionsForProvider(next, voices)[0]?.id ?? ''
    setCandidateProvider(next)
    setCandidateVoice(config ? selectedVoice(config, next) || first : first)
  }

  const selectionDirty = config
    ? provider !== selectedProvider(config) || voice !== selectedVoice(config, provider)
    : false

  const preview = async () => {
    setPreviewing(true)
    try {
      await playSpeechText(copy.previewPhrase, {
        preview: { provider, voice },
        source: 'voice-conversation'
      })
    } catch (error) {
      notifyError(error, copy.previewFailed)
    } finally {
      setPreviewing(false)
    }
  }

  return (
    <Popover onOpenChange={setOpen} open={open}>
      <PopoverTrigger asChild>
        <Button aria-label={copy.title} disabled={saving} size="icon" type="button" variant="ghost">
          <span aria-hidden="true">⚙</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 space-y-3" side="top">
        <div>
          <p className="text-sm font-medium">{copy.title}</p>
          <p className="text-xs text-muted-foreground">{copy.description}</p>
        </div>
        {config ? (
          <>
            <label className="grid gap-1 text-xs">
              <span>{copy.provider}</span>
              <select
                aria-label={copy.provider}
                className="h-8 rounded-md border border-border bg-background px-2"
                disabled={saving}
                onChange={event => chooseProvider(event.target.value as ConversationVoiceProvider)}
                value={provider}
              >
                {CONVERSATION_VOICE_PROVIDERS.map(item => (
                  <option key={item} value={item}>{copy.providers[item]}</option>
                ))}
              </select>
            </label>
            <label className="grid gap-1 text-xs">
              <span>{copy.voice}</span>
              <select
                aria-label={copy.voice}
                className="h-8 rounded-md border border-border bg-background px-2"
                disabled={saving || options.length === 0}
                onChange={event => setCandidateVoice(event.target.value)}
                value={voice}
              >
                {options.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label className="grid gap-1 text-xs">
              <span>{copy.visualizer}</span>
              <select
                aria-label={copy.visualizer}
                className="h-8 rounded-md border border-border bg-background px-2"
                disabled={saving}
                onChange={event => void save(fresh => applyVoiceVisualizerVariant(fresh, event.target.value as VoiceVisualizerVariant))}
                value={variant}
              >
                {VOICE_VISUALIZER_VARIANTS.map(item => <option key={item} value={item}>{copy.visualizers[item]}</option>)}
              </select>
            </label>
            <Button
              className="w-full"
              disabled={previewing || saving || status === 'speaking'}
              onClick={() => void preview()}
              size="sm"
              type="button"
              variant="outline"
            >
              {previewing ? copy.previewing : copy.preview}
            </Button>
            <Button
              className="w-full"
              disabled={!selectionDirty || saving || previewing}
              onClick={() => void save(fresh => applyVoiceSelection(fresh, provider, voice))}
              size="sm"
              type="button"
            >
              {copy.save}
            </Button>
          </>
        ) : (
          <p aria-live="polite" className="text-xs text-muted-foreground">{copy.loading}</p>
        )}
      </PopoverContent>
    </Popover>
  )
}
