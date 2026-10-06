import { toolTrailLabel } from '../lib/text.js'
import type { ActiveTool } from '../types.js'
import type { TernLiveNode } from './liveProjection.js'

export function projectTernActiveTools(tools: readonly ActiveTool[]): readonly TernLiveNode[] {
  return tools.map(tool => ({
    id: `hermes:tool:${tool.id}`,
    k: 'tool',
    p: {
      name: tool.name,
      title: toolTrailLabel(tool.name),
      ...(tool.context?.trim() ? { target: tool.context.trim(), targetKind: 'text' } : {}),
      status: 'running',
      collapsible: true,
      collapsed: false
    },
    ...(tool.verboseArgs?.trim()
      ? {
          c: [
            {
              id: `hermes:tool:${tool.id}:args`,
              k: 'code',
              p: { lang: 'text', text: tool.verboseArgs.trim() }
            }
          ]
        }
      : {})
  }))
}
