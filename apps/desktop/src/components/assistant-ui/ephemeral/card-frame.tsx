'use client'

import { memo, useEffect, useMemo, useRef, useState } from 'react'

import { useIsDark } from '@/components/assistant-ui/embeds/use-is-dark'
import { PreviewDocumentFrame } from '@/components/ui/preview-document-frame'
import { useThemeEpoch } from '@/hooks/use-theme-epoch'
import { useI18n } from '@/i18n/context'

import { ephemeralCardSpec, type EphemeralMatch, type EphemeralMessage, lifetimeMessage, parseEphemeralMessage, readDesktopPalette } from './model'

// The generated kit is large, so it loads only once a card is actually on screen.
const loadDocument = () => import('./document')

interface EphemeralCardFrameProps {
  match: EphemeralMatch
  title: string
  /** Draw the card already kept (no lifetime): the input bar popup. */
  pinned?: boolean
  /** Start the card's ring with this lifetime once it is ready; null keeps it waiting. */
  lifetimeMs?: number | null
  onMessage?: (message: EphemeralMessage) => void
}

/** One kit card in a sandboxed frame: no same-origin, no network (its CSP), no host access. */
export const EphemeralCardFrame = memo(function EphemeralCardFrame({ match, title, pinned = false, lifetimeMs = null, onMessage }: EphemeralCardFrameProps) {
  const { t } = useI18n()
  const dark = useIsDark()
  const epoch = useThemeEpoch()
  const [channel] = useState(() => Math.random().toString(36).slice(2))
  const [html, setHtml] = useState<string | null>(null)
  const [height, setHeight] = useState(180)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const box = useRef<HTMLDivElement>(null)
  const handler = useRef(onMessage)
  handler.current = onMessage

  const spec = useMemo(() => JSON.stringify(ephemeralCardSpec(match)), [match])
  const kind = match.kind
  const palette = useMemo(() => JSON.stringify(readDesktopPalette()), [dark, epoch]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let live = true
    setReady(false)
    void loadDocument().then(module => {
      if (live) {
        setHtml(module.ephemeralCardDocument({ channel, scheme: dark ? 'dark' : 'light', palette: JSON.parse(palette), card: JSON.parse(spec), pinned }))
      }
    })

    return () => {
      live = false
    }
  }, [channel, dark, palette, pinned, spec])

  useEffect(() => {
    const onWindowMessage = (event: MessageEvent) => {
      const message = parseEphemeralMessage(event.data, channel)

      if (!message) {
        return
      }

      if (message.type === 'height') {
        setHeight(message.value)
      } else if (message.type === 'ready') {
        setReady(true)
      } else if (message.type === 'error') {
        setError(t.openui.kitFailed.replace('{kind}', message.kind).replace('{reason}', message.reason))
      }

      handler.current?.(message)
    }

    window.addEventListener('message', onWindowMessage)

    return () => window.removeEventListener('message', onWindowMessage)
  }, [channel, t])

  // The Webapp hosts preview documents one frame deeper; its loader relays this message down.
  useEffect(() => {
    if (ready && lifetimeMs !== null && !pinned) {
      box.current?.querySelector('iframe')?.contentWindow?.postMessage(lifetimeMessage(channel, lifetimeMs), '*')
    }
  }, [channel, lifetimeMs, pinned, ready])

  return (
    <div className="min-w-0" data-ephemeral-card={kind} data-ephemeral-ready={ready ? '' : undefined} ref={box}>
      {html === null ? (
        <p className="px-1 py-2 text-xs text-muted-foreground" role="status">{t.openui.kitLoading}</p>
      ) : (
        <PreviewDocumentFrame
          className="block w-full border-0"
          sandbox="allow-scripts"
          srcDoc={html}
          style={{ height, colorScheme: dark ? 'dark' : 'light' }}
          title={title}
        />
      )}
      {error && <p className="px-1 text-xs text-destructive" role="alert">{error}</p>}
    </div>
  )
})
