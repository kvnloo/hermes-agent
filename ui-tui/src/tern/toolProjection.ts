import type { TranscriptRow } from '../app/interfaces.js'
import { toolTrailLabel } from '../lib/text.js'
import type { ActiveTool, Msg, NativeToolSnapshot } from '../types.js'
import type { TernLiveNode } from './liveProjection.js'

const toolId = (id: string) => `hermes:tool:${id}`

const runningNode = (tool: ActiveTool): TernLiveNode => ({
  id: toolId(tool.id),
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
            id: `${toolId(tool.id)}:args`,
            k: 'code',
            p: { lang: 'text', text: tool.verboseArgs.trim() }
          }
        ]
      }
    : {})
})

const terminalNode = (tool: NativeToolSnapshot): TernLiveNode => {
  const children: TernLiveNode[] = []

  if (tool.verboseArgs?.trim()) {
    children.push({
      id: `${toolId(tool.id)}:args`,
      k: 'code',
      p: { lang: 'text', text: tool.verboseArgs.trim() }
    })
  }

  if (tool.summary?.trim()) {
    children.push({
      id: `${toolId(tool.id)}:summary`,
      k: 'text',
      p: { text: tool.summary.trim(), tone: tool.status === 'failed' ? 'error' : 'muted' }
    })
  }

  if (tool.resultText?.trim()) {
    children.push({
      id: `${toolId(tool.id)}:result`,
      k: 'code',
      p: { lang: 'text', text: tool.resultText.trim() }
    })
  }

  return {
    id: toolId(tool.id),
    k: 'tool',
    p: {
      name: tool.name,
      title: toolTrailLabel(tool.name),
      ...(tool.context?.trim() ? { target: tool.context.trim(), targetKind: 'text' } : {}),
      status: tool.status === 'done' ? 'done' : tool.status === 'failed' ? 'error' : 'cancelled',
      ...(typeof tool.durationSeconds === 'number' && Number.isFinite(tool.durationSeconds)
        ? { took: Math.max(0, Math.round(tool.durationSeconds * 1000)) }
        : {}),
      collapsible: true,
      collapsed: tool.status === 'done'
    },
    ...(children.length ? { c: children } : {})
  }
}

const snapshotsFromMessages = (messages: readonly Msg[]): NativeToolSnapshot[] =>
  messages.flatMap(message => message.nativeTools ?? [])

export function projectTernActiveTools(tools: readonly ActiveTool[]): readonly TernLiveNode[] {
  return tools.map(runningNode)
}

/** Stable tool projection from existing Hermes turn/transcript state.
 * Terminal snapshots are retained in ordinary Msg segments; active calls then
 * replace the same id in place while running. */
export function projectTernTools(
  historyRows: readonly TranscriptRow[],
  streamSegments: readonly Msg[],
  activeTools: readonly ActiveTool[]
): readonly TernLiveNode[] {
  const ordered: string[] = []
  const byId = new Map<string, TernLiveNode>()

  const put = (id: string, node: TernLiveNode) => {
    if (!byId.has(id)) ordered.push(id)
    byId.set(id, node)
  }

  // Cold-resumed transcripts predate renderer-only nativeTools metadata. Keep
  // their existing tool trail visible as a generic historical row instead of
  // guessing a tool id/status from formatted prose.
  for (const row of historyRows) {
    if (row.msg.nativeTools?.length || !row.msg.tools?.length) {
      continue
    }

    const historyId = `history:${row.key.replace(/:c\d+$/, '')}`
    put(historyId, {
      id: `hermes:tool-${historyId}`,
      k: 'text',
      p: { text: row.msg.tools.join('\n'), tone: 'muted' }
    })
  }

  for (const snapshot of [
    ...snapshotsFromMessages(historyRows.map(row => row.msg)),
    ...snapshotsFromMessages(streamSegments)
  ]) {
    put(snapshot.id, terminalNode(snapshot))
  }

  for (const tool of activeTools) {
    put(tool.id, runningNode(tool))
  }

  return ordered.map(id => byId.get(id)!).filter(Boolean)
}
