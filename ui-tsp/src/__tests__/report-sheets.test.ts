import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { node, Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, type MockInstance, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'
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
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'btw.list') {
      return { threads: [] }
    }

    if (method === 'operations.report') {
      return { view: 'mcp-list', scope: 'fixture', state: 'ready', read_only: true, rows: [], message: 'Read-only Hermes inventory.' }
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

  surface.render = next => { view = View.from(next); render(next) }
  const nodes = (region: string) => flatten(view.regions.find(item => item?.id === region)?.children ?? [])

  try {
    await run({
      app, gw, surface, nodes, request,
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

describe('native report sheets', () => {
  it.each(['/usage', '/context', '/skills', '/tools'])('%s preserves CLI output as literal monospace rows in the sheet', async command => {
    await withApp(async ({ app, nodes, request }) => {
      const before = [...app.transcript.entries]
      await app.slash(command)
      await rendered()
      expect(sheet(nodes)?.props.head).toBe(command)
      const body = nodes('layer').find(node => node.props.role === 'omp.report.body')!
      expect(body.kind).toBe('text')
      expect(body.props.spans).toEqual([{ s: 'mono', t: '# Report\n\nExact **Markdown** body.\n' }])
      expect(body.props.wrap).toBe('none')
      expect(nodes('layer').some(node => node.kind === 'md')).toBe(false)
      expect(app.transcript.entries).toEqual(before)
      expect(nodes('main').some(node => node.props.role === 'omp.custom')).toBe(false)
      expect(request).toHaveBeenCalledWith('slash.exec', { command: command.slice(1), session_id: 'session-1' })
    })
  })

  it('a non-report slash command retains its transcript panel', async () => {
    await withApp(async ({ app, nodes }) => {
      await app.slash('/compress')
      await rendered()
      expect(sheet(nodes)).toBeUndefined()
      expect(app.transcript.entries.at(-1)).toMatchObject({ kind: 'panel', title: '/compress', text: '# Report\n\nExact **Markdown** body.\n' })
      expect(nodes('main').some(node => node.props.role === 'omp.custom')).toBe(true)
    })
  })

  it.each(['background.complete', 'btw.complete'])('%s shows a dock notice; native View opens the exact report without a transcript entry', async type => {
    await withApp(async ({ app, gw, nodes, click }) => {
      const before = [...app.transcript.entries]
      gw.emit('event', { type, session_id: app.sid, payload: { task_id: 'task-1', text: '# Side result\n\nActual report' } })
      await rendered()
      expect(sheet(nodes)).toBeUndefined()
      expect(nodes('dock').find(node => node.props.key === 'label')?.props.text).toBe(type === 'background.complete' ? 'background task done ·' : 'Side question answered ·')
      await click('dock', 'view')()
      await rendered()
      expect(sheet(nodes)?.props.head).toBe(type === 'btw.complete' ? '/btw' : 'Background task')
      expect(nodes('layer').find(node => node.kind === 'md')?.props.text).toBe('# Side result\n\nActual report')
      expect(app.transcript.entries).toEqual(before)
    })
  })

  it.each(['escape', 'button'])('Close via %s restores the exact composer draft/caret/focus without touching main', async close => {
    await withApp(async ({ app, surface, nodes, press, click }) => {
      app.composer.set('  unsent\nUnicode 🦉 draft  ', 7)
      app.changed()
      await rendered()
      const main = nodes('main')
      const focus = vi.spyOn(surface, 'focus')
      const scroll = vi.spyOn(surface, 'scroll')
      await app.slash('/usage')
      await rendered()
      expect(focus).toHaveBeenLastCalledWith(null)
      await press('\x1b[200~not inserted\x1b[201~')
      await press('\x03')
      await surface.dispatch({ ev: 'edit', id: INPUT_ID, sf: 'hermes', raw: {}, from: 0, to: 0, text: 'native edit', cursor: 11, len: app.composer.text.length })?.()

      if (close === 'escape') {
        await press('\x1b[27u')
      } else {
        await click('layer', 'close')()
      }

      await rendered()
      expect(sheet(nodes)).toBeUndefined()
      expect(app.composer.text).toBe('  unsent\nUnicode 🦉 draft  ')
      expect(app.composer.cursor).toBe(7)
      expect(focus).toHaveBeenLastCalledWith(INPUT_ID)
      expect(nodes('main')).toEqual(main)
      expect(scroll).not.toHaveBeenCalled()
    })
  })

  it.each([['\x1b[99;3u', 'context'], ['\x1b[117;3u', 'usage']])('shortcut %s opens /%s in the shared sheet', async (bytes, command) => {
    await withApp(async ({ app, press, nodes, request }) => {
      const before = [...app.transcript.entries]
      app.composer.set('keep this draft', 4)
      await press(bytes)
      expect(sheet(nodes)?.props.head).toBe(`/${command}`)
      expect(app.transcript.entries).toEqual(before)
      expect(request).toHaveBeenCalledWith('slash.exec', { command, session_id: 'session-1' })
      expect(app.composer.text).toBe('keep this draft')
      expect(app.composer.cursor).toBe(4)
    })
  })

  it.each(['/btw', '/context', '/history', '/tools', '/help usage', '/status', '/mcp'])('%s uses the explicit report route', async command => {
    await withApp(async ({ app, nodes }) => {
      await app.slash(command)
      await rendered()
      expect(sheet(nodes)?.props.head).toBe(command)
      expect(app.transcript.entries.some(entry => entry.kind === 'panel')).toBe(false)
    })
  })

  it('keeps mutating and unknown command forms outside the report list', () => {
    for (const [name, arg] of [['mcp', 'reload'], ['agents', 'stop'], ['status', 'set'], ['unknown', ''], ['compress', '']]) {
      expect(isReportCommand(name!, arg!)).toBe(false)
    }
  })

  it('scrolls only the native overlay, never main', async () => {
    await withApp(async ({ app, surface, nodes, press }) => {
      app.report({ title: 'Long report', text: Array.from({ length: 100 }, (_, i) => `Row ${i}`).join('\n\n') })
      await rendered()
      const scroll = vi.spyOn(surface, 'scroll')
      const id = sheet(nodes)!.id

      for (const [bytes, to] of [['\x1b[6~', 'page-down'], ['\x1b[5~', 'page-up'], ['\x1b[F', 'end'], ['\x1b[H', 'start'], ['\x1b[B', 'line-down'], ['\x1b[A', 'line-up']]) {
        await press(bytes!)
        expect(scroll).toHaveBeenLastCalledWith(`${id}.body.markdown`, to)
      }

      expect(scroll).toHaveBeenCalledTimes(6)
    })
  })

  it('Copy emits exact report-only OSC52 bytes and handles copy failure within the sheet', async () => {
    await withApp(async ({ app, nodes, click }) => {
      const text = '# Report\n\nUnicode 🦉\n'
      app.report({ title: 'Copy report', text })
      await rendered()
      const before = [...app.transcript.entries]
      const write = vi.spyOn(process.stdout, 'write').mockReturnValue(true)

      try {
        await click('layer', 'copy')()
        expect(write).toHaveBeenCalledWith(`\x1b]52;c;${Buffer.from(text).toString('base64')}\x07`)
        write.mockImplementation(() => { throw new Error('clipboard unavailable') })
        await click('layer', 'copy')()
      } finally {
        write.mockRestore()
      }

      await rendered()
      expect(nodes('layer').some(node => node.props.text === 'Could not copy the report to the clipboard.')).toBe(true)
      expect(app.transcript.entries).toEqual(before)
    })
  })

  it('does not publish a late report from a session the user has left', async () => {
    await withApp(async ({ app, request, nodes }) => {
      const reply = Promise.withResolvers<unknown>()
      request.mockReturnValueOnce(reply.promise)
      const pending = app.slash('/usage')
      app.sid = 'session-2'
      reply.resolve({ output: 'Old private report' })
      await pending
      await rendered()
      expect(sheet(nodes)).toBeUndefined()
      expect(app.transcript.entries.some(entry => entry.kind === 'panel')).toBe(false)
    })
  })

  it('does not cover a pending approval with an asynchronously completed slash report', async () => {
    await withApp(async ({ app, nodes }) => {
      const approval = {
        key: 'prompt:approval-1', modal: true,
        node: (id: string) => node('overlay', { key: id.slice('layer.'.length), head: 'Approval required', modal: true }),
        onKey: () => true
      }

      app.open(approval)
      await app.slash('/usage')
      await rendered()
      expect(app.overlays.at(-1)).toBe(approval)
      expect(sheet(nodes)?.props.head).toBe('/usage')
      app.close(approval)
      await rendered()
      expect(app.overlays.at(-1)?.key).toBe('report')
    })
  })

  it('clears report notices and the open sheet when the gateway adopts a different session', async () => {
    await withApp(async ({ app, gw, request, nodes, click }) => {
      gw.emit('event', { type: 'background.complete', session_id: app.sid, payload: { task_id: 'old', text: 'Private old-session report' } })
      await rendered()
      await click('dock', 'view')()
      await rendered()
      expect(sheet(nodes)).toBeDefined()
      request.mockImplementation(async method => {
        if (method === 'setup.status') {
          return { provider_configured: true }
        }

        if (method === 'session.close') {
          return {}
        }

        if (method === 'session.create') {
          return { session_id: 'session-2' }
        }

        if (method === 'complete.slash') {
          return { items: [] }
        }

        throw new Error(`Unexpected fixture RPC: ${method}`)
      })
      await app.newSession()
      await rendered()
      expect(app.sid).toBe('session-2')
      expect(sheet(nodes)).toBeUndefined()
      expect(nodes('dock').some(node => node.props.role === 'omp.report.view')).toBe(false)
      gw.emit('event', { type: 'background.complete', session_id: 'session-1', payload: { task_id: 'late', text: 'Late old-session report' } })
      await rendered()
      expect(nodes('dock').some(node => node.props.role === 'omp.report.view')).toBe(false)
    })
  })

  it('shows errors as failed notices and rejects stale View callbacks after dismissal', async () => {
    await withApp(async ({ app, gw, click, nodes }) => {
      gw.emit('event', { type: 'background.complete', session_id: app.sid, payload: { task_id: 'bad', text: 'error: denied by backend' } })
      await rendered()
      expect(nodes('dock').find(node => node.props.key === 'label')?.props).toMatchObject({ text: 'background task failed ·', tone: 'error' })
      const stale = click('dock', 'view')
      await click('dock', 'dismiss')()
      await stale()
      await rendered()
      expect(sheet(nodes)).toBeUndefined()
      expect(nodes('dock').some(node => node.props.role === 'omp.report.notice')).toBe(false)
    })
  })
})
