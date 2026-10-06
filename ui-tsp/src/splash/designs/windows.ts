// "Windows" — after the footer plate, where the bust of Hermes is ringed by
// little floating program windows. A desktop of them pops open one by one,
// each doing a small job (a log, an eye, meters, a scope, static), and the
// last one to open — inverted, on top — carries the wordmark.

import {
  ACCENT,
  BG_INK,
  BG_PAPER,
  BG_SHADE,
  bloom,
  Canvas,
  chrome,
  clamp01,
  compact,
  DIM,
  Dots,
  easeOut,
  easeOutBack,
  fits,
  hash,
  INK,
  PAPER,
  RAY,
  SHADE,
  span,
  type SplashCells,
  type SplashFrame,
  typed
} from '../canvas.js'
import { TERN_SPLASH_PALETTE } from '../theme.js'
import { renderWordmark, wordmarkWidth } from '../wordmark.js'

interface Win {
  title: string
  // Fractions of the screen.
  x: number
  y: number
  w: number
  h: number
  born: number
  body: (c: Canvas, x: number, y: number, w: number, h: number, age: number, t: number) => void
}

const LOG = [
  'boot  hermes-tui',
  'spawn gateway',
  'load  SOUL.md',
  'scan  skills/',
  'mount memory',
  'dial  providers',
  'bind  mcp servers',
  'open  session',
  'ready'
]

const log: Win['body'] = (c, x, y, w, h, age) => {
  const shown = Math.floor(age / 210)
  const first = Math.max(0, shown - h + 1)

  for (let i = 0; i < h; i++) {
    const n = first + i

    if (n > shown) {
      break
    }

    const line = LOG[n % LOG.length]!
    const text = `${String(n).padStart(2, '0')} ${line}`

    c.put(x, y + i, typed(text, n === shown ? (age % 210) / 150 : 1).slice(0, w), n === shown ? INK : DIM)
  }
}

const eye: Win['body'] = (c, x, y, w, h, _age, t) => {
  const cx = x + w / 2
  const cy = y + h / 2
  const gx = Math.sin(t * 0.0012) * w * 0.12
  const blink = t % 3100 < 140 ? 0.15 : 1

  for (let j = 0; j < h; j++) {
    for (let i = 0; i < w; i++) {
      const nx = (x + i + 0.5 - cx) / (w * 0.46)
      const ny = (y + j + 0.5 - cy) / (h * 0.46 * blink)

      if (Math.abs(nx) >= 1 || Math.abs(ny) > (1 - nx * nx) ** 0.6) {
        continue
      }

      const r = Math.hypot(x + i + 0.5 - cx - gx, (y + j + 0.5 - cy) * 2) / (h * 0.8)

      c.set(x + i, y + j, r < 0.3 ? '⣿' : r < 0.62 ? '•' : '·', r < 0.3 ? SHADE : r < 0.62 ? RAY : INK)
    }
  }
}

const meters: Win['body'] = (c, x, y, w, h, age) => {
  const rows = ['SKILLS', 'MEMORY', 'TOOLS', 'MCP', 'CRON']

  for (let i = 0; i < Math.min(h, rows.length); i++) {
    const bar = Math.max(0, w - 8)
    const fill = Math.round(bar * easeOut(clamp01((age - i * 160) / 900)) * (0.55 + 0.45 * hash(i, 11)))

    c.put(x, y + i, rows[i]!.padEnd(7), DIM)
    c.put(x + 7, y + i, '█'.repeat(fill), INK)
    c.put(x + 7 + fill, y + i, '░'.repeat(Math.max(0, bar - fill)), RAY)
  }
}

const scope: Win['body'] = (c, x, y, w, h, age, t) => {
  const d = new Dots(w, h)
  const drawn = Math.round(d.w * clamp01(age / 600))
  let py = d.h / 2

  for (let i = 0; i < drawn; i++) {
    const v = Math.sin(i * 0.21 + t * 0.006) * 0.55 + Math.sin(i * 0.057 - t * 0.002) * 0.35
    const ny = d.h / 2 - v * d.h * 0.45

    d.line(i - 1, py, i, ny, INK)
    py = ny
  }

  d.flush(c, x, y)
}

const noise: Win['body'] = (c, x, y, w, h, _age, t) => {
  const seed = Math.floor(t / 90)

  for (let j = 0; j < h; j++) {
    for (let i = 0; i < w; i++) {
      const n = hash(x + i, y + j, seed)

      c.set(x + i, y + j, String.fromCharCode(0x2800 | Math.floor(n * 255)), n > 0.55 ? RAY : SHADE)
    }
  }
}

