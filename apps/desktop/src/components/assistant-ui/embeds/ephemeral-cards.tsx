'use client'

import { defineComponent } from '@openuidev/react-lang'
import { memo, useEffect, useMemo, useState } from 'react'

import { requestComposerInsertAcked } from '@/app/chat/composer/focus'
import { Button } from '@/components/ui/button'
import { PreviewDocumentFrame } from '@/components/ui/preview-document-frame'
import { useThemeEpoch } from '@/hooks/use-theme-epoch'
import { useI18n } from '@/i18n/context'

import {
  EPHEMERAL_LIMITS,
  ephemeralCardApp,
  ephemeralCardsProps,
  type EphemeralCardsProps,
  type EphemeralIntent,
  ephemeralIntentContext,
  parseEphemeralMessage,
  readDesktopPalette
} from './ephemeral-cards-model'
import { EPHEMERAL_UI_KINDS, EPHEMERAL_UI_REVISION } from './ephemeral-ui-kinds.generated'
import { useIsDark } from './use-is-dark'

// The generated kit is large, so it loads only once a board actually has ephemeral-ui cards.
const loadDocument = () => import('./ephemeral-cards-document')

type AddState = 'idle' | 'added' | 'missing'

export const EphemeralCardsPanel = memo(function EphemeralCardsPanel({ props }: { props: EphemeralCardsProps }) {
  const { t } = useI18n()
  const dark = useIsDark()
  const epoch = useThemeEpoch()
  const [channel] = useState(() => Math.random().toString(36).slice(2))
  const [html, setHtml] = useState<string | null>(null)
  const [height, setHeight] = useState(360)
  const [intent, setIntent] = useState<EphemeralIntent | null>(null)
  const [errors, setErrors] = useState<string[]>([])
  const [added, setAdded] = useState<AddState>('idle')

  // Rebuild the document only when the cards or the theme change, not on every parent render.
  const cards = JSON.stringify(props.cards.map(card => ({ ...card, app: ephemeralCardApp(card.kind, card.app) })))
  const palette = useMemo(() => JSON.stringify(readDesktopPalette()), [dark, epoch]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let live = true
    void loadDocument().then(module => {
      if (live) {
        setHtml(module.ephemeralCardsDocument({
          channel,
          scheme: dark ? 'dark' : 'light',
          palette: JSON.parse(palette),
          cards: JSON.parse(cards)
        }))
      }
    })

    return () => {
      live = false
    }
  }, [cards, channel, dark, palette])

  useEffect(() => {
    const onMessage = (event: MessageEvent) => {
      const message = parseEphemeralMessage(event.data, channel)

      if (message?.type === 'height') {
        setHeight(message.value)
      } else if (message?.type === 'intent') {
        setIntent(message.intent)
        setAdded('idle')
      } else if (message?.type === 'error') {
        setErrors(current => [...current, t.openui.kitFailed.replace('{kind}', message.kind).replace('{reason}', message.reason)].slice(-4))
      }
    }

    window.addEventListener('message', onMessage)

    return () => window.removeEventListener('message', onMessage)
  }, [channel, t])

  const addToChat = async () => {
    if (!intent) {
      return
    }

    const card = props.cards.find(entry => entry.kind === intent.kind)
    const app = intent.app || (card ? ephemeralCardApp(card.kind, card.app) : 'ephemeral-ui')
    const ok = await requestComposerInsertAcked(ephemeralIntentContext(intent, app), { mode: 'block', target: 'main' })
    setAdded(ok ? 'added' : 'missing')
  }

  return (
    <section
      aria-label={props.title}
      className="min-w-0 space-y-2 rounded-lg border border-(--ui-stroke-tertiary) bg-muted/20 p-2"
      data-ephemeral-ui-cards={props.cards.map(card => card.kind).join(' ')}
      role="region"
    >
      <h4 className="px-1 text-sm font-semibold">{props.title}</h4>
      {html === null ? (
        <p className="px-1 text-xs text-muted-foreground" role="status">{t.openui.kitLoading}</p>
      ) : (
        // No allow-same-origin: the kit runs in an opaque origin with no network (its CSP) and no host access.
        <PreviewDocumentFrame
          className="block w-full border-0"
          sandbox="allow-scripts"
          srcDoc={html}
          style={{ height, colorScheme: dark ? 'dark' : 'light' }}
          title={props.title}
        />
      )}
      <div aria-live="polite" className="flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-muted-foreground">
        <p className="min-w-0 flex-1">
          {intent ? t.openui.kitPicked.replace('{what}', intent.label || intent.action) : t.openui.kitIdle}
          {added === 'added' && <> · {t.openui.kitAdded}</>}
          {added === 'missing' && <> · {t.openui.kitNoComposer}</>}
        </p>
        {intent && added !== 'added' && (
          <Button onClick={() => void addToChat()} size="sm" variant="outline">{t.openui.kitAddToChat}</Button>
        )}
        <span className="tabular-nums" title={EPHEMERAL_UI_REVISION}>ephemeral-ui {EPHEMERAL_UI_REVISION.slice(0, 7)}</span>
      </div>
      {errors.map(error => (
        <p className="px-1 text-xs text-destructive" key={error} role="alert">{error}</p>
      ))}
    </section>
  )
})

export const EphemeralCards = defineComponent({
  name: 'EphemeralCards',
  description:
    `Cards from the ephemeral-ui kit, drawn by the kit itself: a title, then up to ${EPHEMERAL_LIMITS.cards} cards ` +
    `{kind, app?, input?, options?}. kind is one of ${EPHEMERAL_UI_KINDS.join(', ')}. app is a catalog app id ` +
    '(gmail, github, uber, stripe…); omit it for the kind\'s default. Only trace kinds take input (omp-stats JSON) ' +
    'and options {range, view, sort, tab, focusTool, scope}. Every other kind shows the kit\'s sample data.',
  props: ephemeralCardsProps,
  component: EphemeralCardsPanel
})
