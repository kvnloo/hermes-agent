import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { Surface } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import type { MockInstance } from 'vitest'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import * as panes from '../pane-launcher.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-fork-pane-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

// Fail closed even if a fixture accidentally stops replacing the pane launcher.
vi.mock('../pane-launcher.js', () => ({ launchPane: vi.fn(() => { throw new Error('Real pane launch forbidden in tests') }) }))

const tick = () => new Promise<void>(resolve => setImmediate(resolve))
interface Fixture {
  app: App
  calls: { method: string; params: unknown }[]
  launcher: MockInstance<typeof panes.launchPane>
  view(): View | undefined
  press(bytes: string): Promise<void>
}
interface Options {
  inTern?: boolean
  profile?: string
  request?: () => Promise<unknown>
}

async function withApp(run: (fixture: Fixture) => Promise<void>, options: Options = {}) {
  vi.stubEnv('TERN_WINDOW_KEY', options.inTern === false ? '' : 'fake-window-no-real-daemon')
  const launcher = vi.spyOn(panes, 'launchPane').mockReset().mockResolvedValue(undefined)
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const calls: Fixture['calls'] = []
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    if (method === 'session.fork') {
      return options.request ? options.request() : { session_id: 'stored-child', parent: 'stored-parent', profile: options.profile ?? 'owning-profile', message_count: 8 }
    }

    if (method === 'complete.slash') { return { items: [] } }

    if (method === 'commands.catalog') { return { pairs: [] } }
    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'runtime-parent'
  app.storedSid = 'stored-parent'
  app.info = { model: 'fixture-model' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface: Surface = tern.surfaces[0]!
  let latest: View | undefined
  const render = surface.render.bind(surface)

  surface.render = view => { latest = View.from(view); render(view) }

  try {
    await run({ app, calls, launcher, view: () => latest, press: async bytes => {
      input.emit('data', bytes)
      await tick()
      await tick()
    } })
  } finally {
    app.quit()
    await running
    vi.restoreAllMocks()
    vi.unstubAllEnvs()
  }
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }

  if (isolated.splash === undefined) { delete process.env.HERMES_TUI_SPLASH } else { process.env.HERMES_TUI_SPLASH = isolated.splash }
  rmSync(isolated.home, { force: true, recursive: true })
})

