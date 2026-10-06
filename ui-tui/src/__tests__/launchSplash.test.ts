import { describe, expect, it } from 'vitest'

import { pickSplashDesign } from '../components/launchSplash.js'
import {
  DEFAULT_SPLASH_DESIGN,
  renderSplashFrame,
  SPLASH_DESIGN_NAMES,
  SPLASH_EXIT_MS,
  SPLASH_INTRO_MS
} from '../splash/index.js'
import { renderWordmark, WORDMARK_MIN_ROWS, wordmarkWidth } from '../splash/wordmark.js'

// eslint-disable-next-line no-control-regex
const strip = (s: string) => s.replace(/\x1b\[[0-9;]*m/g, '')

const frame = (design: string, width: number, height: number, elapsedMs: number, extra = {}) =>
  renderSplashFrame({ design, elapsedMs, height, width, ...extra })

describe.each(SPLASH_DESIGN_NAMES)('splash design %s', design => {
  it.each([
    [80, 24],
    [150, 46],
    [240, 58],
    [56, 20],
    [40, 10],
    [12, 3],
    [1, 1]
  ])('fills exactly %dx%d cells at every stage', (w, h) => {
    for (const t of [0, 200, 900, 1600, SPLASH_INTRO_MS, 9000]) {
      const lines = frame(design, w, h, t, { status: 'summoning hermes…' })

      expect(lines).toHaveLength(h)

      for (const line of lines) {
        expect([...strip(line)]).toHaveLength(w)
      }
    }
  })

  it('is a pure function of its inputs', () => {
    expect(frame(design, 100, 30, 1234)).toEqual(frame(design, 100, 30, 1234))
  })

  it('keeps animating after the intro so it can cover a slow boot', () => {
    const stills = [400, 1400, 2400, 3400].map(dt => frame(design, 100, 30, SPLASH_INTRO_MS + dt).join('\n'))

    expect(new Set(stills).size).toBeGreaterThan(1)
  })

  it('shows the live status once settled', () => {
    const text = frame(design, 100, 30, SPLASH_INTRO_MS + 100, { status: 'loading skills' })
      .map(strip)
      .join('\n')

    expect(text).toContain('LOADING SKILLS')
  })

  it('dissolves to an empty screen on exit', () => {
    const lines = frame(design, 100, 30, 5000, { exitMs: SPLASH_EXIT_MS })

    expect(lines.every(line => strip(line).trim() === '')).toBe(true)
    expect(lines.join('')).not.toContain('\x1b[48')
  })

  it('emits no escape codes without colour', () => {
    expect(frame(design, 100, 30, 3000, { color: 'none' }).join('')).not.toContain('\x1b')
  })

  it('falls back to a letterspaced title when the scene cannot fit', () => {
    const text = frame(design, 40, 10, 3000).map(strip).join('\n')

    expect(text).toContain('H E R M E S   A G E N T')
  })
})

describe('renderSplashFrame', () => {
  it('ships the caduceus plus six alternates', () => {
    expect(SPLASH_DESIGN_NAMES).toHaveLength(7)
    expect(SPLASH_DESIGN_NAMES[0]).toBe(DEFAULT_SPLASH_DESIGN)
  })

  it('draws the default for an unknown design', () => {
    expect(frame('nope', 100, 30, 3000)).toEqual(frame(DEFAULT_SPLASH_DESIGN, 100, 30, 3000))
  })

  it('settles the default on wordmark and tagline', () => {
    const text = frame(DEFAULT_SPLASH_DESIGN, 100, 30, SPLASH_INTRO_MS + 100)
      .map(strip)
      .join('\n')

    expect(text).toContain('THE AGENT THAT GROWS WITH YOU')
    expect(text).toContain('├─┤')
  })
})

describe('pickSplashDesign', () => {
  it('resolves names, random and junk', () => {
    expect(pickSplashDesign('atlas')).toBe('atlas')
    expect(pickSplashDesign('')).toBe(DEFAULT_SPLASH_DESIGN)
    expect(pickSplashDesign('nope')).toBe(DEFAULT_SPLASH_DESIGN)
    expect(pickSplashDesign('random', () => 0.999)).toBe(SPLASH_DESIGN_NAMES.at(-1))
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
