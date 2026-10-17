import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Node, Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import type { ToolCall } from '../model.js'
import { Transcript } from '../transcript.js'
import { runBox, runElapsed, runFootFacts, runState } from '../view/runbox.js'
import { toolNode } from '../view/tools.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-tern-runbox-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))

function node(value: unknown): Node {
  if (!(value instanceof Node)) {
    throw new Error('Expected a native Tern node')
  }

  return value
}

function child(parent: Node, role: string): Node | undefined {
  return parent.children.find(n => n instanceof Node && n.props.role === role) as Node | undefined
}

function terminal(
  status: ToolCall['status'],
  result?: Record<string, unknown>,
  args: Record<string, unknown> = {}
): ToolCall {
  return {
    args: { command: 'npm test', ...args },
    argsText: '',
    context: 'npm test',
    id: 'term-1',
    name: 'terminal',
    result,
    startedAt: 0,
    status
  }
}

function nativeRun(call: ToolCall, collapsed?: boolean) {
  const tool = node(toolNode(call, 0, '', collapsed))
  const box = node(tool.children[0])
  const foot = child(box, 'omp.run.foot')

  if (!foot) {
    throw new Error('The run box footer is missing')
  }

  const status = child(foot, 'omp.run.state')
  const facts = child(foot, 'omp.run.facts')
  const label = (status?.props.spans as { t: string }[] | undefined)?.[0]?.t ?? ''
  const detail = (facts?.props.spans as { t: string }[] | undefined)?.[0]?.t ?? ''

  return { box, detail, foot, label, status, tool }
}

describe('Hermes run-state mapping', () => {
  it('exposes one native semantic input/output/footer builder', () => {
    const box = node(runBox({ command: 'echo hello', output: 'hello', state: 'ok', exit: 0 }))
    expect(box.props.role).toBe('omp.run')
    expect(child(box, 'omp.run.input')).toBeDefined()
    expect(child(box, 'omp.run.result')).toBeDefined()
    expect(child(box, 'omp.run.foot')).toBeDefined()
  })

  it('recognizes Hermes foreground-to-background yield without claiming exit zero', () => {
    const call = terminal('done', {
      status: 'yielded_to_background',
      exit_code: null,
      error: null,
      pid: 4321,
      session_id: 'yield-9',
      output: 'still running'
    })

    const view = nativeRun(call)
    expect(view.label).toBe('background')
    expect(view.detail).toContain('pid 4321')
    expect(view.detail).not.toContain('exit 0')
  })

  it.each([
    {
      name: 'running',
      call: terminal('running'),
      expected: 'running'
    },
    {
      name: 'foreground exit zero',
      call: terminal('done', { exit_code: 0, output: 'ok', error: null }),
      expected: 'ok'
    },
    {
      name: 'nonzero command exit',
      call: terminal('error', { exit_code: 17, output: 'failure', error: null }),
      expected: 'exit 17'
    },
    {
      name: 'backend timeout',
      call: terminal('error', { exit_code: 124, error: 'Command timed out after 180 seconds' }),
      expected: 'timeout'
    },
    {
      name: 'interrupted command',
      call: terminal('cancelled', { exit_code: 130, output: 'stopped\n[Command interrupted]' }),
      expected: 'cancelled'
    },
    {
      name: 'background launch',
      call: terminal(
        'done',
        { output: 'Background process started', exit_code: 0, error: null, pid: 4360, session_id: 'proc-123' },
        { background: true }
      ),
      expected: 'background'
    },
    {
      name: 'backend/tool error with no valid exit',
      call: terminal('error', { output: '', exit_code: -1, error: 'Failed to spawn process' }),
      expected: 'error'
    }
  ])('renders $name as $expected, not a generic failure', ({ call, expected }) => {
    const view = nativeRun(call)

    expect(view.box.props.role).toBe('omp.run')
    expect(view.label).toBe(expected)
    expect(runState(call, call.result as Record<string, unknown> | undefined)).toBe(
      expected === 'exit 17' ? 'exit' : expected
    )
    expect(child(view.box, 'omp.run.input')).toBeDefined()
    expect(view.foot.props.role).toBe('omp.run.foot')
    const evalView = nativeRun({ ...call, name: 'execute_code', args: { ...call.args, code: 'print(1)' } })
    expect(evalView.label).toBe(view.label)
    expect(evalView.detail).toBe(view.detail)
  })

  it('recognizes the terminal executor timeout suffix retained by finalization', () => {
    const view = nativeRun(
      terminal('error', {
        exit_code: 124,
        error: null,
        output: 'partial\n[Command timed out after 5s]'
      })
    )

    expect(view.label).toBe('timeout')
  })

  it('respects execute_code status errors even without a separate error string', () => {
    expect(
      nativeRun({ ...terminal('done', { status: 'error', output: 'Traceback' }), name: 'execute_code' }).label
    ).toBe('error')
  })

  it('does not call a plain exit 124 a timeout without Hermes timeout evidence', () => {
    const result = nativeRun(terminal('error', { exit_code: 124, error: null }))

    expect(result.label).toBe('exit 124')
    expect(result.status?.props.spans).toEqual([{ s: 'error', t: 'exit 124' }])
  })

  it('names timeout distinctly in warning tone and background with its real process id', () => {
    const timeout = nativeRun(
      terminal('error', {
        exit_code: 124,
        error: 'Command timed out after 60 seconds'
      })
    )

    const background = nativeRun(
      terminal(
        'done',
        {
          session_id: 'bg-1',
          pid: 1234,
          output: 'Background process started',
          exit_code: 0,
          error: null
        },
        { background: true }
      )
    )

    expect(timeout.status?.props.spans).toEqual([{ s: 'warning', t: 'timeout' }])
    expect(background.detail).toContain('pid 1234')
    expect(background.detail).not.toContain('exit 0')
    expect(background.tool.props.exit).toBeUndefined()
    expect(background.tool.props.took).toBeUndefined()
  })
})

