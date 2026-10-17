import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { TranscriptMessage } from '@hermes/shared/gateway-events'
import type { Surface } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-targeted-rewind-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

const rendered = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

type Tree = NonNullable<View['regions'][number]>

function descendants(nodes: readonly Tree[]): Tree[] {
  return nodes.flatMap(node => [node, ...descendants(node.children)])
}

const history: TranscriptMessage[] = [1, 2, 3, 4].flatMap(i => [
  { role: 'user', row_id: i * 10, text: `question ${i}` },
  { role: 'assistant', row_id: i * 10 + 1, text: `answer ${i}` }
])

interface Call {
  method: string
  params: unknown
}

interface Fixture {
  failPreview?: boolean
  undo?: () => Promise<unknown>
}

async function withApp(run: (app: App, surface: Surface, nodes: (region: string) => Tree[], click: (node: Tree) => Promise<void>, calls: Call[], press: (bytes: string) => Promise<void>) => Promise<void>, fixture: Fixture = {}) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const calls: Call[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'complete.slash') {
      return { items: [] }
    }

    calls.push({ method, params })

    if (method === 'session.rewind_preview') {
        if (fixture.failPreview) {
          throw new Error('This merged turn is not a rewindable target.')
        }

      return { history_token: 'snapshot', removed: 0, text: 'question 2', turns_removed: 3 }
    }

    if (method === 'session.undo') {
      return fixture.undo ? fixture.undo() : { messages: history.slice(0, 2), removed: 6, text: 'question 2', turns_removed: 3 }
    }

    if (method === 'prompt.submit') {
      return { status: 'streaming', user_row_id: 50 }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.transcript.load(history)
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view: View | undefined
  const render = surface.render.bind(surface)

  surface.render = value => {
    view = View.from(value)
    render(value)
  }

  const nodes = (region: string) => descendants(view?.regions.find(item => item?.id === region)?.children ?? [])

  const click = async (node: Tree) => {
    const action = surface.dispatch({ act: 'click', ev: 'action', id: node.id, raw: {}, sf: 'hermes' })
    expect(action).toBeTypeOf('function')
    await action!()
    await rendered()
  }

  try {
    app.changed()
    await rendered()
    await run(app, surface, nodes, click, calls, async bytes => {
      input.emit('data', bytes)
      await rendered()
    })
  } finally {
    app.quit()
    await running
  }
}

function required(nodes: Tree[], key: string): Tree {
  const result = nodes.find(node => node.props.key === key)

  if (!result) {
    throw new Error(`Missing action ${key}`)
  }

  return result
}

