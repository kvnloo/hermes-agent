import { afterEach, describe, expect, it, vi } from 'vitest'

import { TRANSLATIONS } from '@/i18n/catalog'
import { setRuntimeI18nLocale } from '@/i18n/runtime'

import { paletteToggle } from './contrib'

afterEach(() => {
  setRuntimeI18nLocale('en')
})

describe('paletteToggle', () => {
  it('resolves live on/off details in the current locale without re-registering the row', () => {
    let enabled = false
    const set = vi.fn((value: boolean) => {
      enabled = value
    })

    setRuntimeI18nLocale('en')
    const row = paletteToggle({ id: 'toggle-status', label: 'Toggle status', get: () => enabled, set }).data

    expect(row.detail?.()).toBe('off')

    setRuntimeI18nLocale('ru')
    expect(row.detail?.()).toBe(TRANSLATIONS.ru.common.off.toLowerCase())

    row.run()
    expect(set).toHaveBeenCalledWith(true)
    expect(row.detail?.()).toBe(TRANSLATIONS.ru.common.on.toLowerCase())

    setRuntimeI18nLocale('en')
    expect(row.detail?.()).toBe('on')
  })
})
