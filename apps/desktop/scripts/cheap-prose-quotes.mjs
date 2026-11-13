// `@tailwindcss/typography` hangs blockquote quote marks off
// `blockquote p:first-of-type::before` / `p:last-of-type::after`. Chromium
// keys type-position invalidation on the tag alone, so appending one <p> to a
// streaming message re-styles every <p> sibling: O(n) per paragraph, O(n²) per
// reply, ~1.3 s of style recalc while a long answer streams. The child forms
// draw the same marks on a quote's paragraphs and only touch the old last child.
const TYPE_POSITION = /blockquote p:(first|last)-of-type/g

export const cheapProseQuotes = css => css.replace(TYPE_POSITION, 'blockquote>p:$1-child')

export function cheapProseQuotesPlugin() {
  return {
    name: 'hermes:cheap-prose-quotes',
    enforce: 'pre',
    transform(code, id) {
      if (!/\.css(\?|$)/.test(id) || !code.includes('-of-type')) return

      return { code: cheapProseQuotes(code), map: null }
    }
  }
}
