import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { SettingsGetResult } from '@hermes/shared/gateway-events'
import type { Surface, Tree } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { actionForKey, APP_ACTIONS, effectiveActions, normalizeChord, shortcutsMarkdown } from '../actions.js'
import { App, INPUT_ID } from '../app.js'
import { openSettings } from '../overlays/settings.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-tern-bindings-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const chord = (name: string, modifiers = 1) => `\x1b[${name.codePointAt(0)};${modifiers}u`
const ctx = { busy: false, completionOpen: false, composerEmpty: true, overlayOpen: false, queued: false }
const key = (name: string) => ({ alt: false, ctrl: false, meta: false, name, shift: false })

function profile(name: string, bindings: unknown = {}, visible = false): SettingsGetResult {
  return { profile: name, fields: {
    'display.tern_keybindings': { category: 'display', default: {}, description: 'Action bindings', type: 'object', value: bindings },
    'display.tern_profile_identity': { category: 'display', default: false, description: 'Owning profile', type: 'boolean', value: visible }
  } }
}

interface Harness {
  app: App
  gw: GatewayClient
  surface: Surface
  nodes(): Tree[]
  press(bytes: string): Promise<void>
  change(item: string, value: unknown): Promise<void>
}

async function withApp(initial: SettingsGetResult, run: (h: Harness) => Promise<void>) {
  let stored = structuredClone(initial)
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const handshake = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await handshake).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    switch (method) {
      case 'settings.get': return structuredClone(stored)
      case 'settings.set': {
        const p = params as { key: string; value: unknown }
        stored.fields[p.key]!.value = p.value

        return { confirm_required: false, confirm_message: '', key: p.key, value: p.value }
      }

      case 'setup.status': return { provider_configured: true }

      case 'config.get': return { value: 'queue' }

      case 'jobs.list': return { jobs: [] }

      case 'session.create': return { session_id: 'session-1', info: { cwd: '/not-a-profile', model: 'fixture' } }

      case 'commands.catalog': return { pairs: [] }

      case 'complete.slash': return { items: [] }

      case 'prompt.submit': return { status: 'ok' }

      default: throw new Error(`Unexpected fixture RPC ${method}`)
    }
  })
  const app = new App(tern, gw, 'test')
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view = View.from({ main: [], dock: [], layer: [] })
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }

  const nodes = (): Tree[] => {
    const flatten = (node: Tree): Tree[] => [node, ...node.children.flatMap(flatten)]

    return view.regions.flatMap(region => region?.children.flatMap(flatten) ?? [])
  }

  const press = async (bytes: string) => { input.emit('data', bytes); await rendered(); await rendered() }

  try {
    await app.newSession()
    await rendered()
    await rendered()
    await run({ app, gw, surface, nodes, press, change: async (item, value) => {
      const prefs = nodes().find(node => node.kind === 'prefs')!
      const action = surface.dispatch({ ev: 'change', id: prefs.id, item, raw: {}, sf: 'hermes', value } as Parameters<Surface['dispatch']>[0])
      expect(action).toBeTypeOf('function')
      await action!()
      await rendered()
      await rendered()
    } })
  } finally {
    app.quit()
    await running
  }
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.splash === undefined) { delete process.env.HERMES_TUI_SPLASH } else { process.env.HERMES_TUI_SPLASH = isolated.splash }
  rmSync(isolated.home, { force: true, recursive: true })
})

