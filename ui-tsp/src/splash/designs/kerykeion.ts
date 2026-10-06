// "Kerykeion" — the herald's staff.
//
// A lit, slowly turning double helix of serpents under a pair of wings,
// printed as a two-ink halftone on ultramarine paper the way
// nousresearch.com prints its statuary. Every tone comes from ordered (Bayer)
// dithering at braille sub-cell resolution: off-white ink for lights, navy
// ink for shadows, bare paper for midtones.

import {
  ACCENT,
  bayer,
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
  RAY,
  SHADE,
  span,
  type SplashCells,
  type SplashFrame,
  TAU,
  typed,
  wordmark
} from '../canvas.js'
import { TERN_SPLASH_PALETTE } from '../theme.js'
import { wordmarkWidth } from '../wordmark.js'

const MAX_FIGURE_ROWS = 38

// Braille dot bit for sub-cell (col 0-1, row 0-3).
const DOT = [0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80]

// ── Scene ────────────────────────────────────────────────────────────────
// Figure space: origin at the figure's centre, y down, the staff spans
// v ∈ [-0.5, 0.5]. One unit = the figure's height in braille dots.

interface Pose {
  /** Dots per figure unit. */
  scale: number
  staff: number
  orb: number
  grow: number
  wing: number
  rot: number
  lx: number
  lz: number
}

const ORB_V = -0.432
const ORB_R = 0.052
const STAFF_TOP = -0.38
const STAFF_BOT = 0.5
const SNAKE_TOP = -0.2
const SNAKE_BOT = 0.47
const SNAKE_TURNS = 1.5
const WING_ROOT_V = -0.3
const FEATHERS = 6
const RAY_V = -0.04
const RAY_COUNT = 48

// Sample result packed into two module-level slots to keep the per-dot loop
// allocation-free: `hit` 0 = miss, 1 = body, 2 = knockout outline.
let sLum = 0

const tubeLum = (s: number, depth: number, lx: number, lz: number) => {
  const nz = Math.sqrt(Math.max(0, 1 - s * s))

  return (s * lx + nz * lz) * 0.9 + 0.25 + depth * 0.35
}

