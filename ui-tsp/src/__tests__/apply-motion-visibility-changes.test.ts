import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { paletteOf } from '../palette.js'
import { renderSplashFrame, SPLASH_EXIT_MS, SPLASH_INTRO_MS, SPLASH_TICK_MS } from '../splash/index.js'
import { SPLASH_MAX_MS, splashInsets } from '../splash/launch.js'
import { splashNode } from '../view/splash.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-splash-environment-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))

interface Fixture {
  app: App
  gw: GatewayClient
  splash: Surface
  frames: View[]
  frameAt(ms: number): View
  event(event: object): Promise<void>
  press(bytes: string): Promise<void>
}

async function withApp(run: (fixture: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  acknowledgeFrames(tern)

  const frames: View[] = []
  const open = tern.open.bind(tern)

  tern.open = options => {
    const surface = open(options)

    if (surface.id === 'splash') {
      const render = surface.render.bind(surface)
      vi.spyOn(surface, 'render').mockImplementation(view => {
        frames.push(View.from(view))
        render(view)
      })
    }

    return surface
  }

  const gw = new GatewayClient()
  // Stay before gateway.ready unless the test explicitly delivers it.
  vi.spyOn(gw, 'request').mockImplementation(() => new Promise(() => {}))
  const app = new App(tern, gw, 'test')
  const running = app.run()
  const splash = tern.surfaces.find(surface => surface.id === 'splash')!
  expect(splash).toBeDefined()

  const press = async (bytes: string) => {
    input.emit('data', bytes)
    await rendered()
    await rendered()
  }

  try {
    await run({
      app, gw, splash, frames, press,
      frameAt: elapsedMs => {
        const size = splashInsets(tern.caps.cols, process.stdout.rows ?? 24)

        return View.from(splashNode(renderSplashFrame({
          design: 'kerykeion', elapsedMs, width: size.cols, height: size.rows, status: 'summoning hermes…'
        })))
      },
      event: event => press(`\x1b_tsp;e;${JSON.stringify(event)}\x1b\\`)
    })
  } finally {
    app.quit()
    await rendered()
    // The real SDK drains input for 50 ms when closing the Session.
    await vi.advanceTimersByTimeAsync(50)
    await running
    await rendered()
  }

  expect(vi.getTimerCount()).toBe(0)
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'setTimeout', 'clearTimeout', 'performance'] })
  vi.stubEnv('HERMES_TUI_SPLASH', 'kerykeion')
  vi.stubEnv('HERMES_TUI_QUERY', '')
  vi.stubEnv('HERMES_TUI_SPLASH_FPS', '')
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllEnvs()
  vi.restoreAllMocks()
})

