import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { SessionTreeParams, SessionTreeResult, SessionTreeRow } from '@hermes/shared/gateway-events'
import type { Surface, Tree, TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { APP_ACTIONS, matchesAction, SESSION_ACTIONS } from '../actions.js'
import { App } from '../app.js'
import { localCommand } from '../commands.js'
import { openSessionPicker } from '../overlays/sessions.js'
import { adjacentBranch, projectSessionTree } from '../session-tree.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-session-tree-'))
  const previous = process.env.HERMES_HOME
  const previousWindow = process.env.TERN_WINDOW_KEY
  delete process.env.TERN_WINDOW_KEY
  process.env.HERMES_HOME = home

  return { home, previous, previousWindow }
})

const tick = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

function row(id: string, parent: string | null = null, extra: Partial<SessionTreeRow> = {}): SessionTreeRow {
  return { cwd: `/work/${id}`, edge_kind: parent ? 'fork' : 'root', id, message_count: 2,
    parent_session_id: parent, preview: '', source: 'tui', started_at: 1, title: id, ...extra }
}

function page(rows: SessionTreeRow[], next: number | null = null, total = rows.length): SessionTreeResult {
  return { ancestors: [], next_offset: next, sessions: rows, total }
}

interface Harness {
  app: App
  surface: Surface
  picker(): Tree
  event(event: Partial<TspEvent>): () => void | Promise<void>
  action(name: string): Promise<void>
  key(name: string, text?: string): Promise<void>
  calls: { method: string; params: unknown }[]
}

interface Fixture {
  read(params: SessionTreeParams): Promise<SessionTreeResult>
  rename?(id: string, title: string): Promise<{ session_key: string; title: string }>
}

