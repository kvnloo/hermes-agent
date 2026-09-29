import { afterEach, describe, expect, it } from 'vitest'

import {
  CHROME_GLYPH_KEYS,
  chromeGlyph,
  chromeSampleRow,
  DEFAULT_GLYPH_PRESET,
  GLYPH_PRESETS,
  GLYPH_TABLES,
  getActiveGlyphPreset,
  isAsciiChrome,
  normalizeGlyphPreset,
  setActiveGlyphPreset,
  type ChromeGlyphKey,
  type GlyphPreset
} from '../lib/glyphPreset.js'
import { disclosureGlyph } from '../lib/disclosureGlyph.js'
import { processGlyph } from '../lib/processGlyph.js'
import { statusGlyph } from '../lib/subagentGlyph.js'
import { DEFAULT_THEME } from '../theme.js'

afterEach(() => {
  setActiveGlyphPreset(DEFAULT_GLYPH_PRESET)
})

describe('normalizeGlyphPreset', () => {
  it('passes through the canonical enum', () => {
    expect(normalizeGlyphPreset('nerd')).toBe('nerd')
    expect(normalizeGlyphPreset('unicode')).toBe('unicode')
    expect(normalizeGlyphPreset('ascii')).toBe('ascii')
  })

  it('trims and lowercases input', () => {
    expect(normalizeGlyphPreset(' ASCII ')).toBe('ascii')
    expect(normalizeGlyphPreset('Nerd')).toBe('nerd')
  })

  it('defaults to unicode for missing/unknown values', () => {
    expect(normalizeGlyphPreset(undefined)).toBe('unicode')
    expect(normalizeGlyphPreset(null)).toBe('unicode')
    expect(normalizeGlyphPreset('')).toBe('unicode')
    expect(normalizeGlyphPreset('emoji')).toBe('unicode')
    expect(normalizeGlyphPreset(42)).toBe('unicode')
  })
})

describe('ascii preset emits zero non-ASCII chrome', () => {
  it('every chrome key is printable ASCII', () => {
    for (const key of CHROME_GLYPH_KEYS) {
      const g = chromeGlyph(key, 'ascii')
      expect(isAsciiChrome(g), `${key}=${JSON.stringify(g)}`).toBe(true)
    }
  })

  it('sample row at 40/80 width budgets stays ASCII', () => {
    const row = chromeSampleRow('ascii')
    expect(isAsciiChrome(row)).toBe(true)
    expect(row.length).toBeGreaterThan(10)
    // Width-matrix smoke: row fits in a narrow (40) and normal (80) status span.
    expect(row.length).toBeLessThanOrEqual(40)
    expect(row.length).toBeLessThanOrEqual(80)
  })
})

describe('shared table covers required chrome families', () => {
  const families: Array<{ prefix: string; keys: ChromeGlyphKey[] }> = [
    {
      prefix: 'disclosure',
      keys: ['disclosure.collapsed', 'disclosure.expanded']
    },
    {
      prefix: 'status',
      keys: ['status.running', 'status.success', 'status.failure', 'status.skipped']
    },
    {
      prefix: 'rail',
      keys: ['rail.vertical', 'rail.branch', 'rail.last', 'rail.space']
    },
    {
      prefix: 'tool',
      keys: ['tool.prefix', 'busy.static']
    }
  ]

  for (const preset of GLYPH_PRESETS) {
    it(`${preset}: required families resolve to non-empty glyphs`, () => {
      for (const fam of families) {
        for (const key of fam.keys) {
          expect(chromeGlyph(key, preset).length).toBeGreaterThan(0)
        }
      }
    })
  }

  it('presets differ on at least one chrome key (nerd ≠ unicode ≠ ascii)', () => {
    const key: ChromeGlyphKey = 'disclosure.collapsed'
    expect(chromeGlyph(key, 'ascii')).not.toBe(chromeGlyph(key, 'unicode'))
    expect(chromeGlyph(key, 'nerd')).not.toBe(chromeGlyph(key, 'ascii'))
  })
})

describe('active preset drives helpers without per-call argument', () => {
  it('disclosure / process / agent glyphs follow setActiveGlyphPreset', () => {
    setActiveGlyphPreset('ascii')
    expect(getActiveGlyphPreset()).toBe('ascii')
    expect(disclosureGlyph(false)).toBe('> ')
    expect(disclosureGlyph(true)).toBe('v ')
    expect(processGlyph('done', DEFAULT_THEME).glyph).toBe('+')
    expect(processGlyph('failed', DEFAULT_THEME).glyph).toBe('x')
    expect(statusGlyph('completed', DEFAULT_THEME).glyph).toBe('+')
    expect(statusGlyph('failed', DEFAULT_THEME).glyph).toBe('x')

    setActiveGlyphPreset('unicode')
    expect(disclosureGlyph(false)).toBe('▸ ')
    expect(processGlyph('done', DEFAULT_THEME).glyph).toBe('✔')
    expect(statusGlyph('completed', DEFAULT_THEME).glyph).toBe('✓')
  })
})

describe('tui_status_indicator remains independent', () => {
  it('glyph preset enum does not include busy-indicator animation styles', () => {
    expect(GLYPH_PRESETS).toEqual(['nerd', 'unicode', 'ascii'])
    expect((GLYPH_PRESETS as readonly string[]).includes('kaomoji')).toBe(false)
    expect((GLYPH_PRESETS as readonly string[]).includes('emoji')).toBe(false)
  })

  it('every glyph table is complete for all chrome keys', () => {
    for (const preset of GLYPH_PRESETS) {
      const table = GLYPH_TABLES[preset as GlyphPreset]
      for (const key of CHROME_GLYPH_KEYS) {
        expect(table[key], `${preset}.${key}`).toBeTypeOf('string')
      }
    }
  })
})

describe('width matrix smoke (40 / 80)', () => {
  for (const cols of [40, 80] as const) {
    for (const preset of GLYPH_PRESETS) {
      it(`${preset} sample row fits and is stable at ${cols} cols`, () => {
        const row = chromeSampleRow(preset)
        expect(row.length).toBeGreaterThan(0)
        // Sample is a single status-like span; must not exceed the column budget.
        expect(row.length).toBeLessThanOrEqual(cols)
        if (preset === 'ascii') {
          expect(isAsciiChrome(row)).toBe(true)
        }
      })
    }
  }
})
