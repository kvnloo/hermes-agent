import { chromeGlyph, getActiveGlyphPreset, type GlyphPreset } from './glyphPreset.js'

/** Disclosure chevron for expand/collapse chrome. Trailing space matches
 * historical `▸ `/`▾ ` rendering so layout widths stay stable. */
export const disclosureGlyph = (
  open: boolean,
  preset: GlyphPreset = getActiveGlyphPreset()
): string => `${chromeGlyph(open ? 'disclosure.expanded' : 'disclosure.collapsed', preset)} `
