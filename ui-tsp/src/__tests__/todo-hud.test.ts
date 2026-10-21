import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import type { Todo } from '../model.js'
import { TodoHud } from '../todo-hud.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-todo-hud-'))
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

function todo(id: string, status: Todo['status'], content = id): Todo {
  return { id, status, content }
}

async function withApp(
  run: (app: App, gw: GatewayClient, surface: Surface, latest: () => View | undefined) => Promise<void>
): Promise<void> {
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
  const gw = new GatewayClient()

  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'session.resume') {
      const requested = (params as { session_id: string }).session_id

      return {
        session_id: 'runtime-' + requested,
        stored_session_id: requested,
        info: { model: 'fixture', stored_session_id: requested }
      } as never
    }

    if (method === 'session.close' || method === 'complete.slash') {
      return {} as never
    }

    throw new Error('Unexpected fixture request: ' + method)
  })

  const app = new App(tern, gw, 'test')
  const running = app.run()
  const surface = tern.surfaces[0]!
  const original = surface.render.bind(surface)
  let last: View | undefined

  surface.render = view => {
    last = View.from(view)
    original(view)
  }

  try {
    await app.resume('a')
    await rendered()
    await run(app, gw, surface, () => last)
  } finally {
    app.quit()
    await running

    if (previousSplash === undefined) {
      delete process.env.HERMES_TUI_SPLASH
    } else {
      process.env.HERMES_TUI_SPLASH = previousSplash
    }
  }
}

function checklist(view: View | undefined) {
  return view?.regions.find(region => region?.id === 'dock')?.children.find(item => item.kind === 'checklist')
}

describe('Hermes todo HUD projection', () => {
  it('replaces a three-row HUD without changing the previous transcript tool', async () => {
    await withApp(async (app, gw, _surface, latest) => {
      app.transcript.start(0)
      app.transcript.toolStart({ args: {}, name: 'todo_list', tool_id: 'old' }, 1)
      app.transcript.toolComplete({
        name: 'todo_list', tool_id: 'old',
        todos: [todo('a', 'completed'), todo('b', 'pending'), todo('c', 'pending')]
      }, 2)
      app.transcript.complete({ status: 'complete' }, 3)
      const turn = app.transcript.entries.find(e => e.kind === 'turn')
      const old = turn?.kind === 'turn' ? turn.blocks.find(b => b.kind === 'tool') : undefined

      // A snapshot may arrive without a new todo tool (for example on refresh).
      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-a',
        payload: { revision: 0, todos: [todo('a', 'completed'), todo('b', 'in_progress')] }
      })
      await rendered()
      expect(old?.kind === 'tool' && old.call.todos?.[1]?.status).toBe('pending')

      app.transcript.start(4)
      app.transcript.toolStart({ name: 'todo_list', tool_id: 'new', args: {} }, 5)
      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-a',
        payload: { revision: 1, todos: [
          todo('a', 'completed'), todo('b', 'in_progress'), todo('c', 'pending')
        ] }
      })
      await rendered()
      const shown = checklist(latest())
      expect(shown?.props.mode).toBe('full')
      const phases = shown?.props.phases as { items: { status: string }[] }[]
      expect(phases[0]?.items.map(i => i.status)).toEqual(['done', 'active', 'pending'])

      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-a',
        payload: { revision: 2, todos: [
          todo('a', 'completed'), todo('b', 'completed'), todo('c', 'in_progress')
        ] }
      })
      await rendered()
      const updated = checklist(latest())?.props.phases as { items: { status: string }[] }[]
      expect(updated[0]?.items.map(i => i.status)).toEqual(['done', 'done', 'active'])
      expect(old?.kind === 'tool' && old.call.todos?.[1]?.status).toBe('pending')
    })
  })

  it('collapses eight items to exact done counts and expands on a native click', async () => {
    await withApp(async (_app, gw, surface, latest) => {
      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-a',
        payload: { revision: 1, todos: Array.from({ length: 8 }, (_, i) =>
          todo(String(i), i < 3 ? 'completed' : i === 3 ? 'in_progress' : i === 7 ? 'cancelled' : 'pending', 'Task ' + i)
        ) }
      })
      await rendered()
      expect(checklist(latest())).toBeUndefined()

      const summary = () => latest()?.regions.find(region => region?.id === 'dock')?.children
        .find(item => item.props.role === 'omp.todo.summary')

      expect(summary()?.props.text).toBe('3/8 done · now: Task 3')
      const action = surface.dispatch({ act: 'click', ev: 'action', id: summary()!.id, raw: {}, sf: 'hermes' })
      expect(action).toBeTypeOf('function')
      action!()
      await rendered()
      const shown = checklist(latest())
      expect(shown?.props.mode).toBe('full')
      const phases = shown?.props.phases as { items: { status: string; text: string }[] }[]
      expect(phases[0]?.items.filter(i => i.status === 'done')).toHaveLength(3)
      expect(phases[0]?.items.find(i => i.status === 'active')?.text).toBe('Task 3')
      expect(phases[0]?.items).toHaveLength(8)
      surface.dispatch({ act: 'click', ev: 'action', id: summary()!.id, raw: {}, sf: 'hermes' })!()
      await rendered()
      expect(checklist(latest())).toBeUndefined()
    })
  })

  it('isolates session plans, restores them on return, and clears completed plans', async () => {
    await withApp(async (app, gw, _surface, latest) => {
      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-a',
        payload: { revision: 1, todos: [todo('a', 'in_progress')] }
      })
      await rendered()
      expect(checklist(latest())).toBeDefined()

      await app.resume('b')
      await rendered()
      expect(checklist(latest())).toBeUndefined()

      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-b',
        payload: { revision: 2, todos: [todo('b', 'pending')] }
      })
      await rendered()
      await app.resume('a')
      await rendered()
      const restored = checklist(latest())?.props.phases as { items: { id: string }[] }[]
      expect(restored[0]?.items[0]?.id).toBe('a')

      gw.emit('event', { type: 'message.start', session_id: 'runtime-a', payload: {} })
      gw.emit('event', {
        type: 'todo.updated', session_id: 'runtime-a',
        payload: { revision: 3, todos: [todo('a', 'completed')] }
      })
      await rendered()
      expect(checklist(latest())).toBeDefined()
      gw.emit('event', {
        type: 'message.complete', session_id: 'runtime-a', payload: { status: 'complete' }
      })
      await rendered()
      expect(checklist(latest())).toBeUndefined()
    })
  })
})

describe('todo HUD state', () => {
  it('keeps snapshots separate and hides a fully finished idle plan', () => {
    const hud = new TodoHud()
    hud.adopt('a')
    const original = [todo('a', 'pending')]
    hud.update(original)
    hud.update([todo('a', 'completed'), todo('b', 'in_progress')])
    expect(hud.visible(false)).toHaveLength(2)
    expect(original[0]?.status).toBe('pending')
    hud.adopt('b')
    expect(hud.visible(false)).toEqual([])
    hud.adopt('a')
    expect(hud.visible(false)).toHaveLength(2)
    hud.update([todo('a', 'completed')])
    expect(hud.visible(true)).toHaveLength(1)
    expect(hud.visible(false)).toEqual([])
    hud.update([])
    expect(hud.visible(true)).toEqual([])
  })
})
