'use client'

import { useMemo, useState } from 'react'

import { Button } from '@/components/ui/button'
import { useI18n } from '@/i18n/context'

import { inspectOpenUiBoard, OpenUiBoard, previewStreamingBoard } from './openui-catalog'
import type { RichFenceProps } from './types'

// The normal Markdown code card is handed through as "source": a toggle never
// reconstructs the program or hides it behind a parser failure.
export default function OpenUiEmbed({ code, source, streaming }: RichFenceProps) {
  const { t } = useI18n()
  const [showSource, setShowSource] = useState(false)
  const status = useMemo(() => inspectOpenUiBoard(code), [code])
  // While the fence is still arriving, render its complete statements as a
  // board (with placeholders for panels still to come) instead of a wall of
  // source that later snaps into cards.
  const preview = useMemo(
    () => (streaming && status.kind === 'incomplete' ? previewStreamingBoard(code) : { kind: 'none' as const }),
    [code, status.kind, streaming]
  )
  const original = source ?? (
    <pre className="max-h-96 overflow-auto p-3 text-xs whitespace-pre-wrap wrap-anywhere">
      <code>{code}</code>
    </pre>
  )
  const ready = status.kind === 'ready'
  const board = !ready && preview.kind === 'board' ? preview : null
  const previewing = board !== null
  const waiting = Boolean(streaming) && status.kind === 'incomplete' && !previewing
  const sourceVisible = showSource || (!ready && !previewing && !waiting)

  return (
    <section className="not-prose my-2 min-w-0 overflow-hidden rounded-md border border-(--ui-stroke-tertiary) bg-muted/20" data-openui-catalog="2">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-(--ui-stroke-tertiary) px-3 py-1.5">
        <span className="text-xs text-muted-foreground">
          {t.openui.label} · {t.openui.readOnly}{streaming ? ` · ${t.openui.receiving}` : ''}
        </span>
        {ready && (
          <Button aria-pressed={sourceVisible} onClick={() => setShowSource(value => !value)} size="sm" type="button" variant="text">
            {sourceVisible ? t.openui.showBoard : t.openui.showSource}
          </Button>
        )}
      </header>
      {!ready && !previewing && !waiting && (
        <p className="px-3 py-2 text-xs text-muted-foreground" role="alert">
          {t.openui[status.reason]}
        </p>
      )}
      {waiting && !showSource ? (
        <p className="px-3 py-2 text-xs text-muted-foreground" role="status">{t.openui.receiving}…</p>
      ) : sourceVisible ? original : (
        <OpenUiBoard code={board ? board.code : code} pending={board ? board.pending : 0} streaming={streaming} />
      )}
    </section>
  )
}