afterAll(() => {
  if (isolated.previous === undefined) {
    delete process.env.HERMES_HOME
  } else {
    process.env.HERMES_HOME = isolated.previous
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('running launch splash environment', () => {
  it('settles Reduce Motion immediately, stops frame scheduling, and resumes on the original clock', async () => {
    await withApp(async ({ event, frames, splash, frameAt }) => {
      await vi.advanceTimersByTimeAsync(400)
      await event({ ev: 'motion', reduce: true })
      expect(frames.at(-1)).toEqual(frameAt(SPLASH_INTRO_MS))
      const count = frames.length
      await vi.advanceTimersByTimeAsync(2000)
      expect(frames).toHaveLength(count)
      expect(splash.closed).toBe(false)

      await event({ ev: 'motion', reduce: false })
      expect(frames.at(-1)).toEqual(frameAt(2400))
      await vi.advanceTimersByTimeAsync(2 * SPLASH_TICK_MS)
      expect(frames.length).toBeGreaterThan(count + 1)
    })
  })

  it.each(['splash', 'hermes', undefined])('pauses hidden frames addressed to %s and redraws on show', async sf => {
    await withApp(async ({ event, frames, splash }) => {
      await vi.advanceTimersByTimeAsync(400)
      await event({ ev: 'visible', sf, visible: false })
      const count = frames.length
      await vi.advanceTimersByTimeAsync(1000)
      expect(frames).toHaveLength(count)
      expect(splash.closed).toBe(false)
      await event({ ev: 'visible', sf, visible: true })
      expect(frames).toHaveLength(count + 1)
      await vi.advanceTimersByTimeAsync(SPLASH_TICK_MS)
      expect(frames).toHaveLength(count + 2)
    })
  })

  it('honors visibility carried by resize and ignores unrelated surfaces', async () => {
    await withApp(async ({ event, frames }) => {
      await event({ ev: 'visible', sf: 'other', visible: false })
      const before = frames.length
      await vi.advanceTimersByTimeAsync(2 * SPLASH_TICK_MS)
      expect(frames.length).toBeGreaterThan(before)
      await event({ ev: 'resize', sf: 'splash', cols: 80, rows: 24, visible: false })
      const hidden = frames.length
      await vi.advanceTimersByTimeAsync(400)
      expect(frames).toHaveLength(hidden)
    })
  })

  it('leaves native theme tokens in place and applies skin changes without restarting paused animation', async () => {
    await withApp(async ({ event, frames, gw, splash }) => {
      await event({ ev: 'motion', reduce: true })
      const count = frames.length
      const palette = vi.spyOn(splash, 'palette')
      await event({ ev: 'theme', dark: false })
      const skin = { name: 'ember', colors: { ui_accent: '#ffd166', ui_text: '#ffe9d6' } }
      gw.emit('event', { type: 'skin.changed', payload: skin })
      expect(palette).toHaveBeenLastCalledWith(paletteOf(skin))
      expect(JSON.stringify(frames.at(-1))).not.toMatch(/#[0-9a-f]{6}/i)
      await vi.advanceTimersByTimeAsync(400)
      expect(frames).toHaveLength(count)
    })
  })

  it('spends the skip key and immediately hands off without a reduced-motion dissolve', async () => {
    await withApp(async ({ app, event, press, splash }) => {
      await event({ ev: 'motion', reduce: true })
      await press('x')
      expect(splash.closed).toBe(true)
      expect(app.composer.text).toBe('')
      await press('y')
      expect(app.composer.text).toBe('y')
    })
  })

  it('spends only the skip key: typing during the exit dissolve reaches the composer', async () => {
    await withApp(async ({ app, press, splash }) => {
      await vi.advanceTimersByTimeAsync(400)
      await press('x')
      await vi.advanceTimersByTimeAsync(SPLASH_TICK_MS)
      // A burst typed right after the skip key lands while the splash still dissolves.
      expect(splash.closed).toBe(false)
      await press('y')
      await press('z')
      expect(app.composer.text).toBe('yz')
      await vi.advanceTimersByTimeAsync(SPLASH_EXIT_MS + SPLASH_TICK_MS)
      expect(splash.closed).toBe(true)
      expect(app.composer.text).toBe('yz')
    })
  })

  it('keeps keys typed while a ready splash plays its own exit dissolve', async () => {
    await withApp(async ({ app, gw, press, splash }) => {
      gw.emit('event', { type: 'gateway.ready', payload: {} })
      await vi.advanceTimersByTimeAsync(SPLASH_INTRO_MS + SPLASH_TICK_MS)
      expect(splash.closed).toBe(false)
      await press('h')
      await press('i')
      expect(app.composer.text).toBe('hi')
    })
  })

  it.each([
    { ev: 'visible', sf: 'splash', visible: false },
    { ev: 'motion', reduce: true }
  ])('keeps the original boot deadline while paused by $ev', async pause => {
    await withApp(async ({ event, frames, splash }) => {
      await vi.advanceTimersByTimeAsync(1000)
      await event(pause)
      const count = frames.length
      await vi.advanceTimersByTimeAsync(SPLASH_MAX_MS - 1001)
      expect(splash.closed).toBe(false)
      await vi.advanceTimersByTimeAsync(1)
      expect(splash.closed).toBe(true)
      expect(frames).toHaveLength(count)
      await event({ ev: 'motion', reduce: false })
      await event({ ev: 'visible', sf: 'splash', visible: true })
      await vi.advanceTimersByTimeAsync(1000)
      expect(frames).toHaveLength(count)
    })
  })

  it('hands off on gateway readiness while hidden without waiting for a visibility event', async () => {
    await withApp(async ({ event, gw, splash }) => {
      await event({ ev: 'visible', sf: 'splash', visible: false })
      gw.emit('event', { type: 'gateway.ready', payload: {} })
      await vi.advanceTimersByTimeAsync(SPLASH_INTRO_MS - 1)
      expect(splash.closed).toBe(false)
      await vi.advanceTimersByTimeAsync(1)
      expect(splash.closed).toBe(true)
    })
  })

  it('preserves the ordinary key skip dissolve', async () => {
    await withApp(async ({ app, press, splash }) => {
      await press('x')
      expect(splash.closed).toBe(false)
      await vi.advanceTimersByTimeAsync(SPLASH_EXIT_MS + 2 * SPLASH_TICK_MS)
      expect(splash.closed).toBe(true)
      expect(app.composer.text).toBe('')
    })
  })

  it('finishes a dissolving splash when motion is disabled', async () => {
    await withApp(async ({ event, press, splash }) => {
      await press('x')
      await vi.advanceTimersByTimeAsync(SPLASH_TICK_MS)
      await event({ ev: 'motion', reduce: true })
      expect(splash.closed).toBe(true)
    })
  })

  it('relinquishes the surface and first key to a modal while paused', async () => {
    await withApp(async ({ app, event, press, splash }) => {
      await event({ ev: 'motion', reduce: true })
      const onKey = vi.fn(() => true)
      app.open({ key: 'fixture', modal: true, node: () => splashNode([]), onKey })
      expect(splash.closed).toBe(true)
      await press('x')
      expect(onKey).toHaveBeenCalledExactlyOnceWith(expect.objectContaining({ name: 'x' }))
      expect(app.composer.text).toBe('')
    })
  })

  it.each([false, true])('retires a gone splash immediately (hidden=%s) before startup completes', async hidden => {
    await withApp(async ({ event, frames, splash }) => {
      if (hidden) {
        await event({ ev: 'visible', sf: 'splash', visible: false })
      }

      await event({ ev: 'gone', sf: 'splash', ids: ['splash'] })
      expect(splash.closed).toBe(true)
      expect(vi.getTimerCount()).toBe(0)
      const count = frames.length
      await event({ ev: 'motion', reduce: false })
      await event({ ev: 'visible', sf: 'splash', visible: true })
      await vi.advanceTimersByTimeAsync(SPLASH_MAX_MS + SPLASH_EXIT_MS)
      expect(frames).toHaveLength(count)
    })
  })

  it.each([false, true])('cancels every splash timer on quit before startup completes (hidden=%s)', async hidden => {
    await withApp(async ({ app, event, frames, splash }) => {
      if (hidden) {
        await event({ ev: 'visible', sf: 'splash', visible: false })
      }

      app.quit()
      await rendered()
      await vi.advanceTimersByTimeAsync(50)
      expect(splash.closed).toBe(true)
      expect(vi.getTimerCount()).toBe(0)
      const count = frames.length
      await vi.advanceTimersByTimeAsync(SPLASH_MAX_MS + SPLASH_EXIT_MS)
      expect(frames).toHaveLength(count)
    })
  })
})
