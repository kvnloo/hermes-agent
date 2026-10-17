import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Node, Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { answerText, copyAnswer } from '../answer-actions.js'
import { App } from '../app.js'
import type { TurnEntry } from '../model.js'
import { promptOverlay } from '../overlays/prompts.js'
import { Transcript } from '../transcript.js'
import { toolNode } from '../view/tools.js'
import { entryNode } from '../view/transcript.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-tern-answer-actions-'))
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

function completedTurn(): TurnEntry {
  const t = new Transcript()
  t.start(0)
  t.reasoning('Do not copy thinking', 1)
  t.text('  First answer.  ', 2)
  t.toolStart({ name: 'read_file', tool_id: 'read-1', args: { path: 'README.md' } }, 3)
  t.toolComplete({ name: 'read_file', tool_id: 'read-1', result: { content: '1|internal' } }, 4)
  t.text('Second answer.', 5)
  t.complete({ status: 'complete', text: 'Second answer.' }, 6)

  return t.entries.findLast(e => e.kind === 'turn') as TurnEntry
}

function footerOf(turn: TurnEntry): Node | undefined {
  const entry = node(entryNode(turn, 'main.' + turn.id, {
    copy: () => undefined, cwd: '', now: 0, welcome: { tip: '', version: '' }
  }))

  return entry.children.find(child => child instanceof Node && child.props.role === 'omp.turn.actions') as Node | undefined
}

function lastTool(view: View | undefined) {
  const assistant = view?.regions.find(region => region?.id === 'main')?.children.findLast(child => child.kind === 'col' && child.props.role === 'omp.assistant')

  return assistant?.children.findLast(child => child.kind === 'tool')
}

describe('native assistant answer actions', () => {
  it('copies only visible answer blocks with a blank line between them', () => {
    const turn = completedTurn()
    expect(answerText(turn)).toBe('First answer.\n\nSecond answer.')
    const clipboard = vi.fn()
    const failure = vi.fn()
    copyAnswer(turn, clipboard, failure)
    expect(clipboard).toHaveBeenCalledExactlyOnceWith('First answer.\n\nSecond answer.')
    expect(failure).not.toHaveBeenCalled()
    expect(footerOf(turn)?.children.some(c => c instanceof Node && c.props.role === 'omp.turn.copy')).toBe(true)
  })

  it('does not offer Copy during streaming and offers it on completion', () => {
    const transcript = new Transcript()
    transcript.start(0)
    transcript.text('Streaming answer', 1)
    const turn = transcript.live!

    expect(footerOf(turn)).toBeUndefined()
    const clipboard = vi.fn()
    copyAnswer(turn, clipboard, vi.fn())
    expect(clipboard).not.toHaveBeenCalled()

    transcript.complete({ status: 'complete', text: 'Streaming answer' }, 2)
    expect(footerOf(turn)).toBeDefined()
  })

  it('converts a clipboard failure into a notice, never a thrown exception', () => {
    const failure = vi.fn()
    expect(() => copyAnswer(completedTurn(), () => {
      throw new Error('EPIPE')
    }, failure)).not.toThrow()
    expect(failure).toHaveBeenCalledOnce()
  })

  it('dispatches the rendered Copy action through OSC 52 and reports write failures', async () => {
    const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
    const app = new App(tern, new GatewayClient(), 'test')
    app.sid = 'session-1'
    const running = app.run()
    const surface = tern.surfaces[0]!
    const render = surface.render.bind(surface)
    let latest: View | undefined

    surface.render = view => {
      latest = View.from(view)
      render(view)
    }

    try {
      app.transcript.entries.push(completedTurn())
      app.changed()
      await rendered()

      const copy = latest?.regions.find(region => region?.id === 'main')?.children
        .flatMap(turn => turn.children).flatMap(row => row.children)
        .find(child => child.props.role === 'omp.turn.copy')

      expect(copy).toBeDefined()
      const action = surface.dispatch({ act: 'click', ev: 'action', id: copy!.id, raw: {}, sf: 'hermes' })
      expect(action).toBeTypeOf('function')
      const write = vi.spyOn(process.stdout, 'write').mockReturnValue(true)

      try {
        action!()
        expect(write).toHaveBeenCalledExactlyOnceWith(`\x1b]52;c;${Buffer.from('First answer.\n\nSecond answer.').toString('base64')}\x07`)
        write.mockImplementation(() => { throw new Error('EPIPE') })
        expect(() => action!()).not.toThrow()
      } finally {
        write.mockRestore()
      }

      await rendered()
      expect(app.transcript.entries).toContainEqual(expect.objectContaining({
        kind: 'notice', tone: 'warning', text: 'Could not copy the answer to the clipboard.'
      }))
    } finally {
      app.quit()
      await running
    }
  })

  it('wraps explicit source code nodes using the documented SDK prop', () => {
    const read = node(toolNode({
      args: { path: 'README.md' }, argsText: '', context: '', id: 'read',
      name: 'read_file', result: { content: '1|some very long source text' }, startedAt: 0, status: 'done'
    }, 0))

    const code = read.children.find(c => c instanceof Node && c.kind === 'code') as Node | undefined
    expect(code?.props.wrap).toBe(true)
  })
})