function secondRewind(nodes: Tree[]): Tree {
  const result = nodes.filter(node => node.props.key === 'rewind')[1]

  if (!result) {
    throw new Error('Missing second user message rewind action')
  }

  return result
}

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('targeted rewind', () => {
  it('rewinds the second of four user messages by durable id only after confirmation', async () => {
    await withApp(async (app, _surface, nodes, click, calls) => {
      await click(secondRewind(nodes('main')))
      expect(calls).toEqual([{ method: 'session.rewind_preview', params: { session_id: 'session-1', target_message_id: 20 } }])
      expect(nodes('layer').some(node => typeof node.props.text === 'string' && node.props.text.includes('Remove 3 user turns'))).toBe(true)
      expect(app.transcript.entries.filter(entry => entry.kind === 'user')).toHaveLength(4)
      await click(required(nodes('layer'), 'ok'))
      expect(calls[1]).toEqual({ method: 'session.undo', params: { expected_history_token: 'snapshot', session_id: 'session-1', target_message_id: 20 } })
      expect(app.transcript.entries.filter(entry => entry.kind === 'user').map(entry => entry.text)).toEqual(['question 1'])
    })
  })

  it('cancelling the confirmation sends no destructive RPC and preserves the draft and history', async () => {
    await withApp(async (app, _surface, nodes, click, calls, press) => {
      app.composer.set('keep draft', 3)
      await click(secondRewind(nodes('main')))
      await press('\x1b[27u')
      expect(calls.filter(call => call.method === 'session.undo')).toHaveLength(0)
      expect(calls).toHaveLength(1)
      expect(app.overlays).toHaveLength(0)
      expect(app.composer.text).toBe('keep draft')
      expect(app.composer.cursor).toBe(3)
      expect(app.transcript.entries.filter(entry => entry.kind === 'user')).toHaveLength(4)
    })
  })

  it('does not reuse a cancelled native confirm callback', async () => {
    await withApp(async (_app, surface, nodes, click, calls, press) => {
      await click(secondRewind(nodes('main')))
      const confirm = surface.dispatch({ act: 'click', ev: 'action', id: required(nodes('layer'), 'ok').id, raw: {}, sf: 'hermes' })
      expect(confirm).toBeTypeOf('function')
      await press('\x1b[27u')
      await confirm!()
      await rendered()
      expect(calls.filter(call => call.method === 'session.undo')).toHaveLength(0)
    })
  })

  it('coalesces duplicate confirms and refuses native send while the rewind is in flight', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async (app, surface, nodes, click, calls) => {
      await click(secondRewind(nodes('main')))
      const confirm = surface.dispatch({ act: 'click', ev: 'action', id: required(nodes('layer'), 'ok').id, raw: {}, sf: 'hermes' })
      expect(confirm).toBeTypeOf('function')
      await confirm!()
      await confirm!()
      await rendered()
      app.composer.set('do not send')
      await surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'do not send' })?.()
      await rendered()
      expect(calls.filter(call => call.method === 'session.undo')).toHaveLength(1)
      expect(calls.filter(call => call.method === 'prompt.submit')).toHaveLength(0)
      expect(app.composer.text).toBe('do not send')
      expect(nodes('dock').some(node => JSON.stringify(node.props).includes('Rewinding'))).toBe(true)
      gate.resolve({ messages: history.slice(0, 2), removed: 6, text: 'question 2' })
      await rendered()
      expect(app.composer.text).toBe('question 2')
    }, { undo: () => gate.promise })
  })

  it('restores the selected message in the composer after success', async () => {
    await withApp(async (app, _surface, nodes, click) => {
      app.composer.set('old draft')
      await click(secondRewind(nodes('main')))
      expect(app.composer.text).toBe('old draft')
      await click(required(nodes('layer'), 'ok'))
      expect(app.composer.text).toBe('question 2')
      expect(app.composer.cursor).toBe('question 2'.length)
      expect(app.rewinding).toBeNull()
    })
  })

  it('disables unsupported targets with the backend reason instead of undoing the last turn', async () => {
    await withApp(async (_app, surface, nodes, click, calls) => {
      await click(secondRewind(nodes('main')))
      const action = secondRewind(nodes('main'))
      expect(action.props.title).toBe('This merged turn is not a rewindable target.')
      expect(surface.dispatch({ act: 'click', ev: 'action', id: action.id, raw: {}, sf: 'hermes' })).toBeUndefined()
      expect(calls).toHaveLength(1)
    }, { failPreview: true })
  })

  it('does not overwrite the composer or transcript when a confirmed rewind fails', async () => {
    await withApp(async (app, _surface, nodes, click) => {
      app.composer.set('keep on failure')
      await click(secondRewind(nodes('main')))
      await click(required(nodes('layer'), 'ok'))
      expect(app.composer.text).toBe('keep on failure')
      expect(app.transcript.entries.filter(entry => entry.kind === 'user')).toHaveLength(4)
      expect(app.transcript.entries.some(entry => entry.kind === 'notice' && entry.text.includes('History changed'))).toBe(true)
    }, { undo: async () => { throw new Error('History changed after confirmation') } })
  })

  it('does not apply a late rewind response to a different session', async () => {
    const gate = Promise.withResolvers<unknown>()
    await withApp(async (app, _surface, nodes, click) => {
      await click(secondRewind(nodes('main')))
      await click(required(nodes('layer'), 'ok'))
      expect(app.rewinding?.label).toBe('Rewinding…')
      app.sid = 'different-session'
      app.transcript.clear()
      app.composer.set('new session draft')
      gate.resolve({ messages: history.slice(0, 2), removed: 6, text: 'question 2' })
      await rendered()
      expect(app.composer.text).toBe('new session draft')
      expect(app.transcript.entries).toHaveLength(0)
    }, { undo: () => gate.promise })
  })

  it('uses prompt.submit durable ids for live messages and disables rows without one', async () => {
    await withApp(async (app, surface, nodes) => {
      app.composer.set('new prompt')
      await surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'new prompt' })?.()
      await rendered()
      const entry = app.transcript.entries.findLast(item => item.kind === 'user')
      expect(entry).toMatchObject({ rowId: 50, text: 'new prompt' })
      app.busy = null
      app.transcript.user('unpersisted')
      app.changed()
      await rendered()
      const action = nodes('main').filter(node => node.props.key === 'rewind').at(-1)
      expect(action?.props.title).toContain('no durable rewind address')
    })
  })
})
