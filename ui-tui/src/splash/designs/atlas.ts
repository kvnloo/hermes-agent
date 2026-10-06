// "Atlas" — after the "Lives Everywhere" plate: a wireframe globe on a
// plotted axis. Meridians and parallels are inked in, the sphere turns, and
// every surface Hermes speaks on is pinned to it and swings in and out of
// view. Hidden lines are kept but printed faint.

import {
  ACCENT,
  bloom,
  Canvas,
  chrome,
  compact,
  DIM,
  Dots,
  easeOut,
  fits,
  grain,
  INK,
  NOUS_PALETTE,
  RAY,
  span,
  type SplashFrame,
  TAU,
  typed,
  wordmark
} from '../canvas.js'
import { wordmarkWidth } from '../wordmark.js'

const PINS: [string, number, number][] = [
  ['TELEGRAM', 0.5, 0.2],
  ['DISCORD', -0.3, 1.1],
  ['SLACK', 0.15, 2.0],
  ['WHATSAPP', -0.55, 2.9],
  ['SIGNAL', 0.7, 3.8],
  ['EMAIL', -0.1, 4.7],
  ['CLI', 0.35, 5.6]
]

const TILT = 0.38

export function atlas(frame: SplashFrame): string[] {
  const title = frame.title ?? 'HERMES AGENT'

  if (!fits(frame) || wordmarkWidth(title) + 4 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const tagline = (frame.tagline ?? 'THE AGENT THAT GROWS WITH YOU').toUpperCase()
  const c = new Canvas(w, h)
  const d = new Dots(w, h)
  const markRows = Math.max(5, Math.min(8, Math.round(h * 0.2)))
  const figRows = Math.min(40, h - markRows - 5)
  const figTop = 1 + Math.floor((h - markRows - 5 - figRows) / 2)
  const markTop = figTop + figRows + 1
  const cx = d.w / 2
  const cy = (figTop + figRows / 2) * 4
  const radius = Math.min(figRows * 2 - 3, w * 0.42)
  const spin = t * 0.00055 + 1.6 * (1 - easeOut(span(t, 200, 1800)))
  const ct = Math.cos(TILT)
  const st = Math.sin(TILT)

  // (lat, lon) on the unit sphere → screen dots + depth.
  const project = (lat: number, lon: number): [number, number, number] => {
    const cl = Math.cos(lat)
    const x = cl * Math.sin(lon + spin)
    const z0 = cl * Math.cos(lon + spin)
    const y0 = Math.sin(lat)
    const y = y0 * ct - z0 * st
    const z = y0 * st + z0 * ct

    return [cx + x * radius, cy - y * radius, z]
  }

  const arc = (pt: (s: number) => [number, number], drawn: number) => {
    const steps = 56
    let prev = project(...pt(0))

    for (let i = 1; i <= Math.floor(steps * drawn); i++) {
      const next = project(...pt(i / steps))

      d.line(prev[0], prev[1], next[0], next[1], prev[2] + next[2] > 0 ? INK : RAY)
      prev = next
    }
  }

  for (let m = 0; m < 12; m++) {
    arc(s => [-Math.PI / 2 + Math.PI * s, (m / 12) * TAU], easeOut(span(t, 300 + m * 50, 1100 + m * 50)))
  }

  for (let p = 1; p < 6; p++) {
    arc(s => [-Math.PI / 2 + (p / 6) * Math.PI, s * TAU], easeOut(span(t, 700 + p * 80, 1600 + p * 80)))
  }

  // Plotted axes with ticks, as on the plate.
  const axis = easeOut(span(t, 150, 900))
  const ax = cx - radius - 10
  const ay = cy + radius + 5

  d.line(ax, ay, ax, ay - (radius * 2 + 8) * axis, DIM)
  d.line(ax, ay, ax + (radius * 2 + 18) * axis, ay, DIM)

  for (let k = 1; k * 6 < (radius * 2 + 8) * axis; k++) {
    d.line(ax - (k % 4 === 0 ? 4 : 2), ay - k * 6, ax, ay - k * 6, DIM)
  }

  for (let k = 1; k * 8 < (radius * 2 + 18) * axis; k++) {
    d.line(ax + k * 8, ay, ax + k * 8, ay + (k % 4 === 0 ? 3 : 1.5), DIM)
  }

  d.flush(c)

  // Pins: marker on the surface, label alongside while it faces us.
  for (const [i, [name, lat, lon]] of PINS.entries()) {
    const born = 1150 + i * 140

    if (t < born) {
      continue
    }

    const [px, py, z] = project(lat, lon)
    const col = Math.round(px / 2)
    const row = Math.round(py / 4)

    if (z > 0.12) {
      c.set(col, row, '◆', ACCENT)
      c.clear(col + 1, row, col + 2 + name.length, row)
      c.put(col + 2, row, typed(name, span(t, born, born + 260)), INK)
    } else {
      c.set(col, row, '◇', RAY)
    }
  }

  const lon = ((((spin / TAU) * 360) % 360) + 360) % 360
  const readout = `LON ${lon.toFixed(1).padStart(5, '0')}°  TILT ${((TILT / TAU) * 360).toFixed(1)}°`

  c.put(Math.round(ax / 2) + 2, Math.round((ay - radius * 2 - 8) / 4), typed(readout, span(t, 900, 1400)), DIM)
  wordmark(c, title, markTop, markRows, easeOut(span(t, 1450, 2200)), easeOut(span(t, 1450, 1850)))
  c.put(Math.floor((w - tagline.length) / 2), markTop + markRows + 1, typed(tagline, span(t, 1900, 2350)), DIM)
  grain(c, t, 0.05)
  chrome(c, frame)

  return c.serialize(frame.color ?? 'truecolor', frame.palette ?? NOUS_PALETTE, bloom(frame, w, h))
}
