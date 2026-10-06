// Shared drawing layer for the launch-splash designs: a cell buffer with
// foreground/background tones, a braille dot layer for sub-cell drawing, the
// cells → segments pass that hands a frame to the Tern view, and the handful
// of easing/noise helpers every design reaches for. Designs stay pure
// functions of (size, time, palette) and know nothing of Tern or ANSI.

import { type SplashPalette, TERN_SPLASH_PALETTE } from './theme.js'
import { renderWordmark, WORDMARK_MIN_ROWS } from './wordmark.js'

/** One run of cells in one ink: `s` is a span token; none means the segment's base ink. */
export interface SplashSpan {
  t: string
  s?: string
}

export type SplashGround = 'ink' | 'none' | 'paper' | 'shade'
export type SplashBase = 'none' | 'paper' | 'shade'

/** A run of cells on one ground. `base` is the ground colour its un-tokened spans are inked in. */
export interface SplashSegment {
  ground: SplashGround
  base: SplashBase
  spans: SplashSpan[]
}

/** A frame: rows of segments, each row exactly the frame's width in cells. */
export type SplashCells = SplashSegment[][]

export interface SplashFrame {
  width: number
  height: number
  /** Milliseconds since the splash mounted. */
  elapsedMs: number
  /** Milliseconds since the exit dissolve began; omit while loading. */
  exitMs?: number
  /** Live loader line, e.g. "connecting gateway". */
  status?: string
  /** Which Tern palette token carries each of the six colours. */
  palette?: SplashPalette
  title?: string
  tagline?: string
  /** Which design to draw; see SPLASH_DESIGNS. */
  design?: string
}

export const SPLASH_INTRO_MS = 2400
export const SPLASH_EXIT_MS = 460
export const SPLASH_TICK_MS = 40

export const TAU = Math.PI * 2
export const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v)
export const span = (t: number, a: number, b: number) => clamp01((t - a) / (b - a))
export const easeOut = (t: number) => 1 - (1 - t) ** 3
export const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)
export const easeOutBack = (t: number) => 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t

// 4×4 Bayer matrix, normalised to thresholds in (0,1).
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16)
export const bayer = (x: number, y: number) => BAYER[(y & 3) * 4 + (x & 3)]!

export const hash = (x: number, y: number, s = 0) => {
  let h = Math.imul(x, 374761393) + Math.imul(y, 668265263) + Math.imul(s, 2147483647)

  h = Math.imul(h ^ (h >>> 13), 1274126177)

  return ((h ^ (h >>> 16)) >>> 0) / 4294967296
}

// Foreground tones.
export const INK = 1
export const SHADE = 2
export const ACCENT = 3
export const DIM = 4
export const RAY = 5
/** Paper-coloured ink, for drawing on an inverted (ink) ground. */
export const PAPER = 6

// Background grounds.
export const BG_PAPER = 1
export const BG_INK = 2
export const BG_SHADE = 3

const GROUNDS: SplashGround[] = ['none', 'paper', 'ink', 'shade']

export class Canvas {
  readonly glyph: string[]
  readonly fg: Uint8Array
  readonly bg: Uint8Array

  constructor(
    readonly w: number,
    readonly h: number,
    ground = BG_PAPER
  ) {
    this.glyph = new Array<string>(w * h).fill(' ')
    this.fg = new Uint8Array(w * h)
    this.bg = new Uint8Array(w * h).fill(ground)
  }

  set(x: number, y: number, ch: string, tone: number) {
    if (x >= 0 && x < this.w && y >= 0 && y < this.h) {
      this.glyph[y * this.w + x] = ch
      this.fg[y * this.w + x] = tone
    }
  }

  /** Write text; spaces are transparent unless `opaque`. */
  put(x: number, y: number, text: string, tone: number, opaque = false) {
    let cx = Math.round(x)
    const cy = Math.round(y)

    for (const ch of text) {
      if (ch !== ' ' || opaque) {
        this.set(cx, cy, ch, tone)
      }

      cx++
    }
  }

  center(y: number, text: string, tone: number) {
    this.put(Math.floor((this.w - text.length) / 2), y, text, tone)
  }

  ground(x0: number, y0: number, x1: number, y1: number, ground: number) {
    for (let y = Math.max(0, y0); y <= Math.min(this.h - 1, y1); y++) {
      for (let x = Math.max(0, x0); x <= Math.min(this.w - 1, x1); x++) {
        this.bg[y * this.w + x] = ground
      }
    }
  }

  clear(x0: number, y0: number, x1: number, y1: number) {
    for (let y = Math.max(0, y0); y <= Math.min(this.h - 1, y1); y++) {
      for (let x = Math.max(0, x0); x <= Math.min(this.w - 1, x1); x++) {
        this.glyph[y * this.w + x] = ' '
        this.fg[y * this.w + x] = 0
      }
    }
  }

