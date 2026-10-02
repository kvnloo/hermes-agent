import { PassThrough } from 'node:stream'

import { Box, forceRedraw, renderSync, Text } from '@hermes/ink'
import type { GoalSnapshot } from '@hermes/shared/gateway-events'
import React, { Profiler } from 'react'
import stripAnsi from 'strip-ansi'
import { expect, it, vi } from 'vitest'

import { applyGoalSnapshot, goalLine } from '../app/goalStatus.js'
import { getUiState, patchUiState, resetUiState } from '../app/uiStore.js'
import { GoalBar, GoalBarView } from '../components/goalBar.js'
import { DEFAULT_THEME } from '../theme.js'

const goal = (patch: Partial<GoalSnapshot> = {}): GoalSnapshot => ({
  contract: {},
  gates: [],
  max_turns: 20,
  status: 'active',
  subgoals: [],
  title: 'ship the goal bar',
  turns_used: 3,
  ...patch
})

const paint = (element: React.ReactElement): string => {
  const stdout = Object.assign(new PassThrough(), { columns: 60, rows: 10 })
  const frames: string[] = []
  stdout.on('data', chunk => frames.push(chunk.toString()))

  const view = renderSync(element, {
    stdout: stdout as unknown as NodeJS.WriteStream,
    stdin: new PassThrough() as unknown as NodeJS.ReadStream
  })

  view.unmount()
  view.cleanup()

  return stripAnsi(frames.join(''))
}

it('shows a standing goal (active, parked, paused) and hides it once done or cleared', () => {
  expect(goalLine(goal())).toMatchObject({ detail: '3/20 turns', glyph: '⊙', label: 'goal' })
  expect(
    goalLine(goal({ wait_barrier: { reason: 'build running', target: 'proc_1', type: 'session' } }))
  ).toMatchObject({ detail: 'on session proc_1 · build running · 3/20 turns', glyph: '⏳', label: 'goal parked' })
  expect(goalLine(goal({ paused_reason: 'budget', status: 'paused' }))).toMatchObject({
    detail: 'budget · 3/20 turns',
    label: 'goal paused'
  })
  expect(goalLine(goal({ status: 'done' }))).toBeNull()
  expect(goalLine(null)).toBeNull()

  const painted = paint(<GoalBarView cols={58} line={goalLine(goal())} t={DEFAULT_THEME} />)
  expect(painted).toContain('⊙ goal · 3/20 turns · ship the goal bar')
  expect(paint(<GoalBarView cols={58} line={null} t={DEFAULT_THEME} />).trim()).toBe('')
})

it('keeps the mounted goal consumer asleep for status churn while following theme, goal and session changes', async () => {
  resetUiState()
  applyGoalSnapshot('goal-owner', goal({ title: 'fixturegoal' }))
  patchUiState({ sid: 'goal-owner' })
  const stdout = Object.assign(new PassThrough(), { columns: 80, rows: 10, isTTY: true })
  const stdin = Object.assign(new PassThrough(), { isTTY: false })
  let output = ''
  stdout.on('data', chunk => {
    output += String(chunk)
  })
  const onRender = vi.fn()

  const view = renderSync(
    <Box flexDirection="column" height={6}>
      <Profiler id="goal-consumer" onRender={onRender}>
        <GoalBar cols={78} />
      </Profiler>
      <Text>GOAL_CONTROL</Text>
    </Box>,
    {
      patchConsole: false,
      stdout: stdout as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream
    }
  )

  const frame = () => {
    output = ''
    expect(forceRedraw(stdout as unknown as NodeJS.WriteStream)).toBe(true)
    const text = stripAnsi(output)
    expect(text).toContain('GOAL_CONTROL')

    return text
  }

  try {
    await vi.waitFor(() => expect(frame()).toContain('fixturegoal'))
    const initial = onRender.mock.calls.length
    expect(initial).toBeGreaterThan(0)

    for (let i = 0; i < 20; i++) {
      patchUiState({ status: `streaming-${i}` })
    }

    await new Promise(resolve => setTimeout(resolve, 0))
    expect(onRender).toHaveBeenCalledTimes(initial)
    await vi.waitFor(() => expect(frame()).toContain('fixturegoal'))

    const theme = getUiState().theme
    patchUiState({ theme: { ...theme, color: { ...theme.color, accent: '#ee8844' } } })
    await expect.poll(() => onRender.mock.calls.length).toBe(initial + 1)
    await vi.waitFor(() => expect(frame()).toContain('fixturegoal'))

    applyGoalSnapshot('goal-owner', goal({ title: 'changedgoal', turns_used: 4 }))
    await expect.poll(() => onRender.mock.calls.length).toBe(initial + 2)
    await vi.waitFor(() => {
      const painted = frame()
      expect(painted).toContain('changedgoal')
      expect(painted).toContain('4/20')
    })

    patchUiState({ sid: 'other-session' })
    await expect.poll(() => onRender.mock.calls.length).toBe(initial + 3)
    await vi.waitFor(() => expect(frame()).not.toContain('changedgoal'))

    patchUiState({ sid: 'goal-owner' })
    await expect.poll(() => onRender.mock.calls.length).toBe(initial + 4)
    await vi.waitFor(() => expect(frame()).toContain('changedgoal'))
  } finally {
    view.unmount()
    view.cleanup()
    resetUiState()
    applyGoalSnapshot(null)
  }
})
