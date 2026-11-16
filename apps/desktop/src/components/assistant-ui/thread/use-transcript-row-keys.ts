import { useAuiState } from '@assistant-ui/react'
import { useState } from 'react'

interface MessageIdentity {
  id: string
  rowIds: number[]
}

interface RowKeyState {
  signature: string
  scope: string | null | undefined
  byId: Map<string, { key: string; rowIds: number[] }>
  byRowId: Map<number, string>
  keys: string[]
}

function reconcileRowKeys(signature: string, scope: RowKeyState['scope'], previous?: RowKeyState): RowKeyState {
  const identities: MessageIdentity[] = JSON.parse(signature)
  const byId: RowKeyState['byId'] = new Map()
  const byRowId = new Map<number, string>()
  const seen = new Set<string>()

  const keys = identities.map(({ id, rowIds }) => {
    const prior = previous?.byId.get(id)
    const sameOccurrence = !prior || !prior.rowIds.length || !rowIds.length || rowIds.some(rowId => prior.rowIds.includes(rowId))
    const known =
      rowIds.map(rowId => previous?.byRowId.get(rowId)).find(key => key !== undefined) ??
      (sameOccurrence ? prior?.key : undefined)

    const candidate = known ?? JSON.stringify([scope, rowIds.length ? 'row' : 'message', rowIds[0] ?? id])
    // Hydration can split one durable row across several rendered messages.
    const key = seen.has(candidate) ? JSON.stringify([scope, 'message', id]) : candidate
    seen.add(key)
    byId.set(id, { key, rowIds })

    for (const rowId of rowIds) {
      if (!byRowId.has(rowId)) {
        byRowId.set(rowId, key)
      }
    }

    return key
  })

  // Keep aliases only for the current transcript window.
  return { signature, scope, byId, byRowId, keys }
}

/** Bind durable ids to the first render key, rather than replacing that key. */
export function useTranscriptRowKeys(scope: RowKeyState['scope']): readonly string[] {
  const signature = useAuiState(s =>
    JSON.stringify(
      s.thread.messages.map(message => {
        const rowId = message.metadata?.custom?.rowId
        const rowIds = new Set<number>(typeof rowId === 'number' ? [rowId] : [])

        // A history fold can move the bubble's rowId but retains its parts' source rows.
        for (const part of message.content) {
          if ('sourceRowId' in part && typeof part.sourceRowId === 'number') {
            rowIds.add(part.sourceRowId)
          }
        }

        return { id: message.id, rowIds: [...rowIds] }
      })
    )
  )

  const [state, setState] = useState(() => reconcileRowKeys(signature, scope))

  if (state.signature !== signature || state.scope !== scope) {
    const next = reconcileRowKeys(signature, scope, state.scope === scope ? state : undefined)
    setState(next)

    return next.keys
  }

  return state.keys
}