async function withApp(fixture: Fixture, run: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const calls: Harness['calls'] = []
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    if (method === 'session.tree') {
      return fixture.read(params as SessionTreeParams)
    }

    if (method === 'session.rename' && fixture.rename && params && 'session_key' in params && 'title' in params) {
      return fixture.rename(String(params.session_key), String(params.title))
    }

    if (method === 'jobs.list') {
      return { jobs: [] }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'settings.get') {
      return { fields: {}, profile: 'fixture' }
    }

    if (method === 'session.close') {
      return {}
    }

    if (method === 'session.fork') {
      return { message_count: 2, parent: 'active', profile: 'fixture', session_id: 'fork-saved' }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'fixture')
  app.sid = 'live'
  app.storedSid = 'active'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view: View | undefined
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }

  const picker = () => {
    const root = view?.regions[2]?.children.find(node => node.kind === 'picker')

    if (!root) {
      throw new Error('Session picker did not render')
    }

    return root
  }

  const event = (event: Partial<TspEvent>) => {
    const action = surface.dispatch({ id: picker().id, raw: {}, sf: 'hermes', ...event } as TspEvent)

    if (!action) {
      throw new Error('Picker did not accept event')
    }

    return action
  }

  try {
    await run({ app, calls, event, picker, surface,
      action: async name => { await event({ act: name, ev: 'action' })(); await tick() },
      key: async (name, text) => {
        app.overlays.at(-1)?.onKey({ alt: false, ctrl: false, meta: false, name, shift: false, text })
        app.changed()
        await tick()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  if (isolated.previousWindow !== undefined) {
    process.env.TERN_WINDOW_KEY = isolated.previousWindow
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('session / branch tree, not another flat resume picker', () => {
  it('projects nested and filtered forks using raw ancestry and crosses visible branches', () => {
    const rows = [row('root'), row('head-a', 'root'), row('leaf-a', 'head-a', { edge_kind: 'continuation' }),
      row('nested', 'head-a'), row('head-b', 'root'), row('leaf-b', 'head-b', { edge_kind: 'continuation' })]

    const projection = projectSessionTree(rows, new Set(['leaf-a', 'nested', 'leaf-b']), 'leaf-a')
    expect(projection.entries.map(entry => [entry.row.id, entry.depth])).toEqual([['leaf-a', 2], ['nested', 2], ['leaf-b', 2]])
    expect(adjacentBranch(projection, 'leaf-a', 1)).toBe('nested')
    expect(adjacentBranch(projection, 'nested', 1)).toBe('leaf-b')
    expect(adjacentBranch(projection, 'leaf-a', -1)).toBe('leaf-b')
  })

  it('puts the active branch first, renders tree depth, and selection highlights only', async () => {
    await withApp({ read: async () => page([row('other'), row('root'), row('sibling', 'root'), row('active', 'root')]) }, async h => {
      await localCommand('tree')?.run(h.app, '')
      await tick()
      expect(h.picker().props).toMatchObject({ current: ['active'], layout: 'tree', selected: 'active' })
      expect(h.picker().props.order).toEqual(['root', 'active', 'sibling', 'other'])
      expect(h.picker().props.items).toContainEqual(expect.objectContaining({ depth: 1, id: 'active' }))
      await h.event({ ev: 'select', item: 'sibling' })()
      await tick()
      expect(h.picker().props.selected).toBe('sibling')
      expect(h.calls.filter(call => call.method !== 'session.tree' && call.method !== 'complete.slash')).toEqual([])
      await h.action('nextBranch')
      expect(h.picker().props.selected).toBe('other')
      expect(h.app.storedSid).toBe('active')
    })
  })

  it('tolerates missing parents and cycles with exactly one visible row per stored session', () => {
    const rows = [row('orphan', 'missing'), row('b', 'a'), row('a', 'b'), row('self', 'self')]
    const projection = projectSessionTree(rows, new Set(rows.map(row => row.id)), null)
    expect(new Set(projection.entries.map(entry => entry.row.id))).toEqual(new Set(['orphan', 'a', 'b', 'self']))
    expect(projection.entries.find(entry => entry.row.id === 'orphan')?.depth).toBe(0)
    expect(projection.entries.find(entry => entry.row.id === 'a')?.depth).toBe(0)
    expect(projection.entries.find(entry => entry.row.id === 'b')?.depth).toBe(1)
  })

  it('loads beyond 200 on explicit intent, deduplicates ancestor copies and preserves selection', async () => {
    const rows = Array.from({ length: 225 }, (_, i) => row(`saved-${i}`, i ? 'saved-0' : null))
    await withApp({ read: async params => params.offset ? { ...page(rows.slice(200), null, 225), ancestors: [rows[0]!] } : page(rows.slice(0, 200), 200, 225) }, async h => {
      openSessionPicker(h.app, true)
      await tick()
      expect(h.picker().props.order).toHaveLength(200)
      await h.event({ ev: 'select', item: 'saved-199' })()
      await h.action('more')
      expect(h.picker().props.order).toHaveLength(225)
      expect(h.picker().props.selected).toBe('saved-199')
      expect(h.calls.filter(call => call.method === 'session.tree')).toHaveLength(2)
      await tick()
      expect(h.calls.filter(call => call.method === 'session.tree')).toHaveLength(2)
    })
  })

  it('renames with canonical readback, sorts without losing selection, and shows workspace paths in the flat picker too', async () => {
    let title = 'saved'
    const renamed = Promise.withResolvers<{ session_key: string; title: string }>()
    await withApp({
      read: async () => page([row('active'), row('saved', null, { title })]),
      rename: async (id, value) => {
        expect([id, value]).toEqual(['saved', 'Canonical'])
        title = 'Canonical'

        return renamed.promise
      }
    }, async h => {
      openSessionPicker(h.app)
      await tick()
      await h.event({ ev: 'select', item: 'saved' })()
      await h.action('sort')
      expect(h.picker().props.selected).toBe('saved')
      expect(h.calls.at(-1)?.params).toMatchObject({ selected_session_id: 'saved', sort: 'title' })
      expect(h.picker().props.items).toContainEqual(expect.objectContaining({ facts: expect.objectContaining({ path: '/work/saved' }), id: 'saved' }))
      await h.action('path')
      expect(h.picker().props.columns).toEqual([{ format: 'dim', id: 'size' }])
      await h.action('rename')
      await h.key('u', undefined)
      // Native picker owns drawing, not editing. Ctrl+U clears its private title draft.
      h.app.overlays.at(-1)?.onKey({ alt: false, ctrl: true, meta: false, name: 'u', shift: false })
      await h.key('paste', 'Canonical')
      await h.key('enter')
      await h.key('enter')
      expect(h.calls.filter(call => call.method === 'session.rename')).toHaveLength(1)
      renamed.resolve({ session_key: 'saved', title: 'Canonical' })
      await tick()
      expect(h.picker().props.items).toContainEqual(expect.objectContaining({ id: 'saved', label: 'Canonical' }))
      expect(h.picker().props.selected).toBe('saved')
      expect(h.app.storedSid).toBe('active')
    })
  })

  it('activates only after safe confirmation, Enter defaults to cancel, and busy sessions never resume', async () => {
    await withApp({ read: async () => page([row('active'), row('saved')]) }, async h => {
      const resume = vi.spyOn(h.app, 'resume').mockResolvedValue()
      openSessionPicker(h.app, true)
      await tick()
      await h.event({ ev: 'activate', item: 'saved' })()
      expect(h.app.overlays.at(-1)?.key).toContain('confirm:')
      expect(resume).not.toHaveBeenCalled()
      await h.key('enter')
      expect(resume).not.toHaveBeenCalled()
      await h.event({ ev: 'activate', item: 'saved' })()
      h.app.busy = { label: 'Running', since: {}, startedAt: Date.now() }
      await h.key('y')
      expect(resume).not.toHaveBeenCalled()
      h.app.busy = null
      await h.event({ ev: 'activate', item: 'saved' })()
      await h.key('y')
      expect(resume).toHaveBeenCalledExactlyOnceWith('saved')
      expect(h.calls.some(call => call.method === 'session.undo')).toBe(false)
    })
  })

  it('reuses durable fork intent only after confirmation and never forks a highlighted foreign branch', async () => {
    await withApp({ read: async () => page([row('active'), row('saved')]) }, async h => {
      openSessionPicker(h.app, true)
      await tick()
      await h.event({ ev: 'select', item: 'saved' })()
      await h.action('fork')
      expect(h.calls.some(call => call.method === 'session.fork')).toBe(false)
      await h.event({ ev: 'select', item: 'active' })()
      await h.action('fork')
      expect(h.calls.some(call => call.method === 'session.fork')).toBe(false)
      await h.key('y')
      expect(h.calls.filter(call => call.method === 'session.fork')).toEqual([{ method: 'session.fork', params: { session_id: 'live' } }])
    })
  })

  it('ignores stale list replies, old native callbacks, and confirmations after a session switch', async () => {
    const late = Promise.withResolvers<SessionTreeResult>()
    let reads = 0
    await withApp({ read: async () => ++reads === 1 ? late.promise : page([row('saved')]) }, async h => {
      const resume = vi.spyOn(h.app, 'resume').mockResolvedValue()
      openSessionPicker(h.app, true)
      await tick()
      const old = h.event({ ev: 'activate', item: 'saved' })
      h.app.close(h.app.overlays.at(-1)!)
      openSessionPicker(h.app, true)
      await tick()
      await old()
      late.resolve(page([row('wrong-late-row')]))
      await tick()
      expect(h.picker().props.order).toEqual(['saved'])
      await h.event({ ev: 'activate', item: 'saved' })()
      h.app.sid = 'different-live'
      await h.key('y')
      expect(resume).not.toHaveBeenCalled()
    })
  })

  it('searches the authority rather than only the loaded page and ignores out-of-order search results', async () => {
    const old = Promise.withResolvers<SessionTreeResult>()
    await withApp({ read: async params => params.query === 'x' ? old.promise : page([row(params.query ? 'needle-fork' : 'active')]) }, async h => {
      openSessionPicker(h.app, true)
      await tick()
      await h.key('x', 'x')
      await h.key('paste', 'needle')
      old.resolve(page([row('wrong-old-search')]))
      await tick()
      expect(h.picker().props.order).toEqual(['needle-fork'])
      expect(h.calls.filter(call => call.method === 'session.tree').at(-1)?.params).toMatchObject({ offset: 0, query: 'xneedle' })
    })
  })

  it('registers tree/search/previousBranch/nextBranch intents with no local-key collisions', () => {
    expect(APP_ACTIONS.map(action => action.id)).toEqual(expect.arrayContaining(['app.tree', 'app.tree.search']))
    expect(SESSION_ACTIONS.map(action => action.id)).toEqual(expect.arrayContaining(['search', 'previousBranch', 'nextBranch']))

    for (const binding of SESSION_ACTIONS) {
      for (const chord of binding.keys) {
        const parts = chord.split('+')
        const name = parts.pop()!
        const key = { alt: parts.includes('alt'), ctrl: parts.includes('ctrl'), meta: false, name, shift: parts.includes('shift') }
        expect(SESSION_ACTIONS.filter(action => matchesAction(action, key))).toEqual([binding])
      }
    }
  })
})
