// "Unleash" — the pricing tiers read FREE / RELEASE / LIBERATE / UNLEASH
// HERMES, and the site's compressed type already looks like bars. So: the
// screen starts as a cage of hairlines; the gates open from the middle; the
// bars that remain shorten until they are the stems of the wordmark.

import {
  ACCENT,
  bloom,
  Canvas,
  chrome,
  clamp01,
  compact,
  DIM,
  easeInOut,
  easeOut,
  fits,
  hash,
  INK,
  lerp,
  RAY,
  span,
  type SplashCells,
  type SplashFrame
} from '../canvas.js'
import { TERN_SPLASH_PALETTE } from '../theme.js'
import { renderWordmark, wordmarkWidth } from '../wordmark.js'

const TIERS = ['FREE', 'RELEASE', 'LIBERATE', 'UNLEASH']
const STEMS = new Set(['│', '├', '┤', '╷', '╵', '┌', '└', '┐', '┘', '╭', '╮', '╰', '╯', '┬'])

export function unleash(frame: SplashFrame): SplashCells {
  const title = (frame.title ?? 'HERMES AGENT').toUpperCase()
  const markW = wordmarkWidth(title)

  if (!fits(frame) || markW + 4 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const c = new Canvas(w, h)
  const markRows = Math.max(6, Math.min(13, Math.round(h * 0.34)))
  const markTop = Math.floor((h - markRows) / 2) - 1
  const lines = renderWordmark(title, markRows)
  const mx = Math.floor((w - markW) / 2)
  const top = 1
  const bottom = h - 2
  const stemAt = (x: number) => x >= mx && x < mx + markW && lines.some(line => STEMS.has(line[x - mx]!))

  // After the intro, a pulse runs left→right: stems lunge back to full height.
  const pulseAt = ((t - 2600) % 3000) / 3000

  for (let x = 0; x < w; x++) {
    const stem = stemAt(x)

    if (!stem && x % 2 !== 0) {
      continue
    }

    const drop = easeOut(span(t, 60 + hash(x, 1) * 260, 420 + hash(x, 1) * 260))
    let y0 = top
    let y1 = Math.round(lerp(top, bottom, drop))

    if (stem) {
      // Shorten to the letter's own extent.
      const settle = easeInOut(span(t, 1250, 1950))
      const kick = t > 2600 ? Math.max(0, 1 - Math.abs(pulseAt * 1.4 - x / w) * 9) * 0.55 : 0
      const k = settle * (1 - kick)

      y0 = Math.round(lerp(top, markTop, k))
      y1 = Math.round(lerp(y1, markTop + markRows - 1, k))
    } else {
      // Gates open from the centre outward; alternate bars leave up and down.
      const dist = Math.abs(x - w / 2) / (w / 2)
      const gone = easeInOut(span(t, 620 + dist * 620, 1080 + dist * 620))

      if ((x >> 1) & 1) {
        y1 = Math.round(lerp(y1, top - 1, gone))
      } else {
        y0 = Math.round(lerp(top, bottom + 1, gone))
      }
    }

    for (let y = y0; y <= y1; y++) {
      c.set(x, y, '│', stem ? INK : RAY)
    }
  }

  // Cross-strokes and bowls resolve last, over the stems.
  const resolve = span(t, 1750, 2300)

  if (resolve > 0) {
    lines.forEach((line, k) => {
      for (let i = 0; i < line.length; i++) {
        if (line[i] !== ' ' && hash(i, k, 4) < resolve * 1.2) {
          c.set(mx + i, markTop + k, line[i]!, INK)
        }
      }
    })
  }

  // The tier names tick over as the cage gives way.
  const tier = Math.min(TIERS.length - 1, Math.floor(clamp01(t / 2000) * TIERS.length))
  const word = TIERS[tier]!.split('').join(' ')
  const label = `${word}   H E R M E S`
  const ly = Math.min(h - 3, markTop + markRows + 2)
  const lx = Math.floor((w - label.length) / 2)

  c.clear(lx - 2, ly, lx + label.length + 1, ly)
  c.put(lx, ly, word, tier === TIERS.length - 1 ? ACCENT : INK)
  c.put(lx + word.length + 3, ly, 'H E R M E S', DIM)
  chrome(c, frame)

  return c.cells(frame.palette ?? TERN_SPLASH_PALETTE, bloom(frame, w, h))
}
