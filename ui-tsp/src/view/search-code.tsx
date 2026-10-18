import type { JSX } from '@stencil-hq/tern'

import { displayText } from '../display-text.js'

/** Keep dense search output lossless while giving each file its own syntax context. */
export function searchCode(text: string, format: unknown): JSX.Element[] {
  if (typeof format !== 'string' || !format.startsWith('path-grouped:')) {
    return [<code key="matches" lang="text" text={displayText(text)} wrap />]
  }

  // The producer emits a raw path on its own line, then indented line-number rows.
  // Keep those labels and all whitespace verbatim; path selects syntax, not navigation.
  return text
    .split(/\n(?=\S)/u)
    .map((group, index, groups) => (
      <code
        key={`matches-${index}`}
        path={group.split('\n', 1)[0]}
        text={displayText(group + (index < groups.length - 1 ? '\n' : ''))}
        wrap
      />
    ))
}