  /**
   * The frame as rows of segments. Cells where `visible` is false are bare
   * pane — that is how every design blooms in and dissolves out. Geometry
   * (text, grounds, base inks) never depends on `pal`; only span tokens do.
   */
  cells(pal: SplashPalette, visible?: (x: number, y: number) => boolean): SplashCells {
    const token = ['', pal.ink, '', pal.accent, pal.dim, pal.ray, '']
    const rows: SplashCells = []

    for (let y = 0; y < this.h; y++) {
      const row: SplashSegment[] = []
      let seg: SplashSegment | undefined
      let span: SplashSpan | undefined

      for (let x = 0; x < this.w; x++) {
        const i = y * this.w + x
        const ground = GROUNDS[visible && !visible(x, y) ? 0 : this.bg[i]!]!
        const blank = ground === 'none' || this.glyph[i] === ' ' || this.fg[i] === 0
        const tone = blank ? 0 : this.fg[i]!
        // A ground-coloured ink (shade or paper used as ink) is the segment's base ink.
        const base: SplashBase | undefined = tone === SHADE ? 'shade' : tone === PAPER ? 'paper' : undefined

        if (!seg || seg.ground !== ground || (base && seg.base !== 'none' && seg.base !== base)) {
          seg = { base: 'none', ground, spans: [] }
          row.push(seg)
          span = undefined
        }

        if (base) {
          seg.base = base
        }

        // Blanks ride along with whatever span is open; only a visible ink changes it.
        const s = blank ? span?.s : token[tone] || undefined

        if (!span || span.s !== s) {
          span = s ? { s, t: '' } : { t: '' }
          seg.spans.push(span)
        }

        span.t += blank ? ' ' : this.glyph[i]
      }

      rows.push(row)
    }

    return rows
  }
}

// Braille dot bit for sub-cell (col 0-1, row 0-3).
const DOT = [0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80]

/** A 2×4-per-cell dot layer; each dot carries a tone. */
export class Dots {
  readonly w: number
  readonly h: number
  readonly data: Uint8Array

  constructor(
    readonly cols: number,
    readonly rows: number
  ) {
    this.w = cols * 2
    this.h = rows * 4
    this.data = new Uint8Array(this.w * this.h)
  }

  set(x: number, y: number, tone: number) {
    const ix = Math.floor(x)
    const iy = Math.floor(y)

    if (ix >= 0 && ix < this.w && iy >= 0 && iy < this.h) {
      this.data[iy * this.w + ix] = tone
    }
  }

  line(x0: number, y0: number, x1: number, y1: number, tone: number) {
    const steps = Math.max(1, Math.ceil(Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0))))

    for (let i = 0; i <= steps; i++) {
      this.set(x0 + ((x1 - x0) * i) / steps, y0 + ((y1 - y0) * i) / steps, tone)
    }
  }

  /** Composite onto the canvas; each cell takes its most common tone. */
  flush(c: Canvas, ox = 0, oy = 0) {
    const tally = [0, 0, 0, 0, 0, 0, 0]

    for (let cy = 0; cy < this.rows; cy++) {
      for (let cx = 0; cx < this.cols; cx++) {
        tally.fill(0)
        let any = false

        for (let sub = 0; sub < 8; sub++) {
          const tone = this.data[(cy * 4 + (sub >> 1)) * this.w + cx * 2 + (sub & 1)]!

          if (tone) {
            tally[tone]!++
            any = true
          }
        }

        if (!any) {
          continue
        }

        let best = 1

        for (let k = 2; k < tally.length; k++) {
          if (tally[k]! > tally[best]!) {
            best = k
          }
        }

        let bits = 0

        for (let sub = 0; sub < 8; sub++) {
          if (this.data[(cy * 4 + (sub >> 1)) * this.w + cx * 2 + (sub & 1)] === best) {
            bits |= DOT[sub]!
          }
        }

        c.set(ox + cx, oy + cy, String.fromCharCode(0x2800 | bits), best)
      }
    }
  }
}

// ── shared scene furniture ───────────────────────────────────────────────

export const typed = (text: string, p: number) => text.slice(0, Math.round(text.length * clamp01(p)))

/** Halftone bloom from the centre on entry, and back out on exit. */
export function bloom(frame: SplashFrame, w: number, h: number): (x: number, y: number) => boolean {
  const exit = frame.exitMs === undefined ? 0 : easeInOut(clamp01(frame.exitMs / SPLASH_EXIT_MS))
  const p = easeOut(span(frame.elapsedMs, 0, 420)) * (1 - exit)
  const maxR = Math.hypot(w / 2, h)

  if (p >= 1) {
    return () => true
  }

  return (x, y) => p * 1.9 - (Math.hypot(x - w / 2, (y - h / 2) * 2) / maxR) * 0.9 > bayer(x, y)
}

