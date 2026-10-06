import { describe, expect, it } from 'vitest'

import { paletteOf } from '../palette.js'

describe('palette', () => {
  it('keeps syntax and muted colors as hex', () => {
    const dark = paletteOf({
      colors: {
        banner_accent: '#FFBF00',
        banner_text: '#FFF8DC',
        banner_title: '#FFD700'
      },
      name: 'default'
    }).dark

    expect(dark?.syntaxString).toMatch(/^#[0-9a-f]{6}$/i)
    expect(dark?.syntaxKeyword).toMatch(/^#[0-9a-f]{6}$/i)
    expect(dark?.muted).toMatch(/^#[0-9a-f]{6}$/i)
    expect(dark?.accent?.toLowerCase()).toBe('#ffbf00')
  })
})
