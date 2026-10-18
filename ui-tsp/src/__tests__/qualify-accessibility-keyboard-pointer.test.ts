import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session, type Surface, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { normalizeChord } from '../actions.js'
import { App, INPUT_ID } from '../app.js'
import { openBrowserBlocks } from '../overlays/browser-blocks.js'
import { openHelp } from '../overlays/help.js'
import { openSettings } from '../overlays/settings.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-a11y-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const flatten = (trees: readonly Tree[]): Tree[] => trees.flatMap(tree => [tree, ...flatten(tree.children)])

interface Harness {
  app: App
  gw: GatewayClient
  surface: Surface
  nodes(): Tree[]
  press(bytes: string): Promise<void>
  click(target: Tree): Promise<void>
}

async function withApp(run: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async method => {
    switch (method) {
      case 'setup.status': return { provider_configured: true }

      case 'session.create': return { session_id: 'a11y-session', info: { model: 'fixture-model', reasoning_effort: 'medium' } }

      case 'settings.get': return { fields: {}, profile: 'a11y-fixture' }

      case 'config.get': return { value: 'queue' }

      case 'jobs.list': return { jobs: [] }

      case 'commands.catalog': return { pairs: [] }

      case 'complete.slash': return { items: [] }

      case 'plan.status': return { enabled: false, generating: false, plan: null }

      case 'browser.blocks': return { available: true, blocks: [
        { target_id: 'owned', owned: true, available: true, title: 'Owned fixture', url: 'about:blank' },
        { target_id: 'other', owned: false, available: false, title: 'Unavailable fixture', url: 'about:blank' }
      ] }

      default: throw new Error(`Unexpected accessibility fixture RPC: ${method}`)
    }
  })
  const app = new App(tern, gw, 'test')
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }
  const nodes = () => view.regions.flatMap(region => flatten(region?.children ?? []))

  const press = async (bytes: string) => { input.emit('data', bytes); await rendered(); await rendered() }

  try {
    await app.newSession()
    await rendered()
    await rendered()
    await run({ app, gw, surface, nodes, press, click: async target => {
      const action = surface.dispatch({ ev: 'action', act: 'click', id: target.id, sf: surface.id, raw: {} })
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

function button(nodes: Tree[], role: string): Tree {
  const target = nodes.find(node => node.props.role === role)!
  expect(target, role).toBeDefined()
  expect(target.kind, role).toBe('el')
  expect(target.props.tag, role).toBe('button')
  expect(target.props.aria || target.props.text || flatten(target.children).some(child => child.props.text), role).toBeTruthy()

  return target
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.splash === undefined) { delete process.env.HERMES_TUI_SPLASH } else { process.env.HERMES_TUI_SPLASH = isolated.splash }
  rmSync(isolated.home, { force: true, recursive: true })
})

describe('T19 accessibility and input ownership (SDK peer, not native-window certification)', () => {
  it('emits named host buttons for dock actions and sheet actions without changing OMP roles', async () => {
    await withApp(async ({ app, nodes, click }) => {
      for (const role of ['omp.composer.model', 'omp.composer.effort', 'omp.composer.mic', 'omp.composer.settings', 'omp.composer.send', 'omp.composer.mic.hold-unavailable', 'omp.live.toggle']) {
        button(nodes(), role)
      }

      await click(button(nodes(), 'omp.composer.settings'))
      expect(nodes().some(node => node.kind === 'prefs')).toBe(true)
      app.close(app.overlays.at(-1)!)
      app.report({ title: 'Accessibility report', text: 'Read-only fixture', status: 'ready' })
      await rendered()
      expect(nodes().filter(node => node.props.role === 'omp.btn').every(node => node.kind === 'el' && node.props.tag === 'button')).toBe(true)
      button(nodes(), 'omp.btn')
    })
  })

  it('browser sheet actions and editor are named while unavailable ownership stays guarded', async () => {
    await withApp(async ({ app, nodes, click, gw, press, surface }) => {
      const focus = vi.spyOn(surface, 'focus')
      openBrowserBlocks(app)
      await rendered()
      const buttons = nodes().filter(node => node.props.role === 'omp.btn')
      expect(buttons.length).toBeGreaterThan(3)
      expect(buttons.every(node => node.kind === 'el' && node.props.tag === 'button')).toBe(true)
      const unavailable = buttons.find(node => node.props.title === 'Hand over block other')!
      await click(unavailable)
      expect(gw.request).not.toHaveBeenCalledWith('browser.adopt', expect.anything())
      await click(buttons.find(node => node.props.key === 'frame')!)
      const field = nodes().find(node => node.props.key === 'frame-path')!
      expect(field.props.aria).toBe('Evaluation frame path')
      expect(focus).toHaveBeenLastCalledWith(field.id)
      await press('0')
      expect(nodes().find(node => node.props.key === 'frame-path')?.props.text).toBe('main0')
      expect(app.composer.text).toBe('')
      await press('\x1b[27u')
      expect(nodes().some(node => node.props.key === 'frame-path')).toBe(false)
      expect(app.overlays.at(-1)?.key).toBe('browser-blocks')
      await press('\x1b[27u')
      expect(app.overlays).toHaveLength(0)
    })
  })

  it('keyboard and pointer dismissal restore exact hidden composer draft/caret; nested secret keeps priority', async () => {
    await withApp(async ({ app, surface, nodes, press, click, gw }) => {
      app.composer.set('Preserved draft', 4)
      const focus = vi.spyOn(surface, 'focus')
      openSettings(app)
      await rendered()
      await press('\x1b[27u')
      expect(focus).toHaveBeenLastCalledWith(INPUT_ID)
      expect([app.composer.text, app.composer.cursor]).toEqual(['Preserved draft', 4])
      await openHelp(app)
      await rendered()
      const staleClose = nodes().find(node => node.props.key === 'close' && node.props.role === 'omp.btn')!
      gw.emit('request', { id: 'masked-a11y', method: 'secret', params: { session_id: app.sid, prompt: 'Fixture secret', env_var: 'FIXTURE' }, respond: vi.fn() })
      await rendered()
      const field = nodes().find(node => node.kind === 'input')!
      expect(field.props.aria).toBeTruthy()
      await click(staleClose)
      expect(app.overlays.at(-1)?.key).toBe('prompt:masked-a11y')
      await press('\x1b[27u')
      expect(app.overlays.at(-1)?.key).toBe('help')
      await click(nodes().find(node => node.props.key === 'close' && node.props.role === 'omp.btn')!)
      expect(focus).toHaveBeenLastCalledWith(INPUT_ID)
      expect([app.composer.text, app.composer.cursor]).toEqual(['Preserved draft', 4])
      expect(gw.request).not.toHaveBeenCalledWith('prompt.submit', expect.anything())
    })
  })

  it('pairs approval actions with native buttons and labels list navigation without bypassing the owner', async () => {
    await withApp(async ({ app, gw, nodes }) => {
      const respond = vi.fn()
      gw.emit('request', { id: 'approval-a11y', method: 'approval', params: { session_id: app.sid, command: 'fixture-only', choices: ['once', 'deny'] }, respond })
      await rendered()
      expect(nodes().find(node => node.kind === 'list')?.props.aria).toBe('Approval choices')
      const choices = nodes().filter(node => node.props.role === 'omp.btn')
      expect(choices.map(node => [node.kind, node.props.tag, node.props.text])).toEqual([
        ['el', 'button', 'Deny'], ['el', 'button', 'Choose']
      ])
      expect(respond).not.toHaveBeenCalled()
    })
  })

  it('explains host/preset interception and keeps host-owned chords out of configurable bindings', async () => {
    await withApp(async ({ app, nodes }) => {
      await openHelp(app)
      await rendered()
      expect(nodes().find(node => node.props.key === 'host-keys')?.props.text).toContain('active preset may intercept')

      for (const chord of ['meta+h', 'ctrl+shift+c', 'alt+f4']) {expect(() => normalizeChord(chord)).toThrow('Host-reserved')}
    })
  })
})