describe('elapsed and captured-output evidence', () => {
  it('only reports elapsed for separate observed tool.start and tool.complete events', () => {
    const t = new Transcript()
    t.toolStart({ name: 'terminal', tool_id: 'real', args: { command: 'sleep 1' } }, 1_000)
    t.toolComplete({ name: 'terminal', tool_id: 'real', result: { exit_code: 0, output: '' } }, 1_800)

    const real = t.entries.flatMap(entry =>
      entry.kind === 'turn' ? entry.blocks.flatMap(b => (b.kind === 'tool' ? [b.call] : [])) : []
    )[0]!

    expect(real.startedObserved).toBe(true)
    expect(real.finishedAt).toBe(1_800)
    expect(runElapsed(real)).toBe(800)
    expect(nativeRun(real).detail).toContain('800ms')

    const recovered = new Transcript()
    recovered.toolComplete(
      {
        name: 'terminal',
        tool_id: 'late',
        result: { exit_code: 0, output: '' }
      },
      1_800
    )

    const fallback = recovered.entries.flatMap(entry =>
      entry.kind === 'turn' ? entry.blocks.flatMap(b => (b.kind === 'tool' ? [b.call] : [])) : []
    )[0]!

    expect(fallback.startedObserved).toBe(false)
    expect(runElapsed(fallback)).toBeUndefined()
    expect(nativeRun(fallback).detail).not.toMatch(/\d+(ms|s|m)\b/)
    expect(runElapsed(terminal('done', { exit_code: 0 }))).toBeUndefined()
  })

  it('states only the visible tail count when native preview folds long bash output', () => {
    const output = Array.from({ length: 15 }, (_, n) => 'line ' + n).join('\n')

    const result = nativeRun(
      terminal('done', {
        exit_code: 0,
        error: null,
        output,
        output_total_chars: 10_000,
        full_output_path: '/sandbox/output.log',
        truncation_note: 'Output exceeded capture window (head+tail)'
      })
    )

    expect(result.detail).toContain('truncated: showing last 10 lines')
    expect(result.detail).toContain('capture truncated: head + tail retained')
    expect(result.tool.props.preview).toBeUndefined()
    const outputs = child(child(result.box, 'omp.run.result')!, 'omp.run.outputs')!
    expect(child(outputs, 'omp.run.output')?.props.text).toBe(output.split('\n').slice(-10).join('\n'))

    const expanded = nativeRun(terminal('done', { exit_code: 0, output }), false)
    const allOutput = child(child(expanded.box, 'omp.run.result')!, 'omp.run.outputs')!
    expect(child(allOutput, 'omp.run.output')?.props.text).toBe(output)
    expect(expanded.detail).not.toContain('truncated: showing')
  })

  it('counts blank output lines and keeps the measured preview count exact', () => {
    const output = Array.from({ length: 13 }, (_, i) => (i % 2 ? '' : `row ${i}`)).join('\n')
    const result = nativeRun(terminal('done', { exit_code: 0, output }))
    const outputs = child(child(result.box, 'omp.run.result')!, 'omp.run.outputs')!

    expect(result.detail).toContain('truncated: showing last 10 lines')
    expect(child(outputs, 'omp.run.output')?.props.text).toBe(output.split('\n').slice(-10).join('\n'))
  })

  it('never invents a truncated count from a small output or backend-only spill', () => {
    expect(
      runFootFacts({
        command: 'ls',
        output: 'short',
        state: 'ok',
        truncated: true,
        previewLines: 10
      })
    ).toEqual([])
    expect(
      runFootFacts({
        command: 'ls',
        output: 'short',
        state: 'ok',
        captureTruncated: true,
        previewLines: 10
      })
    ).toEqual(['capture truncated: head + tail retained'])
  })

  it('uses the same run builder for eval and bash with truthful state footers', () => {
    const bash = nativeRun(terminal('error', { exit_code: 2, error: null, output: 'bad' }))

    const evalCall: ToolCall = {
      ...terminal('error', { exit_code: 2, error: null, output: 'bad' }),
      args: { code: 'print(1)', language: 'python' },
      context: 'print(1)',
      name: 'execute_code'
    }

    const evalRun = nativeRun(evalCall)
    const input = child(evalRun.box, 'omp.run.input')
    const code = input?.children.find(n => n instanceof Node && n.kind === 'code') as Node | undefined

    expect(evalRun.box.props.role).toBe(bash.box.props.role)
    expect(evalRun.label).toBe(bash.label)
    expect(code?.props.lang).toBe('python')
    expect(evalRun.tool.props.name).toBe('eval')

    const output = Array.from({ length: 12 }, (_, n) => 'out ' + n).join('\n')
    const longEval = nativeRun({ ...evalCall, status: 'done', result: { output, exit_code: 0 } })
    expect(longEval.detail).toContain('truncated: showing first 8 lines')
  })

  it('keeps the footer stable in a real native SDK Session view', async () => {
    const previousSplash = process.env.HERMES_TUI_SPLASH
    process.env.HERMES_TUI_SPLASH = '0'
    const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
    const gw = new GatewayClient()
    const app = new App(tern, gw, 'test')
    app.sid = 'session-1'
    acknowledgeFrames(tern)
    const running = app.run()
    const surface = tern.surfaces[0]!
    const original = surface.render.bind(surface)
    let latest: View | undefined

    surface.render = view => {
      latest = View.from(view)
      original(view)
    }

    try {
      gw.emit('event', {
        type: 'tool.start',
        session_id: 'session-1',
        payload: { name: 'terminal', tool_id: 'cmd', args: { command: 'run' } }
      })
      gw.emit('event', {
        type: 'tool.complete',
        session_id: 'session-1',
        payload: { name: 'terminal', tool_id: 'cmd', result: { exit_code: 0, error: null, output: 'ok' } }
      })
      app.changed()
      await rendered()

      const tool = latest?.regions
        .find(region => region?.id === 'main')
        ?.children.find(n => n.kind === 'tool')

      const box = tool?.children.find(n => n.kind === 'col' && n.props.role === 'omp.run')
      const foot = box?.children.find(n => n.kind === 'row' && n.props.role === 'omp.run.foot')
      const status = foot?.children.find(n => n.kind === 'text' && n.props.role === 'omp.run.state')

      expect((status?.props.spans as { t: string }[] | undefined)?.[0]?.t).toBe('ok')
    } finally {
      app.quit()
      await running

      if (previousSplash === undefined) {
        delete process.env.HERMES_TUI_SPLASH
      } else {
        process.env.HERMES_TUI_SPLASH = previousSplash
      }
    }
  })
})
