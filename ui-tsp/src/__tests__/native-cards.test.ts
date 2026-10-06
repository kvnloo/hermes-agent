import { describe, expect, it } from 'vitest'

import type { ToolCall } from '../model.js'
import { toolNode } from '../view/tools.js'

function call(partial: Partial<ToolCall> & Pick<ToolCall, 'name'>): ToolCall {
  return {
    args: {},
    argsText: '',
    context: '',
    id: 'c1',
    startedAt: 0,
    status: 'done',
    ...partial
  }
}

function kinds(node: { kind: string; children?: readonly { kind: string; children?: readonly unknown[] }[] }): string[] {
  return [node.kind, ...(node.children ?? []).flatMap(child => kinds(child as typeof node))]
}

describe('native tool cards', () => {
  it('draws bash output as code, not ansi', () => {
    const card = toolNode(
      call({
        args: { command: 'ls' },
        name: 'terminal',
        result: { output: '\u001b[32mtotal 1\u001b[0m' }
      }),
      0
    )

    expect(kinds(card)).not.toContain('ansi')
    expect(kinds(card)).toContain('code')
    expect(card.children[0]?.props.text).toBe('total 1')
  })

  it('folds a long read to three lines and badges the rest', () => {
    const card = toolNode(
      call({
        args: { path: 'src/index.ts' },
        name: 'read_file',
        result: { content: '1|a\n2|b\n3|c\n4|d\n5|e', total_lines: 5 }
      }),
      0
    )

    expect(card.props).toMatchObject({
      badges: [{ text: '2 more lines', tone: 'muted' }],
      name: 'read',
      preview: { lines: 3 }
    })
  })
})
