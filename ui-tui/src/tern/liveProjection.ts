import type { TranscriptRow } from '../app/interfaces.js'

export interface TernLiveNode {
  id: string
  k: string
  p?: Record<string, unknown>
  c?: readonly TernLiveNode[]
}

export const stableTernMessageId = (row: Pick<TranscriptRow, 'key'>): string =>
  `hermes:message:${row.key.replace(/:c\\d+$/, '')}`

export function projectTernTranscript(
  _rows: readonly TranscriptRow[],
  _streaming: string
): readonly TernLiveNode[] {
  return []
}
