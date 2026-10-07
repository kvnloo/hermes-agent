import { EventEmitter } from 'node:events'

import type { Palette, Session, Surface } from '@stencil-hq/tern'
import type { GatewayClient } from '@tui/gatewayClient.js'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { paletteOf, programPaletteOf } from '../palette.js'
import {
  DEFAULT_SPLASH_DESIGN,
  renderSplashFrame,
  segmentRole,
  SPLASH_DESIGN_NAMES,
  SPLASH_EXIT_MS,
  SPLASH_GLYPHS,
  SPLASH_INTRO_MS,
  SPLASH_ROLE,
  SPLASH_TICK_MS,
  type SplashCells,
  type SplashPalette,
  splashStylesheet,
  TERN_SPLASH_PALETTE
} from '../splash/index.js'
import {
  LaunchSplash,
  pickSplashDesign,
  SPLASH_MAX_MS,
  splashInsets,
  splashSetting,
  type SplashSurface,
  splashTickMs
} from '../splash/launch.js'
import { renderWordmark, WORDMARK_MIN_ROWS, wordmarkWidth } from '../splash/wordmark.js'
import { splashNode } from '../view/splash.js'

const SWAPPED: SplashPalette = {
  accent: 'tokAccent',
  dim: 'tokDim',
  ink: 'tokInk',
  ray: 'tokRay',
  shade: 'ins'
}

const frame = (design: string, width: number, height: number, elapsedMs: number, extra = {}) =>
  renderSplashFrame({ design, elapsedMs, height, width, ...extra })

const rowText = (row: SplashCells[number]) => row.flatMap(seg => seg.spans.map(sp => sp.t)).join('')
const text = (cells: SplashCells) => cells.map(rowText).join('\n')

/** Everything about a frame but its colour tokens. */
const geometry = (cells: SplashCells) =>
  cells.map(row => row.map(seg => ({ base: seg.base, ground: seg.ground, runs: seg.spans.map(sp => sp.t) })))

const tokens = (cells: SplashCells) =>
  new Set(cells.flatMap(row => row.flatMap(seg => seg.spans.flatMap(sp => (sp.s ? [sp.s] : [])))))

describe.each(SPLASH_DESIGN_NAMES)('splash design %s', design => {
  it.each([
    [80, 24],
    [156, 43],
    [240, 58],
    [56, 20],
    [40, 10],
    [12, 3],
    [1, 1]
  ])('fills exactly %dx%d cells at every stage', (w, h) => {
    for (const t of [0, 200, 900, 1600, SPLASH_INTRO_MS, 9000]) {
      const cells = frame(design, w, h, t, { status: 'summoning hermes…' })

      expect(cells).toHaveLength(h)

      for (const row of cells) {
        expect([...rowText(row)]).toHaveLength(w)
      }
    }
  })

  it('returns the same cells for a fixed size and elapsed time', () => {
    expect(frame(design, 100, 30, 1234)).toEqual(frame(design, 100, 30, 1234))
  })

  it('carries colour as palette tokens, never as escape codes', () => {
    const cells = frame(design, 100, 30, 3000, { status: 'loading skills' })

    const allowed = new Set([
      TERN_SPLASH_PALETTE.ink,
      TERN_SPLASH_PALETTE.accent,
      TERN_SPLASH_PALETTE.dim,
      TERN_SPLASH_PALETTE.ray,
      TERN_SPLASH_PALETTE.shade
    ])

    expect(text(cells)).not.toContain('\x1b')
    expect(tokens(cells).size).toBeGreaterThan(0)

    for (const token of tokens(cells)) {
      expect(allowed).toContain(token)
    }
  })

  it('changes colour tokens, not geometry, under a swapped palette', () => {
    for (const t of [600, 1700, 3000]) {
      const base = frame(design, 100, 30, t, { status: 'loading skills' })
      const swapped = frame(design, 100, 30, t, { palette: SWAPPED, status: 'loading skills' })

      expect(geometry(swapped)).toEqual(geometry(base))
      expect(swapped).not.toEqual(base)

      for (const token of tokens(swapped)) {
        expect(Object.values(SWAPPED)).toContain(token)
      }
    }
  })

  it('uses only glyphs the pane font holds at a fixed advance', () => {
    for (const t of [300, 1200, 2000, 3000, 5200]) {
      for (const row of frame(design, 156, 43, t, { status: 'summoning hermes…' })) {
        expect(rowText(row)).toMatch(SPLASH_GLYPHS)
      }
    }
  })

  it('keeps animating after the intro so it can cover a slow boot', () => {
    const stills = [400, 1400, 2400, 3400].map(dt => text(frame(design, 100, 30, SPLASH_INTRO_MS + dt)))

    expect(new Set(stills).size).toBeGreaterThan(1)
  })

  it('shows the live status once settled', () => {
    expect(text(frame(design, 100, 30, SPLASH_INTRO_MS + 100, { status: 'loading skills' }))).toContain(
      'LOADING SKILLS'
    )
  })

  it('dissolves to a bare pane on exit', () => {
    const cells = frame(design, 100, 30, 5000, { exitMs: SPLASH_EXIT_MS })

    expect(text(cells).trim()).toBe('')
    expect(cells.every(row => row.every(seg => seg.ground === 'none'))).toBe(true)
  })

  it('falls back to a letterspaced title when the scene cannot fit', () => {
    expect(text(frame(design, 40, 10, 3000))).toContain('H E R M E S   A G E N T')
  })
})

