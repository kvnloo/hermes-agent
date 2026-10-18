import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { BtwThread } from '@hermes/shared/gateway-events'
import { node, Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, type MockInstance, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-report-sheets-'))
  const previous = process.env.HERMES_HOME
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, previousSplash }
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  if (isolated.previousSplash === undefined) {
    delete process.env.HERMES_TUI_SPLASH
  } else {
    process.env.HERMES_TUI_SPLASH = isolated.previousSplash
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
type Tree = NonNullable<View['regions'][number]>['children'][number]

function flatten(nodes: readonly Tree[]): Tree[] {
  return nodes.flatMap(node => [node, ...flatten(node.children)])
}

interface Fixture {
  app: App
  gw: GatewayClient
  surface: Surface
  nodes(region: string): Tree[]
  press(bytes: string): Promise<void>
  click(region: string, key: string): () => void | Promise<void>
  request: MockInstance<GatewayClient['request']>
}

async function withApp(run: (fixture: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'btw.list') {
      return { threads: [] }
    }

    if (method === 'slash.exec') {
      return { output: '# Report\n\nExact **Markdown** body.\n' }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => {
    view = View.from(next)
    render(next)
  }

  const nodes = (region: string) => flatten(view.regions.find(item => item?.id === region)?.children ?? [])

  try {
    await run({
      app,
      gw,
      surface,
      nodes,
      request,
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
        await rendered()
      },
      click: (region, key) => {
        const target = nodes(region).find(node => node.props.key === key)

        if (!target) {
          throw new Error(`Missing native action: ${region}/${key}`)
        }

        const action = surface.dispatch({ ev: 'action', act: 'click', id: target.id, sf: 'hermes', raw: {} })

        if (!action) {
          throw new Error(`Missing native handler: ${target.id}`)
        }

        return action
      }
    })
  } finally {
    app.quit()
    await running
  }
}

function sheet(nodes: Fixture['nodes']) {
  return nodes('layer').find(node => node.props.role === 'omp.overlay.report')
}

function thread(id: string, state: BtwThread['turns'][number]['state'] = 'answered'): BtwThread {
  return {
    id,
    revision: 1,
    turns: [{ id: `${id}-turn`, question: `Question ${id}`, answer: `Answer ${id}\n`.repeat(100), state, error: null }]
  }
}

const field = (nodes: Fixture['nodes']) => nodes('layer').find(node => node.props.key === 'followup')!

async function edit(f: Fixture, text: string) {
  const target = field(f.nodes)
  await f.surface.dispatch({
    ev: 'edit',
    id: target.id,
    sf: 'hermes',
    raw: {},
    from: 0,
    to: String(target.props.text).length,
    text,
    cursor: text.length,
    len: String(target.props.text).length
  })?.()
  await rendered()
}

describe('selectable BTW side threads', () => {
  it('loads every long thread without a UI cap and selects a prior thread with independent reader/history scroll targets', async () => {
    await withApp(async f => {
      const threads = Array.from({ length: 237 }, (_, i) => thread(`thread-${i}`))
      f.request.mockResolvedValueOnce({ threads })
      await f.app.slash('/btw')
      await rendered()
      expect(f.nodes('layer').filter(node => node.props.role === 'omp.btw.turn')).toHaveLength(1)
      expect(f.nodes('layer').filter(node => node.props.role === 'omp.btn').length).toBeGreaterThan(237)
      await f.click('layer', 'thread-0')()
      await rendered()
      expect(f.nodes('layer').some(node => node.props.text === threads[0]!.turns[0]!.answer)).toBe(true)
      const scroll = vi.spyOn(f.surface, 'scroll')
      await f.press('\x1b[9u')
      await f.press('\x1b[6~')
      expect(scroll).toHaveBeenLastCalledWith(`${sheet(f.nodes)!.id}.body.panes.history`, 'page-down')
      await f.press('\x1b[9u')
      await f.press('\x1b[6~')
      expect(scroll).toHaveBeenLastCalledWith(`${sheet(f.nodes)!.id}.body.panes.reader`, 'page-down')
      expect(f.app.transcript.entries.some(entry => entry.kind === 'panel' || entry.kind === 'user')).toBe(false)
    })
  })

  it('submits the selected exact thread and projects streamed answers outside main', async () => {
    await withApp(async f => {
      f.request.mockResolvedValueOnce({ threads: [thread('prior')] })
      await f.app.slash('/btw')
      await rendered()
      await edit(f, 'Follow up 🦉')
      const running = thread('prior', 'running')
      running.turns.push({ id: 'followup', question: 'Follow up 🦉', answer: '', state: 'running', error: null })
      f.request.mockResolvedValueOnce({ thread: running, turn_id: 'followup' })
      await f.click('layer', 'send')()
      await rendered()
      expect(f.request).toHaveBeenCalledWith('btw.submit', {
        session_id: 'session-1',
        thread_id: 'prior',
        text: 'Follow up 🦉'
      })
      const streaming = structuredClone(running)
      streaming.revision++
      streaming.turns.at(-1)!.answer = 'Actual delta'
      f.gw.emit('event', { type: 'btw.update', session_id: f.app.sid, payload: { thread: streaming } })
      await rendered()
      expect(f.nodes('layer').findLast(node => node.props.role === 'omp.btw.answer')?.props).toMatchObject({
        text: 'Actual delta',
        stream: true
      })
      expect(
        f.app.transcript.entries.some(entry => entry.kind === 'panel' || entry.kind === 'user' || entry.kind === 'turn')
      ).toBe(false)
    })
  })

  it('new questions use canonical ids and expose pending, failure and cancellation readback', async () => {
    await withApp(async f => {
      const reply = Promise.withResolvers<unknown>()
      f.request.mockResolvedValueOnce({ threads: [] }).mockReturnValueOnce(reply.promise)
      const pending = f.app.slash('/btw why?')
      await rendered()
      expect(f.nodes('layer').some(node => node.props.text === 'Submitting side question…')).toBe(true)
      const active = thread('canonical', 'running')
      reply.resolve({ thread: active, turn_id: 'canonical-turn' })
      await pending
      await rendered()
      expect(f.request).toHaveBeenCalledWith('btw.submit', { session_id: 'session-1', text: 'why?' })
      const cancelled = thread('canonical', 'cancelled')
      cancelled.revision = 2
      f.request.mockResolvedValueOnce({ thread: cancelled, turn_id: 'canonical-turn' })
      await f.click('layer', 'cancel')()
      await rendered()
      expect(f.request).toHaveBeenCalledWith('btw.cancel', {
        session_id: 'session-1',
        thread_id: 'canonical',
        turn_id: 'canonical-turn'
      })
      expect(f.nodes('layer').some(node => node.props.text === 'cancelled')).toBe(true)
      const failed = thread('canonical', 'error')
      failed.revision = 3
      failed.turns[0]!.error = 'Provider unavailable'
      f.gw.emit('event', { type: 'btw.update', session_id: f.app.sid, payload: { thread: failed } })
      await rendered()
      expect(
        f.nodes('layer').some(node => node.props.role === 'omp.btw.error' && node.props.text === 'Provider unavailable')
      ).toBe(true)
      await edit(f, 'keep failed draft')
      f.request.mockRejectedValueOnce(new Error('Backend rejected follow-up'))
      await f.click('layer', 'send')()
      await rendered()
      expect(field(f.nodes).props.text).toBe('keep failed draft')
      expect(f.nodes('layer').some(node => node.props.text === 'Backend rejected follow-up')).toBe(true)
    })
  })

  it('preserves per-thread follow-up drafts across selection, approval preemption and return to the main draft', async () => {
    await withApp(async f => {
      f.app.composer.set('main draft 🦉', 4)
      f.request.mockResolvedValueOnce({ threads: [thread('first'), thread('second')] })
      await f.app.slash('/btw')
      await rendered()
      await f.click('layer', 'first')()
      await rendered()
      await edit(f, 'first unsent')
      await f.click('layer', 'second')()
      await rendered()
      await edit(f, 'second unsent')
      await f.click('layer', 'first')()
      await rendered()
      expect(field(f.nodes).props.text).toBe('first unsent')

      const approval = {
        key: 'prompt:approval',
        modal: true,
        node: (id: string) => node('overlay', { key: id.slice(6), head: 'Approval required', modal: true }),
        onKey: () => true
      }

      f.app.open(approval)
      await rendered()
      const before = f.request.mock.calls.length
      // Already-resolved native callbacks are ownership-fenced by App.
      expect(f.app.owns(f.app.overlays.find(item => item.key === 'report')!)).toBe(false)
      await f.press('\x1b[13;3u')
      expect(f.request.mock.calls).toHaveLength(before)
      f.app.close(approval)
      await rendered()
      expect(field(f.nodes).props.text).toBe('first unsent')
      await f.click('layer', 'close')()
      await rendered()
      expect(f.app.composer.text).toBe('main draft 🦉')
      expect(f.app.composer.cursor).toBe(4)
      await f.app.slash('/btw')
      await rendered()
      expect(field(f.nodes).props.text).toBe('first unsent')
    })
  })

  it('copies only the selected thread with exact Unicode and reports clipboard errors', async () => {
    await withApp(async f => {
      const selected = thread('copy-thread')
      f.request.mockResolvedValueOnce({ threads: [selected] })
      await f.app.slash('/btw')
      await rendered()
      const write = vi.spyOn(process.stdout, 'write').mockReturnValue(true)

      try {
        await f.click('layer', 'copy')()
        expect(write).toHaveBeenCalledWith(
          `\x1b]52;c;${Buffer.from(`${selected.turns[0]!.question}\n\n${selected.turns[0]!.answer}`).toString('base64')}\x07`
        )
        write.mockImplementation(() => {
          throw new Error('no clipboard')
        })
        await f.click('layer', 'copy')()
      } finally {
        write.mockRestore()
      }

      await rendered()
      expect(f.nodes('layer').some(node => node.props.text === 'Could not copy the report to the clipboard.')).toBe(
        true
      )
    })
  })

  it('ignores stale-session list, submit and stream results and invalidates old actions', async () => {
    await withApp(async f => {
      const reply = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(reply.promise)
      const pending = f.app.slash('/btw')
      f.app.sid = 'different-session'
      f.app.btw.adopt(f.app.sid)
      reply.resolve({ threads: [thread('private-old')] })
      await pending
      f.gw.emit('event', { type: 'btw.update', session_id: 'session-1', payload: { thread: thread('private-event') } })
      await rendered()
      expect(f.app.btw.threads).toEqual([])
      expect(sheet(f.nodes)).toBeUndefined()
      f.request.mockResolvedValueOnce({ threads: [] })
      await f.app.slash('/btw')
      await rendered()
      await edit(f, 'private question')
      const submit = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(submit.promise)
      await f.click('layer', 'send')()
      f.app.sid = 'third-session'
      f.app.btw.adopt(f.app.sid)
      submit.resolve({ thread: thread('private-submit'), turn_id: 'private-submit-turn' })
      await rendered()
      expect(f.app.btw.threads).toEqual([])
      expect(sheet(f.nodes)).toBeUndefined()
    })
  })
})
