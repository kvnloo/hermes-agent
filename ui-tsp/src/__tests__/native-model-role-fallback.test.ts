import { EventEmitter } from 'node:events'
import { readFileSync, rmSync } from 'node:fs'

import type { ModelHubGetResult, ModelHubSetParams, ModelOptionProvider, ModelOptionsResult } from '@hermes/shared/gateway-events'
import type { Surface, TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { localCommand } from '../commands.js'
import { cycleModel } from '../model-cycle.js'
import { openModelHub } from '../overlays/model-hub.js'
import { openModelPicker, switchModel } from '../overlays/models.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-model-hub-'))
  const previous = process.env.HERMES_HOME
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, previousSplash }
})

const rendered = async () => { await new Promise<void>(resolve => setImmediate(resolve)); await new Promise<void>(resolve => setImmediate(resolve)) }
const views = new WeakMap<Surface, View>()

const providers: ModelOptionProvider[] = [
  ...['pool-only', 'oauth', 'api-key', 'custom:lab'].map(slug => ({ authenticated: true, models: ['one', 'two'], name: slug, slug })),
  { authenticated: false, models: ['one'], name: 'Locked', slug: 'locked' },
  { authenticated: false, models: [], name: 'Empty locked', slug: 'empty' }
]

function snapshot(): ModelHubGetResult {
  return {
    fallbacks: [{ model: 'two', provider: 'oauth' }],
    operations: { fallback_scopes: ['profile'], login_hint: 'Use Hermes model setup in a terminal.', max_fallbacks: 8, native_login: false, role_scopes: ['profile'], writable: true },
    profile: 'fixture-profile', providers: structuredClone(providers), revision: 'revision-1',
    roles: [{ id: 'vision', label: 'Vision', route: null, scope: 'profile' }, { id: 'plugin_role', label: 'Plugin role', route: { model: 'one', provider: 'api-key' }, scope: 'profile' }]
  }
}

function nodes(surface: Surface) {
  type Nodes = NonNullable<View['regions'][number]>['children']
  const walk = (items: Nodes): Nodes => items.flatMap(node => [node, ...walk(node.children)])

  return walk(views.get(surface)?.regions.flatMap(region => region?.children ?? []) ?? [])
}

async function click(surface: Surface, title: string) {
  const target = nodes(surface).find(node => typeof node.props.title === 'string' && node.props.title.startsWith(title))
  expect(target, title).toBeDefined()
  expect(target!.kind).toBe('el')
  expect(target!.props.tag).toBe('button')
  expect(target!.props.aria || target!.props.text).toBeTruthy()
  await surface.dispatch({ act: 'click', ev: 'action', id: target!.id, raw: {}, sf: 'hermes' })!()
  await rendered()
}

async function activate(surface: Surface, item: string) {
  const picker = nodes(surface).find(node => node.kind === 'picker')!
  expect(picker).toBeDefined()
  await surface.dispatch({ ev: 'activate', id: picker.id, item, raw: {}, sf: 'hermes' } as TspEvent)!()
  await rendered()
}

interface Fixture {
  read?: () => Promise<ModelHubGetResult>
  write?: (intent: ModelHubSetParams) => Promise<unknown>
}

