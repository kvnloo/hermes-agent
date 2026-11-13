import { describe, expect, it } from 'vitest'

import { cheapProseQuotes } from './cheap-prose-quotes.mjs'

describe('cheapProseQuotes', () => {
  it('moves the blockquote quote marks onto child position', () => {
    const css =
      '.prose :where(blockquote p:first-of-type):not(:where([class~=not-prose],[class~=not-prose] *)):before{content:open-quote}' +
      '.prose :where(blockquote p:last-of-type):not(:where([class~=not-prose],[class~=not-prose] *)):after{content:close-quote}'

    expect(cheapProseQuotes(css)).not.toContain('-of-type')
    expect(cheapProseQuotes(css)).toContain(':where(blockquote>p:first-child)')
    expect(cheapProseQuotes(css)).toContain(':where(blockquote>p:last-child)')
  })

  it('leaves other type-position rules alone', () => {
    const css = 'li:first-of-type{margin:0}'

    expect(cheapProseQuotes(css)).toBe(css)
  })
})
