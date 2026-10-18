// Browser-only presentation; compatible with the result adapter registry.

import type { JSX } from '@stencil-hq/tern'

import type { ToolCall } from '../model.js'
import { record } from '../transcript.js'

import { ActionButton } from './action-button.js'

interface BrowserCard {
  target?: string
  targetKind?: 'command' | 'path' | 'pattern' | 'query' | 'text'
  meta?: string[]
  folded?: boolean
  body: JSX.Element[]
}

export function browserBlockCard<T extends BrowserCard>(card: T, call: ToolCall, focus?: (id: string) => void): T {
  const target = record(record(call.result)?.tern_target)
  const id = target?.target_id

  if (
    !call.name.startsWith('browser') ||
    target?.in_tern !== true ||
    typeof id !== 'string' ||
    !/^[1-9][0-9]*$/.test(id)
  ) {
    return card
  }

  const title = typeof target.title === 'string' ? target.title : ''
  const url = typeof target.url === 'string' ? target.url : ''
  const frame = typeof target.frame === 'string' ? `evaluation frame ${target.frame}` : undefined

  return {
    ...card,
    target: url || card.target,
    targetKind: 'path',
    meta: [
      ...new Set([...(card.meta ?? []), ...(title ? [title] : []), `in Tern block ${id}`, ...(frame ? [frame] : [])])
    ],
    folded: false,
    body: [
      ...(focus
        ? [
            <ActionButton key="browser-focus" onClick={() => focus(id)} role="omp.btn" title={`Focus Tern block ${id}`}>
              <text key="label" text="Focus browser block" />
            </ActionButton>
          ]
        : []),
      ...card.body
    ]
  }
}
