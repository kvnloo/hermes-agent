import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { Key, Surface, TspEvent } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { matchesAction, VIM_ACTIONS } from '../actions.js'
import { App, INPUT_ID } from '../app.js'
import { openSettings } from '../overlays/settings.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-vim-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const views = new WeakMap<Surface, View>()
const esc = '\x1b[27u'

interface Harness {
  app: App
  gw: GatewayClient
  surface: Surface
  press(bytes: string): Promise<void>
  native(event: Record<string, unknown>): Promise<void>
}

function editor(surface: Surface) {
  const result = views
    .get(surface)
    ?.regions[1]?.children.flatMap(node => node.children)
    .flatMap(node => node.children)
    .find(node => node.kind === 'editor')

  if (!result) {
    throw new Error('Composer editor was not painted')
  }

  return result.props
}

async function withApp(enabled: unknown, run: (h: Harness) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'config.get') {
      return params && 'key' in params && params.key === 'full'
        ? { config: { display: { vim_mode: enabled } } }
        : { value: 'queue' }
    }

    if (method === 'settings.get') {
      return { fields: {}, profile: 'fixture' }
    }

    if (method === 'session.interrupt') {
      return {}
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test', () => {})
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)

  surface.render = view => {
    views.set(surface, View.from(view))
    render(view)
  }

  await app.vimPreference.refresh()
  await rendered()
  await rendered()

  try {
    await run({
      app,
      gw,
      surface,
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
        await rendered()
      },
      native: async event => {
        const handler = surface.dispatch({ sf: 'hermes', id: INPUT_ID, raw: {}, ...event } as TspEvent)
        expect(handler).toBeTypeOf('function')
        await handler?.()
        await rendered()
        await rendered()
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

  if (isolated.splash === undefined) {
    delete process.env.HERMES_TUI_SPLASH
  } else {
    process.env.HERMES_TUI_SPLASH = isolated.splash
  }

  rmSync(isolated.home, { recursive: true, force: true })
})

describe('optional Vim composer state machine', () => {
  it.each([undefined, false, 'false'])(
    'is off unless the canonical profile explicitly enables it (%s)',
    async enabled => {
      await withApp(enabled, async ({ app, surface, press, native }) => {
        expect(editor(surface).mode).toBeUndefined()
        await press('x')
        expect(app.composer.text).toBe('x')
        await native({ ev: 'edit', from: 1, to: 1, text: '文', cursor: 2, len: 1 })
        expect(app.composer.text).toBe('x文')
        await press(esc)
        expect(app.composer.vim.mode).toBe('insert')
      })
    }
  )

  it('consumes Insert Escape before interrupt; quiet Normal Escape keeps the existing interrupt policy', async () => {
    await withApp(true, async ({ app, gw, surface, press }) => {
      app.busy = { since: {}, startedAt: Date.now(), label: 'Working' }
      await press('hello')
      expect(editor(surface).mode).toBe('insert')
      await press(esc)
      expect(editor(surface).mode).toBe('normal')
      expect(app.composer.cursor).toBe(4)
      expect(gw.request).not.toHaveBeenCalledWith('session.interrupt', expect.anything())
      await press('d')
      expect(app.composer.vim.pending).toBe('d')
      await press(esc)
      expect(app.composer.vim.pending).toBe('')
      expect(gw.request).not.toHaveBeenCalledWith('session.interrupt', expect.anything())
      await press(esc)
      expect(gw.request).toHaveBeenCalledWith('session.interrupt', { session_id: 'session-1' })
      expect(app.composer.text).toBe('hello')
    })
  })

  it('keeps overlays and completion ahead of Vim Escape without touching the hidden draft', async () => {
    await withApp(true, async ({ app, surface, press }) => {
      await press('draft')
      openSettings(app)
      await rendered()
      await rendered()
      await press(esc)
      expect(app.overlays).toHaveLength(0)
      expect(editor(surface).mode).toBe('insert')
      app.composer.set('/sett')
      app.changed()
      await vi.waitFor(() =>
        expect(views.get(surface)?.regions[2]?.children.some(node => node.props.role === 'omp.autocomplete')).toBe(true)
      )
      await press(esc)
      expect(app.composer.vim.mode).toBe('insert')
      await press(esc)
      expect(app.composer.vim.mode).toBe('normal')
    })
  })

  it('moves Normal and Visual cursors by whole graphemes across multiline text, without browsing history at edges', async () => {
    await withApp(true, async ({ app, surface, press }) => {
      const emoji = '👨‍👩‍👧‍👦'
      const text = `a${emoji}e\u0301\nZ\n甲乙丙`
      app.composer.set(text, 0)
      await press(esc)
      await press('l')
      expect(app.composer.cursor).toBe(1)
      await press('l')
      expect(app.composer.cursor).toBe(1 + emoji.length)
      await press('j')
      expect(app.composer.cursor).toBe(text.indexOf('Z'))
      await press('j')
      expect(app.composer.cursor).toBe(text.indexOf('丙'))
      await press('j')
      expect(app.composer.text).toBe(text)
      await press('gglv')
      expect(editor(surface).anchor).toBe(1)
      expect(editor(surface).cursor).toBe(1 + emoji.length)
      await press('l')
      expect(editor(surface).cursor).toBe(text.indexOf('\n'))
      await press('r界')
      expect(app.composer.text).toBe('a界界\nZ\n甲乙丙')
    })
  })

  it('yanks inclusive visual selections to the Vim register, pastes and replaces them atomically', async () => {
    await withApp(true, async ({ app, press }) => {
      app.composer.set('one two', 0)
      await press(esc)
      await press('vely')
      expect(app.composer.text).toBe('one two')
      expect(app.composer.vim.mode).toBe('normal')
      await press('$p')
      expect(app.composer.text).toBe('one twoone ')
      await press('u')
      expect(app.composer.text).toBe('one two')
      await press('ggvllrX')
      expect(app.composer.text).toBe('XXX two')
      await press('u')
      expect(app.composer.text).toBe('one two')
    })
  })

  it('composes counted motions/operators and linewise operations with explicit undo/redo boundaries', async () => {
    await withApp(true, async ({ app, press }) => {
      await press('one two three')
      await press(esc)
      await press('di')
      expect(app.composer.vim.mode).toBe('normal')
      expect(app.composer.vim.pending).toBe('')
      expect(app.composer.text).toBe('one two three')
      await press('0dw')
      expect(app.composer.text).toBe('two three')
      await press('u')
      expect(app.composer.text).toBe('one two three')
      await press('u')
      expect(app.composer.text).toBe('')
      await press('\x1b[114;5u')
      expect(app.composer.text).toBe('one two three')
      app.composer.set('one\ntwo\nthree', 0)
      await press('2dd')
      expect(app.composer.text).toBe('three')
      await press('u')
      expect(app.composer.text).toBe('one\ntwo\nthree')
      await press('Gdd')
      expect(app.composer.text).toBe('one\ntwo')
      await press('u')
      await press('ggcc甲')
      expect(app.composer.text).toBe('甲\ntwo\nthree')
      await press(esc)
      await press('u')
      expect(app.composer.text).toBe('\ntwo\nthree')
    })
  })

  it('changes words without eating the gap and preserves line structure for visual line changes', async () => {
    await withApp(true, async ({ app, surface, press }) => {
      app.composer.set('one two\nthree\nfour', 0)
      await press(esc)
      await press('cw甲')
      expect(app.composer.text).toBe('甲 two\nthree\nfour')
      await press(esc)
      await press('ggVjc乙')
      expect(app.composer.text).toBe('乙\nfour')
      await press(esc)
      await press('ggyyGp')
      expect(app.composer.text).toBe('乙\nfour\n乙')
      await press('d')
      expect(
        views
          .get(surface)
          ?.regions[1]?.children.flatMap(node => node.children)
          .find(node => node.props.role === 'omp.composer.bar')
          ?.children.flatMap(node => node.children).find(node => node.props.role === 'omp.composer.vim')?.props.text
      ).toBe('NORMAL d')
      await press(esc)
      await press('vhr界')
      expect(app.composer.text).toBe('乙\nfour\n界')
    })
  })

  it('accepts composed Unicode and atomic paste in Insert, treats Normal paste literally, and excludes competing native edit/send/undo', async () => {
    await withApp(true, async ({ app, gw, surface, press, native }) => {
      await press('日本語e\u0301👩‍💻')
      expect(app.composer.text).toBe('日本語e\u0301👩‍💻')
      await press('\x1b[200~\r\nPASTE\x1b[201~')
      expect(app.composer.text).toBe('日本語e\u0301👩‍💻\nPASTE')
      await press(esc)
      await press('u')
      expect(app.composer.text).toBe('日本語e\u0301👩‍💻')
      await press('0')
      await press('\x1b[200~dd\r\n日本\x1b[201~')
      expect(app.composer.text).toBe('dd\n日本日本語e\u0301👩‍💻')
      const before = app.composer.text
      await native({
        ev: 'edit',
        from: 0,
        to: before.length,
        text: 'competing native text',
        cursor: 21,
        len: before.length
      })
      await native({ ev: 'send', text: 'stale native draft' })
      await native({ ev: 'undo' })
      expect(app.composer.text).toBe(before)
      expect(editor(surface).mode).toBe('normal')
      expect(gw.request).not.toHaveBeenCalledWith('prompt.submit', expect.anything())
    })
  })

  it('reads canonical profile settings on refresh, rejects stale session readbacks, and preserves the draft when disabled', async () => {
    await withApp(true, async ({ app, gw, surface, press }) => {
      await press('draft')
      await press(esc)
      const pending = Promise.withResolvers<{ config: { display: { vim_mode: boolean } } }>()
      vi.mocked(gw.request).mockImplementationOnce(() => pending.promise)
      const refreshing = app.vimPreference.refresh()
      app.sid = 'session-2'
      pending.resolve({ config: { display: { vim_mode: false } } })
      await refreshing
      expect(app.composer.vim.enabled).toBe(true)
      vi.mocked(gw.request).mockResolvedValueOnce({ config: { display: { vim_mode: false } } })
      await app.vimPreference.refresh()
      await rendered()
      await rendered()
      expect(editor(surface).mode).toBeUndefined()
      expect(app.composer.text).toBe('draft')
      await press('x')
      expect(app.composer.text).toBe('drafxt')
    })
  })

  it('registers collision-free named modal defaults independently of application actions', () => {
    for (const name of new Set(VIM_ACTIONS.flatMap(action => action.keys.map(key => key.split('+').at(-1)!)))) {
      for (let mask = 0; mask < 16; mask++) {
        const key: Key = {
          name,
          ctrl: Boolean(mask & 1),
          alt: Boolean(mask & 2),
          shift: Boolean(mask & 4),
          meta: Boolean(mask & 8)
        }

        expect(VIM_ACTIONS.filter(action => matchesAction(action, key)).length, `${name}:${mask}`).toBeLessThanOrEqual(
          1
        )
      }
    }
  })
})
