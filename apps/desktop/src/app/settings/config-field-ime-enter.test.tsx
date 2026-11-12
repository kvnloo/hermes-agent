/**
 * IME Enter regression adapted from kouyichi's tests in
 * NousResearch/hermes-agent#154473, for the fix in #154522.
 * CJK candidate-confirm Enter must not commit the partially composed list.
 */

import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'

import { ConfigField } from './config-field'

afterEach(cleanup)

function mount() {
  const onChange = vi.fn()

  render(
    <I18nProvider configClient={null} initialLocale="en">
      <ConfigField onChange={onChange} schema={{ type: 'list' }} schemaKey="tools.allowed" value={['111']} />
    </I18nProvider>
  )

  const input = screen.getByRole('textbox')
  input.focus()

  return { input, onChange }
}

it('commits the draft on a real Enter', () => {
  const { input, onChange } = mount()

  fireEvent.change(input, { target: { value: '111, 222' } })
  fireEvent.keyDown(input, { key: 'Enter' })

  expect(onChange).toHaveBeenCalledWith(['111', '222'])
})

it('does not commit on an in-flight IME composition Enter', () => {
  const { input, onChange } = mount()

  fireEvent.change(input, { target: { value: '中文' } })
  fireEvent.keyDown(input, { isComposing: true, key: 'Enter' })

  expect(onChange).not.toHaveBeenCalled()
})

it('does not commit on legacy keyCode 229 after compositionend', () => {
  const { input, onChange } = mount()

  fireEvent.change(input, { target: { value: '中文' } })
  fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 })

  expect(onChange).not.toHaveBeenCalled()
})
