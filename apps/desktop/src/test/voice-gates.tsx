import '../styles.css'

import { createRoot } from 'react-dom/client'

import { ConversationPill } from '@/app/chat/composer/controls'
import { VoiceVisualizer, type VoiceVisualizerVariant } from '@/app/chat/composer/voice-visualizer'
import { I18nProvider } from '@/i18n'
import { ThemeProvider } from '@/themes/context'
import type { HermesConfigRecord } from '@/types/hermes'

let config: HermesConfigRecord = {
  tts: {
    edge: { voice: 'en-US-AriaNeural' },
    elevenlabs: { voice_id: 'rachel' },
    openai: { voice: 'alloy' },
    provider: 'edge'
  },
  voice: { desktop_visualizer: 'orb' }
}

const api = async (request: { body?: { config?: HermesConfigRecord }; method?: string; path: string }) => {
  if (request.path === '/api/config' && request.method === 'PUT' && request.body?.config) {
    config = structuredClone(request.body.config)
    return { ok: true }
  }
  if (request.path === '/api/config') {
    return structuredClone(config)
  }
  if (request.path === '/api/audio/elevenlabs/voices') {
    return { available: true, voices: [{ label: 'Rachel', name: 'Rachel', voice_id: 'rachel' }] }
  }
  if (request.path === '/api/audio/speak') {
    return { data_url: 'data:audio/wav;base64,UklGRg==' }
  }
  throw new Error(`Unexpected mocked Hermes IPC request: ${request.path}`)
}

window.hermesDesktop = { api } as unknown as Window['hermesDesktop']

document.documentElement.style.setProperty('--composer-control-size', '2.25rem')
document.documentElement.style.setProperty('--composer-control-gap', '0.5rem')

const variants: VoiceVisualizerVariant[] = ['pill', 'orb', 'waveform', 'minimal']

function VoiceGateHarness() {
  return (
    <I18nProvider configClient={null} initialLocale="en">
      <ThemeProvider>
        <main className="min-h-screen bg-background p-10 text-foreground">
        <header className="mb-8">
          <p className="text-xs font-medium uppercase tracking-[0.22em] text-muted-foreground">Test-only real component harness</p>
          <h1 className="mt-2 text-2xl font-semibold">Hermes conversation voice</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Real production components with an in-memory, profile-safe Hermes IPC mock. No active config writes.
          </p>
        </header>

        <section aria-labelledby="variants-heading">
          <h2 className="mb-3 text-sm font-semibold" id="variants-heading">Visualizer variants</h2>
          <div className="grid grid-cols-4 gap-3">
            {variants.map(variant => (
              <article className="rounded-xl border border-border bg-card p-5" data-proof={variant} key={variant}>
                <p className="mb-4 text-xs uppercase tracking-wider text-muted-foreground">{variant}</p>
                <VoiceVisualizer label={variant === 'minimal' ? 'Thinking' : 'Listening'} level={0.72} status={variant === 'minimal' ? 'thinking' : 'listening'} variant={variant} />
              </article>
            ))}
          </div>
        </section>

        <section aria-labelledby="pill-heading" className="mt-8 rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5 text-sm font-semibold" id="pill-heading">Conversation pill · latency</h2>
          <ConversationPill
            active
            disabled={false}
            error={null}
            latency={{ captureMs: 1250, modelMs: 842, playbackMs: 231, sttMs: 388, ttsMs: 476 }}
            level={0.64}
            muted={false}
            onEnd={() => undefined}
            onRetry={() => undefined}
            onStart={() => undefined}
            onStopTurn={() => undefined}
            onToggleMute={() => undefined}
            status="listening"
          />
        </section>

        <section aria-labelledby="error-heading" className="mt-5 rounded-xl border border-border bg-card p-6">
          <h2 className="mb-5 text-sm font-semibold" id="error-heading">Stage error · recovery</h2>
          <ConversationPill
            active
            disabled={false}
            error={{ message: 'Provider unavailable', stage: 'tts' }}
            latency={{ captureMs: 1250, modelMs: 842, sttMs: 388 }}
            level={0}
            muted={false}
            onEnd={() => undefined}
            onRetry={() => undefined}
            onStart={() => undefined}
            onStopTurn={() => undefined}
            onToggleMute={() => undefined}
            status="error"
          />
        </section>

        <p className="mt-6 text-xs text-muted-foreground" id="motion-proof">
          Motion preference: <strong>{matchMedia('(prefers-reduced-motion: reduce)').matches ? 'reduced' : 'standard'}</strong>
        </p>
        </main>
      </ThemeProvider>
    </I18nProvider>
  )
}

createRoot(document.getElementById('root')!).render(<VoiceGateHarness />)
