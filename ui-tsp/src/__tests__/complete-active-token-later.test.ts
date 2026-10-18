import { EventEmitter } from 'node:events'

import type { CompletionItem } from '@hermes/shared/gateway-events'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const history = vi.hoisted(() => [] as string[])
vi.mock('@tui/lib/history.js', () => ({ append: (text: string) => history.push(text), load: () => history }))

interface Reply {
  items: CompletionItem[]
  replace_from?: number
}
interface Harness {
  app: App
  requests: { method: string; params: unknown }[]
  set(text: string, cursor?: number): Promise<void>
  press(bytes: string): Promise<void>
  overlay(): boolean
}

const flush = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

const settled = async () => {
  await new Promise(resolve => setTimeout(resolve, 100))
  await flush()
}

async function withApp(reply: () => Reply | Promise<Reply>, run: (h: Harness) => Promise<void>) {
  history.length = 0
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const handshake = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await handshake).toBe(true)
  const gw = new GatewayClient()
  const requests: Harness['requests'] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    requests.push({ method, params })

    if (method === 'complete.slash' || method === 'complete.path') {
      return reply()
    }
    throw new Error(`Unexpected RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => {
    view = View.from(next)
    render(next)
  }

  try {
    await run({
      app,
      requests,
      set: async (text, cursor = text.length) => {
        app.composer.set(text, cursor)
        app.changed()
        await settled()
      },
      press: async bytes => {
        input.emit('data', bytes)
        await flush()
      },
      overlay: () => view.regions.some(region => region?.children.some(node => node.props.role === 'omp.autocomplete'))
    })
  } finally {
    app.quit()
    await running

    if (splash === undefined) {
      delete process.env.HERMES_TUI_SPLASH
    } else {
      process.env.HERMES_TUI_SPLASH = splash
    }
  }
}

const row = (text: string, kind?: string): CompletionItem => ({ display: text, kind, text })

describe('completion of active tokens on later composer lines', () => {
  it.each([
    { typed: '/he', text: '/help', method: 'complete.slash', params: { text: '/he', session_id: 'session-1' } },
    {
      typed: 'use /cle',
      text: '/clean',
      kind: 'skill',
      method: 'complete.slash',
      params: { text: '/cle', session_id: 'session-1' }
    },
    { typed: '@src/a', text: '@file:src/app.ts', method: 'complete.path', params: { word: '@src/a' } },
    { typed: 'see ./src/a', text: './src/app.ts', method: 'complete.path', params: { word: './src/a' } }
  ])(
    'preserves previous lines and sends only supported context for $typed',
    async ({ typed, text, kind, method, params }) => {
      await withApp(
        () => ({ items: [row(text, kind)] }),
        async h => {
          const prefix = 'Earlier 🧑‍💻 日本語\n'
          await h.set(prefix + typed)
          expect(h.requests[0]).toEqual({ method, params })
          expect(h.overlay()).toBe(true)
          await h.press('\t')
          expect(h.app.composer.text).toBe(
            prefix + (typed.startsWith('use ') ? 'use ' : typed.startsWith('see ') ? 'see ' : '') + text
          )
          expect(h.requests.some(request => request.method === 'prompt.submit')).toBe(false)
        }
      )
    }
  )

  it.each(['\t', '\r'])(
    'replaces a complete token at a mid-token caret with %j, leaving later words/lines intact',
    async key => {
      await withApp(
        () => ({ items: [row('/help')] }),
        async h => {
          await h.set('前🙂\n/hextra keep\nlast', '前🙂\n/he'.length)
          await h.press(key)
          expect(h.app.composer.text).toBe('前🙂\n/help keep\nlast')
          expect(h.app.composer.cursor).toBe('前🙂\n/help'.length)
          h.app.composer.undo()
          expect(h.app.composer.text).toBe('前🙂\n/hextra keep\nlast')
        }
      )
    }
  )

  it('does not submit when the row matches the caret prefix but changes the token suffix', async () => {
    await withApp(
      () => ({ items: [row('/help')] }),
      async h => {
        await h.set('first\n/helpx keep', 'first\n/help'.length)
        await h.press('\r')
        expect(h.app.composer.text).toBe('first\n/help keep')
      }
    )
  })

  it('keeps inline slash results skill-only', async () => {
    await withApp(
      () => ({ items: [row('/clear', 'command'), row('/clean', 'skill')] }),
      async h => {
        await h.set('first\nuse /cl')
        await h.press('\t')
        expect(h.app.composer.text).toBe('first\nuse /clean')
      }
    )
  })

  it('uses line-relative Python offsets for slash argument completions', async () => {
    await withApp(
      () => ({ items: [row('value')], replace_from: [...'/cmd 🙂 '].length }),
      async h => {
        await h.set('first\n/cmd 🙂 va')
        await h.press('\t')
        expect(h.app.composer.text).toBe('first\n/cmd 🙂 value')
      }
    )
  })

  it.each(['session', 'caret', 'suffix', 'generation'])('rejects stale responses after a $0 change', async change => {
    const pending = Promise.withResolvers<Reply>()
    let requests = 0
    await withApp(
      () => (requests++ === 0 ? pending.promise : { items: [] }),
      async h => {
        await h.set('first\n/he tail', 'first\n/he'.length)

        if (change === 'session') {
          h.app.sid = 'session-2'
        }

        if (change === 'caret') {
          h.app.composer.cursor--
        }

        if (change === 'suffix') {
          h.app.composer.set('first\n/he changed', 'first\n/he'.length)
        }

        if (change === 'generation') {
          await h.set('first\n/hx')
        }
        pending.resolve({ items: [row('/help')] })
        await flush()
        await h.press('\t')
        expect(h.app.composer.text).not.toContain('/help')
      }
    )
  })

  it('rejects already-visible rows after session or suffix changes before the next paint', async () => {
    await withApp(
      () => ({ items: [row('/help')] }),
      async h => {
        await h.set('first\n/he tail', 'first\n/he'.length)
        h.app.sid = 'session-2'
        await h.press('\t')
        expect(h.app.composer.text).toBe('first\n/he tail')
      }
    )
  })

  it('completes a multiline draft recalled from history without changing the recalled prefix', async () => {
    await withApp(
      () => ({ items: [row('/clean', 'skill')] }),
      async h => {
        history.push('recalled 🙂\nuse /cle')
        await h.press('\x1b[A')
        await settled()
        expect(h.overlay()).toBe(true)
        await h.press('\t')
        expect(h.app.composer.text).toBe('recalled 🙂\nuse /clean')
      }
    )
  })
})
