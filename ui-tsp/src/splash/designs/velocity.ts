// "Velocity" — the site files the TUI under "Terminal Velocity". Speed
// lines tear across three parallax depths, the Hermes wing arrives hot from
// the left trailing a wake, and everything brakes to cruising speed as the
// wordmark slides in.

import { HERMES_WING, sampleBitmap } from '../bitmaps.js'
import {
  ACCENT,
  bayer,
  bloom,
  Canvas,
  chrome,
  compact,
  DIM,
  Dots,
  easeOut,
  fits,
  hash,
  INK,
  lerp,
  RAY,
  span,
  type SplashCells,
  type SplashFrame,
  typed,
  wordmark
} from '../canvas.js'
import { TERN_SPLASH_PALETTE } from '../theme.js'
import { wordmarkWidth } from '../wordmark.js'

export function velocity(frame: SplashFrame): SplashCells {
  const title = frame.title ?? 'HERMES AGENT'
  const markW = wordmarkWidth(title)

  if (!fits(frame, 72) || markW + 4 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const tagline = (frame.tagline ?? 'THE AGENT THAT GROWS WITH YOU').toUpperCase()
  const c = new Canvas(w, h)
  // Distance travelled: flat out, then braking to a steady cruise.
  const brake = easeOut(span(t, 700, 2200))
  const travel = t * lerp(0.16, 0.022, brake) + brake * 150

  // ── speed lines ──
  for (let i = 0; i < h * 3; i++) {
    const depth = i % 3
    const y = 1 + Math.floor(hash(i, 1) * (h - 2))
    const len = Math.round((3 + hash(i, 2) * 14) * (depth + 1) * lerp(1.6, 0.5, brake))
    const lane = w + len + 10
    const x = Math.floor(lane - ((travel * (0.5 + depth * 0.7) + hash(i, 3) * lane) % lane)) - len
    const ch = depth === 2 ? '━' : depth === 1 ? '─' : '╌'
    const tone = depth === 2 ? INK : depth === 1 ? RAY : DIM

    for (let k = 0; k < len; k++) {
      // Tails thin out.
      if (k > len * 0.6 && k & 1) {
        continue
      }

      c.set(x + k, y, ch, tone)
    }
  }

  // ── wing ──
  const wingRows = Math.min(34, h - 4)
  const wingCols = Math.round(wingRows * 0.98)
  const markRows = Math.max(5, Math.min(9, Math.round(h * 0.26)))
  const group = wingCols + 4 + markW
  const restX = Math.max(2, Math.floor((w - group) / 2))
  const wingX = Math.round(lerp(-wingCols - 10, restX, easeOut(span(t, 250, 1300))))
  const wingY = Math.floor((h - wingRows) / 2) + Math.round(Math.sin(t * 0.0021) * 0.6 * brake)
  const d = new Dots(wingCols + 30, wingRows)
  const lead = 60
  const wake = Math.round(lerp(56, 8, brake))

  for (let y = 0; y < d.h; y++) {
    let edge = -1

    for (let x = 0; x < wingCols * 2; x++) {
      const val = sampleBitmap(HERMES_WING, (x + 0.5) / (wingCols * 2), (y + 0.5) / d.h)

      if (val > 0.1 + bayer(x, y) * 0.8) {
        d.set(lead + x, y, INK)

        if (edge < 0) {
          edge = x
        }
      }
    }

    // Wake: each printed row drags a dithered streak behind its leading edge.
    if (edge >= 0 && (y & 1) === 0) {
      for (let k = 1; k < wake; k++) {
        if (hash(k, y, 9) > k / wake) {
          d.set(lead + edge - k, y, RAY)
        }
      }
    }
  }

  c.clear(wingX, wingY, wingX + wingCols - 1, wingY + wingRows - 1)
  d.flush(c, wingX - lead / 2, wingY)

  // ── wordmark arrives from the right ──
  const slide = easeOut(span(t, 1150, 2000))
  const markX = restX + wingCols + 4
  const markTop = Math.floor((h - markRows) / 2) - 1
  const offset = Math.round((1 - slide) * (w - markX + 4))

  if (slide > 0) {
    c.clear(markX + offset - 2, markTop - 2, markX + offset + markW + 1, markTop + markRows + 2)
    wordmark(c, title, markTop, markRows, easeOut(span(t, 1500, 2300)), 1, INK, markX + offset + markW / 2)
    c.put(markX + offset, markTop - 2, typed('TUI ■ TERMINAL VELOCITY', span(t, 1700, 2100)), ACCENT)
    c.put(markX + offset, markTop + markRows + 1, typed(tagline, span(t, 1900, 2350)), DIM)
  }

  chrome(c, frame)

  return c.cells(frame.palette ?? TERN_SPLASH_PALETTE, bloom(frame, w, h))
}