describe('Ctrl+O native tool folding', () => {
  it('toggles the latest foldable tool and ignores modal sheets and nonempty drafts', async () => {
    const previousSplash = process.env.HERMES_TUI_SPLASH
    process.env.HERMES_TUI_SPLASH = '0'
    const input = new EventEmitter()
    const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
    const connecting = tern.handshake()
    input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
    expect(await connecting).toBe(true)
    const app = new App(tern, new GatewayClient(), 'test')
    app.sid = 'session-1'
    const running = app.run()
    const surface = tern.surfaces[0]!
    const original = surface.render.bind(surface)
    let latest: View | undefined

    surface.render = view => {
      latest = View.from(view)
      original(view)
    }

    const press = async (bytes: string) => {
      input.emit('data', bytes)
      await rendered()
      await rendered()
    }

    try {
      app.transcript.start(0)
      app.transcript.toolStart({ args: { path: 'README.md' }, name: 'read_file', tool_id: 'read-1' }, 1)
      app.transcript.toolComplete({ name: 'read_file', result: { content: '1|source text' }, tool_id: 'read-1' }, 2)
      app.transcript.toolStart({ args: { path: 'second.ts' }, name: 'read_file', tool_id: 'read-2' }, 3)
      app.transcript.toolComplete({ name: 'read_file', result: { content: '1|second source' }, tool_id: 'read-2' }, 4)
      app.transcript.complete({ status: 'complete' }, 5)
      app.changed()
      await rendered()

      expect(lastTool(latest)?.props.collapsed).toBe(true)
      await press('\x0f') // Ctrl+O
      expect(lastTool(latest)?.props.collapsed).toBe(false)
      expect(lastTool(latest)?.props.key).toBe('read-2')

      const firstTool = latest?.regions.find(region => region?.id === 'main')?.children
        .flatMap(turn => turn.children).find(child => child.props.key === 'read-1')

      expect(firstTool?.props.collapsed).toBe(true)
      await press('\x0f')
      expect(lastTool(latest)?.props.collapsed).toBe(true)

      const respond = vi.fn()

      const overlay = promptOverlay(app, {
        id: 'approval-fixture', method: 'approval', params: { command: 'fixture' }, respond, fail: vi.fn()
      })!

      expect(overlay.modal).toBe(true)

      app.open(overlay)
      await rendered()
      await press('\x0f')
      app.close(overlay)
      await rendered()
      expect(lastTool(latest)?.props.collapsed).toBe(true)

      app.composer.set('selected draft')
      await press('\x0f')
      expect(lastTool(latest)?.props.collapsed).toBe(true)
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
