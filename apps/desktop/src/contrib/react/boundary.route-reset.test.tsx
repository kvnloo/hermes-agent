import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ContribBoundary } from './boundary'

function BrokenCapabilities() {
  throw new Error('Capabilities failed to render')
}

function WorkspacePages() {
  const { pathname } = useLocation()
  const navigate = useNavigate()

  return (
    <>
      <button onClick={() => navigate('/messaging')} type="button">
        Open Messaging
      </button>
      <ContribBoundary id="workspace">
        {pathname === '/capabilities' ? <BrokenCapabilities /> : <div>Messaging page is ready</div>}
      </ContribBoundary>
    </>
  )
}

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('workspace route error recovery', () => {
  it('unblocks the next page after a previous page throws without clicking Retry', () => {
    vi.spyOn(console, 'error').mockImplementation(() => undefined)

    render(
      <MemoryRouter initialEntries={['/capabilities']}>
        <WorkspacePages />
      </MemoryRouter>
    )

    expect(screen.getByRole('button', { name: 'Retry' })).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Open Messaging' }))

    expect(screen.getByText('Messaging page is ready')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Retry' })).toBeNull()
  })
})
