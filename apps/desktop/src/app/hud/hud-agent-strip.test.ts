import { describe, expect, it } from 'vitest'

import { neighbors, stepAgentTarget, type AgentTarget } from './hud-agent-strip'

const windows: AgentTarget[] = [
  { app: 'kitty', id: 1, title: 'term' },
  { app: 'firefox', id: 2, title: 'web' },
  { app: 'code', id: 3, title: 'edit' }
]

describe('stepAgentTarget', () => {
  it('wraps left from the first app', () => {
    expect(stepAgentTarget(windows, 1, -1)).toBe(3)
  })

  it('wraps right from the last app', () => {
    expect(stepAgentTarget(windows, 3, 1)).toBe(1)
  })

  it('starts at the first app when nothing is selected', () => {
    expect(stepAgentTarget(windows, null, 1)).toBe(1)
  })
})

describe('neighbors', () => {
  it('shows both neighbors around the center', () => {
    expect(neighbors(windows, 2)).toEqual({
      center: windows[1],
      left: windows[0],
      right: windows[2]
    })
  })
})
