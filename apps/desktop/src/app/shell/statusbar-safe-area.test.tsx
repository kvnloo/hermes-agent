import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

import { StatusbarControls } from '@/app/shell/statusbar-controls'
import { stubMenuDomApis, stubResizeObserver } from '@/test/jsdom'

beforeAll(() => {
  stubResizeObserver()
  stubMenuDomApis()
})

afterEach(cleanup)

describe('installed Android webapp statusbar', () => {
  it('keeps a 44px coarse-pointer hit target above the bottom gesture inset (#152083)', () => {
    const onSelect = vi.fn()
    render(
      <MemoryRouter>
        <StatusbarControls items={[{ id: 'model', label: 'Model', onSelect, variant: 'action' }]} />
      </MemoryRouter>
    )

    const footer = screen.getByRole('contentinfo')
    const model = screen.getByRole('button', { name: 'Model' })

    // Footer's content height stays 20px on fine pointers and grows to
    // 44px on touch, with the browser's bottom gesture inset reserved below it.
    expect(footer.classList.contains('h-[calc(1.25rem+env(safe-area-inset-bottom,0px))]')).toBe(true)
    expect(
      footer.classList.contains('[@media(pointer:coarse)]:h-[calc(2.75rem+env(safe-area-inset-bottom,0px))]')
    ).toBe(true)
    expect(footer.classList.contains('pb-[env(safe-area-inset-bottom,0px)]')).toBe(true)
    expect(model.classList.contains('[@media(pointer:coarse)]:min-h-11')).toBe(true)

    fireEvent.click(model)
    expect(onSelect).toHaveBeenCalledWith({ shiftKey: false })
  })
})
