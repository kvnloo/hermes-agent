import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { BrowserBlock } from '@hermes/shared/gateway-events'
import type { Surface } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { openBrowserBlocks } from '../overlays/browser-blocks.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-browser-blocks-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, previousSplash }
})

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

const rendered = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

type Tree = NonNullable<View['regions'][number]>
const descendants = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...descendants(node.children)])
interface Call {
  method: string
  params: unknown
}
interface Fixture {
  available?: boolean
  blocks?: BrowserBlock[]
  adopt?: () => Promise<unknown>
  list?: () => Promise<unknown>
}
interface Harness {
  app: App
  calls: Call[]
  nodes(region: string): Tree[]
  click(node: Tree): Promise<void>
  press(bytes: string): Promise<void>
}

async function withApp(run: (h: Harness) => Promise<void>, fixture: Fixture = {}) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const calls: Call[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'complete.slash') {
      return { items: [] }
    }

    calls.push({ method, params })

    if (method === 'browser.blocks') {
      return fixture.list
        ? fixture.list()
        : { available: fixture.available ?? true, blocks: fixture.blocks ?? [userBlock] }
    }

    if (method === 'browser.adopt') {
      return fixture.adopt ? fixture.adopt() : { ...target }
    }

    if (method === 'browser.focus') {
      return { ...target }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]! as Surface
  let view: View | undefined
  const render = surface.render.bind(surface)

  surface.render = value => {
    view = View.from(value)
    render(value)
  }

  try {
    app.changed()
    await rendered()
    await run({
      app,
      calls,
      nodes: region => descendants(view?.regions.find(item => item?.id === region)?.children ?? []),
      click: async node => {
        const action = surface.dispatch({ act: 'click', ev: 'action', id: node.id, raw: {}, sf: 'hermes' })
        expect(action).toBeTypeOf('function')
        await action!()
        await rendered()
      },
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

const target = { target_id: '7', title: 'User page', url: 'https://example.org/', in_tern: true }

const userBlock: BrowserBlock = {
  target_id: '7',
  title: target.title,
  url: target.url,
  owner: null,
  owned: false,
  available: true
}

const find = (nodes: Tree[], key: string) => {
  const result = nodes.find(node => node.props.key === key)
  expect(result, `missing ${key}`).toBeDefined()

  return result!
}

describe('Tern browser blocks', () => {
  it('lists target, URL, title and owner without adopting; Alt+Shift+B uses the action registry', async () => {
    await withApp(async h => {
      h.app.composer.set('keep my draft', 4)
      await h.press('\x1b[98;4u')
      expect(
        h
          .nodes('layer')
          .some(node => String(node.props.text).includes('7 · User page · https://example.org/ · owner docked'))
      ).toBe(true)
      expect(h.calls).toEqual([{ method: 'browser.blocks', params: { session_id: 'session-1' } }])
      await h.press('\x1b[27u')
      expect(h.app.overlays).toHaveLength(0)
      expect(h.app.composer.text).toBe('keep my draft')
      expect(h.app.composer.cursor).toBe(4)
    })
  })

  it('only the user handover action adopts the exact selected target', async () => {
    await withApp(async h => {
      openBrowserBlocks(h.app)
      await rendered()
      await h.click(find(h.nodes('layer'), 'choose'))
      expect(h.calls.at(-1)).toEqual({ method: 'browser.adopt', params: { session_id: 'session-1', target_id: '7' } })
      expect(h.app.overlays).toHaveLength(0)
    })
  })

  it('does not hand over another session’s driven block', async () => {
    await withApp(
      async h => {
        openBrowserBlocks(h.app)
        await rendered()
        await h.click(find(h.nodes('layer'), 'choose'))
        expect(h.calls.map(call => call.method)).toEqual(['browser.blocks'])
      },
      { blocks: [{ ...userBlock, available: false }] }
    )
  })

  it('shows backend refusal instead of claiming adoption', async () => {
    await withApp(
      async h => {
        openBrowserBlocks(h.app)
        await rendered()
        await h.click(find(h.nodes('layer'), 'choose'))
        expect(h.nodes('layer').some(node => node.props.text === 'Block already driven')).toBe(true)
        expect(h.app.overlays).toHaveLength(1)
      },
      {
        adopt: async () => {
          throw new Error('Block already driven')
        }
      }
    )
  })

  it('outside Tern shows unavailable and leaves the existing browser backend untouched', async () => {
    await withApp(
      async h => {
        openBrowserBlocks(h.app)
        await rendered()
        expect(
          h.nodes('layer').some(node => String(node.props.text).includes('existing browser backend is unchanged'))
        ).toBe(true)
        expect(h.calls.map(call => call.method)).toEqual(['browser.blocks'])
      },
      { available: false, blocks: [] }
    )
  })

  it('browser card shows the confirmed target identity and SDK focus action carries its id', async () => {
    await withApp(async h => {
      h.app.transcript.load([
        {
          role: 'assistant',
          tool_calls: [
            {
              id: 'browse',
              type: 'function',
              function: { name: 'browser_navigate', arguments: JSON.stringify({ url: 'https://old.example/' }) }
            }
          ]
        },
        {
          role: 'tool',
          name: 'browser_navigate',
          args: { url: 'https://old.example/' },
          tool_call_id: 'browse',
          content: JSON.stringify({ success: true, tern_target: target })
        }
      ])
      h.app.changed()
      await rendered()
      const tool = h.nodes('main').find(node => node.kind === 'tool')!
      expect(tool.props.target).toBe(target.url)
      expect(tool.props.meta).toContain(target.title)
      expect(tool.props.meta).toContain('in Tern block 7')
      await h.click(find(h.nodes('main'), 'browser-focus'))
      expect(h.calls.at(-1)).toEqual({ method: 'browser.focus', params: { session_id: 'session-1', target_id: '7' } })
    })
  })

  it('closed and stale sheets never adopt a late listing', async () => {
    const deferred = Promise.withResolvers<unknown>()
    await withApp(
      async h => {
        openBrowserBlocks(h.app)
        await rendered()
        await h.click(find(h.nodes('layer'), 'close'))
        deferred.resolve({ available: true, blocks: [userBlock] })
        await rendered()
        expect(h.app.overlays).toHaveLength(0)
        expect(h.calls.map(call => call.method)).toEqual(['browser.blocks'])
      },
      { list: () => deferred.promise }
    )
  })
})
