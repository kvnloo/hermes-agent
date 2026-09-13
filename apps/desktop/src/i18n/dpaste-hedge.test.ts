import { describe, expect, it } from 'vitest'

import { en } from './en'
import { ru } from './ru'
import { zh } from './zh'

// G24: the desktop debug-share description hedges the dpaste.com fallback
// (the maintenance panel shows this static copy next to the run button).
describe('debugShareDesc hedges the dpaste.com fallback', () => {
  it.each([
    ['en', en],
    ['zh', zh],
    ['ru', ru],
  ])('%s mentions dpaste.com fallback retention', (_locale, cat) => {
    const desc = cat.commandCenter.maintenance.debugShareDesc
    // English hedge phrase used as the canonical marker.
    expect(desc).not.toBe('')
    // Each localized copy must disclose a dpaste.com fallback path.
    expect(desc.toLowerCase()).toContain('dpaste.com')
  })

  it('en copy bounds the fallback retention to 1 day', () => {
    expect(en.commandCenter.maintenance.debugShareDesc).toContain('1 day')
  })
})