describe('renderSplashFrame', () => {
  it('ships the seven designs, kerykeion first', () => {
    expect(SPLASH_DESIGN_NAMES).toEqual(['kerykeion', 'sigil', 'velocity', 'atlas', 'windows', 'unleash', 'soul'])
    expect(DEFAULT_SPLASH_DESIGN).toBe('kerykeion')
  })

  it('draws the default for an unknown design', () => {
    expect(frame('nope', 100, 30, 3000)).toEqual(frame(DEFAULT_SPLASH_DESIGN, 100, 30, 3000))
  })

  it('settles the default on wordmark and tagline', () => {
    const settled = text(frame(DEFAULT_SPLASH_DESIGN, 100, 30, SPLASH_INTRO_MS + 100))

    expect(settled).toContain('THE AGENT THAT GROWS WITH YOU')
    expect(settled).toContain('├─┤')
  })

  it('carries shadow as its own span token, and paper-as-ink as the base of an inverted card', () => {
    const bases = (design: string) =>
      new Set(frame(design, 120, 40, 3000).flatMap(row => row.map(seg => `${seg.ground}/${seg.base}`)))

    expect(tokens(frame('kerykeion', 120, 40, 3000))).toContain(TERN_SPLASH_PALETTE.shade)
    expect(bases('sigil')).toContain('ink/paper')
    expect(bases('windows')).toContain('shade/none')
  })
})

