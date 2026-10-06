// The launch splash's shell on Tern: it owns the clock, the skip, the 15 s
// cap and the hand-off, and nothing about the picture. It draws on its own
// `screen` surface, above the session chrome, and closes it when done.

import type { Palette } from '@stencil-hq/tern'

import { splashNode } from '../view/splash.js'

import {
  DEFAULT_SPLASH_DESIGN,
  renderSplashFrame,
  SPLASH_DESIGN_NAMES,
  SPLASH_EXIT_MS,
  SPLASH_INTRO_MS,
  SPLASH_TICK_MS,
  type SplashCells,
  type SplashPalette,
  splashStylesheet,
  TERN_SPLASH_PALETTE
} from './index.js'

/** Never hold the app hostage: past this the splash hands over whatever the gateway is doing. */
export const SPLASH_MAX_MS = 15_000

/** What `HERMES_TUI_SPLASH` asks for. */
export interface SplashSetting {
  enabled: boolean
  /** A design name, `random`, or '' for the default. */
  design: string
}

/**
 * Reads `HERMES_TUI_SPLASH`: `0`/`false`/`off`/`no` disables the splash, a
 * design name picks one, `random` picks per launch, anything else (or unset)
 * is the default. A launch that already carries a prompt skips it.
 */
export function splashSetting(env: Readonly<Record<string, string | undefined>> = process.env): SplashSetting {
  const raw = (env.HERMES_TUI_SPLASH ?? '').trim().toLowerCase()
  const off = /^(?:0|false|no|off)$/.test(raw)
  const on = /^(?:1|true|yes|on)$/.test(raw)
  const prompted = Boolean(env.HERMES_TUI_QUERY?.trim())

  return { design: off || on ? '' : raw, enabled: !off && !prompted }
}

/** Resolves a `HERMES_TUI_SPLASH` design value to a design name. */
export function pickSplashDesign(setting: string, random: () => number = Math.random): string {
  if (setting === 'random') {
    return SPLASH_DESIGN_NAMES[Math.floor(random() * SPLASH_DESIGN_NAMES.length)]!
  }

  return SPLASH_DESIGN_NAMES.includes(setting) ? setting : DEFAULT_SPLASH_DESIGN
}

// A screen surface is inset from the pane: Tern pads the region 16px a side
// (two cells at the default 8px cell) and 6px top and bottom. Draw inside it,
// or the last columns clip and the last row scrolls.
const INSET_COLS = 4
const INSET_ROWS = 2

/** The cells a splash may fill in a pane of `cols` × `rows`. */
export const splashInsets = (cols: number, rows: number) => ({
  cols: Math.max(1, cols - INSET_COLS),
  rows: Math.max(1, rows - INSET_ROWS)
})

/** The part of a Tern surface the splash uses. */
export interface SplashSurface {
  readonly closed: boolean
  render(view: ReturnType<typeof splashNode>): void
  palette(palette: Palette): void
  stylesheet(name: string, css: string | null): void
  close(options?: { keep?: boolean }): unknown
}

export interface LaunchSplashOptions {
  /** Opens the surface the splash draws on. */
  open: () => SplashSurface
  /** The cells the splash may fill. */
  size: () => { cols: number; rows: number }
  /** A design name (see `SPLASH_DESIGN_NAMES`). */
  design: string
  /** Called once, after the splash's surface is closed. */
  onDone: () => void
  /** The program palette to start with (the skin's, once one is known). */
  palette?: Palette
  /** Which palette token carries each splash colour. */
  tokens?: SplashPalette
  status?: string
  now?: () => number
  setInterval?: (fn: () => void, ms: number) => unknown
  clearInterval?: (handle: unknown) => void
}

/** Plays one design until the app is ready (or a key, or the cap), then dissolves and hands off. */
export class LaunchSplash {
  readonly design: string
  status: string
  readonly #options: LaunchSplashOptions
  readonly #now: () => number
  readonly #tokens: SplashPalette
  #surface: SplashSurface | undefined
  #timer: unknown
  #startedAt = 0
  #exitAt: number | null = null
  #ready = false
  #skipped = false
  #done = false

  constructor(options: LaunchSplashOptions) {
    this.#options = options
    this.#now = options.now ?? (() => performance.now())
    this.#tokens = options.tokens ?? TERN_SPLASH_PALETTE
    this.design = options.design
    this.status = options.status ?? ''
  }

  /** Whether the splash still owns the pane (and the keys). */
  get active(): boolean {
    return this.#surface !== undefined && !this.#done
  }

  start() {
    if (this.#surface || this.#done) {
      return
    }

    this.#surface = this.#options.open()
    this.#surface.stylesheet('splash', splashStylesheet(this.#tokens))

    if (this.#options.palette) {
      this.#surface.palette(this.#options.palette)
    }

    this.#startedAt = this.#now()
    this.#timer = (this.#options.setInterval ?? setInterval)(() => this.tick(), SPLASH_TICK_MS)
    this.tick()
  }

  /** Startup work is finished: play out the intro, then leave. */
  ready() {
    this.#ready = true
  }

  /** Any key: leave now. */
  skip() {
    this.#skipped = true
  }

  /** A skin arrived or changed: the next frame is drawn in it. */
  palette(palette: Palette) {
    if (this.active) {
      this.#surface!.palette(palette)
    }
  }

  /** The frame for the current instant. */
  frame(): SplashCells {
    const t = this.#now()
    const { cols, rows } = this.#options.size()

    return renderSplashFrame({
      design: this.design,
      elapsedMs: t - this.#startedAt,
      exitMs: this.#exitAt === null ? undefined : t - this.#exitAt,
      height: rows,
      palette: this.#tokens,
      status: this.status,
      width: cols
    })
  }

  /** One step of the clock: decide whether to leave, then draw or hand off. */
  tick() {
    if (!this.active) {
      return
    }

    const t = this.#now()
    const elapsed = t - this.#startedAt

    if (
      this.#exitAt === null &&
      (this.#skipped || elapsed >= SPLASH_MAX_MS || (this.#ready && elapsed >= SPLASH_INTRO_MS))
    ) {
      this.#exitAt = t
    }

    if (this.#surface!.closed || (this.#exitAt !== null && t - this.#exitAt >= SPLASH_EXIT_MS)) {
      return this.#finish()
    }

    this.#surface!.render(splashNode(this.frame()))
  }

  #finish() {
    this.#done = true
    ;(this.#options.clearInterval ?? (h => clearInterval(h as NodeJS.Timeout)))(this.#timer)

    if (!this.#surface!.closed) {
      void this.#surface!.close({ keep: false })
    }

    this.#options.onDone()
  }
}
