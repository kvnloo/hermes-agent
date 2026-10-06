import type { SubagentProgress } from '../types.js'
import type { TernLiveNode } from './liveProjection.js'

const statusOf = (status: SubagentProgress['status']): string => {
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
        collapsed: running
      },
      ...(children.length ? { c: children } : {})
    }
  })
}
