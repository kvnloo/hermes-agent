const ORDERED_ITEM_RE = /^ {0,3}(\d{1,9})[.)][ \t]+\S/
const EMPTY_ORDERED_ITEM_RE = /^ {0,3}(\d{1,9})[.)][ \t]*$/
const BLANK_OR_HEADING_RE = /^(?:[ \t]*$| {0,3}#{1,6}(?:[ \t]|$))/
// Lines that open (or continue) a non-paragraph block: bullets, ordered items,
// blockquotes, table rows, indented code.
const OTHER_BLOCK_RE = /^(?: {0,3}(?:[-*+][ \t]|\d{1,9}[.)](?:[ \t]|$)|>|\|)| {4}|\t)/

/**
 * CommonMark lets an ordered list interrupt a paragraph only when it starts
 * at 1, so a reply like `**Follow-ups**\n4. First\n5. Second` parses as one
 * run-on paragraph. Insert the missing blank line before such a list.
 *
 * Runs on prose segments only (fences are split out by the caller). Lists
 * already rendering as lists, list continuations and blockquotes are left
 * untouched, and the pass is idempotent.
 */
export function separateOrderedLists(text: string): string {
  const out: string[] = []
  let inParagraph = false
  let blockStart = true

  const lines = text.split('\n')

  for (const [index, line] of lines.entries()) {
    if (BLANK_OR_HEADING_RE.test(line)) {
      inParagraph = false
      blockStart = true
      out.push(line)

      continue
    }

    const item = ORDERED_ITEM_RE.exec(line)
    const emptyItem = EMPTY_ORDERED_ITEM_RE.exec(line)
    const nextItem = index + 1 < lines.length ? ORDERED_ITEM_RE.exec(lines[index + 1]) : null
    // An empty item cannot interrupt prose by itself. Only split when a
    // consecutive populated item proves this is a continued list.
    const startsEmptyContinuation =
      emptyItem !== null &&
      nextItem !== null &&
      Number(emptyItem[1]) !== 1 &&
      Number(nextItem[1]) === Number(emptyItem[1]) + 1

    if (inParagraph && ((item && Number(item[1]) !== 1) || startsEmptyContinuation)) {
      out.push('')
      inParagraph = false
    } else if (OTHER_BLOCK_RE.test(line)) {
      if (blockStart || !/^[ \t]/.test(line)) {
        inParagraph = false
      }
    } else if (blockStart) {
      inParagraph = true
    }

    blockStart = false
    out.push(line)
  }

  return out.join('\n')
}
