import { type Tree, View } from '@stencil-hq/tern'
import { describe, expect, it, vi } from 'vitest'

import { Composer } from '../composer.js'
import { type DockContext, dockNodes } from '../view/dock.js'

function context(): DockContext {
  const noop = () => {}

  return {
    branch: '', busy: { label: 'Working', since: {}, startedAt: 0 }, composer: new Composer(),
    cwd: '/fixture', dispatches: [], effort: '', inputId: 'composer', jobs: 0, model: 'fixture', now: 1000,
    onContext: noop, onDismiss: noop, onEdit: noop, onEffort: noop, onInterrupt: vi.fn(), onJobs: noop,
    onModel: noop, onQueueEdit: noop, onSend: noop, onSettings: noop, onSubmit: noop, onTodoToggle: noop,
    onUndo: noop, placeholder: 'Ask Hermes', queued: [], ready: false, todoExpanded: false, todos: []
  }
}

const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])
const render = (cx: DockContext) => flatten(View.from({ dock: dockNodes(cx) }).regions.flatMap(region => region?.children ?? []))

describe('OMP working-row indicator', () => {
  it('retains the native spinner without requiring an image orb, before elapsed and intent', () => {
    const cx = context()
    const nodes = render(cx)
    const row = nodes.find(node => node.props.role === 'omp.working')!

    expect(row.children.slice(0, 4).map(node => node.kind)).toEqual(['spinner', 'elapsed', 'text', 'shimmer'])
    expect(row.children[0]?.props).toMatchObject({ style: 'starburst', tone: 'accent' })
    expect(nodes.some(node => node.props.role === 'hermes.agent.orb')).toBe(false)
    const stop = nodes.find(node => node.props.role === 'omp.working.stop')!

    expect(stop.props.tag).toBe('button')
    expect(stop.node.handlers?.onClick).toBe(cx.onInterrupt)
  })

  it('removes the working row when idle', () => {
    const cx = context()
    cx.busy = undefined
    expect(render(cx).some(node => node.props.role === 'omp.working')).toBe(false)
  })
})
