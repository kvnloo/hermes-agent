'use client'

import { useEffect, useMemo, useState } from 'react'

import { requestComposerSubmit } from '@/app/chat/composer/focus'
import { PreviewDocumentFrame } from '@/components/ui/preview-document-frame'
import { useThemeEpoch } from '@/hooks/use-theme-epoch'
import { useI18n } from '@/i18n/context'

import {
  collectThemeBridge,
  evaluateIntent,
  frameSizeFromMessage,
  intentAckMessage,
  type IntentAck,
  intentScript,
  measurementScript
} from '../inline-preview-directive'
import type { RichFenceProps } from '../types'

import { ephemeralFrameDocument, isTraceKind, parseEphemeralFence } from './ephemeral-ui-model'

interface KitAssets {
  css: string
  files: Record<string, string>
  runtime: string
}

// Loaded on first use, in their own chunk: ordinary Markdown never pays for
// the kit. The trace fixture (~1.2 MB) is fetched only for trace kinds.
let core: Promise<Omit<KitAssets, 'files'> & { files: Record<string, string> }> | null = null
let trace: Promise<string> | null = null

function loadKit(withTrace: boolean): Promise<KitAssets> {
  core ??= Promise.all([
    import('virtual:ephemeral-ui-frame'),
    import('./vendor/styles.css?raw'),
    import('./vendor/trace.css?raw'),
    import('./vendor/intent.css?raw'),
    import('./vendor/infra.css?raw'),
    import('./vendor/data/apps.json?raw'),
    import('./vendor/data/themes.json?raw'),
    import('./vendor/data/intent-snapshot.json?raw')
  ]).then(([runtime, styles, traceCss, intentCss, infraCss, apps, themes, intent]) => ({
    css: [styles, traceCss, intentCss, infraCss].map(m => m.default).join('\n'),
    files: { 'data/apps.json': apps.default, 'data/intent-snapshot.json': intent.default, 'data/themes.json': themes.default },
    runtime: runtime.default
  }))

  if (!withTrace) {
    return core
  }

  trace ??= import('./vendor/data/trace-fixture.json?raw').then(m => m.default)

  return Promise.all([core, trace]).then(([kit, fixture]) => ({
    ...kit,
    files: { ...kit.files, 'data/trace-fixture.json': fixture }
  }))
}

const DEFAULT_HEIGHT = 360

/** The skin `applyTheme` (themes/context.tsx) stamps on the root. */
const activeSkin = () => (typeof document === 'undefined' ? '' : document.documentElement.dataset.hermesTheme ?? '')

export default function EphemeralUiEmbed({ code, source, streaming }: RichFenceProps) {
  const { t } = useI18n()
  const parsed = useMemo(() => parseEphemeralFence(code), [code])
  const cards = parsed.kind === 'ready' ? parsed.cards : null
  const withTrace = Boolean(cards?.some(card => isTraceKind(card.kind)))
  const themeEpoch = useThemeEpoch()
  const [scheme, setScheme] = useState(() => collectThemeBridge().colorScheme)
  const [skin, setSkin] = useState(activeSkin)
  const [kit, setKit] = useState<KitAssets | null>(null)
  const [failed, setFailed] = useState(false)
  const [height, setHeight] = useState<number | null>(null)
  const [showSource, setShowSource] = useState(false)
  const token = useMemo(() => Math.random().toString(36).slice(2), [])

  useEffect(() => {
    setScheme(collectThemeBridge().colorScheme)
    setSkin(activeSkin())
  }, [themeEpoch])

  useEffect(() => {
    if (!cards || streaming) {
      return
    }

    let alive = true

    loadKit(withTrace).then(
      assets => alive && setKit(assets),
      () => alive && setFailed(true)
    )

    return () => {
      alive = false
    }
  }, [cards, streaming, withTrace])

  // Same trust boundary as inline widgets: only this mount's token moves the
  // frame or reaches the composer, and an intent is a hidden user turn.
  useEffect(() => {
    let lastIntentAt = 0

    const onMessage = (event: MessageEvent) => {
      const decision = evaluateIntent(event.data, token, Date.now(), lastIntentAt)

      if (decision !== null) {
        let ack: IntentAck

        if (decision.kind === 'reject') {
          ack = decision.ack
        } else {
          lastIntentAt = Date.now()
          ack = requestComposerSubmit(decision.prompt, { target: 'active', displayKind: 'hidden' })
            ? { ok: true }
            : { error: 'undelivered', ok: false }
        }

        const reply = event.source as Window | null

        if (decision.id !== null && reply) {
          reply.postMessage(intentAckMessage(token, decision.id, ack), '*')
        }

        return
      }

      const size = frameSizeFromMessage(event.data, token)

      if (size) {
        setHeight(prev => (prev !== null && Math.abs(prev - size.height) <= 4 ? prev : size.height))
      }
    }

    window.addEventListener('message', onMessage)

    return () => window.removeEventListener('message', onMessage)
  }, [token])

  const doc = useMemo(
    () =>
      kit && cards
        ? ephemeralFrameDocument({ cards, chrome: measurementScript(token) + intentScript(token), ...kit, scheme, skin })
        : null,
    [cards, kit, scheme, skin, token]
  )

  if (parsed.kind === 'invalid' && !streaming) {
    return (
      <section className="not-prose my-2" data-ephemeral-ui="invalid">
        <p className="px-1 py-1 text-xs text-muted-foreground" role="alert">
          {t.ephemeralUi.invalid}
          {parsed.detail ? ` (${parsed.detail})` : ''}
        </p>
        {source}
      </section>
    )
  }

  if (failed) {
    return <>{source}</>
  }

  const kinds = cards?.map(card => card.kind).join(', ') ?? ''

  return (
    <section
      className="not-prose my-2 min-w-0 overflow-hidden rounded-md border border-(--ui-stroke-tertiary)"
      data-ephemeral-ui="1"
      data-ephemeral-kinds={kinds}
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
        <span className="text-xs text-muted-foreground">
          {t.ephemeralUi.label} · {kinds}
        </span>
        <button
          aria-pressed={showSource}
          className="text-xs text-muted-foreground hover:text-foreground"
          onClick={() => setShowSource(value => !value)}
          type="button"
        >
          {showSource ? t.ephemeralUi.showCards : t.ephemeralUi.showSource}
        </button>
      </header>
      {showSource ? (
        source
      ) : doc === null ? (
        <div
          aria-hidden="true"
          className="h-24 animate-pulse bg-muted/20 motion-reduce:animate-none"
          data-ephemeral-loading=""
        />
      ) : (
        <div className="relative w-full transition-[height] duration-200" style={{ height: height ?? DEFAULT_HEIGHT }}>
          <PreviewDocumentFrame
            className="absolute inset-0 size-full border-0 bg-transparent"
            sandbox="allow-scripts"
            srcDoc={doc}
            style={{ colorScheme: scheme }}
            title={`${t.ephemeralUi.label}: ${kinds}`}
          />
        </div>
      )}
    </section>
  )
}