function sampleFigure(u: number, v: number, p: Pose): number {
  const px = 1 / p.scale
  const outline = 1.15 * px
  let best = 0
  let bestZ = -9
  let lum = 0

  // Orb — a lit sphere crowning the staff.
  if (p.orb > 0) {
    const r = Math.max(ORB_R * p.orb, 1.6 * px)
    const dx = u
    const dy = v - ORB_V
    const d2 = dx * dx + dy * dy

    if (d2 < (r + outline) ** 2) {
      if (d2 < r * r) {
        const nx = dx / r
        const ny = dy / r
        const nz = Math.sqrt(Math.max(0, 1 - nx * nx - ny * ny))

        lum = (nx * p.lx - ny * 0.45 + nz * p.lz) * 1.3 - 0.1
        best = 1
      } else {
        best = 2
      }

      bestZ = 5
    }
  }

  // Wings — a mirrored fan of tapered, drooping feathers. Earlier (upper)
  // feathers overlap later ones.
  if (bestZ < 4 && p.wing > 0 && v < 0.02 && v > -0.62) {
    const au = Math.abs(u)
    const lx = u < 0 ? -p.lx : p.lx

    for (let j = 0; j < FEATHERS; j++) {
      const f = easeOut(clamp01(p.wing * 1.7 - j * 0.1))

      if (f <= 0) {
        continue
      }

      const target = ((34 - j * 14.4) * Math.PI) / 180
      const ang = -1.4 + (target + 1.4) * f
      const len = (0.5 - j * 0.06) * (0.25 + 0.75 * f)
      const x0 = 0.012
      const y0 = WING_ROOT_V + j * 0.013
      const droop = 0.3
      const xm = x0 + Math.cos(ang) * len * 0.55
      const ym = y0 - Math.sin(ang) * len * 0.55
      const x1 = xm + Math.cos(ang - droop) * len * 0.45
      const y1 = ym - Math.sin(ang - droop) * len * 0.45
      let hit = 0

      for (let seg = 0; seg < 2 && !hit; seg++) {
        const ax = seg ? xm : x0
        const ay = seg ? ym : y0
        const bx = seg ? x1 : xm
        const by = seg ? y1 : ym
        const ex = bx - ax
        const ey = by - ay
        const t = clamp01(((au - ax) * ex + (v - ay) * ey) / (ex * ex + ey * ey))
        const cx = au - (ax + ex * t)
        const cy = v - (ay + ey * t)
        const along = seg ? 0.55 + 0.45 * t : 0.55 * t
        const r = Math.max(0.042 - 0.03 * along, 1.25 * px)
        const d = Math.hypot(cx, cy)

        if (d < r + outline) {
          if (d < r) {
            // Lit from above: the lower flank of each feather falls into shadow.
            const side = (ex * cy - ey * cx) / (Math.hypot(ex, ey) * r)

            lum = 0.85 - 1.2 * Math.max(0, side) ** 1.5 - j * 0.03 + lx * 0.15
            hit = 1
          } else {
            hit = 2
          }
        }
      }

      if (hit) {
        best = hit
        bestZ = 4

        break
      }
    }
  }

  if (bestZ >= 4) {
    sLum = lum > 0 ? lum + clamp01((110 - p.scale) / 70) * 0.45 : lum

    return best
  }

  // Staff — z = 0, so each serpent passes in front of it and behind it.
  if (p.staff > 0 && v > STAFF_TOP && v < STAFF_TOP + (STAFF_BOT - STAFF_TOP) * p.staff) {
    const taper = clamp01((STAFF_BOT - v) / 0.05)
    const r = Math.max(0.013 * (0.35 + 0.65 * taper), 0.75 * px)
    const d = Math.abs(u)

    if (d < r + outline) {
      best = d < r ? 1 : 2
      bestZ = 0
      lum = tubeLum(u / r, 0, p.lx, p.lz) + 0.1
    }
  }

  // Serpents — two strands of a helix around the staff, 180° apart.
  if (p.grow > 0 && v > SNAKE_TOP - 0.05 && v < SNAKE_BOT + 0.02) {
    const h = clamp01((SNAKE_BOT - v) / (SNAKE_BOT - SNAKE_TOP))

    if (h <= p.grow) {
      const amp = 0.04 + 0.14 * h ** 0.75 * (1 - 0.5 * clamp01((h - 0.86) / 0.14))
      const theta = TAU * SNAKE_TURNS * h + p.rot
      // Head swells at the growing tip; body tapers to the tail.
      const head = clamp01(1 - (p.grow - h) / 0.07)
      const r = Math.max((0.02 + 0.016 * h) * (1 + 0.45 * head), 1.05 * px)
      const dTheta = (TAU * SNAKE_TURNS) / (SNAKE_BOT - SNAKE_TOP)

      for (let k = 0; k < 2; k++) {
        const th = theta + k * Math.PI
        const sx = amp * Math.sin(th)
        const z = Math.cos(th)
        // Perpendicular distance ≈ horizontal distance foreshortened by slope.
        const slope = amp * Math.cos(th) * dTheta
        const d = Math.abs(u - sx) / Math.sqrt(1 + slope * slope)

        if (d < r + outline) {
          const zz = z * amp

          if (!best || zz > bestZ) {
            best = d < r ? 1 : 2
            bestZ = zz
            lum = tubeLum((u - sx) / Math.sqrt(1 + slope * slope) / r, z, p.lx, p.lz)
          }
        }
      }
    }
  }

  // Small figures have no room for halftone: push lit surfaces toward solid.
  sLum = lum > 0 ? lum + clamp01((110 - p.scale) / 70) * 0.45 : lum

  return best
}

/** Engraved sunburst behind the figure. Returns 1 where a ray is inked. */
function sampleRays(u: number, v: number, scale: number, reach: number, t: number): number {
  if (reach <= 0) {
    return 0
  }

  const dy = v - RAY_V
  const r = Math.hypot(u, dy)

  if (r < 0.33 || r > 0.62) {
    return 0
  }

  const a = (Math.atan2(dy, u) / TAU + 1) * RAY_COUNT
  const i = Math.round(a)
  const idx = ((i % RAY_COUNT) + RAY_COUNT) % RAY_COUNT
  // Arc-length distance to the ray's centre line, in dots.
  const off = Math.abs(a - i) * (TAU / RAY_COUNT) * r * scale

  if (off > 0.62) {
    return 0
  }

  const breathe = 0.035 * Math.sin(t * 0.0021 + idx * 2.399)
  const long = idx & 1 ? 0.6 : 0.54
  const inner = idx & 1 ? 0.34 : 0.4
  const outer = inner + (long - inner + breathe) * reach

  return r > inner && r < outer ? 1 : 0
}

