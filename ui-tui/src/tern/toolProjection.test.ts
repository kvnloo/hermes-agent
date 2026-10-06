import { describe, expect, it } from 'vitest'

import type { ActiveTool } from '../types.js'
import { projectTernActiveTools } from './toolProjection.js'

const tool = (patch: Partial<ActiveTool> = {}): ActiveTool => ({
  context: 'src/tasks.ts',
  id: 'call-7',
  name: 'read_file',
  startedAt: 1_000,
  verboseArgs: '{"path":"src/tasks.ts"}',
  ...patch
})

describe('native running-tool projection', () => {
  it('uses the Hermes tool call id as stable native identity', () => {
    const first = projectTernActiveTools([tool()])[0]!
    const updated = projectTernActiveTools([tool({ context: 'src/tasks.ts:20-40' })])[0]!

    expect(first.id).toBe('hermes:tool:call-7')
    expect(updated.id).toBe(first.id)
    expect(first).toMatchObject({
      k: 'tool',
      p: {
        name: 'read_file',
        title: 'Read File',
        target: 'src/tasks.ts',
        targetKind: 'text',
        status: 'running',
        collapsible: true,
        collapsed: false
      }
    })
  })

  it('never fabricates terminal success or failure from a running snapshot', () => {
    const node = projectTernActiveTools([tool({ context: 'error: permission denied' })])[0]!
    expect(node.p?.status).toBe('running')
    expect(node.p?.note).toBeUndefined()
  })

  it('keeps each concurrent call distinct even when names match', () => {
    const nodes = projectTernActiveTools([tool(), tool({ id: 'call-8' })])
    expect(nodes.map(node => node.id)).toEqual(['hermes:tool:call-7', 'hermes:tool:call-8'])
  })
})
