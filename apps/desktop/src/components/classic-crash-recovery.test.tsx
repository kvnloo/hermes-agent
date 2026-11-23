import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'

import { $portalShell, $shellChoice } from '@/store/shell-variant'

import { RootErrorBoundary } from './error-boundary'

const shellKey = 'hermes.desktop.agentShell.v1'
const recovery = { name: 'Switch to classic' }

function Workspace() {
  if ($portalShell.get()) {
    throw new Error('fixture: only the redesigned workspace fails')
  }

  return <div>Classic workspace is working</div>
}

afterEach(() => {
  cleanup()
  $shellChoice.set(null)
  vi.restoreAllMocks()
})

it('offers recovery after Retry repeats a redesign-only crash, and remembers the classic choice', () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  $shellChoice.set(true)
  render(
    <RootErrorBoundary>
      <Workspace />
    </RootErrorBoundary>
  )

  expect(screen.getByRole('button', { name: 'Reload window' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
  expect(screen.queryByText('Classic workspace is working')).toBeNull()
  fireEvent.click(screen.getByRole('button', recovery))

  expect(screen.getByText('Classic workspace is working')).toBeTruthy()
  expect(localStorage.getItem(shellKey)).toBe('false')
})

it('does not offer a shell switch in an already classic renderer', () => {
  vi.spyOn(console, 'error').mockImplementation(() => undefined)
  $shellChoice.set(false)

  function CrashedClassic() {
    throw new Error('fixture: classic workspace fails')
  }

  render(
    <RootErrorBoundary>
      <CrashedClassic />
    </RootErrorBoundary>
  )

  expect(screen.getByRole('button', { name: 'Reload window' })).toBeTruthy()
  expect(screen.queryByRole('button', recovery)).toBeNull()
})
