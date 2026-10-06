// "Sigil" — the Nous mark, struck onto a white card the way a dot-matrix
// head would print it: row by row, the head racing across the line it is on.
// The only design that shows the logo itself rather than Hermes imagery.

import { NOUS_MARK, sampleBitmap } from '../bitmaps.js'
import {
  bayer,
  BG_INK,
  BG_PAPER,
  bloom,
  Canvas,
  chrome,
  compact,
  DIM,
  Dots,
  easeInOut,
  easeOut,
  fits,
  grain,
  NOUS_PALETTE,
  PAPER,
  span,
  type SplashFrame,
  typed,
  wordmark
} from '../canvas.js'
import { wordmarkWidth } from '../wordmark.js'

export function sigil(frame: SplashFrame): string[] {
  const title = frame.title ?? 'HERMES AGENT'

  if (!fits(frame) || wordmarkWidth(title) + 4 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const c = new Canvas(w, h)
  const markRows = Math.max(5, Math.min(7, Math.round(h * 0.17)))
  const cardRows = Math.min(40, h - markRows - 6)
  const cardCols = Math.min(w - 8, cardRows * 2)
  const cardTop = 1 + Math.floor((h - markRows - 6 - cardRows) / 2) + 1
  const markTop = cardTop + cardRows + 2
  // The card is dealt face-on: it swings open about its vertical axis.
  const swing = easeOut(span(t, 120, 520))
  const cols = Math.max(0, Math.round((cardCols * swing) / 2) * 2)
  const left = Math.floor((w - cols) / 2)

  if (cols >= 4) {
    c.ground(left, cardTop, left + cols - 1, cardTop + cardRows - 1, BG_INK)

    // Rounded corners.
    for (const [x, y] of [
      [left, cardTop],
      [left + cols - 1, cardTop],
      [left, cardTop + cardRows - 1],
      [left + cols - 1, cardTop + cardRows - 1]
    ] as const) {
      c.ground(x, y, x, y, BG_PAPER)
    }

    const d = new Dots(cols, cardRows)
    const printed = easeInOut(span(t, 450, 1750)) * d.h
    const headRow = Math.floor(printed)
    // The head sweeps the current line a few times a second.
    const sweepPos = (t * 0.0045) % 1
    const headX = (sweepPos < 0.5 ? sweepPos * 2 : 2 - sweepPos * 2) * d.w
    // After printing, a sheen crosses the card now and then.
    const sheen = ((t - 2400) % 3200) / 900

    for (let y = 0; y < d.h; y++) {
      if (y > headRow) {
        break
      }

      for (let x = 0; x < d.w; x++) {
        if (y === headRow && printed < d.h && x > headX) {
          break
        }

        const u = (x + 0.5) / d.w
        const v = (y + 0.5) / d.h
        const glint = t > 2400 && Math.abs(u + v * 0.35 - sheen * 1.5) < 0.05 ? 0.3 : 0
        const val = sampleBitmap(NOUS_MARK, 0.02 + u * 0.96, 0.02 + v * 0.96)

        if (val - glint > 0.12 + bayer(x, y) * 0.76) {
          d.set(x, y, PAPER)
        }
      }
    }

    d.flush(c, left, cardTop)

    if (printed < d.h && printed > 0) {
      c.set(left + Math.min(cols - 1, Math.floor(headX / 2)), cardTop + Math.floor(headRow / 4), '▐', PAPER)
    }
  }

  const caption = 'NOUS RESEARCH PRESENTS'

  c.put(Math.floor((w - caption.length) / 2), markTop - 1, typed(caption, span(t, 1500, 1900)), DIM)
  wordmark(c, title, markTop, markRows, easeOut(span(t, 1700, 2350)), easeOut(span(t, 1700, 2050)))
  grain(c, t, 0.06)
  chrome(c, frame)

  return c.serialize(frame.color ?? 'truecolor', frame.palette ?? NOUS_PALETTE, bloom(frame, w, h))
}