/** Sparse shadow-ink specks on empty paper cells, reshuffled ~7×/s. */
export function grain(c: Canvas, t: number, density = 0.09) {
  const seed = Math.floor(t / 140)

  for (let y = 0; y < c.h; y++) {
    for (let x = 0; x < c.w; x++) {
      const i = y * c.w + x

      if (c.glyph[i] === ' ' && c.bg[i] === BG_PAPER) {
        const g = hash(x, y, seed)

        if (g < density) {
          c.glyph[i] = String.fromCharCode(0x2800 | DOT[Math.floor((g / density) * 7.99)]!)
          c.fg[i] = SHADE
        }
      }
    }
  }
}

// Glyphs: Tern draws surface text in the pane's font at a fixed advance, but
// only for what that font holds. Stay within ASCII, box drawing, block
// elements, braille and the few marks below; a fallback glyph (●, ◆, ▪, ▮)
// is wider or narrower and shears its whole row. `SPLASH_GLYPHS` is tested.
export const SPLASH_GLYPHS = /^[\x20-\x7e\u2500-\u259f\u2800-\u28ff·•×…■]*$/u

/** Loader line (bottom-left), skip hint (bottom-right) and corner labels. */
export function chrome(c: Canvas, frame: SplashFrame, opts: { tone?: number; dim?: number; labels?: boolean } = {}) {
  const t = frame.elapsedMs
  const tone = opts.tone ?? INK
  const dim = opts.dim ?? DIM
  const { h, w } = c

  if (h >= 3) {
    const status = (frame.status ?? '').toUpperCase().slice(0, Math.max(0, w - 8))

    if (status) {
      c.clear(1, h - 1, 5 + status.length, h - 1)
      c.put(2, h - 1, Math.floor(t / 420) % 2 === 0 ? '■' : '·', opts.tone === PAPER ? PAPER : ACCENT)
      c.put(4, h - 1, status, tone)
    }

    const hint = 'ANY KEY TO SKIP'

    if (status.length + hint.length + 10 <= w) {
      const shown = typed(hint, span(t, 900, 1300))

      c.clear(w - 3 - shown.length, h - 1, w - 2, h - 1)
      c.put(w - 2 - hint.length, h - 1, shown, dim)
    }
  }

  if (opts.labels !== false && h >= 8 && w >= 56) {
    const left = typed('NOUS RESEARCH', span(t, 250, 700))
    const right = typed('OPEN SOURCE ■ MIT LICENSE', span(t, 250, 700))

    c.clear(1, 0, 3 + left.length, 0)
    c.put(2, 0, left, dim)
    c.clear(w - 3 - right.length, 0, w - 2, 0)
    c.put(w - 2 - right.length, 0, right, dim)
  }
}

/**
 * Draw the box-drawing wordmark centred on `cx`, growing from a squat seed to
 * `rows` tall as `growth` runs 0→1 and wiping in left→right with `wipe`.
 * Returns its bounding box so a design can knock a hole for it.
 */
export function wordmark(
  c: Canvas,
  title: string,
  top: number,
  rows: number,
  growth: number,
  wipe: number,
  tone = INK,
  cx = c.w / 2
) {
  const full = Math.max(WORDMARK_MIN_ROWS, rows)
  const cur = Math.round(lerp(WORDMARK_MIN_ROWS, full, clamp01(growth)))
  const lines = renderWordmark(title, cur)
  const width = lines[0]!.length
  const x = Math.floor(cx - width / 2)
  const y = top + Math.floor((full - cur) / 2)
  const cut = Math.round(width * clamp01(wipe))

  if (growth > 0 || wipe > 0) {
    lines.forEach((line, i) => c.put(x, y + i, line.slice(0, cut), tone))
  }

  return { height: full, width, x, y: top }
}

/** Letterspaced fallback for terminals too small for a scene. */
export function compact(frame: SplashFrame, ground = BG_PAPER, tone = INK, dim = DIM): SplashCells {
  const w = Math.max(1, Math.floor(frame.width))
  const h = Math.max(1, Math.floor(frame.height))
  const t = frame.elapsedMs
  const c = new Canvas(w, h, ground)
  const title = (frame.title ?? 'HERMES AGENT').toUpperCase()
  const tagline = (frame.tagline ?? 'THE AGENT THAT GROWS WITH YOU').toUpperCase()
  const spaced = title.split('').join(' ')
  const text = spaced.length + 2 <= w ? spaced : title.slice(0, w)
  const y = Math.max(0, Math.floor(h / 2) - 1)

  c.center(y, typed(text, span(t, 150, 900)), tone)

  if (h >= 5 && tagline.length + 2 <= w) {
    c.center(y + 2, typed(tagline, span(t, 700, 1400)), dim)
  }

  chrome(c, frame, { dim, labels: false, tone })

  return c.cells(frame.palette ?? TERN_SPLASH_PALETTE, bloom(frame, w, h))
}

export const fits = (frame: SplashFrame, cols = 56, rows = 20) => frame.width >= cols && frame.height >= rows
