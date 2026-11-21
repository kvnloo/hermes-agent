'use client'

import { type ComponentType, lazy, type LazyExoticComponent, type ReactNode, Suspense } from 'react'

import { RichBoundary } from './rich-boundary'
import type { RichFenceProps } from './types'

// Root renderer for fenced code blocks: a language → lazy-renderer table. Each
// renderer is split and loaded only when a block of that language appears. The
// Mermaid renderer defers its heavier runtime import until after its source
// fallback has had a chance to paint.
const LAZY_FENCE: Record<string, LazyExoticComponent<ComponentType<RichFenceProps>>> = {
  'ephemeral-ui': lazy(() => import('../ephemeral/fence-card')),
  listing: lazy(() => import('./listing-embed')),
  mermaid: lazy(() => import('./mermaid-embed')),
  'openui-v2': lazy(() => import('./openui-embed')),
  svg: lazy(() => import('./svg-embed'))
}

export const RICH_FENCE_LANGUAGES: ReadonlySet<string> = new Set(Object.keys(LAZY_FENCE))

interface RichCodeBlockProps extends RichFenceProps {
  /** Rendered for unhandled languages, while the chunk loads, and on failure
   *  (typically the normal syntax-highlighted code block). */
  fallback: ReactNode
  language?: string
}

export function RichCodeBlock({ code, fallback, language, streaming }: RichCodeBlockProps) {
  const Renderer = language ? LAZY_FENCE[language.toLowerCase()] : undefined

  if (!Renderer) {
    return <>{fallback}</>
  }

  // A streaming board's first chunk would otherwise flash its raw source while
  // the renderer chunk loads; a quiet placeholder holds the space instead.
  const loading = streaming && language?.toLowerCase() === 'openui-v2'
    ? <div aria-hidden="true" className="my-2 h-24 animate-pulse rounded-md border border-(--ui-stroke-tertiary) bg-muted/20 motion-reduce:animate-none" data-openui-loading="" />
    : fallback

  return (
    <RichBoundary fallback={fallback} resetKey={code}>
      <Suspense fallback={loading}>
        <Renderer code={code} source={fallback} streaming={streaming} />
      </Suspense>
    </RichBoundary>
  )
}