describe('fork into a different Tern pane', () => {
  it('the production adapter uses fixed tern split argv with a fake process runner and shell disabled', async () => {
    const actual = await vi.importActual<typeof panes>('../pane-launcher.js')
    const execute = vi.fn().mockResolvedValue({ stdout: '', stderr: '' })
    const argv = ['hermes', '--resume', 'stored-child', '-p', 'owning-profile']
    await actual.launchPane(argv, execute)
    expect(execute).toHaveBeenCalledExactlyOnceWith('tern', ['split', '@focused', 'right', '--', ...argv], { shell: false })
  })
  it('/fork calls the RPC before the fake launcher with exact resume/profile argv; original remains adopted', async () => {
    const result = Promise.withResolvers<unknown>()
    await withApp(async ({ app, calls, launcher, view, press }) => {
      app.composer.set('original draft', 4)
      const originalInfo = app.info
      const forking = app.slash('/fork-message')
      expect(calls).toContainEqual({ method: 'session.fork', params: { session_id: 'runtime-parent' } })
      expect(launcher).not.toHaveBeenCalled()
      result.resolve({ session_id: 'stored-child', parent: 'stored-parent', profile: 'owning-profile', message_count: 8 })
      await forking
      await press('')
      expect(launcher).toHaveBeenCalledExactlyOnceWith(['hermes', '--resume', 'stored-child', '-p', 'owning-profile'])
      expect(app.sid).toBe('runtime-parent')
      expect(app.storedSid).toBe('stored-parent')
      expect(app.info).toBe(originalInfo)
      expect(app.composer.text).toBe('original draft')
      expect(app.composer.cursor).toBe(4)
      expect(JSON.stringify(view())).toContain('Opened fork stored-child')
      expect(calls.some(call => call.method === 'session.resume' || call.method === 'prompt.submit')).toBe(false)
    }, { request: () => result.promise })
  })

  it('outside Tern shows the stored id and resume hint without invoking a launcher', async () => {
    await withApp(async ({ app, launcher, view, press }) => {
      await app.slash('/fork-message')
      await press('')
      expect(launcher).not.toHaveBeenCalled()
      expect(JSON.stringify(view())).toContain('Forked session stored-child')
      expect(JSON.stringify(view())).toContain('hermes --resume stored-child -p owning-profile')
    }, { inTern: false })
  })

  it('the registry chord uses the same fork intent', async () => {
    await withApp(async ({ calls, launcher, press }) => {
      await press('\x1b[102;4u') // Alt+Shift+F
      expect(calls).toContainEqual({ method: 'session.fork', params: { session_id: 'runtime-parent' } })
      expect(launcher).toHaveBeenCalledExactlyOnceWith(['hermes', '--resume', 'stored-child', '-p', 'owning-profile'])
    })
  })

  it('a targeted fork sends only the exact durable id, not transcript text or an ordinal', async () => {
    await withApp(async ({ app, calls }) => {
      await app.slash('/fork-message 123')
      expect(calls).toContainEqual({ method: 'session.fork', params: { session_id: 'runtime-parent', target_message_id: 123 } })
    })
  })

  it.each(['0', '-1', '1.5', '1e3', '123 extra', '9007199254740992'])('invalid target %s never forks', async target => {
    await withApp(async ({ app, calls, launcher }) => {
      await app.slash(`/fork-message ${target}`)
      expect(calls.some(call => call.method === 'session.fork')).toBe(false)
      expect(launcher).not.toHaveBeenCalled()
    })
  })

  it('launcher failure retains the durable child and recovery hint, never repeats the RPC', async () => {
    await withApp(async ({ app, calls, launcher, view, press }) => {
      launcher.mockRejectedValueOnce(new Error('fake split failure'))
      await app.slash('/fork-message')
      await press('')
      expect(calls.filter(call => call.method === 'session.fork')).toHaveLength(1)
      expect(JSON.stringify(view())).toContain('Fork saved, but the Tern pane could not open: fake split failure')
      expect(JSON.stringify(view())).toContain('hermes --resume stored-child -p owning-profile')
    })
  })

  it('an RPC failure does not launch or report an invented session id', async () => {
    await withApp(async ({ app, launcher, view, press }) => {
      await app.slash('/fork-message')
      await press('')
      expect(launcher).not.toHaveBeenCalled()
      expect(JSON.stringify(view())).toContain('fake database unavailable')
      expect(JSON.stringify(view())).not.toContain('Forked session')
    }, { request: async () => { throw new Error('fake database unavailable') } })
  })

  it('coalesces repeated fork requests while one is pending', async () => {
    const result = Promise.withResolvers<unknown>()
    await withApp(async ({ app, calls, launcher }) => {
      const first = app.slash('/fork-message')
      await app.slash('/fork-message')
      expect(calls.filter(call => call.method === 'session.fork')).toHaveLength(1)
      result.resolve({ session_id: 'stored-child', parent: 'stored-parent', profile: 'owning-profile', message_count: 8 })
      await first
      expect(launcher).toHaveBeenCalledTimes(1)
    }, { request: () => result.promise })
  })

  it('never opens a pane for a replaced session, but preserves the already-created child hint', async () => {
    const result = Promise.withResolvers<unknown>()
    await withApp(async ({ app, launcher, view, press }) => {
      const first = app.slash('/fork-message')
      app.sid = 'another-runtime'
      result.resolve({ session_id: 'stored-child', parent: 'stored-parent', profile: 'owning-profile', message_count: 8 })
      await first
      await press('')
      expect(launcher).not.toHaveBeenCalled()
      expect(app.sid).toBe('another-runtime')
      expect(JSON.stringify(view())).toContain('Forked session stored-child')
    }, { request: () => result.promise })
  })

  it('profile text is a single literal argv entry, never shell syntax', async () => {
    await withApp(async ({ app, launcher }) => {
      await app.slash('/fork-message')
      expect(launcher).toHaveBeenCalledExactlyOnceWith(['hermes', '--resume', 'stored-child', '-p', 'profile ; $(do-not-run)'])
    }, { profile: 'profile ; $(do-not-run)' })
  })

  it('busy session refuses a fork without hiding the running state', async () => {
    await withApp(async ({ app, calls, launcher }) => {
      app.busy = { label: 'Working', since: {}, startedAt: Date.now() }
      await app.slash('/fork-message')
      expect(app.busy?.label).toBe('Working')
      expect(calls.some(call => call.method === 'session.fork')).toBe(false)
      expect(launcher).not.toHaveBeenCalled()
    })
  })

  it('native help advertises /fork without depending on the backend command catalog', async () => {
    await withApp(async ({ app, view, press }) => {
      await app.slash('/help')
      await press('')
      expect(JSON.stringify(view())).toContain('/fork')
      expect(JSON.stringify(view())).toContain('alt+shift+f')
    })
  })
})
