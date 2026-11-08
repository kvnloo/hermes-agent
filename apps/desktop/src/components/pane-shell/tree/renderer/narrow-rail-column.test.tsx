import { cleanup, render } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { registry } from '@/contrib/registry'
import { stubResizeObserver } from '@/test/jsdom'

import { group, split } from '../model'
import { $hiddenTreePanes, $layoutTree, $narrowViewport } from '../store'

import { TreeSplit } from './tree-split'

// Regression from superniker (NousResearch/hermes-agent#151150): a narrow
// sessions stack with a non-collapsible preview kept a blank docked column.
beforeAll(() => {
  stubResizeObserver()
  vi.stubGlobal('CSS', { ...globalThis.CSS, escape: (value: string) => value })
})

const disposers: (() => void)[] = []

beforeEach(() => {
  window.localStorage.clear()
  $hiddenTreePanes.set(new Set())

  for (const [id, data] of [
    ['sessions', { collapsible: true, placement: 'left', width: '237px' }],
    ['preview', { placement: 'right', width: '237px' }],
    ['workspace', { placement: 'main', uncloseable: true }]
  ] as const) {
    disposers.push(registry.register({ area: 'panes', data, id, render: () => null, title: id }))
  }
})

afterEach(() => {
  cleanup()
  $hiddenTreePanes.set(new Set())
  $layoutTree.set(null)
  $narrowViewport.set(false)
  disposers.splice(0).forEach(dispose => dispose())
})

// The direct split-child wrapper owns the flex track and display:none.
const splitChild = (i: number) =>
  document.querySelector<HTMLElement>('[data-tree-split]')?.children[i] as HTMLElement | undefined

const mixedStackTree = () =>
  split('row', [group(['sessions', 'preview'], { id: 'grp-sessions' }), group(['workspace'], { id: 'grp-main' })])

describe('rails below the sidebar-collapse breakpoint', () => {
  it('drops a mixed stack (collapsible + non-collapsible pane) out of the grid', () => {
    $narrowViewport.set(true)
    const tree = mixedStackTree()

    $layoutTree.set(tree)
    render(<TreeSplit node={tree} root rootRow />)

    expect(splitChild(0)?.style.display).toBe('none')
    expect(splitChild(1)?.style.display).not.toBe('none')
  })

  it('keeps the same stack docked above the breakpoint', () => {
    $narrowViewport.set(false)
    const tree = mixedStackTree()

    $layoutTree.set(tree)
    render(<TreeSplit node={tree} root rootRow />)

    expect(splitChild(0)?.style.display).not.toBe('none')
  })

  it('never drops a column that carries the main pane', () => {
    $narrowViewport.set(true)
    const tree = split('row', [
      group(['sessions'], { id: 'grp-sessions' }),
      group(['workspace', 'preview'], { id: 'grp-mixed-main' })
    ])

    $layoutTree.set(tree)
    render(<TreeSplit node={tree} root rootRow />)

    expect(splitChild(0)?.style.display).toBe('none')
    expect(splitChild(1)?.style.display).not.toBe('none')
  })
})
