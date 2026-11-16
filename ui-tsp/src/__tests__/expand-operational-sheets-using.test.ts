import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { OperationalReportResult, OperationalView } from '@hermes/shared/gateway-events'
import { node, Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, type MockInstance, vi } from 'vitest'

import { App } from '../app.js'
import { isReportCommand } from '../reports.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-report-sheets-'))
  const previous = process.env.HERMES_HOME
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
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

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
type Tree = NonNullable<View['regions'][number]>['children'][number]

function flatten(nodes: readonly Tree[]): Tree[] {
  return nodes.flatMap(node => [node, ...flatten(node.children)])
}

interface Fixture {
  app: App
  gw: GatewayClient
  surface: Surface
  nodes(region: string): Tree[]
  press(bytes: string): Promise<void>
  click(region: string, key: string): () => void | Promise<void>
  request: MockInstance<GatewayClient['request']>
}

async function withApp(run: (fixture: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'operations.report') {
      return {
        view: 'mcp-list',
        scope: 'fixture',
        state: 'ready',
        read_only: true,
        rows: [],
        message: 'Read-only Hermes inventory.'
      }
    }

    if (method === 'slash.exec') {
      return { output: '# Report\n\nExact **Markdown** body.\n' }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    throw new Error(`Unexpected fixture RPC: ${method}`)
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

  const nodes = (region: string) => flatten(view.regions.find(item => item?.id === region)?.children ?? [])

  try {
    await run({
      app,
      gw,
      surface,
      nodes,
      request,
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
        await rendered()
      },
      click: (region, key) => {
        const target = nodes(region).find(node => node.props.key === key)

        if (!target) {
          throw new Error(`Missing native action: ${region}/${key}`)
        }

        const action = surface.dispatch({ ev: 'action', act: 'click', id: target.id, sf: 'hermes', raw: {} })

        if (!action) {
          throw new Error(`Missing native handler: ${target.id}`)
        }

        return action
      }
    })
  } finally {
    app.quit()
    await running
  }
}

function sheet(nodes: Fixture['nodes']) {
  return nodes('layer').find(node => node.props.role === 'omp.overlay.report')
}

function report(view: OperationalView = 'mcp-list'): OperationalReportResult {
  return {
    view,
    scope: 'owned-profile',
    state: 'ready',
    read_only: true,
    rows: [],
    message: 'Read-only Hermes inventory.'
  }
}

const body = (nodes: Fixture['nodes']) => {
  const props = nodes('layer').find(node => node.props.role === 'omp.report.body')?.props

  return String(props?.text ?? (props?.spans as { t: string }[] | undefined)?.map(span => span.t).join('') ?? '')
}

const status = (nodes: Fixture['nodes']) =>
  nodes('layer').find(node => node.props.role === 'omp.report.state')?.props.text

