import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { Key, Surface } from '@stencil-hq/tern'
import { node, Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { type Action, type ActionContext, APP_ACTIONS, matchesAction } from '../actions.js'
import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-action-registry-'))
  const previous = process.env.HERMES_HOME
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, previousSplash }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const views = new WeakMap<Surface, View>()
const chord = (name: string, modifiers = 1) => `\x1b[${name.codePointAt(0)};${modifiers}u`

interface Harness {
  app: App
  gw: GatewayClient
  surface: Surface
  press(bytes: string): Promise<void>
}

async function withApp(run: (harness: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  let display = 'show'
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'config.get') {
      return { value: 'medium', display }
    }

    if (method === 'config.set') {
      const value = params && 'value' in params ? params.value : undefined

      if (value === 'show' || value === 'hide') {
        display = value
      }

      return { value }
    }

    if (method === 'model.options') {
      return {
        model: 'fixture-model',
        providers: [{ slug: 'fixture', name: 'Fixture', is_current: true, models: ['fixture-model'] }]
      }
    }

    if (method === 'settings.get') {
      return { fields: {}, profile: 'fixture' }
    }

    if (method === 'jobs.list') {
      return { jobs: [] }
    }

    if (method === 'subagent.hub') {
      return { agents: [] }
    }

    if (method === 'session.list') {
      return { sessions: [] }
    }

    if (method === 'session.tree') {
      return { ancestors: [], next_offset: null, sessions: [], total: 0 }
    }

    if (method === 'commands.catalog') {
      return { pairs: [['/context', 'Context details']] }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'slash.exec') {
      return { output: 'Gateway command output' }
    }

    if (method === 'session.interrupt') {
      return {}
    }

    throw new Error(`Unexpected RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.info = { model: 'fixture-model', reasoning_effort: 'medium' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)

  surface.render = view => {
    views.set(surface, View.from(view))
    render(view)
  }

  try {
    await run({
      app,
      gw,
      surface,
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
        await rendered()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

const shortcuts = [
  ['alt+m', chord('m', 3), 'models'],
  ['alt+p', chord('p', 3), 'models'],
  ['alt+,', chord(',', 3), 'settings'],
  ['ctrl+,', chord(',', 5), 'settings'],
  ['alt+s', chord('s', 3), 'sessions'],
  ['alt+j', chord('j', 3), 'jobs'],
  ['f1', '\x1bOP', 'help'],
  ['alt+/', chord('/', 3), 'help']
] as const

const slashShortcuts = [
  ['alt+c', chord('c', 3), 'context'],
  ['alt+u', chord('u', 3), 'usage'],
  ['alt+a', chord('a', 3), 'agents']
] as const

const newChords = [
  ...shortcuts.map(([name, bytes]) => [name, bytes]),
  ...slashShortcuts.map(([name, bytes]) => [name, bytes]),
  ['alt+h', chord('h', 3)],
  ['ctrl+t', chord('t', 5)],
  ['alt+shift+c', chord('c', 4)]
]

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

describe('app action registry', () => {
  it.each(shortcuts)('%s opens the %s sheet without changing the draft', async (_name, bytes, overlay) => {
    await withApp(async ({ app, gw, surface, press }) => {
      app.composer.set('draft kept', 3)
      await press(bytes)
      expect(app.overlays.at(-1)?.key).toBe(overlay)
      expect(app.composer.text).toBe('draft kept')
      expect(app.composer.cursor).toBe(3)
      expect(views.get(surface)?.regions[2]?.children.length).toBeGreaterThan(0)
      expect(gw.request).not.toHaveBeenCalledWith('prompt.submit', expect.anything())
    })
  })

  it('Alt+P locks the picker to session scope while Alt+M keeps profile-default choice', async () => {
    await withApp(async ({ app, gw, surface, press }) => {
      await press(chord('m', 3))
      expect(JSON.stringify(views.get(surface)?.regions[2])).toContain('Save as default')
      app.close(app.overlays[0]!)
      await press(chord('p', 3))
      expect(JSON.stringify(views.get(surface)?.regions[2])).not.toContain('Save as default')
      await press(chord('g', 5))
      await press('\x1b[13u')
      expect(gw.request).toHaveBeenCalledWith('config.set', {
        confirm_expensive_model: false,
        key: 'model',
        session_id: 'session-1',
        value: 'fixture-model --provider fixture --session'
      })
    })
  })

  it.each(slashShortcuts)('%s uses the existing slash path for /%s', async (_name, bytes, command) => {
    await withApp(async ({ app, gw, surface, press }) => {
      app.composer.set('unfinished prompt', 5)
      await press(bytes)
      const hub = command === 'agents'
      expect(gw.request).toHaveBeenCalledWith(hub ? 'subagent.hub' : 'slash.exec', hub ? { session_id: 'session-1' } : { command, session_id: 'session-1' })
      expect(app.transcript.entries.some(entry => entry.kind === 'panel')).toBe(false)
      const root = views.get(surface)?.regions.find(region => region?.id === 'layer')?.children[0]
      expect(root?.props.head).toBe(hub ? 'Agents · owned hub' : `/${command}`)

      if (!hub) {
        expect(root?.children[0]?.children[0]?.props.spans).toEqual([{ s: 'mono', t: 'Gateway command output' }])
      }

      expect(app.composer.text).toBe('unfinished prompt')
      expect(app.composer.cursor).toBe(5)
    })
  })

  it('Ctrl+T serializes canonical show/hide through the existing reasoning command without cycling effort', async () => {
    await withApp(async ({ app, gw, press }) => {
      await press(chord('t', 5) + chord('t', 5))
      expect(gw.request).toHaveBeenCalledWith('config.set', {
        key: 'reasoning',
        session_id: 'session-1',
        value: 'hide'
      })
      expect(gw.request).toHaveBeenCalledWith('config.set', {
        key: 'reasoning',
        session_id: 'session-1',
        value: 'show'
      })
      expect(app.info?.reasoning_effort).toBe('medium')
    })
  })

  it('does not send an in-flight reasoning toggle to a replacement session', async () => {
    await withApp(async ({ app, gw, press }) => {
      const read = Promise.withResolvers<{ value: string; display: string }>()
      vi.mocked(gw.request).mockReturnValueOnce(read.promise)
      await press(chord('t', 5))
      app.sid = 'session-2'
      read.resolve({ value: 'medium', display: 'show' })
      await rendered()
      expect(gw.request).not.toHaveBeenCalledWith('config.set', expect.anything())
    })
  })

  it('copies the exact Unicode/multiline draft through OSC52 and reports the request', async () => {
    await withApp(async ({ app, press }) => {
      app.composer.set('line one\nλ & 🦉', 2)
      const write = vi.spyOn(process.stdout, 'write').mockImplementation(() => true)

      try {
        await press(chord('c', 4))
        expect(write).toHaveBeenCalledWith(`\x1b]52;c;${Buffer.from('line one\nλ & 🦉').toString('base64')}\x07`)
        expect(app.composer.text).toBe('line one\nλ & 🦉')
        expect(app.composer.cursor).toBe(2)
        expect(app.transcript.entries).toContainEqual(
          expect.objectContaining({ text: 'Composer text sent to the terminal clipboard (OSC 52).' })
        )
      } finally {
        write.mockRestore()
      }
    })
  })

  it.each(newChords)('%s is inert under a modal even when its onKey declines', async (_name, bytes) => {
    await withApp(async ({ app, gw, press }) => {
      app.composer.set('do not edit')

      const owner = {
        key: 'fixture',
        modal: true,
        node: () => node('col', { key: 'fixture' }),
        onKey: vi.fn(() => false)
      }

      app.open(owner)
      await press(bytes!)
      expect(owner.onKey).toHaveBeenCalled()
      expect(app.overlays).toEqual([owner])
      expect(app.composer.text).toBe('do not edit')
      expect(gw.request).not.toHaveBeenCalled()
    })
  })

  it('lets a nonmodal overlay owner consume an app shortcut', async () => {
    await withApp(async ({ app, gw, press }) => {
      const owner = {
        key: 'owner',
        modal: false,
        node: () => node('col', { key: 'fixture' }),
        onKey: vi.fn(() => true)
      }

      app.open(owner)
      await press(chord('m', 3))
      expect(owner.onKey).toHaveBeenCalled()
      expect(app.overlays).toEqual([owner])
      expect(gw.request).not.toHaveBeenCalled()
    })
  })

  it('keeps Ctrl+C cancellation owned by settings', async () => {
    await withApp(async ({ app, press }) => {
      app.composer.set('preserved draft')
      await press(chord(',', 3))
      await press(chord('c', 5))
      expect(app.overlays).toHaveLength(0)
      expect(app.composer.text).toBe('preserved draft')
    })
  })

  it('keeps distinct tool expansion and visibility intents limited to empty drafts without overlays', async () => {
    await withApp(async ({ app, press }) => {
      const fold = vi.spyOn(app, 'toggleToolExpansion')
      const hide = vi.spyOn(app, 'toggleToolVisibility')
      app.composer.set('selection might exist')
      await press(chord('o', 5))
      expect(fold).not.toHaveBeenCalled()
      app.composer.set('')
      await press(chord('o', 5))
      await press(chord('o', 6))
      expect(fold).toHaveBeenCalledOnce()
      expect(hide).toHaveBeenCalledOnce()
    })
  })

  it('keeps effort cycling, queue recall, interrupt and Ctrl+D draft editing', async () => {
    await withApp(async ({ app, gw, press }) => {
      await press('\x1b[9;2u')
      expect(gw.request).toHaveBeenCalledWith('config.set', {
        key: 'reasoning',
        session_id: 'session-1',
        scope: 'session',
        value: 'high'
      })
      app.queue = ['oldest', 'next']
      app.composer.set('draft')
      await press('\x1b[1;3A')
      expect(app.queue).toEqual(['next'])
      expect(app.composer.text).toBe('oldest\ndraft')
      app.composer.set('abc', 1)
      await press(chord('d', 5))
      expect(app.composer.text).toBe('ac')
      app.busy = { label: 'Working', since: {}, startedAt: Date.now() }
      await press('\x1b[27u')
      expect(gw.request).toHaveBeenCalledWith('session.interrupt', { session_id: 'session-1' })
      await press(chord('c', 5))
      expect(app.composer.text).toBe('')
    })
  })

  it('spends the first shortcut on skipping the launch splash', async () => {
    process.env.HERMES_TUI_SPLASH = '1'

    try {
      await withApp(async ({ app, press }) => {
        await press(chord('m', 3))
        expect(app.overlays).toHaveLength(0)
        expect(app.composer.text).toBe('')
      })
    } finally {
      process.env.HERMES_TUI_SPLASH = '0'
    }
  })

  it('quits on Ctrl+D only when the draft is empty', async () => {
    await withApp(async ({ app, press }) => {
      const quit = vi.spyOn(app, 'quit').mockImplementation(() => {})
      await press(chord('d', 5))
      expect(quit).toHaveBeenCalledOnce()
      quit.mockRestore()
    })
  })

  it.each(['escape', 'shift+tab'])('lets completion own %s before interrupt or effort cycling', async binding => {
    await withApp(async ({ app, gw, surface, press }) => {
      const request = vi.mocked(gw.request).getMockImplementation()!
      vi.mocked(gw.request).mockImplementation(async (method, params) =>
        method === 'complete.slash'
          ? { items: [{ text: '/context', display: '/context', kind: 'command' }] }
          : request(method, params)
      )
      app.composer.set('/cont')
      app.busy = { label: 'Working', since: {}, startedAt: Date.now() }
      app.changed()
      await vi.waitFor(() => expect(JSON.stringify(views.get(surface)?.regions[2])).toContain('omp.autocomplete'))
      await press(binding === 'escape' ? '\x1b[27u' : '\x1b[9;2u')
      expect(gw.request).not.toHaveBeenCalledWith('session.interrupt', expect.anything())
      expect(gw.request).not.toHaveBeenCalledWith('config.set', expect.anything())
      expect(app.composer.text).toBe(binding === 'escape' ? '/cont' : '/context')
    })
  })

  it('never inserts unbound Alt letters, while retaining Alt word editing', async () => {
    await withApp(async ({ app, press }) => {
      app.composer.set('one two')
      await press(chord('x', 3))
      expect(app.composer.text).toBe('one two')
      await press(chord('b', 3))
      expect(app.composer.cursor).toBe(4)
      await press(chord('d', 3))
      expect(app.composer.text).toBe('one ')
    })
  })

  it('renders every registered title and chord in grouped help, plus a compact composer hint', async () => {
    await withApp(async ({ app, surface, press }) => {
      await press('\x1bOP')
      const tree = JSON.stringify(views.get(surface))

      for (const action of APP_ACTIONS) {
        expect(tree).toContain(action.title)
        expect(tree).toContain(action.group)

        for (const key of action.keys) {
          expect(tree).toContain(key)
        }
      }

      expect(tree).toContain('f1 help')
      expect(app.overlays.at(-1)?.key).toBe('help')
    })
  })
})

/** Enumerate all boolean contexts and all modifier combinations, including
 * legacy permissive matches; a duplicate must never be silently shadowed.
 */
function assertNoCollisions(actions: readonly Action[]) {
  const names = new Set(actions.flatMap(action => action.keys.map(key => key.split('+').at(-1)!)))

  for (let state = 0; state < 32; state++) {
    const ctx: ActionContext = {
      busy: Boolean(state & 1),
      composerEmpty: Boolean(state & 2),
      queued: Boolean(state & 4),
      overlayOpen: Boolean(state & 8),
      completionOpen: Boolean(state & 16)
    }

    for (const name of names) {
      for (let mods = 0; mods < 16; mods++) {
        const key: Key = {
          name,
          ctrl: Boolean(mods & 1),
          alt: Boolean(mods & 2),
          shift: Boolean(mods & 4),
          meta: Boolean(mods & 8)
        }

        const matches = actions.filter(action => action.when(ctx) && matchesAction(action, key))

        if (matches.length > 1) {
          throw new Error(`Collision: ${matches.map(action => action.id).join(', ')} (${name})`)
        }
      }
    }
  }
}

describe('shortcut collisions', () => {
  it('has no overlapping keys in any app context', () => assertNoCollisions(APP_ACTIONS))
  it('rejects an injected same-chord action with overlapping when', () => {
    const first = APP_ACTIONS.find(action => action.id === 'app.model.select')!
    expect(() => assertNoCollisions([...APP_ACTIONS, { ...first, id: 'duplicate' }])).toThrow(
      'Collision: app.model.select, duplicate'
    )
  })
  it('allows the same chord for mutually exclusive contexts', () => {
    const first = APP_ACTIONS.find(action => action.id === 'app.model.select')!
    expect(() =>
      assertNoCollisions([
        { ...first, when: ctx => ctx.composerEmpty },
        { ...first, id: 'nonempty', when: ctx => !ctx.composerEmpty }
      ])
    ).not.toThrow()
  })
})
