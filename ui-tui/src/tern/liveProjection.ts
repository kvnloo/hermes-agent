import type { TranscriptRow } from '../app/interfaces.js'

export interface TernLiveNode {
  id: string
  k: string
  p?: Record<string, unknown>
  c?: readonly TernLiveNode[]
}

export const stableTernMessageId = (row: Pick<TranscriptRow, 'key'>): string =>
  `hermes:message:${row.key.replace(/:c\\d+$/, '')}`

const proseNode = (row: TranscriptRow): TernLiveNode | null => {
  const { msg } = row

  // First dogfood slice is intentionally prose-only. Intro/panel/trail/diff
  // rows keep their proven Ink presentation until each semantic family has
  // its own native contract.
  if (msg.kind || (msg.role !== 'user' && msg.role !== 'assistant') || !msg.text.trim()) {
    return null
  }

  const id = stableTernMessageId(row)

  if (msg.role === 'user') {
    return {
      id,
      k: 'card',
      p: { role: 'omp.user', tone: 'user' },
      c: [{ id: `${id}:text`, k: 'md', p: { text: msg.text } }]
    }
  }

  return { id, k: 'md', p: { text: msg.text } }
}

export function projectTernTranscript(
  rows: readonly TranscriptRow[],
  streaming: string
): readonly TernLiveNode[] {
  const nodes = rows.map(proseNode).filter((node): node is TernLiveNode => node !== null)

  if (streaming.trim()) {
    nodes.push({
      id: 'hermes:streaming',
      k: 'md',
      p: { text: streaming }
    })
  }

  return nodes
}
