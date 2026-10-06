// Box-drawing wordmark in the spirit of the compressed gothic used across
// nousresearch.com: hairline strokes, far taller than wide. Each glyph is a
// stretchable column — a fixed top, a fixed waist and a fixed foot with
// repeatable stem rows between — so the same letterforms render at any height
// and can *grow* from a squat 4-row seed to full height.

interface Glyph {
  top: string
  /** Stem row repeated above the waist. Empty string = never stretch here. */
  upper: string
  waist: string[]
  /** Stem row repeated below the waist. */
  lower: string
  foot: string
}

const GLYPHS: Record<string, Glyph> = {
  A: { top: '╭─╮', upper: '│ │', waist: ['├─┤'], lower: '│ │', foot: '╵ ╵' },
  E: { top: '┌─╴', upper: '│  ', waist: ['├╴ '], lower: '│  ', foot: '└─╴' },
  G: { top: '╭─╴', upper: '│  ', waist: ['│╶┐'], lower: '│ │', foot: '╰─╯' },
  H: { top: '╷ ╷', upper: '│ │', waist: ['├─┤'], lower: '│ │', foot: '╵ ╵' },
  M: { top: '┌╮╭┐', upper: '', waist: ['│╰╯│'], lower: '│  │', foot: '╵  ╵' },
  N: { top: '┌╮ ╷', upper: '││ │', waist: ['│╰╮│'], lower: '│ ││', foot: '╵ ╰┘' },
  R: { top: '┌─╮', upper: '│ │', waist: ['├┬╯', '│╰╮'], lower: '│ │', foot: '╵ ╵' },
  S: { top: '╭─╴', upper: '│  ', waist: ['╰─╮'], lower: '  │', foot: '╶─╯' },
  T: { top: '╶┬╴', upper: ' │ ', waist: [' │ '], lower: ' │ ', foot: ' ╵ ' }
}

const LETTER_GAP = 1
const WORD_GAP = 3

/** Shortest height every glyph can render at (top + 2-row waist + foot). */
export const WORDMARK_MIN_ROWS = 4

const glyphRows = (g: Glyph, rows: number): string[] => {
  const waist = rows - 2 >= g.waist.length ? g.waist : g.waist.slice(0, 1)
  const spare = Math.max(0, rows - 2 - waist.length)
  const above = g.upper ? Math.floor(spare / 2) : 0
  const out = [g.top]

  for (let i = 0; i < above; i++) {
    out.push(g.upper)
  }

  out.push(...waist)

  for (let i = 0; i < spare - above; i++) {
    out.push(g.lower)
  }

  out.push(g.foot)

  return out
}

/**
 * Render `text` (A-Z subset + spaces) as `rows` lines of box-drawing glyphs.
 * Unknown characters render as blanks so a skin-provided name never throws.
 */
export function renderWordmark(text: string, rows: number): string[] {
  const h = Math.max(WORDMARK_MIN_ROWS, Math.floor(rows))
  const lines = Array.from({ length: h }, () => '')
  let first = true

  for (const ch of text.toUpperCase()) {
    if (ch === ' ') {
      for (let y = 0; y < h; y++) {
        lines[y] += ' '.repeat(WORD_GAP - LETTER_GAP)
      }

      continue
    }

    const g = GLYPHS[ch]
    const cell = g ? glyphRows(g, h) : Array.from({ length: h }, () => '   ')

    for (let y = 0; y < h; y++) {
      lines[y] += (first ? '' : ' '.repeat(LETTER_GAP)) + cell[y]
    }

    first = false
  }

  return lines
}

export const wordmarkWidth = (text: string) => renderWordmark(text, WORDMARK_MIN_ROWS)[0]!.length
