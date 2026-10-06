import type { TranscriptRow } from '../app/interfaces.js'

export interface TernLiveNode {
  id: string
  k: string
  p?: Record<string, unknown>
  c?: readonly TernLiveNode[]
}

export const stableTernMessageId = (row: Pick<TranscriptRow, 'key'>): string =>
  `hermes:message:${row.key.replace(/:c\d+$/, '')}`

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


export type TernLiveOp = readonly unknown[]

const sameLiveValue = (left: unknown, right: unknown): boolean =>
  left === right || JSON.stringify(left) === JSON.stringify(right)

/** Keyed semantic reconciliation for the first live transcript slice.
 * Derived from the same stable-id/minimal-op pattern used by OMP's native
 * reconciler, without importing fixture-only state into the live renderer. */
export function reconcileTernLiveNodes(
  parent: string,
  previous: readonly TernLiveNode[],
  next: readonly TernLiveNode[]
): TernLiveOp[] {
  const ops: TernLiveOp[] = []
  const oldById = new Map(previous.map(node => [node.id, node]))
  const nextIds = new Set(next.map(node => node.id))
  const order = previous.map(node => node.id).filter(id => nextIds.has(id))

  for (const old of previous) {
    if (!nextIds.has(old.id)) {
      ops.push(['del', old.id])
    }
  }

  for (let i = next.length - 1; i >= 0; i -= 1) {
    const node = next[i]!
    const before = next[i + 1]?.id ?? null
    const old = oldById.get(node.id)

    if (!old || old.k !== node.k) {
      if (old) {
        ops.push(['del', old.id])
        const at = order.indexOf(old.id)
        if (at >= 0) order.splice(at, 1)
      }

      ops.push(['add', node.id, parent, before, node])
      const anchor = before === null ? order.length : order.indexOf(before)
      order.splice(anchor < 0 ? order.length : anchor, 0, node.id)
      continue
    }

    const at = order.indexOf(node.id)

    if ((order[at + 1] ?? null) !== before) {
      ops.push(['move', node.id, parent, before])
      order.splice(at, 1)
      const anchor = before === null ? order.length : order.indexOf(before)
      order.splice(anchor < 0 ? order.length : anchor, 0, node.id)
    }

    const oldProps = old.p ?? {}
    const props = node.p ?? {}
    const patch: Record<string, unknown> = {}

    for (const key of new Set([...Object.keys(oldProps), ...Object.keys(props)])) {
      const beforeValue = oldProps[key]
      const nextValue = props[key]

      if (sameLiveValue(beforeValue, nextValue)) {
        continue
      }

      if (key === 'text' && typeof beforeValue === 'string' && typeof nextValue === 'string') {
        const append = nextValue.startsWith(beforeValue)
        ops.push([
          'text',
          node.id,
          append ? 'append' : 'replace',
          append ? nextValue.slice(beforeValue.length) : nextValue
        ])
      } else {
        patch[key] = nextValue ?? null
      }
    }

    if (Object.keys(patch).length) {
      ops.push(['set', node.id, patch])
    }

    ops.push(...reconcileTernLiveNodes(node.id, old.c ?? [], node.c ?? []))
  }

  return ops
}
