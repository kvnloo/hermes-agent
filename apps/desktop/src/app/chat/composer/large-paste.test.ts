import { describe, expect, it } from 'vitest'

import {
  LARGE_PASTE_ATTACHMENT_THRESHOLD,
  largePasteTitlePreview,
  pasteSizeLabel,
  shouldConvertPasteToAttachment
} from './large-paste'

describe('large paste policy', () => {
  it('converts only pastes strictly past the threshold', () => {
    expect(shouldConvertPasteToAttachment('a'.repeat(LARGE_PASTE_ATTACHMENT_THRESHOLD))).toBe(false)
    expect(shouldConvertPasteToAttachment('a'.repeat(LARGE_PASTE_ATTACHMENT_THRESHOLD + 1))).toBe(true)
    expect(shouldConvertPasteToAttachment('a'.repeat(50_000), 0)).toBe(false)
  })

  it('keeps the title preview UTF-16 safe at the emoji boundary', () => {
    // 16 astral emojis before the boundary: the next one straddles unit 1,000.
    const prefix = `${'🧩'.repeat(16)}${'a'.repeat(967)}`
    const paste = `${prefix}🧩${'z'.repeat(4_000)}`

    expect(prefix.length).toBe(999)
    expect(largePasteTitlePreview(paste)).toBe(prefix)
    expect(largePasteTitlePreview(`${prefix.slice(0, -1)}🧩${'z'.repeat(4_000)}`)).toBe(
      `${prefix.slice(0, -1)}🧩`
    )
    expect(largePasteTitlePreview('a'.repeat(4_001))).toBe('a'.repeat(1_000))
  })

  it('labels the chip by encoded byte size, not character count', () => {
    expect(pasteSizeLabel('a'.repeat(512))).toBe('512 B')
    expect(pasteSizeLabel('\u00e9'.repeat(1024))).toBe('2.0 KB')
  })
})
