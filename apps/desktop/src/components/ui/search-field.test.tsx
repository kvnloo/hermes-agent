import { cleanup, fireEvent, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SearchField } from './search-field'

afterEach(cleanup)

describe('SearchField', () => {
  it('lays the input out as a flex child so the clear button pins to the row edge', () => {
    // The row is an inline-flex container. The input stays content-sized
    // (`field-sizing: content`) so width-less callers keep compact rows, but
    // it is also a flex child that absorbs the row's free space (`flex-1` +
    // `min-w-0`) — without flex-1 the input kept text width inside a
    // stretched row (w-full settings rows, flex-1 filter bars) and the clear
    // button trailed the typed text instead of sitting at the row's right
    // edge (#119204).
    const { container, getByRole } = render(<SearchField onChange={() => {}} placeholder="Search" value="abc" />)

    const input = getByRole('searchbox') as HTMLInputElement
    const row = container.firstElementChild as HTMLElement

    expect(row.className).toContain('inline-flex')
    expect(input.className).toContain('flex-1')
    expect(input.className).toContain('[field-sizing:content]')
    expect(input.className).toContain('min-w-0')
  })

  it('treats integration filtering as search rather than a credential input', () => {
    const onChange = vi.fn()
    const { getByRole } = render(<SearchField onChange={onChange} placeholder="Search integrations" value="" />)

    const input = getByRole('searchbox', { name: 'Search integrations' }) as HTMLInputElement
    expect(input.value).toBe('')

    fireEvent.change(input, { target: { value: 'telegram' } })
    expect(onChange).toHaveBeenCalledWith('telegram')
  })

  it('opts out of password-manager autofill so saved usernames never land in filter boxes', () => {
    const { getByRole } = render(<SearchField onChange={() => {}} placeholder="Search" value="" />)

    const input = getByRole('searchbox') as HTMLInputElement

    expect(input.getAttribute('autocomplete')).toBe('off')
    expect(input.getAttribute('name')).toBe('hermes-search')
    expect(input.hasAttribute('data-1p-ignore')).toBe(true)
    expect(input.getAttribute('data-lpignore')).toBe('true')
  })

  it('keeps clear wired to the value reset', () => {
    const onChange = vi.fn()

    const { getByRole } = render(
      <SearchField aria-label="find" onChange={onChange} placeholder="Search" value="query" />
    )

    fireEvent.click(getByRole('button', { name: /clear/i }))

    expect(onChange).toHaveBeenCalledWith('')
  })

  it('renders no clear button while empty or loading', () => {
    const { queryByRole, rerender } = render(<SearchField onChange={() => {}} placeholder="Search" value="" />)

    expect(queryByRole('button', { name: /clear/i })).toBeNull()

    rerender(<SearchField loading onChange={() => {}} placeholder="Search" value="query" />)

    expect(queryByRole('button', { name: /clear/i })).toBeNull()
  })
})
