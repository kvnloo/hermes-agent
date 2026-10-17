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

function node(value: unknown): Node {
  if (!(value instanceof Node)) {
    throw new Error('A tool card element must be a node')
  }

  return value
}

describe('tool cards', () => {
  it('nests child agents by explicit parent id with stable keys', () => {
    const card = node(toolNode({
      args: { tasks: [{ goal: 'root task' }] }, argsText: '', context: '', id: 'call', name: 'delegate_task',
      startedAt: 0, status: 'running',
      subagents: [
        { id: 'root', goal: 'Root', index: 0, status: 'running', startedAt: 0, toolCount: 0, tokens: 0, calls: 0 },
        { id: 'child', parentId: 'root', goal: 'Child', index: 1, status: 'running', startedAt: 0, toolCount: 0, tokens: 0, calls: 0 }
      ]
    }, 0))
    const agents = card.children.filter(child => child instanceof Node && child.kind === 'agent') as Node[]
    expect(agents).toHaveLength(1)
    expect(agents[0]?.props.key).toBe('root')
    const nested = agents[0]?.children.filter(child => child instanceof Node && child.kind === 'agent') as Node[]
    expect(nested).toHaveLength(1)
    expect(nested[0]?.props.key).toBe('child')
  })

  it('keeps cyclic agent parent ids flat rather than recursing', () => {
    const card = node(toolNode({
      args: {}, argsText: '', context: '', id: 'call', name: 'delegate_task',
      startedAt: 0, status: 'running',
      subagents: [
        { id: 'left', parentId: 'right', goal: 'Left', index: 0, status: 'running', startedAt: 0, toolCount: 0, tokens: 0, calls: 0 },
        { id: 'right', parentId: 'left', goal: 'Right', index: 1, status: 'running', startedAt: 0, toolCount: 0, tokens: 0, calls: 0 }
      ]
    }, 0))
    expect(card.children.filter(child => child instanceof Node && child.kind === 'agent')).toHaveLength(2)
  })

  it('folds a long read to three lines and badges the rest', () => {
    const card = node(toolNode(read('1|a\n2|b\n3|c\n4|d\n5|e'), 0))

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
    const card = node(toolNode(
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
    ))

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
    expect(node(card.children[0]).props.lang).toBe('typescript')
  })

  it('keeps a failed shell failed, folded, and exited', () => {
    const output = Array.from({ length: 14 }, (_, i) => `line ${i}`).join('\n')

    const card = node(toolNode(
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
    ))

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
    const card = node(toolNode(
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
    ))

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

    const body = node(card.children[0])
    const result = node(body.children[0])
    const code = node(result.children[1])

    expect(code.props.lang).toBe('python')
  })

  it('keeps a short edit open and shows the diff stats', () => {
    const card = node(toolNode(
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
    ))

    expect(card.props).toMatchObject({
      collapsed: false,
      meta: ['+1 −1'],
      name: 'edit',
      title: 'Edit'
    })
    expect(card.props.preview).toBeUndefined()
    expect(node(card.children[0]).props.lang).toBe('typescript')
  })
})
