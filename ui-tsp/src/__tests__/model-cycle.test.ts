import { spawnSync } from 'node:child_process'
import { EventEmitter } from 'node:events'
import { existsSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'

import type { Surface } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { append } from '@tui/lib/history.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { editExternal } from '../external-editor.js'
import * as models from '../overlays/models.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-model-cycle-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

vi.mock('node:child_process', async importOriginal => ({
  ...await importOriginal<Record<string, unknown>>(),
  spawnSync: vi.fn(() => { throw new Error('Tests must supply a fake editor; real launch forbidden') })
}))
const tick = () => new Promise<void>(resolve => setImmediate(resolve))
const chord = (letter: string, modifiers = 5) => `\x1b[${letter.codePointAt(0)};${modifiers}u`

interface Fixture {
  app: App
  gw: GatewayClient
  view(): View | undefined
  press(bytes: string): Promise<void>
  calls: { method: string; params: unknown }[]
}

async function withApp(run: (fixture: Fixture) => Promise<void>, catalog = ['alpha', 'beta', 'gamma'], confirm = false) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const calls: Fixture['calls'] = []
  let current = catalog[0]
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    if (method === 'model.options') {
      return { model: current, provider: 'fixture', providers: [{ slug: 'fixture', name: 'Fixture', is_current: true, models: catalog }] }
    }

    if (method === 'config.set') {
      const p = params as { value: string; confirm_expensive_model: boolean }

      if (confirm && !p.confirm_expensive_model) {
        return { key: 'model', confirm_required: true, confirm_message: 'Expensive fixture' }
      }

      current = p.value.split(' ')[0]

      return { key: 'model', value: current }
    }

    if (method === 'commands.catalog') { return { pairs: [] } }

    if (method === 'complete.slash') { return { items: [] } }
    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.info = { model: current, provider: 'fixture' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface: Surface = tern.surfaces[0]!
  let latest: View | undefined
  const render = surface.render.bind(surface)

  surface.render = view => { latest = View.from(view); render(view) }

  try {
    await run({ app, gw, calls, view: () => latest, press: async bytes => {
      input.emit('data', bytes)
      await tick()
      await tick()
    } })
  } finally {
    app.quit()
    await running
    vi.restoreAllMocks()
  }
}

function layer(view: View | undefined) {
  return view?.regions[2]?.children[0]
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.splash === undefined) { delete process.env.HERMES_TUI_SPLASH } else { process.env.HERMES_TUI_SPLASH = isolated.splash }
  rmSync(isolated.home, { force: true, recursive: true })
})

describe('model, history and external-editor shortcuts', () => {
  it('cycles next/previous recent models through switchModel and paints the accepted notice', async () => {
    await withApp(async ({ app, press, view }) => {
      await app.slash('/model beta --provider fixture --session')
      await app.slash('/model gamma --provider fixture --session')
      await app.slash('/model alpha --provider fixture --session')
      const switcher = vi.spyOn(models, 'switchModel')
      await press(chord('p'))
      expect(switcher).toHaveBeenLastCalledWith(app, 'beta --provider fixture --session', false, 'session-1')
      expect(app.info?.model).toBe('beta')
      await press(chord('p', 6))
      expect(switcher).toHaveBeenLastCalledWith(app, 'alpha --provider fixture --session', false, 'session-1')
      expect(JSON.stringify(view())).toContain('Switched to alpha.')
    })
  })

  it('uses the configured picker fallback list before any recent selection', async () => {
    await withApp(async ({ app, press }) => {
      await press(chord('p', 6))
      expect(app.info?.model).toBe('gamma')
    })
  })

  it('one model produces a notice without any switch', async () => {
    await withApp(async ({ calls, press, view }) => {
      await press(chord('p'))
      expect(calls.some(call => call.method === 'config.set')).toBe(false)
      expect(JSON.stringify(view())).toContain('Only one model')
    }, ['alpha'])
  })

  it('does not bypass expensive-model confirmation and confirms the exact session-only request', async () => {
    await withApp(async ({ app, calls, press, view }) => {
      await press(chord('p'))
      expect(app.info?.model).toBe('alpha')
      expect(JSON.stringify(view())).toContain('Expensive fixture')
      await press('y')
      expect(app.info?.model).toBe('beta')
      expect(calls.filter(call => call.method === 'config.set').map(call => call.params)).toEqual([
        { key: 'model', session_id: 'session-1', value: 'beta --provider fixture --session', confirm_expensive_model: false },
        { key: 'model', session_id: 'session-1', value: 'beta --provider fixture --session', confirm_expensive_model: true }
      ])
    }, ['alpha', 'beta'], true)
  })

  it('recent navigation is reset for a replaced session', async () => {
    await withApp(async ({ app, press }) => {
      await app.slash('/model beta --provider fixture --session')
      app.sid = 'session-2'
      await press(chord('p'))
      expect(app.info?.model).toBe('gamma')
    })
  })

  it('history typing filters the native sheet; Enter only fills the composer', async () => {
    append('explain the compiler')
    append('write tests for the gateway')
    await withApp(async ({ app, calls, press, view }) => {
      app.composer.set('existing draft')
      await press(chord('r'))
      expect(layer(view())?.kind).toBe('picker')
      await press('compiler')
      expect(layer(view())?.props.query).toBe('compiler')
      expect(layer(view())?.props.items).toEqual([{ id: '1', label: 'explain the compiler', mono: true }])
      await press('\r')
      expect(app.composer.text).toBe('explain the compiler')
      expect(app.overlays).toHaveLength(0)
      expect(calls.some(call => call.method === 'prompt.submit')).toBe(false)
    })
  })

  it('history cancellation preserves the draft and caret', async () => {
    await withApp(async ({ app, press }) => {
      app.composer.set('untouched', 3)
      await press(chord('r'))
      await press(chord('c'))
      expect(app.overlays).toHaveLength(0)
      expect(app.composer.text).toBe('untouched')
      expect(app.composer.cursor).toBe(3)
    })
  })

  it('Ctrl+G round-trips a private temp file through a fake opener, then removes it', async () => {
    vi.stubEnv('TERN_WINDOW_KEY', 'fake-window-never-launch')
    let file = ''
    vi.mocked(spawnSync).mockImplementation((command, args) => {
      expect(command).toBe('tern')
      expect(args?.slice(0, 2)).toEqual(['open', '--wait'])
      file = String(args?.at(-1))
      expect(readFileSync(file, 'utf8')).toBe('draft\nλ')
      expect(statSync(file).mode & 0o777).toBe(0o600)
      writeFileSync(file, 'edited\nλ')

      return { status: 0 } as ReturnType<typeof spawnSync>
    })

    try {
      await withApp(async ({ app, calls, press, view }) => {
        app.composer.set('draft\nλ')
        await press(chord('g'))
        await vi.waitFor(() => expect(app.composer.text).toBe('edited\nλ'))
        await vi.waitFor(() => expect(existsSync(file)).toBe(false))
        await press('!')
        expect(JSON.stringify(view())).toContain('edited')
        expect(calls.some(call => call.method === 'prompt.submit')).toBe(false)
      })
    } finally { vi.unstubAllEnvs() }
  })

  it('an edited result cannot overwrite a newer composer draft', async () => {
    await withApp(async ({ app }) => {
      app.composer.set('initial')
      await editExternal(app, async file => {
        app.composer.set('newer')
        writeFileSync(file, 'external result')
      })
      expect(app.composer.text).toBe('newer')
      expect(JSON.stringify(app.transcript.entries)).toContain('external result')
    })
  })
})
