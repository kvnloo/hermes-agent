import { describe, expect, it } from 'vitest'

import type { SubagentProgress } from '../types.js'
import { projectTernSubagents } from './subagentProjection.js'

const agent = (patch: Partial<SubagentProgress> = {}): SubagentProgress => ({
  apiCalls: 3,
  costUsd: 0.012,
  depth: 1,
  durationSeconds: 4.2,
  goal: 'Review the empty-title edge case',
  id: 'worker-7',
  index: 0,
  inputTokens: 1200,
  model: 'fixture/model',
  notes: [],
  outputTokens: 220,
  parentId: null,
  status: 'running',
  summary: '',
  taskCount: 1,
  thinking: [],
  toolCount: 2,
  tools: ['read', 'grep'],
  ...patch
})

describe('native subagent projection', () => {
  it('keeps one stable semantic id while authoritative lifecycle changes', () => {
    const running = projectTernSubagents([agent()])[0]!
    const completed = projectTernSubagents([agent({ status: 'completed', durationSeconds: 8.5 })])[0]!

    expect(running.id).toBe('hermes:agent:worker-7')
    expect(completed.id).toBe(running.id)
    expect(running).toMatchObject({
      k: 'agent',
      p: {
        name: 'worker-7',
        task: 'Review the empty-title edge case',
        status: 'running',
        model: 'fixture/model',
        stats: { tools: 2, requests: 3, tokens: 1420, cost: 0.012, age: 4200 },
        collapsible: true
      }
    })
    expect(completed.p).toMatchObject({
      status: 'done',
      stats: { took: 8500 }
    })
  })

  it('maps terminal failure-like states without inventing completion percent', () => {
    const states = [
      ['failed', 'failed'],
      ['error', 'failed'],
      ['timeout', 'aborted'],
      ['interrupted', 'aborted'],
      ['queued', 'queued']
    ] as const

    for (const [source, expected] of states) {
      const node = projectTernSubagents([agent({ status: source })])[0]!
      expect(node.p?.status).toBe(expected)
      expect((node.p?.stats as Record<string, unknown>).done).toBeUndefined()
    }
  })

  it('does not present the historical tools list as a currently running tool', () => {
    const node = projectTernSubagents([agent()])[0]!
    expect(node.p?.tool).toBeUndefined()
  })
})
