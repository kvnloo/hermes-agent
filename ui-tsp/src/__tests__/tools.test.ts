import { Node } from '@stencil-hq/tern'
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

    if (!(card instanceof Node)) {
      throw new Error('A tool card must be a node')
    }

    const body = card.children[0]

    expect(card.props).toMatchObject({
      badges: [{ text: '2 more lines', tone: 'muted' }],
      frame: 'inline',
      lang: 'typescript',
      name: 'read',
      preview: { lines: 3 },
      title: 'Read'
    })
    expect(body instanceof Node && body.props.lang).toBe('typescript')
  })

  it('folds a long write and keeps the syntax language', () => {
    const card = toolNode(
      {
        args: { content: Array.from({ length: 12 }, (_, i) => `const n${i} = ${i}`).join('\n'), path: 'src/new.ts' },
        argsText: '',
        context: 'src/new.ts',
        id: 'w1',
        name: 'write_file',
        result: { diff: '@@ -0,0 +1,12 @@\n' },
        startedAt: 0,
        status: 'done'
      },
      0
    )

    expect(card.props).toMatchObject({
      badges: [
        { text: 'new file', tone: 'success' },
        { text: '4 more lines', tone: 'muted' }
      ],
      collapsed: true,
      name: 'write',
      preview: { lines: 8 },
      title: 'Write'
    })
    expect(card.children[0]?.props.lang).toBe('typescript')
  })

  it('keeps a failed shell failed, folded, and exited', () => {
    const output = Array.from({ length: 14 }, (_, i) => `line ${i}`).join('\n')
    const card = toolNode(
      {
        args: { command: 'npm test' },
        argsText: '',
        context: 'npm test',
        id: 'b1',
        name: 'terminal',
        result: { error: 'fail', exit_code: 1, output },
        startedAt: 0,
        status: 'error'
      },
      0
    )

    expect(card.props).toMatchObject({
      badges: [{ text: '4 more lines', tone: 'muted' }],
      collapsed: true,
      exit: 1,
      lang: 'bash',
      name: 'bash',
      preview: { tail: 10 },
      status: 'error',
      title: 'Bash'
    })
  })

  it('folds a long eval and keeps the code language', () => {
    const card = toolNode(
      {
        args: { code: 'print(1)\n', language: 'python' },
        argsText: '',
        context: 'print(1)',
        id: 'e1',
        name: 'execute_code',
        result: { output: Array.from({ length: 12 }, (_, i) => `out ${i}`).join('\n') },
        startedAt: 0,
        status: 'done'
      },
      0
    )

    expect(card.props).toMatchObject({
      badges: [
        { text: 'python' },
        { text: '4 more lines', tone: 'muted' }
      ],
      collapsed: true,
      name: 'eval',
      preview: { lines: 8 },
      title: 'Eval'
    })
    expect(card.children[0]?.children?.[0]?.children?.[1]?.props.lang).toBe('python')
  })

  it('keeps a short edit open and shows the diff stats', () => {
    const card = toolNode(
      {
        args: { path: 'src/index.ts' },
        argsText: '',
        context: 'src/index.ts',
        diff: '@@ -1 +1 @@\n-a\n+b\n',
        id: 'd1',
        name: 'patch',
        startedAt: 0,
        status: 'done'
      },
      0
    )

    expect(card.props).toMatchObject({
      collapsed: false,
      meta: ['+1 −1'],
      name: 'edit',
      title: 'Edit'
    })
    expect(card.props.preview).toBeUndefined()
    expect(card.children[0]?.props.lang).toBe('typescript')
  })
})
