import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { MoaState } from '@/lib/moa-orchestration'

import { MoaThinkingOrbs } from './moa-thinking-orbs'

vi.mock('thinking-orbs', () => ({
  ThinkingOrb: (props: Record<string, unknown>) => (
    <span data-paused={String(props.paused)} data-state={props.state} data-testid="thinking-orb" data-theme={props.theme} />
  )
}))

const state: MoaState = {
  aggregatorLabel: 'judge',
  phase: 'fanout',
  refsDone: 2,
  refsTotal: 6,
  slots: Array.from({ length: 6 }, (_, index) => ({
    id: index + 1,
    label: `advisor-${index + 1}`,
    status: index < 2 ? 'complete' : 'running'
  }))
}

afterEach(() => vi.restoreAllMocks())

describe('MoaThinkingOrbs', () => {
  it('uses library auto theme and six solving markers without muted ink', () => {
    render(<MoaThinkingOrbs reducedMotion={false} state={state} />)
    const orbs = screen.getAllByTestId('thinking-orb')

    expect(orbs).toHaveLength(7)
    expect(orbs.every(orb => orb.dataset.theme === 'auto')).toBe(true)
    expect(orbs.slice(0, 6).every(orb => orb.dataset.state === 'solving')).toBe(true)
    expect(screen.getByTestId('moa-thinking-orbs').className).toContain('text-foreground')
    expect(screen.getByTestId('moa-thinking-orbs').className).not.toContain('muted')
  })

  it('pauses all animation for reduced motion', () => {
    render(<MoaThinkingOrbs reducedMotion state={state} />)
    expect(screen.getAllByTestId('thinking-orb').every(orb => orb.dataset.paused === 'true')).toBe(true)
  })

  it('keeps details expansion-only and announces status without a timer', () => {
    render(<MoaThinkingOrbs reducedMotion state={state} />)
    expect(screen.queryByText('advisor-1')).toBeNull()
    expect(screen.getByRole('status').textContent).toBe('MoA 2 of 6 advisors')

    fireEvent.click(screen.getByRole('button', { name: 'Expand MoA details' }))
    expect(screen.getByText('advisor-1')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Collapse MoA details' })).toBeTruthy()
  })

  it('renders terminal colors and a compact settled summary', () => {
    const terminal: MoaState = {
      ...state,
      phase: 'settled',
      slots: [
        { id: 1, status: 'complete' },
        { id: 2, status: 'failed' },
        { id: 3, status: 'interrupted' }
      ],
      refsDone: 3,
      refsTotal: 3
    }

    render(<MoaThinkingOrbs reducedMotion state={terminal} />)

    expect(screen.getByText('3 advisors → judge')).toBeTruthy()
    cleanup()
    render(<MoaThinkingOrbs reducedMotion state={{ ...terminal, phase: 'fanout' }} />)
    expect(screen.getByTestId('moa-marker-2').className).toContain('text-red-500')
    expect(screen.getByTestId('moa-marker-3').className).toContain('text-amber-500')
  })
})
