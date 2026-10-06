import { describe, expect, it } from 'vitest'

import type { SubagentProgress } from '../types.js'
import { TernComposerTransport, TERN_SURFACE_ID } from './composerSurface.js'
import { parseTspApc, type TspHello } from './protocol.js'
import { projectTernSubagents } from './subagentProjection.js'

const hello: TspHello = {
  r: 'hello',
  v: 1,
  term: 'tern',
  kinds: ['col', 'editor', 'md', 'card', 'agent'],
  features: ['dock'],
  credits: 1
}

const agent = (status: SubagentProgress['status']): SubagentProgress => ({
  apiCalls: 1,
  depth: 1,
  durationSeconds: status === 'running' ? 2 : 5,
  goal: 'Review the edge case',
  id: 'worker-1',
  index: 0,
  model: 'fixture/model',
  notes: [],
  parentId: null,
  status,
  taskCount: 1,
  thinking: [],
  toolCount: 1,
  tools: ['read']
})

const decode = (wire: string) => {
  const envelope = parseTspApc(wire.slice(2, -2))!
  return { verb: envelope.verb, body: JSON.parse(envelope.body) }
}

describe('native subagent surface lifecycle', () => {
  it('updates the same agent node in place across running to completion', () => {
    const writes: string[] = []
    const transport = new TernComposerTransport(data => writes.push(data), hello)

    transport.start({ cursor: 0, text: '' }, false, projectTernSubagents([agent('running')]))
    transport.update({ cursor: 0, text: '' }, false, projectTernSubagents([agent('completed')]))

    expect(writes).toHaveLength(2)
    transport.handleEvent({ ev: 'ack', sf: TERN_SURFACE_ID, s: 1 })

    expect(writes).toHaveLength(3)
    const ops = decode(writes[2]!).body.ops as unknown[][]
    expect(JSON.stringify(ops)).toContain('hermes:agent:worker-1')
    expect(JSON.stringify(ops)).toContain('"done"')
    expect(ops.some(op => op[0] === 'del' && op[1] === 'hermes:agent:worker-1')).toBe(false)
    expect(ops.some(op => op[0] === 'add' && op[1] === 'hermes:agent:worker-1')).toBe(false)
  })
})
