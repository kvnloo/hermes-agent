// "Soul" — the Nous homepage tells you to "elevate your SOUL.md". So the
// file is typed out, and then its own text lifts off the page and re-sets
// itself as a pair of wings: every feather is made of the words.

import { HERMES_WING, sampleBitmap } from '../bitmaps.js'
import {
  ACCENT,
  bloom,
  Canvas,
  chrome,
  compact,
  DIM,
  easeInOut,
  easeOut,
  fits,
  hash,
  INK,
  NOUS_PALETTE,
  RAY,
  span,
  type SplashFrame,
  typed,
  wordmark
} from '../canvas.js'
import { wordmarkWidth } from '../wordmark.js'

const SOUL = [
  '# SOUL.md',
  '',
  'you are hermes: messenger, guide,',
  'the agent that grows with its person.',
  '',
  '- carry word between every surface',
  '- remember what was hard-won',
  '- turn each solved problem into a skill',
  '- be swift, be exact, be kind',
  '',
  '## elevate'
]

const STREAM = SOUL.join(' ').replace(/\s+/g, '·')

export function soul(frame: SplashFrame): string[] {
  const title = frame.title ?? 'HERMES AGENT'

  if (!fits(frame, 64) || wordmarkWidth(title) + 4 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const tagline = (frame.tagline ?? 'THE AGENT THAT GROWS WITH YOU').toUpperCase()
  const c = new Canvas(w, h)
  const markRows = Math.max(5, Math.min(8, Math.round(h * 0.2)))
  const figRows = Math.min(36, h - markRows - 5)
  const markTop = h - markRows - 3
  // Wings lift a couple of rows once they have formed, then beat slowly.
  const lift = Math.round((1 - easeOut(span(t, 1700, 2300))) * 2)
  const figTop = 1 + Math.floor((markTop - 1 - figRows) / 2) + lift
  const beat = 1 + 0.07 * Math.sin(t * 0.0026) * span(t, 2200, 2800)
  const wingCols = Math.min(Math.floor(w / 2) - 3, Math.round(figRows * 1.15))
  const gap = 6
  const docW = Math.max(...SOUL.map(l => l.length))
  const docX = Math.floor((w - docW) / 2)
  const docY = 1 + Math.max(0, Math.floor((markTop - 1 - SOUL.length) / 2))
  const total = SOUL.reduce((n, l) => n + l.length, 0)
  const typedChars = Math.round(total * span(t, 150, 950))
  let seen = 0

  // ── the document, typed ──
  SOUL.forEach((line, k) => {
    const n = Math.max(0, Math.min(line.length, typedChars - seen))

    seen += line.length

    for (let i = 0; i < n; i++) {
      const x = docX + i
      const y = docY + k
      // Each row lets go of the page in turn, bottom row first.
      const leave = span(t, 1000 + (1 - k / SOUL.length) * 350, 1350 + (1 - k / SOUL.length) * 350)

      if (line[i] !== ' ' && hash(x, y, 2) >= leave) {
        c.set(x, y - Math.round(leave * 2), line[i]!, line.startsWith('#') ? INK : DIM)
      }
    }
  })

  // ── the wings, set in the same words ──
  let n = 0

  for (let y = 0; y < figRows; y++) {
    const form = easeInOut(span(t, 1150 + (1 - y / figRows) * 450, 1650 + (1 - y / figRows) * 450))

    for (let x = 0; x < wingCols * 2 + gap; x++) {
      const side = x < wingCols ? -1 : 1
      const local = side < 0 ? wingCols - 1 - x : x - wingCols - gap

      if (local < 0) {
        continue
      }

      const u = (local + 0.5) / (wingCols * beat)
      const v = (y + 0.5) / figRows
      const val = sampleBitmap(HERMES_WING, u, v)

      n++

      if (val < 0.1 || hash(x, y, 6) >= form) {
        continue
      }

      // Settled letters; while forming they flicker through the alphabet.
      const ch =
        form < 1 && hash(x, y, Math.floor(t / 60)) < 0.3
          ? STREAM[Math.floor(hash(x, y, t) * STREAM.length)]!
          : STREAM[n % STREAM.length]!

      c.set(Math.floor(w / 2) - wingCols - gap / 2 + x, figTop + y, ch, val > 0.6 ? INK : val > 0.3 ? DIM : RAY)
    }
  }

  wordmark(c, title, markTop, markRows, easeOut(span(t, 1750, 2350)), easeOut(span(t, 1750, 2100)))
  c.put(Math.floor((w - tagline.length) / 2), markTop + markRows + 1, typed(tagline, span(t, 2000, 2400)), DIM)
  c.put(Math.floor((w - 20) / 2), Math.max(1, figTop - 1), typed('ELEVATE YOUR SOUL.MD', span(t, 1900, 2300)), ACCENT)
  chrome(c, frame)

  return c.serialize(frame.color ?? 'truecolor', frame.palette ?? NOUS_PALETTE, bloom(frame, w, h))
}