const WINDOWS: Win[] = [
  { body: log, born: 200, h: 0.42, title: 'gateway.log', w: 0.3, x: 0.04, y: 0.08 },
  { body: eye, born: 480, h: 0.34, title: 'eye.raw', w: 0.22, x: 0.72, y: 0.06 },
  { body: noise, born: 700, h: 0.26, title: 'field', w: 0.16, x: 0.42, y: 0.04 },
  { body: meters, born: 900, h: 0.34, title: 'inventory', w: 0.3, x: 0.66, y: 0.56 },
  { body: scope, born: 1100, h: 0.3, title: 'signal', w: 0.28, x: 0.08, y: 0.6 }
]

const frameBox = (
  c: Canvas,
  x: number,
  y: number,
  w: number,
  h: number,
  title: string,
  ground: number,
  tone: number
) => {
  // Drop shadow, then the pane itself.
  c.ground(x + 2, y + 1, x + w + 1, y + h, BG_SHADE)
  c.clear(x + 2, y + 1, x + w + 1, y + h)
  c.ground(x, y, x + w - 1, y + h - 1, ground)
  c.clear(x, y, x + w - 1, y + h - 1)

  const label = ` ■ ${title} `.slice(0, Math.max(0, w - 8))

  c.put(x, y, `┌─${label}${'─'.repeat(Math.max(0, w - label.length - 6))} × ┐`, tone)
  c.put(x, y + h - 1, `└${'─'.repeat(w - 2)}┘`, tone)

  for (let j = 1; j < h - 1; j++) {
    c.set(x, y + j, '│', tone)
    c.set(x + w - 1, y + j, '│', tone)
  }
}

export function windows(frame: SplashFrame): SplashCells {
  const title = (frame.title ?? 'HERMES AGENT').toUpperCase()
  const markW = wordmarkWidth(title)

  if (!fits(frame, 72) || markW + 10 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const tagline = (frame.tagline ?? 'THE AGENT THAT GROWS WITH YOU').toUpperCase()
  const c = new Canvas(w, h)

  // Desktop: a faint dot grid.
  for (let y = 2; y < h - 1; y += 2) {
    for (let x = 2; x < w - 1; x += 4) {
      c.set(x, y, '·', RAY)
    }
  }

  for (const win of WINDOWS) {
    const age = t - win.born

    if (age <= 0) {
      continue
    }

    const pop = easeOutBack(span(age, 0, 240))
    const fw = Math.max(14, Math.round(win.w * w))
    const fh = Math.max(5, Math.round(win.h * (h - 2)))
    const ww = Math.max(6, Math.round(fw * pop))
    const wh = Math.max(3, Math.round(fh * pop))
    const x = Math.round(win.x * w + (fw - ww) / 2)
    const y = 1 + Math.round(win.y * (h - 2) + (fh - wh) / 2)

    frameBox(c, x, y, ww, wh, win.title, BG_PAPER, INK)

    if (pop > 0.95 && wh > 2 && ww > 4) {
      win.body(c, x + 2, y + 1, ww - 4, wh - 2, age - 240, t)
    }
  }

  // The headline window: inverted, centred, last to open, always on top.
  const age = t - 1450

  if (age > 0) {
    const pop = easeOutBack(span(age, 0, 300))
    const rows = Math.max(5, Math.min(8, Math.round(h * 0.2)))
    const fw = markW + 8
    const fh = rows + 5
    const ww = Math.max(6, Math.round(fw * pop))
    const wh = Math.max(3, Math.round(fh * pop))
    const x = Math.floor((w - ww) / 2)
    const y = Math.floor((h - wh) / 2)

    frameBox(c, x, y, ww, wh, 'hermes · agent', BG_INK, PAPER)

    if (pop > 0.95) {
      const lines = renderWordmark(title, rows)
      const cut = Math.round(markW * easeOut(span(age, 300, 750)))

      lines.forEach((line, k) => c.put(x + 4, y + 2 + k, line.slice(0, cut), PAPER))
      c.put(
        x + Math.floor((ww - tagline.length) / 2),
        y + rows + 3,
        typed(tagline, span(age, 600, 950)).slice(0, ww - 4),
        PAPER
      )
    }
  }

  void ACCENT
  chrome(c, frame)

  return c.cells(frame.palette ?? TERN_SPLASH_PALETTE, bloom(frame, w, h))
}
