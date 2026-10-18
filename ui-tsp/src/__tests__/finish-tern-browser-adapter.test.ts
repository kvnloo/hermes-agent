// Connected App contract tests only. These do not certify a signed-in native browser.
import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { BrowserBlock } from '@hermes/shared/gateway-events'
import { Session, type Tree, type TspEvent, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { openBrowserBlocks } from '../overlays/browser-blocks.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-finish-browser-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

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

const tick = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])

const owned: BrowserBlock = {
  target_id: '7',
  title: 'Page',
  url: 'https://example.org/',
  owner: null,
  owned: true,
  available: false
}

interface Harness {
  app: App
  calls: { method: string; params: unknown }[]
  nodes(): Tree[]
  event(key: string, event?: Partial<TspEvent>): Promise<void>
}

async function withApp(run: (h: Harness) => Promise<void>, fail?: string) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const calls: Harness['calls'] = []
  let released = false
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'complete.slash') {
      return { items: [] }
    }

    calls.push({ method, params })

    if (method === 'browser.blocks') {
      return { available: true, blocks: released ? [] : [owned] }
    }

    if (fail && method === 'browser.release') {
      throw new Error(fail)
    }

    if (method === 'browser.release') {
      released = true

      return { target_id: '7', released: true }
    }

    if (method === 'browser.frame') {
      return { target_id: '7', frame: '1.0' }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'browser-session'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let view: View | undefined

  surface.render = value => {
    view = View.from(value)
    render(value)
  }

  const nodes = () => flatten(view?.regions.flatMap(region => (region ? [region] : [])) ?? [])

  try {
    await run({
      app,
      calls,
      nodes,
      event: async (key, event = { ev: 'action', act: 'click' }) => {
        const target = nodes().find(node => node.props.key === key)
        expect(target, `missing ${key}`).toBeDefined()
        const action = surface.dispatch({ id: target!.id, raw: {}, sf: surface.id, ...event } as TspEvent)
        expect(action).toBeTypeOf('function')
        await action!()
        await tick()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

describe('finish Tern browser adapter contracts', () => {
  it('only explicit frame intent sends the exact path; limitations stay visible', async () => {
    await withApp(async h => {
      h.app.composer.set('keep my draft')
      openBrowserBlocks(h.app)
      await tick()
      expect(h.calls.map(call => call.method)).toEqual(['browser.blocks'])
      expect(
        h.nodes().some(node => String(node.props.text).includes('recording and annotated capture are unavailable'))
      ).toBe(true)
      await h.event('frame')
      await h.event('frame-path', { ev: 'edit', from: 0, to: 4, text: '1.0', cursor: 3, len: 4 })
      await h.event('apply-frame')
      expect(h.calls.at(-1)).toEqual({
        method: 'browser.frame',
        params: {
          session_id: 'browser-session',
          target_id: '7',
          frame: '1.0'
        }
      })
      expect(h.nodes().some(node => node.props.text === 'Block 7 · evaluation frame 1.0')).toBe(true)
      expect(h.app.composer.text).toBe('keep my draft')
    })
  })

  it('release reads back authoritative discovery and never adopts another page', async () => {
    await withApp(async h => {
      openBrowserBlocks(h.app)
      await tick()
      await h.event('release')
      expect(h.calls).toEqual([
        { method: 'browser.blocks', params: { session_id: 'browser-session' } },
        { method: 'browser.release', params: { session_id: 'browser-session', target_id: '7' } },
        { method: 'browser.blocks', params: { session_id: 'browser-session' } }
      ])
      expect(h.nodes().some(node => node.props.key === 'release')).toBe(false)
    })
  })

  it('busy and stale sheets cannot retarget or release an executing tool', async () => {
    await withApp(async h => {
      openBrowserBlocks(h.app)
      await tick()
      h.app.busy = { label: 'Working', since: {}, startedAt: Date.now(), confirmed: true }
      await h.event('release')
      await h.event('frame')
      expect(h.calls.map(call => call.method)).toEqual(['browser.blocks'])
      h.app.busy = null
      h.app.sid = 'different-session'
      await h.event('release')
      expect(h.calls.map(call => call.method)).toEqual(['browser.blocks'])
    })
  })

  it('cleanup failure remains visible with ownership controls intact', async () => {
    await withApp(async h => {
      openBrowserBlocks(h.app)
      await tick()
      await h.event('release')
      expect(h.nodes().some(node => node.props.text === 'disconnected; ownership retained')).toBe(true)
      expect(h.nodes().some(node => node.props.key === 'release')).toBe(true)
      expect(h.calls.map(call => call.method)).toEqual(['browser.blocks', 'browser.release'])
    }, 'disconnected; ownership retained')
  })

  it.each(['js', 'unsupported', 'open_pending'])(
    'preserves %s errors and confirmed frame identity in browser cards',
    async kind => {
      await withApp(async h => {
        h.app.transcript.load([
          {
            role: 'assistant',
            tool_calls: [
              {
                id: 'browse',
                type: 'function',
                function: {
                  name: 'browser_console',
                  arguments: JSON.stringify({ expression: '1' })
                }
              }
            ]
          },
          {
            role: 'tool',
            name: 'browser_console',
            tool_call_id: 'browse',
            content: JSON.stringify({
              success: false,
              error: `${kind} detail`,
              error_kind: kind,
              tern_target: { target_id: '7', title: 'Page', url: owned.url, in_tern: true, frame: '1.0' }
            })
          }
        ])
        h.app.changed()
        await tick()
        const tool = h.nodes().find(node => node.kind === 'tool')!
        expect(tool.props.meta).toContain('evaluation frame 1.0')
        expect(tool.props.meta).toContain(`Tern ${kind}`)
        expect(JSON.stringify(h.nodes().map(node => node.node.toJSON()))).toContain(`${kind} detail`)
        expect(h.nodes().some(node => node.kind === 'image')).toBe(false)
      })
    }
  )
})