async function withApp(fixture: Fixture, run: (app: App, surface: Surface, gw: GatewayClient, press: (bytes: string) => Promise<void>) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', term: 'fixture', v: 1, ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'model.hub.get') { return fixture.read ? fixture.read() : snapshot() }

    if (method === 'model.hub.set') { return fixture.write ? fixture.write(params as unknown as ModelHubSetParams) : { confirm_message: 'Potentially expensive model.', confirm_required: true } }

    if (method === 'model.options') { return { model: 'one', provider: 'pool-only', providers: structuredClone(providers) } }

    if (method === 'complete.slash') { return { items: [] } }

    if (method === 'config.set') { return { deferred: true, key: 'model', value: 'two' } }
    throw new Error(`Unexpected RPC ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.info = { model: 'one', provider: 'pool-only' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)

  surface.render = view => { views.set(surface, View.from(view)); render(view) }

  try { await run(app, surface, gw, async bytes => { input.emit('data', bytes); await rendered() }) } finally { app.quit(); await running }
}

const text = (surface: Surface) => JSON.stringify(nodes(surface).map(node => node.props))

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.previousSplash === undefined) { delete process.env.HERMES_TUI_SPLASH } else { process.env.HERMES_TUI_SPLASH = isolated.previousSplash }
  rmSync(isolated.home, { force: true, recursive: true })
})

describe('native model-role/fallback/provider management', () => {
  it('names all hub page actions and Close as native buttons, preserving draft on pointer close', async () => {
    await withApp({}, async (app, surface, gw) => {
      app.composer.set('untouched hub draft', 3)
      openModelHub(app)
      await rendered()

      for (const page of ['Auxiliary roles', 'Fallback chain', 'Providers']) {
        await click(surface, page)
        const actions = nodes(surface).filter(node => node.props.role === 'omp.btn')
        expect(actions.length).toBeGreaterThan(4)

        for (const action of actions) {
          expect(action.kind).toBe('el')
          expect(action.props.tag).toBe('button')
          expect(action.props.aria || action.props.text).toBeTruthy()
        }

        expect(nodes(surface).find(node => node.kind === 'list')?.props.aria).toBe('Model management entries')
      }

      await click(surface, 'Close')
      expect(app.overlays).toHaveLength(0)
      expect([app.composer.text, app.composer.cursor]).toEqual(['untouched hub draft', 3])
      expect(gw.request).not.toHaveBeenCalledWith('model.hub.set', expect.anything())
    })
  })

  it('lists every canonical pool, OAuth, API-key and custom provider plus empty locked scopes', async () => {
    await withApp({}, async (app, surface, gw) => {
      openModelPicker(app)
      await rendered()
      const picker = nodes(surface).find(node => node.kind === 'picker')!
      const scopes = picker.props.scopes as { id: string }[]
      expect(providers.every(provider => scopes.some(scope => scope.id === `provider:${provider.slug}`))).toBe(true)
      expect(gw.request).toHaveBeenCalledWith('model.options', { explicit_only: false, include_unconfigured: true, safe_inventory: true, session_id: 'session-1' })
      await activate(surface, 'locked\tone')
      expect(gw.request).not.toHaveBeenCalledWith('config.set', expect.anything())
      expect(text(surface)).toContain('locked')
    })
  })

  it('opens management through its configurable named action without replacing temporary selection', async () => {
    await withApp({}, async (_app, surface, gw, press) => {
      await press('\x1b[111;4u')
      expect(text(surface)).toContain('Models management')
      expect(gw.request).toHaveBeenCalledWith('model.hub.get', { session_id: 'session-1' })
    })
  })

  it('shows supported profile scopes, plugin auxiliary roles, locked-provider setup and separate session selection', async () => {
    await withApp({}, async (app, surface) => {
      expect(localCommand('models')).toBeDefined()
      openModelHub(app)
      await rendered()
      expect(text(surface)).toContain('No session role overrides')
      expect(text(surface)).toContain('Plugin role')
      await click(surface, 'Providers')
      expect(text(surface)).toContain('Locked')
      expect(text(surface)).toContain('Use Hermes model setup')
      await click(surface, 'Choose live session model')
      expect(nodes(surface).find(node => node.kind === 'picker')).toBeDefined()
    })
  })

  it('sets a supported role through exact confirmation and canonical readback, not a session switch', async () => {
    const stored = snapshot()
    const writes: ModelHubSetParams[] = []
    await withApp({ read: async () => structuredClone(stored), write: async intent => {
      writes.push(intent)

      if (!intent.confirmed) { return { confirm_message: 'Potentially expensive model.', confirm_required: true } }
      stored.roles[0]!.route = { model: 'canonical-model', provider: 'oauth' }
      stored.revision = 'revision-2'

      return { confirm_message: '', confirm_required: false }
    } }, async (app, surface, gw) => {
      app.composer.set('preserved draft', 4)
      openModelHub(app)
      await rendered()
      await click(surface, 'Assign selected role')
      await activate(surface, 'oauth\ttwo')
      expect(text(surface)).toContain('Potentially expensive model')
      expect(writes).toHaveLength(1)
      await click(surface, 'Confirm exact profile change')
      expect(writes).toHaveLength(2)
      expect(writes[1]).toMatchObject({ confirmed: true, operation: 'role', profile: 'fixture-profile', revision: 'revision-1', role: 'vision', route: { model: 'two', provider: 'oauth' }, scope: 'profile' })
      expect(text(surface)).toContain('canonical-model')
      expect(gw.request).not.toHaveBeenCalledWith('config.set', expect.anything())
      expect(app.composer.text).toBe('preserved draft')
      expect(app.composer.cursor).toBe(4)
    })
  })

  it('clears one role and resets only auxiliary roles with explicit profile scope', async () => {
    const writes: ModelHubSetParams[] = []
    await withApp({ write: async intent => { writes.push(intent);

 return { confirm_message: '', confirm_required: false } } }, async (app, surface) => {
      openModelHub(app)
      await rendered()
      await click(surface, 'Clear selected role to automatic')
      expect(writes[0]).toMatchObject({ operation: 'role', role: 'vision', route: null, scope: 'profile' })
      await click(surface, 'Reset auxiliary roles only')
      expect(writes[1]).toMatchObject({ operation: 'reset_roles', scope: 'profile' })
    })
  })

  it('adds ordered fallbacks, removes a selected route, and clears only the fallback chain', async () => {
    const stored = snapshot()
    const writes: ModelHubSetParams[] = []
    await withApp({ read: async () => structuredClone(stored), write: async intent => {
      writes.push(intent)
      stored.fallbacks = intent.fallbacks ?? []

      return { confirm_message: '', confirm_required: false }
    } }, async (app, surface) => {
      openModelHub(app)
      await rendered()
      await click(surface, 'Fallback chain')
      await click(surface, 'Add fallback')
      await activate(surface, 'api-key\tone')
      expect(writes[0]?.fallbacks).toEqual([{ model: 'two', provider: 'oauth' }, { model: 'one', provider: 'api-key' }])
      await click(surface, 'Remove selected fallback')
      expect(writes[1]?.fallbacks).toEqual([{ model: 'one', provider: 'api-key' }])
      await click(surface, 'Clear fallback chain only')
      expect(writes[2]).toMatchObject({ fallbacks: [], operation: 'fallbacks', scope: 'profile' })
    })
  })

  it('discards stale replies after session replacement and never sends a stale settings intent', async () => {
    const gate = Promise.withResolvers<ModelHubGetResult>()
    await withApp({ read: () => gate.promise }, async (app, surface, gw) => {
      openModelHub(app)
      await rendered()
      app.sid = 'replacement'
      gate.resolve(snapshot())
      await rendered()
      expect(text(surface)).toContain('previous session')
      expect(text(surface)).not.toContain('Plugin role')
      expect(gw.request).not.toHaveBeenCalledWith('model.hub.set', expect.anything())
    })
  })

  it('cycles from the gateway pending selection while the active model still streams and labels the picker honestly', async () => {
    await withApp({}, async (app, surface, gw) => {
      let pending = 'two'
      const requested: string[] = []
      vi.mocked(gw.request).mockImplementation(async (method, params) => {
        if (method === 'model.options') {
          return { model: 'one', pending_model: pending, pending_provider: 'pool-only', provider: 'pool-only', providers: [{ authenticated: true, is_current: true, models: ['one', 'two', 'three'], name: 'Pool', slug: 'pool-only' }] }
        }

        if (method === 'config.set') {
          const value = (params as { value: string }).value
          requested.push(value)
          pending = value.split(' ')[0]!

          return { deferred: true, key: 'model', value: pending }
        }

        throw new Error(`Unexpected pending RPC ${method}`)
      })

      for (const model of ['one', 'two', 'three']) { app.modelRecents.remember('session-1', { model, provider: 'pool-only' }) }
      openModelPicker(app)
      await rendered()
      expect(text(surface)).toContain('pending · next turn')
      expect(nodes(surface).find(node => node.kind === 'picker')?.props.current).toEqual(['pool-only\ttwo'])
      app.close(app.overlays.at(-1)!)
      cycleModel(app, 1)
      await app.modelRecents.enqueue(async () => {})
      cycleModel(app, 1)
      await app.modelRecents.enqueue(async () => {})
      expect(requested).toEqual(['three --provider pool-only --session', 'one --provider pool-only --session'])
    })
  })

  it('retains pending model-cycle recents without interpreting them as profile assignments', async () => {
    await withApp({}, async (app, surface, gw) => {
      await switchModel(app, 'two --provider oauth --session')
      openModelHub(app)
      await rendered()
      expect(text(surface)).toContain('pending until next turn')
      expect(text(surface)).toContain('oauth / two')
      expect(gw.request).not.toHaveBeenCalledWith('model.hub.set', expect.anything())
    })
  })

  if (process.env.HERMES_MODEL_PROVIDER_RECEIPT) {
    it('renders every provider from the active-profile canonical Hermes listing in the connected native picker', async () => {
      const receipt = JSON.parse(readFileSync(process.env.HERMES_MODEL_PROVIDER_RECEIPT!, 'utf8')) as { canonical_providers: string[]; missing: string[]; options: ModelOptionsResult }
      expect(receipt.missing).toEqual([])
      await withApp({}, async (app, surface, gw) => {
        vi.mocked(gw.request).mockResolvedValueOnce(receipt.options)
        openModelPicker(app)
        await rendered()
        const picker = nodes(surface).find(node => node.kind === 'picker')!
        const scopes = picker.props.scopes as { id: string }[]
        const items = picker.props.items as { id: string }[]
        expect(receipt.canonical_providers.filter(slug => !scopes.some(scope => scope.id === `provider:${slug}`))).toEqual([])

        for (const provider of receipt.options.providers) {
          expect(scopes.some(scope => scope.id === `provider:${provider.slug}`)).toBe(true)
          expect(provider.models?.filter(model => !items.some(item => item.id === `${provider.slug}\t${model}`))).toEqual([])
        }
      })
    })
  }

  it('hides endpoint-embedded login credentials from native model previews', async () => {
    await withApp({}, async (app, surface, gw) => {
      vi.mocked(gw.request).mockResolvedValueOnce({ model: 'one', provider: 'api-key', providers: [{ ...providers[2], api_url: 'https://user:super-secret@example.test?token=another-secret' }] })
      openModelPicker(app)
      await rendered()
      expect(text(surface)).not.toContain('super-secret')
      expect(text(surface)).not.toContain('another-secret')
    })
  })
})
