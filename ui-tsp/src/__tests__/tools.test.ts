import { describe, expect, it } from 'vitest'

import type { ToolCall } from '../model.js'
import { toolNode } from '../view/tools.js'

function read(content: string): ToolCall {
  return {
    args: { path: 'src/index.ts' },
    argsText: '',
    context: 'src/index.ts',
    id: 'r1',
    name: 'read_file',
    result: { content, total_lines: 5 },
    startedAt: 0,
    status: 'done'
  }
}

describe('tool cards', () => {
  it('folds a long read to three lines and badges the rest', () => {
    const card = toolNode(read('1|a\n2|b\n3|c\n4|d\n5|e'), 0)

    expect(card.props).toMatchObject({
      badges: [{ text: '2 more lines', tone: 'muted' }],
      frame: 'inline',
      lang: 'typescript',
      name: 'read',
      preview: { lines: 3 },
      title: 'Read'
    })
    expect(card.children[0]?.props.lang).toBe('typescript')
  })
})
