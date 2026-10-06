import { describe, expect, it } from 'vitest'

import type { TranscriptRow } from '../app/interfaces.js'
import type { ActiveTool, Msg, NativeToolSnapshot } from '../types.js'
import { projectTernActiveTools, projectTernTools } from './toolProjection.js'

const tool = (patch: Partial<ActiveTool> = {}): ActiveTool => ({
  context: 'src/tasks.ts',
  id: 'call-7',
  name: 'read_file',
  startedAt: 1_000,
  verboseArgs: '{"path":"src/tasks.ts"}',
  ...patch
})

const terminal = (patch: Partial<NativeToolSnapshot> = {}): NativeToolSnapshot => ({
  context: 'src/tasks.ts',
  durationSeconds: 1.25,
  id: 'call-7',
  name: 'read_file',
  resultText: 'ok',
  status: 'done',
  summary: 'Read 12 lines',
  verboseArgs: '{"path":"src/tasks.ts"}',
  ...patch
})

const row = (index: number, key: string, msg: Msg): TranscriptRow => ({ index, key, msg })

describe('native running-tool projection', () => {
  it('uses the Hermes tool call id as stable native identity', () => {
    const first = projectTernActiveTools([tool()])[0]!
    const updated = projectTernActiveTools([tool({ context: 'src/tasks.ts:20-40' })])[0]!

    expect(first.id).toBe('hermes:tool:call-7')
    expect(updated.id).toBe(first.id)
    expect(first).toMatchObject({
      k: 'tool',
      p: {
        name: 'read_file',
        title: 'Read File',
        target: 'src/tasks.ts',
        targetKind: 'text',
        status: 'running',
        collapsible: true,
        collapsed: false
      }
    })
  })

  it('never fabricates terminal success or failure from a running snapshot', () => {
    const node = projectTernActiveTools([tool({ context: 'error: permission denied' })])[0]!
    expect(node.p?.status).toBe('running')
    expect(node.p?.note).toBeUndefined()
  })

  it('keeps each concurrent call distinct even when names match', () => {
    const nodes = projectTernActiveTools([tool(), tool({ id: 'call-8' })])
    expect(nodes.map(node => node.id)).toEqual(['hermes:tool:call-7', 'hermes:tool:call-8'])
  })
})

describe('native terminal-tool projection', () => {
  it('keeps the same id across running to done and settles success collapsed', () => {
    const running = projectTernTools([], [], [tool()])[0]!
    const doneMsg: Msg = { role: 'system', kind: 'trail', text: '', nativeTools: [terminal()] }
    const done = projectTernTools([], [doneMsg], [])[0]!

    expect(done.id).toBe(running.id)
    expect(done).toMatchObject({
      k: 'tool',
      p: {
        status: 'done',
        took: 1250,
        collapsed: true
      }
    })
  })

  it('keeps a structured failure expanded and does not rewrite it after another call succeeds', () => {
    const failed = terminal({ id: 'call-7', status: 'failed', summary: 'Permission denied', resultText: 'EACCES' })
    const recovery = terminal({ id: 'call-8', status: 'done', summary: 'Read via fallback' })
    const rows = [
      row(0, 'msg:1:c80', { role: 'system', kind: 'trail', text: '', nativeTools: [failed] }),
      row(1, 'msg:2:c80', { role: 'system', kind: 'trail', text: '', nativeTools: [recovery] })
    ]

    const nodes = projectTernTools(rows, [], [])
    expect(nodes.map(node => node.id)).toEqual(['hermes:tool:call-7', 'hermes:tool:call-8'])
    expect(nodes[0]).toMatchObject({ p: { status: 'error', collapsed: false } })
    expect(JSON.stringify(nodes[0].c)).toContain('Permission denied')
    expect(nodes[1]).toMatchObject({ p: { status: 'done', collapsed: true } })
  })

  it('maps interrupted running calls to cancelled terminal state', () => {
    const msg: Msg = {
      role: 'system',
      kind: 'trail',
      text: '',
      nativeTools: [terminal({ status: 'cancelled', resultText: undefined, summary: undefined })]
    }

    expect(projectTernTools([], [msg], [])[0]).toMatchObject({
      id: 'hermes:tool:call-7',
      p: { status: 'cancelled', collapsed: false }
    })
  })


  it('keeps legacy cold-resume tool trails visible without inventing tool status', () => {
    const rows = [
      row(0, 'msg:legacy:c80', {
        role: 'system',
        kind: 'trail',
        text: '',
        tools: ['Read File("src/tasks.ts") ✓']
      })
    ]

    const node = projectTernTools(rows, [], [])[0]!
    expect(node).toMatchObject({
      id: 'hermes:tool-history:msg:legacy',
      k: 'text',
      p: { text: 'Read File("src/tasks.ts") ✓', tone: 'muted' }
    })
    expect(node.p?.status).toBeUndefined()
  })
})
