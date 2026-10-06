import type { SubagentProgress } from '../types.js'
import type { TernLiveNode } from './liveProjection.js'

const statusOf = (status: SubagentProgress['status']): string => {
  if (status === 'queued') return 'pending'
  if (status === 'completed') return 'done'
  if (status === 'failed' || status === 'error') return 'failed'
  if (status === 'timeout' || status === 'interrupted') return 'aborted'
  return status
}

const tokenTotal = (agent: SubagentProgress): number | undefined => {
  const total =
    (agent.inputTokens ?? 0) +
    (agent.outputTokens ?? 0) +
    (agent.reasoningTokens ?? 0)

  return total > 0 ? total : undefined
}

const millis = (seconds?: number): number | undefined =>
  typeof seconds === 'number' && Number.isFinite(seconds) && seconds >= 0
    ? Math.round(seconds * 1000)
    : undefined

export function projectTernSubagents(subagents: readonly SubagentProgress[]): readonly TernLiveNode[] {
  return subagents.map(agent => {
    const running = agent.status === 'running'
    const duration = millis(agent.durationSeconds)
    const stats: Record<string, unknown> = {
      ...(agent.toolCount > 0 ? { tools: agent.toolCount } : {}),
      ...(agent.apiCalls && agent.apiCalls > 0 ? { requests: agent.apiCalls } : {}),
      ...(tokenTotal(agent) ? { tokens: tokenTotal(agent) } : {}),
      ...(agent.costUsd && agent.costUsd > 0 ? { cost: agent.costUsd } : {}),
      ...(duration !== undefined ? (running ? { age: duration } : { took: duration }) : {})
    }

    const children: TernLiveNode[] = []

    if (agent.summary?.trim()) {
      children.push({
        id: `hermes:agent:${agent.id}:summary`,
        k: 'md',
        p: { text: agent.summary.trim() }
      })
    } else {
      const thinking = agent.thinking.at(-1)?.trim()
      const note = agent.notes.at(-1)?.trim()

      if (thinking) {
        children.push({
          id: `hermes:agent:${agent.id}:thinking`,
          k: 'text',
          p: { text: thinking, tone: 'muted' }
        })
      }

      if (note) {
        children.push({
          id: `hermes:agent:${agent.id}:note`,
          k: 'text',
          p: { text: note, tone: 'muted' }
        })
      }
    }

    const output = agent.outputTail ?? []
    const start = Math.max(0, output.length - 3)

    for (let index = start; index < output.length; index += 1) {
      const item = output[index]!

      children.push({
        id: `hermes:agent:${agent.id}:output:${index}`,
        k: 'text',
        p: {
          text: `${item.tool}: ${item.preview}`,
          tone: item.isError ? 'error' : 'muted'
        }
      })
    }

    return {
      id: `hermes:agent:${agent.id}`,
      k: 'agent',
      p: {
        name: agent.id,
        task: agent.goal || undefined,
        status: statusOf(agent.status),
        model: agent.model || undefined,
        stats,
        depth: agent.depth > 0 ? agent.depth : undefined,
        collapsible: true,
        // Keep the authored value stable so a Tern-side disclosure toggle is not
        // overwritten when lifecycle/stats update in place.
        collapsed: true
      },
      ...(children.length ? { c: children } : {})
    }
  })
}
