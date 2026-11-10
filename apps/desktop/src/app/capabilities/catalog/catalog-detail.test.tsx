import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CatalogDetail } from './catalog-detail'
import { parseCatalog } from './catalog-data'

const locale = { current: 'id' }

vi.mock('@/i18n', async importOriginal => {
  const actual = (await importOriginal()) as {
    useI18n: () => { locale: string }
  } & Record<string, unknown>

  return {
    ...actual,
    useI18n: () => ({
      ...actual.useI18n(),
      locale: locale.current
    })
  }
})

describe('localized catalog detail', () => {
  it('does not repeat the English description when the overview duplicates it', () => {
    const [entry] = parseCatalog('plugins', [
      {
        name: 'stage',
        description: 'English description',
        overview: 'English description',
        tier: 'community',
        i18n: { id: { description: 'Deskripsi Indonesia' } }
      }
    ])

    render(<CatalogDetail dialog={false} entry={entry} kind="plugins" related={[]} />)

    expect(screen.getByText('Deskripsi Indonesia')).toBeTruthy()
    expect(screen.queryByText('English description')).toBeNull()
  })
})