describe('splash view', () => {
  it('draws each row as text nodes whose inks are span tokens and whose grounds are roles', () => {
    const cells = frame('sigil', 100, 30, 3000, { status: 'loading skills' })
    const node = splashNode(cells).toJSON()

    expect(node.k).toBe('col')
    expect(node.p?.role).toBe(SPLASH_ROLE)
    expect(node.c).toHaveLength(30)

    const roles = new Set<string>()

    for (const row of node.c!) {
      expect(row.k).toBe('row')

      for (const seg of row.c!) {
        expect(seg.k).toBe('text')
        expect(seg.p?.wrap).toBe('none')
        roles.add(String(seg.p?.role))
      }
    }

    expect(roles).toContain(segmentRole('paper', 'none'))
    expect(roles).toContain(segmentRole('ink', 'paper'))
    // No colour value and no SGR anywhere in what goes on the wire.
    expect(JSON.stringify(node)).not.toMatch(/#[0-9a-f]{6}|\\u001b|rgb\(/i)
  })
})

describe('splash theme', () => {
  it('inks with tokens every Tern theme defines', () => {
    expect(TERN_SPLASH_PALETTE).toEqual({ accent: 'accent', dim: 'muted', ink: 'text', ray: 'dim', shade: 'del' })
  })

  it('takes paper, ink, shade and inverted grounds from the pane itself, with no colour value of its own', () => {
    const css = splashStylesheet()
    const shade = 'color-mix(in oklab, var(--tv-bg) 58%, black)'

    // Paper is the pane: a paper ground paints nothing. Ink is the pane's text colour.
    expect(css).not.toContain(`[data-role='${segmentRole('paper', 'none')}']`)
    expect(css).toContain(`[data-role^='${SPLASH_ROLE}.on-'] { color: var(--sf-p-text, var(--tv-fg)); }`)
    // Shadow ink rides the `del` span class, re-inked inside the splash only.
    expect(css).toContain(`[data-role^='${SPLASH_ROLE}.on-'] .sf-t-del { color: ${shade}; text-decoration: none; }`)
    expect(css).toContain(
      `[data-role='${segmentRole('ink', 'paper')}'] { background: var(--sf-p-text, var(--tv-fg)); color: var(--tv-bg); }`
    )
    expect(css).toContain(`[data-role='${segmentRole('shade', 'none')}'] { background: ${shade}; }`)
    expect(css).not.toMatch(/#[0-9a-f]{3,8}\b/i)
    expect(css).not.toMatch(/rgb\(\s*\d/)
    expect(splashStylesheet(SWAPPED)).toContain('.sf-t-ins {')
  })

  it('wears Tern\u2019s theme under the built-in default skin, and a chosen skin\u2019s palette otherwise', () => {
    expect(programPaletteOf(undefined)).toEqual({})
    expect(programPaletteOf({ colors: { ui_accent: '#FFBF00' }, name: 'default' })).toEqual({})

    const ember = { colors: { banner_dim: '#c98a5a', ui_accent: '#ffd166', ui_text: '#ffe9d6' }, name: 'ember' }
    const dark = programPaletteOf(ember).dark!

    expect(programPaletteOf(ember)).toEqual(paletteOf(ember))
    expect(dark[TERN_SPLASH_PALETTE.ink]).toBe('#ffe9d6')
    expect(dark[TERN_SPLASH_PALETTE.accent]).toBe('#ffd166')
    expect(dark[TERN_SPLASH_PALETTE.dim]).toMatch(/^#[0-9a-f]{6}$/i)
    expect(dark[TERN_SPLASH_PALETTE.ray]).toMatch(/^#[0-9a-f]{6}$/i)
  })
})

describe('HERMES_TUI_SPLASH', () => {
  it('is on by default with the default design', () => {
    expect(splashSetting({})).toEqual({ design: '', enabled: true })
    expect(pickSplashDesign('')).toBe('kerykeion')
  })

  it.each(['0', 'false', 'off', 'no', ' OFF '])('%j disables it', value => {
    expect(splashSetting({ HERMES_TUI_SPLASH: value }).enabled).toBe(false)
  })

  it('takes a design name, random, or junk', () => {
    expect(pickSplashDesign(splashSetting({ HERMES_TUI_SPLASH: 'Atlas' }).design)).toBe('atlas')
    expect(pickSplashDesign(splashSetting({ HERMES_TUI_SPLASH: '1' }).design)).toBe('kerykeion')
    expect(pickSplashDesign('nope')).toBe('kerykeion')
    expect(pickSplashDesign('random', () => 0)).toBe('kerykeion')
    expect(pickSplashDesign('random', () => 0.999)).toBe('soul')
  })

  it('HERMES_TUI_SPLASH_FPS sets a recording frame rate, bounded', () => {
    expect(splashTickMs({})).toBeUndefined()
    expect(splashTickMs({ HERMES_TUI_SPLASH_FPS: 'fast' })).toBeUndefined()
    expect(splashTickMs({ HERMES_TUI_SPLASH_FPS: '120' })).toBe(8)
    expect(splashTickMs({ HERMES_TUI_SPLASH_FPS: '9000' })).toBe(4)
  })

  it('stays out of the way of a launch that carries a prompt', () => {
    expect(splashSetting({ HERMES_TUI_QUERY: 'hello' }).enabled).toBe(false)
  })

  it('draws inside the screen surface’s insets', () => {
    expect(splashInsets(160, 45)).toEqual({ cols: 156, rows: 43 })
    expect(splashInsets(2, 1)).toEqual({ cols: 1, rows: 1 })
  })
})

class FakeSurface implements SplashSurface {
  closed = false
  frames: ReturnType<typeof splashNode>[] = []
  palettes: Palette[] = []
  sheets: Record<string, string | null> = {}
  closedWith: { keep?: boolean } | undefined

  render(view: ReturnType<typeof splashNode>) {
    this.frames.push(view)
  }

  palette(palette: Palette) {
    this.palettes.push(palette)
  }

  stylesheet(name: string, css: string | null) {
    this.sheets[name] = css
  }

  close(options?: { keep?: boolean }) {
    this.closed = true
    this.closedWith = options
  }
}

/** A splash on a hand-cranked clock. */
function rig(extra: { design?: string } = {}) {
  const surface = new FakeSurface()
  const done = vi.fn()
  let now = 1000

  let step: () => void = () => {}

  const splash = new LaunchSplash({
    clearInterval: () => {
      step = () => {}
    },
    design: extra.design ?? 'kerykeion',
    now: () => now,
    onDone: done,
    open: () => surface,
    setInterval: fn => {
      step = fn
    },
    size: () => ({ cols: 100, rows: 30 }),
    status: 'summoning hermes…'
  })

  /** Runs the clock forward `ms`, a tick at a time. */
  const advance = (ms: number) => {
    for (let left = ms; left > 0; left -= SPLASH_TICK_MS) {
      now += Math.min(left, SPLASH_TICK_MS)
      step()
    }
  }

  return { advance, done, splash, surface }
}

describe('LaunchSplash', () => {
  it('opens its surface with the stylesheet and no palette of its own, and draws at once', () => {
    const { splash, surface } = rig()

    expect(splash.active).toBe(false)
    splash.start()

    expect(splash.active).toBe(true)
    expect(surface.sheets.splash).toBe(splashStylesheet())
    expect(surface.palettes).toEqual([])
    expect(surface.frames).toHaveLength(1)
  })

  it('plays out the intro before leaving, even when the gateway is ready at once', () => {
    const { advance, done, splash, surface } = rig()

    splash.start()
    splash.ready()
    advance(SPLASH_INTRO_MS - SPLASH_TICK_MS)
    expect(done).not.toHaveBeenCalled()

    advance(SPLASH_TICK_MS + SPLASH_EXIT_MS)
    expect(done).toHaveBeenCalledTimes(1)
    expect(surface.closedWith).toEqual({ keep: false })
    expect(splash.active).toBe(false)
  })

  it('idles past the intro until ready, then dissolves and hands off', () => {
    const { advance, done, splash } = rig()

    splash.start()
    advance(6000)
    expect(done).not.toHaveBeenCalled()
    expect(splash.active).toBe(true)

    splash.ready()
    advance(SPLASH_TICK_MS + SPLASH_EXIT_MS)
    expect(done).toHaveBeenCalledTimes(1)
  })

  it('leaves on skip without waiting for the gateway or the intro', () => {
    const { advance, done, splash, surface } = rig()

    splash.start()
    advance(200)
    splash.skip()
    advance(SPLASH_EXIT_MS - SPLASH_TICK_MS)
    expect(done).not.toHaveBeenCalled()

    advance(2 * SPLASH_TICK_MS)
    expect(done).toHaveBeenCalledTimes(1)
    expect(surface.closed).toBe(true)
  })

  it('never holds past 15 seconds', () => {
    const { advance, done, splash } = rig()

    splash.start()
    advance(SPLASH_MAX_MS - SPLASH_TICK_MS)
    expect(done).not.toHaveBeenCalled()

    advance(SPLASH_TICK_MS + SPLASH_EXIT_MS)
    expect(done).toHaveBeenCalledTimes(1)
  })

  it('stops drawing and hands off once, however long the clock runs on', () => {
    const { advance, done, splash, surface } = rig()

    splash.start()
    splash.skip()
    advance(SPLASH_EXIT_MS + SPLASH_TICK_MS)

    const drawn = surface.frames.length

    splash.tick()
    splash.skip()
    advance(1000)
    expect(surface.frames).toHaveLength(drawn)
    expect(done).toHaveBeenCalledTimes(1)
  })

  it('takes a new palette while it shows, and none after', () => {
    const { advance, splash, surface } = rig()
    const ember = paletteOf({ colors: { ui_accent: '#ffd166' }, name: 'ember' })

    splash.start()
    splash.palette(ember)
    expect(surface.palettes.at(-1)).toBe(ember)

    splash.skip()
    advance(SPLASH_EXIT_MS + SPLASH_TICK_MS)
    splash.palette({})
    expect(surface.palettes).toHaveLength(1)
  })

  it.each(SPLASH_DESIGN_NAMES)('draws %s as a native view', design => {
    const { advance, splash, surface } = rig({ design })

    splash.start()
    advance(3000)

    const view = surface.frames.at(-1)!.toJSON()

    expect(view.p?.role).toBe(SPLASH_ROLE)
    expect(view.c).toHaveLength(30)
    expect(JSON.stringify(view)).not.toMatch(/\\u001b/)
  })
})

// ── the app: splash before the chrome, skin events recolour it ───────────

class FakeAppSurface extends FakeSurface {
  rendered: unknown[] = []
  focused: (string | null)[] = []
  dispatch = vi.fn<Surface['dispatch']>()

  constructor(readonly options: { id?: string; mode?: string; role?: string }) {
    super()
  }

  override render(view: never) {
    this.rendered.push(view)
    super.render(view)
  }

  focus(id: string | null) {
    this.focused.push(id)
  }
}

function fakeTern(caps: { reduceMotion?: boolean } = {}) {
  const surfaces: FakeAppSurface[] = []
  const inputs: unknown[] = []
  let wake: (() => void) | undefined
  let closed = false

  const session = {
    blob: () => 'blob',
    caps: { cell: { h: 16, w: 8 }, cols: 100, dark: true, features: [], reduceMotion: caps.reduceMotion ?? false },
    close: async () => {
      closed = true
      wake?.()
    },
    open: (options: { id?: string; mode?: string; role?: string }) => {
      const surface = new FakeAppSurface(options)

      surfaces.push(surface)

      return surface
    },
    async *[Symbol.asyncIterator]() {
      while (!closed) {
        if (inputs.length) {
          yield inputs.shift()
        } else {
          await new Promise<void>(resolve => (wake = resolve))
        }
      }
    }
  }

  const key = (name: string) => {
    inputs.push({ key: { alt: false, ctrl: false, meta: false, name, shift: false, text: name }, type: 'key' })
    wake?.()
  }

  return { key, session: session as unknown as Session, surfaces }
}

function fakeGateway() {
  const gw = new EventEmitter() as EventEmitter & { drain(): void; kill(): void; request(): Promise<unknown> }

  gw.drain = () => {}

  gw.kill = () => {}
  // Never settles: these tests stop at the hand-off, before any session exists.
  gw.request = () => new Promise(() => {})

  return gw
}

describe('App launch splash', () => {
  beforeEach(() => {
    vi.useFakeTimers({
      toFake: ['setInterval', 'clearInterval', 'setTimeout', 'clearTimeout', 'setImmediate', 'performance']
    })
    vi.stubEnv('HERMES_TUI_SPLASH', '')
    vi.stubEnv('HERMES_TUI_QUERY', '')
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllEnvs()
  })

  const launch = (caps: { reduceMotion?: boolean } = {}) => {
    const tern = fakeTern(caps)
    const gw = fakeGateway()
    const app = new App(tern.session, gw as unknown as GatewayClient, '1.2.3')

    void app.run()

    const splash = () => tern.surfaces.find(s => s.options.id === 'splash')
    const chrome = () => tern.surfaces.find(s => s.options.id === 'hermes')!

    return { app, chrome, gw, splash, tern }
  }

  it('covers the session chrome with a screen surface in Tern\u2019s own theme', async () => {
    const { chrome, splash } = launch()

    expect(chrome().options).toMatchObject({ mode: 'inline', role: 'omp.session' })
    expect(splash()!.options).toMatchObject({ mode: 'screen', role: SPLASH_ROLE })
    expect(splash()!.palettes).toEqual([])
    expect(splash()!.sheets.splash).toBe(splashStylesheet())

    await vi.advanceTimersByTimeAsync(400)
    expect(splash()!.frames.length).toBeGreaterThan(5)
    expect(splash()!.closed).toBe(false)
  })

  it('stays in Tern\u2019s theme for the default skin, and recolours on skin.changed', async () => {
    const { chrome, gw, splash } = launch()
    const builtin = { colors: { ui_accent: '#FFBF00' }, name: 'default' }
    const ember = { colors: { ui_accent: '#ffd166', ui_text: '#ffe9d6' }, name: 'ember' }

    await vi.advanceTimersByTimeAsync(200)
    gw.emit('event', { payload: { skin: builtin }, type: 'gateway.ready' })
    // No palette of the program's: the window's theme inks the splash.
    expect(splash()!.palettes.at(-1)).toEqual({})
    // The chrome too: a palette names its skin, and Tern would switch the window to that theme.
    expect(chrome().palettes.at(-1)).toEqual({})

    const before = splash()!.frames.length

    gw.emit('event', { payload: ember, type: 'skin.changed' })
    expect(splash()!.palettes.at(-1)).toEqual(paletteOf(ember))
    expect(splash()!.palettes.at(-1)!.dark![TERN_SPLASH_PALETTE.accent]).toBe('#ffd166')
    expect(chrome().palettes.at(-1)).toEqual(paletteOf(ember))

    // The picture itself carries no colour, so the next frame is simply drawn in the new skin.
    await vi.advanceTimersByTimeAsync(SPLASH_TICK_MS)
    expect(splash()!.frames.length).toBeGreaterThan(before)
    expect(JSON.stringify(splash()!.frames.at(-1))).not.toMatch(/#[0-9a-f]{6}/i)

    // Back to the built-in skin: back to the window's theme.
    gw.emit('event', { payload: builtin, type: 'skin.changed' })
    expect(splash()!.palettes.at(-1)).toEqual({})
    expect(chrome().palettes.at(-1)).toEqual({})
  })

  it('hands off to the chrome once the gateway is ready and the intro has played', async () => {
    const { gw, splash } = launch()

    gw.emit('event', { payload: {}, type: 'gateway.ready' })
    await vi.advanceTimersByTimeAsync(SPLASH_INTRO_MS - 200)
    expect(splash()!.closed).toBe(false)

    await vi.advanceTimersByTimeAsync(200 + SPLASH_EXIT_MS + 2 * SPLASH_TICK_MS)
    expect(splash()!.closed).toBe(true)
    expect(splash()!.closedWith).toEqual({ keep: false })
  })

  it('skips on any key, and spends the key doing so', async () => {
    const { app, splash, tern } = launch()

    await vi.advanceTimersByTimeAsync(300)
    tern.key('x')
    await vi.advanceTimersByTimeAsync(SPLASH_EXIT_MS + 3 * SPLASH_TICK_MS)

    expect(splash()!.closed).toBe(true)
    expect(app.composer.text).toBe('')

    // The next key is the composer's.
    tern.key('y')
    await vi.advanceTimersByTimeAsync(50)
    expect(app.composer.text).toBe('y')
  })

  it('never holds the app past 15 seconds', async () => {
    const { splash } = launch()

    await vi.advanceTimersByTimeAsync(SPLASH_MAX_MS - 500)
    expect(splash()!.closed).toBe(false)

    await vi.advanceTimersByTimeAsync(500 + SPLASH_EXIT_MS + 2 * SPLASH_TICK_MS)
    expect(splash()!.closed).toBe(true)
  })

  it('HERMES_TUI_SPLASH=0 preserves the first composer key', async () => {
    vi.stubEnv('HERMES_TUI_SPLASH', '0')

    const { app, splash, tern } = launch()

    expect(splash()).toBeUndefined()
    tern.key('x')
    await vi.advanceTimersByTimeAsync(50)
    expect(app.composer.text).toBe('x')
  })

  it('HERMES_TUI_SPLASH=<design> picks that design', async () => {
    vi.stubEnv('HERMES_TUI_SPLASH', 'unleash')

    const { splash } = launch()

    await vi.advanceTimersByTimeAsync(2300)
    expect(JSON.stringify(splash()!.frames.at(-1))).toContain('U N L E A S H')
  })

  it('stays off under Reduce Motion', () => {
    expect(launch({ reduceMotion: true }).splash()).toBeUndefined()
  })
})

describe('renderWordmark', () => {
  it('stretches every glyph to the requested height at a constant width', () => {
    for (let rows = WORDMARK_MIN_ROWS; rows <= 12; rows++) {
      const lines = renderWordmark('HERMES AGENT', rows)

      expect(lines).toHaveLength(rows)
      expect(new Set(lines.map(l => l.length))).toEqual(new Set([wordmarkWidth('HERMES AGENT')]))
    }
  })

  it('renders unknown characters as blanks instead of throwing', () => {
    expect(renderWordmark('H3?', 5)).toHaveLength(5)
  })
})