describe('Hermes operational report sheets', () => {
  it('renders inventory punctuation literally without invoking the Markdown/math renderer', async () => {
    await withApp(async f => {
      const inventory = report()
      inventory.rows = [{ name: 'ctx', details: ['Environment configured (values withheld)', 'Literal [brackets], *stars*, and \\(not math\\)'] }]
      f.request.mockResolvedValueOnce(inventory)
      await f.app.slash('/mcp list')
      await rendered()
      const target = f.nodes('layer').find(node => node.props.role === 'omp.report.body')!
      expect(target.kind).toBe('text')
      expect(body(f.nodes)).toContain('Environment configured (values withheld)')
      expect(body(f.nodes)).toContain('Literal [brackets], *stars*')
      expect(f.nodes('layer').some(node => node.kind === 'md')).toBe(false)
    })
  })

  it.each([
    ['/mcp', 'mcp-list'],
    ['/mcp list', 'mcp-list'],
    ['/mcp status', 'mcp-status'],
    ['/mcp tools', 'mcp-tools'],
    ['/mcp catalog', 'mcp-catalog'],
    ['/ssh', 'ssh-list'],
    ['/ssh list', 'ssh-list']
  ] satisfies [string, OperationalView][])(
    '%s uses the explicit session-authorized read route, not slash output',
    async (command, view) => {
      await withApp(async f => {
        f.request.mockResolvedValueOnce(report(view))
        const before = [...f.app.transcript.entries]
        await f.app.slash(command)
        await rendered()
        expect(f.request).toHaveBeenCalledWith('operations.report', { session_id: 'session-1', view })
        expect(f.request.mock.calls.some(([method]) => method === 'slash.exec')).toBe(false)
        expect(sheet(f.nodes)?.props.head).toBe(command)
        expect(status(f.nodes)).toBe('ready')
        expect(f.nodes('layer').some(node => node.props.text === 'Hermes profile: owned-profile · Read only')).toBe(
          true
        )
        expect(f.app.transcript.entries).toEqual(before)
      })
    }
  )

  it.each([
    ['/mcp list', 'mcp-list', 'No MCP servers configured'],
    ['/ssh list', 'ssh-list', 'No SSH hosts configured']
  ] satisfies [string, OperationalView, string][])(
    'renders the empty %s inventory without inventing entries',
    async (command, view, empty) => {
      await withApp(async f => {
        f.request.mockResolvedValueOnce(report(view))
        await f.app.slash(command)
        await rendered()
        expect(body(f.nodes)).toContain(empty)
        expect(status(f.nodes)).toBe('ready')
      })
    }
  )

  it('shows actual loading and unavailable states without raw auth errors or fake empty inventory', async () => {
    await withApp(async f => {
      const reply = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(reply.promise)
      const pending = f.app.slash('/mcp status')
      await rendered()
      expect(status(f.nodes)).toBe('loading')
      reply.reject(new Error('Authorization: Bearer inert-secret-fixture'))
      await pending
      await rendered()
      expect(status(f.nodes)).toBe('unavailable')
      expect(body(f.nodes)).toContain('service is unavailable')
      expect(body(f.nodes)).not.toContain('inert-secret-fixture')
      expect(body(f.nodes)).not.toContain('No MCP servers')
      const unavailable = { ...report('ssh-list'), state: 'unavailable', message: 'Hermes inventory unavailable.' }
      f.request.mockResolvedValueOnce(unavailable)
      await f.app.slash('/ssh list')
      await rendered()
      expect(status(f.nodes)).toBe('unavailable')
      expect(body(f.nodes)).not.toContain('No SSH hosts')
    })
  })

  it('keeps every item in long inventories, scrolls only the sheet and copies the exact read-only body', async () => {
    await withApp(async f => {
      const long = report('mcp-tools')
      long.rows = Array.from({ length: 300 }, (_, i) => ({
        name: `server-${i}`,
        details: [`mcp_server_${i}_read`, 'cached only']
      }))
      f.request.mockResolvedValueOnce(long)
      await f.app.slash('/mcp tools')
      await rendered()
      expect(body(f.nodes)).toContain('server-0')
      expect(body(f.nodes)).toContain('server-299')
      const scroll = vi.spyOn(f.surface, 'scroll')
      await f.press('\x1b[6~')
      expect(scroll).toHaveBeenLastCalledWith(`${sheet(f.nodes)!.id}.body.markdown`, 'page-down')
      const write = vi.spyOn(process.stdout, 'write').mockReturnValue(true)

      try {
        await f.click('layer', 'copy')()
        expect(write).toHaveBeenCalledWith(`\x1b]52;c;${Buffer.from(body(f.nodes)).toString('base64')}\x07`)
      } finally {
        write.mockRestore()
      }
    })
  })

  it.each([
    '/mcp add name',
    '/mcp remove name',
    '/mcp reconnect name',
    '/mcp reload',
    '/mcp auth inert-secret',
    '/ssh add name',
    '/ssh remove name',
    '/ssh reconnect name',
    '/ssh auth inert-secret'
  ])('%s is explicitly unsupported management, never a read-only report route or slash mutation', async command => {
    await withApp(async f => {
      await f.app.slash(command)
      await rendered()
      expect(status(f.nodes)).toBe('unsupported')
      expect(body(f.nodes)).toContain('No command or mutation was sent')
      expect(body(f.nodes)).not.toContain('inert-secret')
      expect(f.request.mock.calls.filter(([method]) => method !== 'complete.slash')).toEqual([])
      const [name, ...args] = command.slice(1).split(' ')
      expect(isReportCommand(name!, args.join(' '))).toBe(false)
    })
  })

  it('ignores results from stale sessions, dismissed sheets and replaced same-key sheets', async () => {
    await withApp(async f => {
      const first = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(first.promise)
      const pending = f.app.slash('/mcp status')
      await rendered()
      f.app.sid = 'new-session'
      first.resolve({ ...report(), rows: [{ name: 'private-old', details: [] }] })
      await pending
      await rendered()
      expect(body(f.nodes)).not.toContain('private-old')
      const second = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(second.promise)
      const old = f.app.slash('/mcp list')
      await rendered()
      f.request.mockResolvedValueOnce(report('ssh-list'))
      await f.app.slash('/ssh list')
      second.resolve({ ...report(), rows: [{ name: 'private-replaced', details: [] }] })
      await old
      await rendered()
      expect(sheet(f.nodes)?.props.head).toBe('/ssh list')
      expect(body(f.nodes)).not.toContain('private-replaced')
      const third = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(third.promise)
      const closed = f.app.slash('/mcp list')
      await rendered()
      await f.click('layer', 'close')()
      third.resolve(report())
      await closed
      await rendered()
      expect(sheet(f.nodes)).toBeUndefined()
    })
  })

  it('keeps approval above pending inventory and preserves the exact main draft/caret on return', async () => {
    await withApp(async f => {
      f.app.composer.set('Main draft 🦉', 5)
      const reply = Promise.withResolvers<unknown>()
      f.request.mockReturnValueOnce(reply.promise)
      const pending = f.app.slash('/mcp list')
      await rendered()
      const staleCopy = f.click('layer', 'copy')

      const approval = {
        key: 'prompt:approval',
        modal: true,
        node: (id: string) => node('overlay', { key: id.slice(6), head: 'Approval required', modal: true }),
        onKey: () => true
      }

      f.app.open(approval)
      reply.resolve(report())
      await pending
      await rendered()
      expect(f.app.overlays.at(-1)).toBe(approval)
      const write = vi.spyOn(process.stdout, 'write').mockReturnValue(true)

      try {
        await staleCopy()
        expect(write).not.toHaveBeenCalled()
      } finally {
        write.mockRestore()
      }

      f.app.close(approval)
      await rendered()
      await f.click('layer', 'close')()
      await rendered()
      expect(f.app.composer.text).toBe('Main draft 🦉')
      expect(f.app.composer.cursor).toBe(5)
    })
  })
})