describe('configurable bindings and owning profile', () => {
  it('composes clarify rebind, disable, reset, collision checks and live dock hints without bypassing prompts', async () => {
    expect(() => effectiveActions({ 'app.help': 'alt+h' })).toThrow('Duplicate')
    await withApp(profile('work', { 'app.clarify.toggle': 'alt+k' }), async ({ app, gw, nodes, press }) => {
      const respond = vi.fn()
      gw.emit('request', {
        id: 'clarify-binding', method: 'clarify',
        params: { session_id: app.sid, questions: [{ qid: 'q0', question: 'Which?', choices: ['A', 'B'] }] },
        respond
      })
      await rendered()
      await press(chord('h', 3))
      expect(nodes().some(node => node.props.key === 'waiting')).toBe(false)
      expect(nodes().some(node => node.props.title === 'Hide  alt+k')).toBe(true)
      await press(chord('k', 3))
      expect(nodes().find(node => node.props.key === 'show')?.props.text).toBe('Show question · alt+k')
      app.composer.set('main draft')
      await press(chord('k', 3))
      expect(nodes().some(node => node.props.key === 'waiting')).toBe(false)
      expect(app.composer.text).toBe('main draft')
      app.bindings.accept(profile('work', { 'app.clarify.toggle': [] }), 'session-1')
      await press(chord('k', 3))
      await press(chord('h', 3))
      expect(nodes().some(node => node.props.key === 'waiting')).toBe(false)
      expect(nodes().some(node => node.props.title === 'Hide  ')).toBe(true)
      app.bindings.accept(profile('work', { 'app.clarify.toggle': null }), 'session-1')
      await press(chord('h', 3))
      expect(nodes().some(node => node.props.key === 'waiting')).toBe(true)
      gw.emit('request', { id: 'priority-secret', method: 'secret', params: { session_id: app.sid, prompt: 'Secret' }, respond: vi.fn() })
      await press(chord('h', 3))
      expect(nodes().some(node => node.props.key === 'waiting')).toBe(true)
      expect(respond).not.toHaveBeenCalled()
    })
  })

  it('loads via the owning gateway, rebinds and resets through native Settings readback, updating help and dock together', async () => {
    await withApp(profile('work'), async ({ app, gw, nodes, press, change }) => {
      expect(gw.request).toHaveBeenCalledWith('settings.get', { session_id: 'session-1' })
      app.composer.set('draft kept', 4)
      openSettings(app)
      await rendered()
      await change('display.tern_keybindings', { 'app.help': ['alt+k'] })
      app.close(app.overlays.at(-1)!)
      await press('\x1bOP')
      expect(app.overlays).toHaveLength(0)
      expect(nodes().find(node => node.props.role === 'omp.composer.hint')?.props.text).toBe('alt+k help')
      await press(chord('k', 3))
      expect(app.overlays.at(-1)?.key).toBe('help')
      expect(JSON.stringify(nodes().filter(node => node.kind === 'table').map(node => node.props))).toContain('alt+k')
      app.close(app.overlays.at(-1)!)
      openSettings(app)
      await rendered()
      await change('display.tern_keybindings', {})
      app.close(app.overlays.at(-1)!)
      await press('\x1bOP')
      expect(app.overlays.at(-1)?.key).toBe('help')
      expect(app.composer.text).toBe('draft kept')
      expect(app.composer.cursor).toBe(4)
    })
  })

  it('rejects duplicates and permissive modifier aliases atomically without saving', async () => {
    expect(() => effectiveActions({ 'app.help': ['shift+alt+m'] })).not.toThrow()
    expect(() => effectiveActions({ 'app.help': ['alt+m'] })).toThrow('Duplicate')
    expect(() => effectiveActions({ 'app.help': ['alt+k', 'option+k'] })).toThrow('Duplicate')
    expect(() => effectiveActions({ 'app.help': ['ctrl+shift+d'] })).toThrow('Overlapping')
    expect(() => effectiveActions({ 'session.rename': ['alt+k'] })).toThrow('Unknown')
    await withApp(profile('work'), async ({ app, gw, nodes, change }) => {
      openSettings(app)
      await rendered()
      await change('display.tern_keybindings', { 'app.help': ['alt+m'] })
      expect(gw.request).not.toHaveBeenCalledWith('settings.set', expect.anything())
      expect(JSON.stringify(nodes())).toContain('Duplicate chord')
      expect(app.bindings.actions.find(action => action.id === 'app.help')?.keys).toEqual(['f1', 'alt+/'])
    })
  })

  it('rejects hidden host aliases and composer-owned chords, while disabled actions disappear from effective hints', async () => {
    for (const chord of ['CMD+h', 'super+h', 'meta+h', 'ctrl+shift+c', 'alt+f4']) {
      expect(() => normalizeChord(chord)).toThrow('Host-reserved')
    }

    for (const chord of ['h', 'shift+h', '.', 'space', 'ctrl+a', 'alt+b', 'enter']) {
      expect(() => effectiveActions({ 'app.help': chord })).toThrow('Composer-owned')
    }

    expect(() => normalizeChord('ctrl+ctrl+h')).toThrow('Invalid')
    await withApp(profile('work', { 'app.help': [] }), async ({ nodes, press, app }) => {
      await press('\x1bOP')
      expect(app.overlays).toHaveLength(0)
      expect(nodes().find(node => node.props.role === 'omp.composer.hint')?.props.text).toBe('/help help')
    })
  })

  it('lets Settings repair an invalid on-disk map without installing partial bindings', async () => {
    await withApp(profile('work', { 'app.help': 'alt+m' }), async ({ app, nodes, change, press }) => {
      expect(app.bindings.actions).toEqual(APP_ACTIONS)
      openSettings(app)
      await rendered()
      expect(nodes().some(node => node.kind === 'prefs')).toBe(true)
      expect(JSON.stringify(nodes())).toContain('Duplicate chord')
      await change('display.tern_keybindings', { 'app.help': 'alt+k' })
      app.close(app.overlays.at(-1)!)
      await press(chord('k', 3))
      expect(app.overlays.at(-1)?.key).toBe('help')
    })
  })

  it('keeps a rebound clear key below modal-local ownership', async () => {
    await withApp(profile('work', { 'app.clear': 'alt+x' }), async ({ app, press }) => {
      app.composer.set('hidden draft')
      await press('\x1bOP')
      await press(chord('x', 3))
      expect(app.composer.text).toBe('hidden draft')
      expect(app.overlays.at(-1)?.key).toBe('help')
    })
  })

  it('keeps overlay-local keys and non-Vim default editing unchanged', async () => {
    await withApp(profile('work', { 'app.help': 'alt+k' }), async ({ app, press }) => {
      await press('hjkl')
      expect(app.composer.text).toBe('hjkl')
      await press(chord('k', 3))
      await press(chord('k', 3))
      expect(app.overlays.at(-1)?.key).toBe('help')
      await press('\x1b[27u')
      expect(app.overlays).toHaveLength(0)
      expect(app.composer.text).toBe('hjkl')
      expect(effectiveActions({})).toEqual(APP_ACTIONS)
      expect(effectiveActions({ 'app.help': null })).toEqual(APP_ACTIONS)
    })
  })

  it('shows only the explicitly enabled owning profile, never cwd or a stale profile across sessions', async () => {
    await withApp(profile('work', {}, true), async ({ app, gw, nodes, change }) => {
      expect(nodes().find(node => node.props.role === 'omp.composer.profile')?.props.text).toBe('work')
      openSettings(app)
      await rendered()
      await change('display.tern_profile_identity', false)
      expect(nodes().find(node => node.props.role === 'omp.composer.profile')).toBeUndefined()
      const stale = Promise.withResolvers<SettingsGetResult>()
      vi.mocked(gw.request).mockReturnValueOnce(stale.promise)
      const reading = app.bindings.refresh()
      app.sid = 'session-2'
      app.bindings.accept(profile('personal', { 'app.help': 'alt+k' }, true), 'session-2')
      stale.resolve(profile('work', {}, true))
      await reading
      await rendered()
      expect(nodes().find(node => node.props.role === 'omp.composer.profile')?.props.text).toBe('personal')
      expect(app.bindings.profile).not.toBe('/not-a-profile')
    })
  })

  it('ignores an older adoption read after a confirmed Settings readback on the same session', async () => {
    await withApp(profile('work'), async ({ app, gw }) => {
      const stale = Promise.withResolvers<SettingsGetResult>()
      vi.mocked(gw.request).mockReturnValueOnce(stale.promise)
      const reading = app.bindings.refresh()
      app.bindings.accept(profile('work', { 'app.help': 'alt+k' }, true), 'session-1')
      stale.resolve(profile('work'))
      await reading
      expect(app.bindings.profile).toBe('work')
      expect(app.bindings.actions.find(action => action.id === 'app.help')?.keys).toEqual(['alt+k'])
    })
  })

  it('drops retained Settings callbacks and old preference loads after session replacement', async () => {
    await withApp(profile('work', {}, true), async ({ app, gw, nodes, surface }) => {
      openSettings(app)
      await rendered()
      const prefs = nodes().find(node => node.kind === 'prefs')!
      const stale = surface.dispatch({ ev: 'change', id: prefs.id, item: 'display.tern_profile_identity', value: false, raw: {}, sf: 'hermes' })!
      app.sid = 'session-2'
      app.changed()
      await rendered()
      expect(app.bindings.profile).toBe('')
      expect(nodes().find(node => node.props.role === 'omp.composer.profile')).toBeUndefined()
      await stale()
      expect(gw.request).not.toHaveBeenCalledWith('settings.set', expect.anything())
    })
  })

  it('composes live-voice and hold-info rebinds, disables and resets below modal ownership', async () => {
    expect(() => effectiveActions({ 'app.live.toggle': 'alt+shift+space' })).toThrow('Duplicate')
    expect(() => effectiveActions({ 'app.stt.hold.info': 'alt+shift+v' })).toThrow('Duplicate')
    await withApp(profile('work', { 'app.live.toggle': 'alt+k', 'app.stt.hold.info': 'alt+y' }), async ({ app, press }) => {
      const live = vi.spyOn(app.liveVoice, 'toggle').mockImplementation(() => {})
      const hold = vi.spyOn(app.dictation, 'explainHold').mockImplementation(() => {})
      await press(chord('v', 4))
      await press('\x1b[32;4u')
      expect(live).not.toHaveBeenCalled()
      expect(hold).not.toHaveBeenCalled()
      await press(chord('k', 3))
      await press(chord('y', 3))
      expect(live).toHaveBeenCalledTimes(1)
      expect(hold).toHaveBeenCalledTimes(1)
      app.bindings.accept(profile('work', { 'app.live.toggle': [], 'app.stt.hold.info': [] }), 'session-1')
      await press(chord('k', 3))
      await press(chord('y', 3))
      expect(live).toHaveBeenCalledTimes(1)
      expect(hold).toHaveBeenCalledTimes(1)
      app.bindings.accept(profile('work', { 'app.live.toggle': null, 'app.stt.hold.info': null }), 'session-1')
      await press(chord('v', 4))
      await press('\x1b[32;4u')
      expect(live).toHaveBeenCalledTimes(2)
      expect(hold).toHaveBeenCalledTimes(2)
      openSettings(app)
      await rendered()
      await press(chord('v', 4))
      await press('\x1b[32;4u')
      expect(live).toHaveBeenCalledTimes(2)
      expect(hold).toHaveBeenCalledTimes(2)
    })
  })

  it('copies the current Unicode line without changing the draft or caret', async () => {
    await withApp(profile('work'), async ({ app, press }) => {
      app.composer.set('first\nλ 🦉 line\nlast', 10)
      const write = vi.spyOn(process.stdout, 'write').mockImplementation(() => true)

      try {
        await press(chord('l', 4))
        expect(write).toHaveBeenCalledWith(`\x1b]52;c;${Buffer.from('λ 🦉 line').toString('base64')}\x07`)
        expect(app.composer.text).toBe('first\nλ 🦉 line\nlast')
        expect(app.composer.cursor).toBe(10)
      } finally { write.mockRestore() }
    })
  })

  it('routes retry through the existing exact text-only failure guard, never a busy/newer draft', async () => {
    await withApp(profile('work'), async ({ app, surface, gw, press }) => {
      await surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text: 'retry text' })!()
      gw.emit('event', { type: 'message.complete', session_id: app.sid, payload: {
        status: 'error', error: 'Transient', error_surface: { layer: 'provider', code: 'transient', retryable: true }
      } })
      await press('\x1b[15~')
      expect(gw.request).toHaveBeenCalledWith('prompt.submit', { session_id: 'session-1', text: 'retry text', image_paths: [] })
      expect(vi.mocked(gw.request).mock.calls.filter(([method]) => method === 'prompt.submit')).toHaveLength(2)
      await press('\x1b[15~')
      expect(vi.mocked(gw.request).mock.calls.filter(([method]) => method === 'prompt.submit')).toHaveLength(2)
    })
  })

  it('makes approval a separate context; a draft or modal cannot be approved by an app key', async () => {
    const bindings = effectiveActions({ 'app.approval.approve': 'alt+k', 'app.help': 'alt+k' })
    expect(actionForKey({ ...key('k'), alt: true }, ctx, bindings)?.id).toBe('app.help')
    await withApp(profile('work', { 'app.approval.approve': 'alt+k' }), async ({ app, gw, press }) => {
      const respond = vi.fn()
      gw.emit('request', { id: 'approval-test', method: 'approval', params: { session_id: app.sid, command: 'echo test', choices: ['once', 'deny'] }, respond })
      await rendered()
      app.composer.set('do not approve')
      await press(chord('k', 3))
      expect(respond).not.toHaveBeenCalled()
      app.composer.set('')
      openSettings(app)
      await rendered()
      await press(chord('k', 3))
      expect(respond).not.toHaveBeenCalled()
      app.close(app.overlays.at(-1)!)
      await press(chord('k', 3))
      expect(respond).toHaveBeenCalledWith({ choice: 'once' })
    })
  })

  it('generates shortcut rows from the complete effective registry, including composed actions', () => {
    const actions = effectiveActions({ 'app.help': ['alt+k'] })
    const doc = shortcutsMarkdown(actions)

    for (const action of actions) {
      expect(doc).toContain(`| ${action.id} | ${action.keys.join(' / ') || '(unbound)'} |`)
    }

    expect(doc).toContain('app.model.cycleForward')
    expect(doc).toContain('app.history.search')
    expect(doc).toContain('app.editor.external')
    expect(doc).toContain('app.tree')
  })
})