export function kerykeion(frame: SplashFrame): SplashCells {
  const title = frame.title ?? 'HERMES AGENT'

  if (!fits(frame) || wordmarkWidth(title) + 4 > frame.width) {
    return compact(frame)
  }

  const w = Math.floor(frame.width)
  const h = Math.floor(frame.height)
  const t = Math.max(0, frame.elapsedMs)
  const tagline = (frame.tagline ?? 'THE AGENT THAT GROWS WITH YOU').toUpperCase()
  const c = new Canvas(w, h)

  // ── layout ──
  const markRows = Math.max(5, Math.min(9, Math.round(h * 0.2)))
  // Cap the figure so a huge terminal doesn't pay for a huge halftone pass.
  const figRows = Math.min(MAX_FIGURE_ROWS, h - markRows - 5)
  const figTop = 1 + Math.floor((h - markRows - 5 - figRows) / 2)
  const markTop = figTop + figRows + 1

  // ── halftone pass ──
  const scale = figRows * 4
  const cxDot = w
  const cyDot = (figTop + figRows / 2) * 4
  const sweep = t * 0.00075

  const pose: Pose = {
    grow: easeInOut(span(t, 450, 1550)),
    lx: Math.sin(sweep) * 0.62,
    lz: 0.62 + 0.12 * Math.cos(sweep),
    orb: easeOut(span(t, 120, 520)),
    rot: t * 0.00105 + 2.6 * (1 - easeOut(span(t, 300, 1900))),
    scale,
    staff: easeOut(span(t, 200, 820)),
    wing: span(t, 1000, 1750)
  }

  const reach = easeOut(span(t, 1250, 2100))
  const grainSeed = Math.floor(t / 140)
  const lastFigRow = Math.min(h - 1, markTop - 1)

  for (let cy = 0; cy <= lastFigRow; cy++) {
    for (let cx = 0; cx < w; cx++) {
      let lightBits = 0
      let darkBits = 0
      let lights = 0
      let darks = 0
      let body = 0

      for (let sub = 0; sub < 8; sub++) {
        const dx = cx * 2 + (sub & 1)
        const dy = cy * 4 + (sub >> 1)
        const u = (dx + 0.5 - cxDot) / scale
        const v = (dy + 0.5 - cyDot) / scale

        if (!(u > -0.66 && u < 0.66 && v > -0.68 && v < 0.6)) {
          continue
        }

        const hit = sampleFigure(u, v, pose)

        if (hit === 1) {
          const th = bayer(dx, dy)

          if (sLum > 0 && sLum * 1.05 > th) {
            lightBits |= DOT[sub]!
            lights++
            body++
          } else if (sLum < 0 && -sLum * 0.9 > th) {
            darkBits |= DOT[sub]!
            darks++
          }
        } else if (hit === 0 && sampleRays(u, v, scale, reach, t)) {
          lightBits |= DOT[sub]!
          lights++
        }
      }

      if (!lights && !darks) {
        // Paper grain: a few shadow-ink specks, reshuffled ~7×/s.
        const g = hash(cx, cy, grainSeed)

        if (g < 0.09) {
          darkBits = DOT[Math.floor(g * 88.8)]!
          darks = 1
        }
      }

      if (lights || darks) {
        const light = lights >= darks

        c.set(cx, cy, String.fromCharCode(0x2800 | (light ? lightBits : darkBits)), light ? (body ? INK : RAY) : SHADE)
      }
    }
  }

  // The orb is the one accent-coloured object in the scene.
  const orbRow = Math.floor((cyDot + ORB_V * scale) / 4)
  const orbHalf = Math.ceil((ORB_R * scale) / 2)

  for (let cy = orbRow - 1; cy <= orbRow + 1; cy++) {
    for (let cx = Math.floor(w / 2) - orbHalf; cx < Math.floor(w / 2) + orbHalf; cx++) {
      const i = cy * w + cx

      if (cy >= 0 && cy < h && cx >= 0 && cx < w && c.fg[i] === INK) {
        const u = (cx * 2 + 1 - cxDot) / scale
        const v = (cy * 4 + 2 - cyDot) / scale - ORB_V

        if (u * u + v * v < (ORB_R * 1.25) ** 2) {
          c.fg[i] = ACCENT
        }
      }
    }
  }

  // The wordmark grows from a squat seed to full height.
  wordmark(c, title, markTop, markRows, easeOut(span(t, 1450, 2200)), easeOut(span(t, 1450, 1850)))
  c.put(Math.floor((w - tagline.length) / 2), markTop + markRows + 1, typed(tagline, span(t, 1900, 2350)), DIM)
  chrome(c, frame)

  return c.cells(frame.palette ?? TERN_SPLASH_PALETTE, bloom(frame, w, h))
}
