import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'
import {
  applyMoaEvent,
  emptyMoaState,
  type MoaOrchestrationState
} from '@/lib/moa-orchestration'

import { MoaThinkingOrbs } from './moa-thinking-orbs'

vi.mock('thinking-orbs', () => ({
  ThinkingOrb: ({
    paused,
    size,
    state,
    theme
  }: {
    paused?: boolean
    size?: number
    state?: string
    theme?: string
  }) => (
    <span
      data-reduced-motion={paused ? 'true' : 'false'}
      data-size={size}
      data-state={state}
      data-theme={theme}
      data-thinking-orb=""
    />
  )
}))

function wrap(ui: React.ReactNode) {
  return render(<I18nProvider configClient={null}>{ui}</I18nProvider>)
}

function fanoutState(): MoaOrchestrationState {
  let state = applyMoaEvent(emptyMoaState(), {
    payload: { refs_done: 0, refs_total: 6, state: 'waiting', elapsed_seconds: 5 },
    type: 'moa.progress'
  })

  state = applyMoaEvent(state, {
    payload: { index: 4, label: 'mock:ref-delta', refs_done: 1, refs_total: 6 },
    type: 'moa.progress'
  })

  return state
}

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('MoaThinkingOrbs', () => {
  it('renders a single inline row with parallel copy, counts, six markers, and waiting aggregator', () => {
    wrap(<MoaThinkingOrbs state={fanoutState()} />)

    const row = screen.getByTestId('moa-thinking-orbs')
    expect(row.getAttribute('data-footprint')).toBe('inline')
    expect(row.querySelectorAll('[data-thinking-orb][data-state="solving"]').length).toBe(6)
    expect(row.querySelector('[data-thinking-orb][data-size="20"]')).not.toBeNull()
    expect(row.textContent).toMatch(/parallel/i)
    expect(row.textContent).toContain('1/6')
    expect(row.textContent).toMatch(/waiting/i)
    expect(screen.queryByTestId('moa-thinking-orbs-details')).toBeNull()
  })

  it('keeps the default footprint to one scaffold line, not a dashboard grid', () => {
    wrap(<MoaThinkingOrbs state={fanoutState()} />)

    const row = screen.getByTestId('moa-thinking-orbs')
    expect(row.getAttribute('data-line-height')).toBe('scaffold')
    expect(row.querySelector('[data-layout="grid"]')).toBeNull()
    expect(row.querySelectorAll('[data-advisor-prose]')).toHaveLength(0)
  })

  it('expands compact labels and hides advisor prose until a slot is opened', () => {
    let state = fanoutState()
    state = applyMoaEvent(state, {
      payload: { count: 6, index: 4, label: 'mock:ref-delta', text: 'delta advice' },
      type: 'moa.reference'
    })

    wrap(<MoaThinkingOrbs state={state} />)

    fireEvent.click(screen.getByRole('button', { name: /MoA/i }))

    const details = screen.getByTestId('moa-thinking-orbs-details')
    expect(details.textContent).toContain('mock:ref-delta')
    expect(details.querySelectorAll('[data-advisor-prose]')).toHaveLength(0)

    fireEvent.click(screen.getByRole('button', { name: /mock:ref-delta/i }))
    expect(screen.getByTestId('moa-advisor-output').textContent).toContain('delta advice')
  })

  it('uses high-contrast ink: white on near-black in dark, black on white in light', () => {
    const { rerender } = wrap(<MoaThinkingOrbs state={fanoutState()} theme="dark" />)
    expect(screen.getByTestId('moa-thinking-orbs').getAttribute('data-ink')).toBe('light')

    rerender(
      <I18nProvider configClient={null}>
        <MoaThinkingOrbs state={fanoutState()} theme="light" />
      </I18nProvider>
    )
    expect(screen.getByTestId('moa-thinking-orbs').getAttribute('data-ink')).toBe('dark')
  })

  it('passes reduced motion through to the library orbs and skips completion bounce', () => {
    wrap(<MoaThinkingOrbs reducedMotion state={fanoutState()} />)

    const orbs = screen.getByTestId('moa-thinking-orbs').querySelectorAll('[data-thinking-orb]')
    expect([...orbs].every(orb => orb.getAttribute('data-reduced-motion') === 'true')).toBe(true)
    expect(screen.getByTestId('moa-thinking-orbs').getAttribute('data-completion-bounce')).toBe('off')
  })

  it('announces status once and does not mention elapsed seconds', () => {
    wrap(<MoaThinkingOrbs elapsedSeconds={12} state={fanoutState()} />)

    const live = screen.getByRole('status')
    expect(live.getAttribute('aria-live')).toBe('polite')
    expect(live.textContent?.toLowerCase()).toContain('parallel')
    expect(live.textContent).not.toContain('12s')
    expect(live.textContent).not.toContain('5s')
  })

  it('shows a compact settled summary that can still expand', () => {
    let state = applyMoaEvent(emptyMoaState(), {
      payload: { index: 1, label: 'a', refs_done: 1, refs_total: 1 },
      type: 'moa.progress'
    })

    state = applyMoaEvent(state, {
      payload: { aggregator: 'mix', phase: 'aggregator', refs_done: 1, refs_total: 1 },
      type: 'moa.phase'
    })
    state = applyMoaEvent(state, { payload: {}, type: 'message.complete' })

    wrap(<MoaThinkingOrbs state={state} />)

    expect(screen.getByTestId('moa-thinking-orbs').textContent).toMatch(/1 advisors → mix/i)
    expect(screen.queryByTestId('moa-thinking-orbs-details')).toBeNull()

    fireEvent.click(screen.getByRole('button', { name: /MoA/i }))
    expect(screen.getByTestId('moa-thinking-orbs-details')).not.toBeNull()
  })

  it('colors terminal states and never treats unknown progress as a thought percent', () => {
    let state = applyMoaEvent(emptyMoaState(), { payload: { refs_done: 0, refs_total: 3 }, type: 'moa.progress' })
    state = applyMoaEvent(state, {
      payload: { count: 3, index: 1, label: 'ok', text: 'advice' },
      type: 'moa.reference'
    })
    state = applyMoaEvent(state, {
      payload: { count: 3, index: 2, label: 'boom', text: '[failed: timeout]' },
      type: 'moa.reference'
    })
    state = applyMoaEvent(state, {
      payload: { count: 3, index: 3, label: 'halted', text: '[skipped: interrupted by user]' },
      type: 'moa.reference'
    })

    wrap(<MoaThinkingOrbs state={state} />)

    const markers = screen.getByTestId('moa-advisor-markers').children
    expect(markers[0]?.getAttribute('data-terminal')).toBe('complete')
    expect(markers[1]?.getAttribute('data-terminal')).toBe('failed')
    expect(markers[2]?.getAttribute('data-terminal')).toBe('interrupted')
    expect(screen.queryByText(/%/)).toBeNull()
    expect(screen.queryByText(/thought/i)).toBeNull()
  })
})
