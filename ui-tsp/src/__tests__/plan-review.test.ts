import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { node, Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, type MockInstance, vi } from 'vitest'

import { actionForKey } from '../actions.js'
import { App, INPUT_ID } from '../app.js'
import { latestPlan, parsePlan } from '../plan.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-plan-review-'))
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

  rmSync(isolated.home, { force: true, recursive: true })
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
type Tree = NonNullable<View['regions'][number]>['children'][number]
const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])

interface Fixture {
  app: App
  surface: Surface
  gw: GatewayClient
  nodes(region: string): Tree[]
  press(bytes: string): Promise<void>
  click(key: string): () => void | Promise<void>
  request: MockInstance<GatewayClient['request']>
}

async function withApp(run: (fixture: Fixture) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const handshake = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await handshake).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'prompt.submit') {
      return {}
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
      surface,
      gw,
      nodes,
      request,
      press: async bytes => {
        input.emit('data', bytes)
        await rendered()
        await rendered()
      },
      click: key => {
        const target = nodes('layer').find(node => node.props.key === key)

        if (!target) {
          throw new Error(`Missing action ${key}`)
        }

        const action = surface.dispatch({ ev: 'action', act: 'click', id: target.id, sf: 'hermes', raw: {} })

        if (!action) {
          throw new Error(`Missing handler ${target.id}`)
        }

        return action
      }
    })
  } finally {
    app.quit()
    await running
  }
}

const planText =
  'Plan introduction.\n\n# Implementation plan\n\nGoal.\n\n## Build\n\nChange src/main.ts.\n\n## Verify\n\nRun the tests.\n'

function seed(app: App) {
  app.transcript.push({
    kind: 'turn',
    id: 'plan-turn',
    status: 'done',
    rev: 1,
    startedAt: 1,
    blocks: [{ kind: 'text', id: 'plan-text', text: planText }]
  })
}

const body = (nodes: Fixture['nodes']) => nodes('layer').find(node => node.props.role === 'omp.plan.body')?.props.text
const sheet = (nodes: Fixture['nodes']) => nodes('layer').find(node => node.props.role === 'omp.overlay.plan')

describe('read-only plan review', () => {
  it('Tab traverses actual rendered actions with a native selected picker and dispatches Settings', async () => {
    await withApp(async ({ app, nodes, press, request }) => {
      seed(app)
      app.composer.set('preserve keyboard draft', 5)
      request.mockImplementation(async method => method === 'settings.get' ? { fields: {}, profile: 'fixture' } : { items: [] })
      app.changed()
      await rendered()
      await press('\t')
      const picker = () => nodes('layer').find(n => n.kind === 'picker' && n.props.title === 'Keyboard actions')!
      expect(picker()).toBeDefined()
      const items = picker().props.items as { id: string; label: string }[]
      expect(items.some(item => item.label.includes('Copy answer'))).toBe(true)
      const settings = items.find(item => /settings/i.test(item.label))!
      expect(settings).toBeDefined()

      for (let i = 0; i < items.length && picker().props.selected !== settings.id; i++) { await press('\t') }
      expect(picker().props.selected).toBe(settings.id)
      await press('\r')
      expect(nodes('layer').some(n => n.kind === 'prefs')).toBe(true)
      expect(app.composer.text).toBe('preserve keyboard draft')
      expect(app.composer.cursor).toBe(5)
    })
  })

  it('Help routes scroll keys to its actual sheet body without leaking edits', async () => {
    await withApp(async ({ app, press, surface, request }) => {
      request.mockResolvedValue({ pairs: [['/late', 'Late command']] })
      app.composer.set('preserved')
      await app.slash('/help')
      await rendered()
      const scroll = vi.spyOn(surface, 'scroll')
      await press('\x1b[6~')
      expect(scroll).toHaveBeenLastCalledWith(expect.stringMatching(/\.body$/), 'page-down')
      await press('\x1b[F')
      expect(scroll).toHaveBeenLastCalledWith(expect.stringMatching(/\.body$/), 'end')
      expect(app.composer.text).toBe('preserved')
    })
  })

  it('/plan builds the ToC from the latest completed assistant heading-structured message and jumps sections', async () => {
    await withApp(async ({ app, nodes, press, surface, click, request }) => {
      seed(app)
      app.transcript.user('# Not an assistant plan')
      app.transcript.panel('A tool report', '# Not a plan either')
      app.transcript.text('# Still streaming')
      const before = structuredClone(app.transcript.entries)
      await app.slash('/plan')
      await rendered()
      expect(sheet(nodes)).toBeDefined()
      expect(
        nodes('layer')
          .filter(n => /^section-\d+$/.test(String(n.props.key)))
          .map(n => flatten(n.children).find(child => child.props.key === 'label')?.props.text)
      ).toEqual(['Implementation plan', '  Build', '  Verify'])
      expect(body(nodes)).toBe('Plan introduction.\n\n# Implementation plan\n\nGoal.\n\n')
      const scroll = vi.spyOn(surface, 'scroll')
      await press('\x1b[B')
      expect(body(nodes)).toBe('## Build\n\nChange src/main.ts.\n\n')
      expect(scroll).toHaveBeenLastCalledWith(`${sheet(nodes)!.id}.body.markdown`, 'start')
      await click('section-2')()
      await rendered()
      expect(body(nodes)).toBe('## Verify\n\nRun the tests.\n')
      await press('\x1b[A')
      expect(body(nodes)).toContain('## Build')
      await press('\x1b[6~')
      expect(scroll).toHaveBeenLastCalledWith(`${sheet(nodes)!.id}.body.markdown`, 'page-down')
      expect(structuredClone(app.transcript.entries)).toEqual(before)
      expect(request.mock.calls.some(([method]) => method === 'slash.exec')).toBe(false)
    })
  })

  it('Approve sends the exact ordinary user message once, including duplicate native callbacks', async () => {
    await withApp(async ({ app, nodes, click, request }) => {
      seed(app)
      app.composer.set('preserve my draft', 4)
      await app.slash('/plan')
      await rendered()
      const approve = click('approve')
      await approve()
      await approve()
      await rendered()
      expect(request.mock.calls.filter(([method]) => method === 'prompt.submit')).toEqual([
        ['prompt.submit', { session_id: 'session-1', text: 'Approved — proceed with the plan.', image_paths: [] }]
      ])
      expect(app.transcript.entries.at(-1)).toMatchObject({ kind: 'user', text: 'Approved — proceed with the plan.' })
      expect(app.composer.text).toBe('preserve my draft')
      expect(app.composer.cursor).toBe(4)
      expect(sheet(nodes)).toBeUndefined()
    })
  })

  it('Refine owns a separate native field, rejects blank notes and submits the composed text', async () => {
    await withApp(async ({ app, surface, nodes, click, request, press }) => {
      seed(app)
      app.composer.set('untouched composer', 6)
      const focus = vi.spyOn(surface, 'focus')
      await app.slash('/plan')
      await rendered()
      await click('refine')()
      await rendered()
      const field = nodes('layer').find(n => n.props.key === 'note')!
      expect(focus).toHaveBeenLastCalledWith(field.id)
      expect(body(nodes)).toBeUndefined()
      await press('\r')
      expect(request.mock.calls.some(([method]) => method === 'prompt.submit')).toBe(false)
      await surface.dispatch({
        ev: 'edit',
        id: field.id,
        sf: 'hermes',
        raw: {},
        from: 0,
        to: 0,
        text: '  Add failure tests 🦉  ',
        cursor: 24,
        len: 0
      })?.()
      await rendered()
      await click('review')()
      await rendered()
      expect(body(nodes)).toContain('# Implementation plan')
      await click('refine')()
      await rendered()
      expect(nodes('layer').find(n => n.props.key === 'note')?.props.text).toBe('  Add failure tests 🦉  ')
      const send = click('refine')
      await send()
      await send()
      await rendered()
      expect(request.mock.calls.filter(([method]) => method === 'prompt.submit')).toEqual([
        ['prompt.submit', { session_id: 'session-1', text: 'Refine the plan: Add failure tests 🦉', image_paths: [] }]
      ])
      expect(app.composer.text).toBe('untouched composer')
      expect(app.composer.cursor).toBe(6)
      expect(focus).toHaveBeenLastCalledWith(INPUT_ID)
    })
  })

  it('shows an explanatory empty state instead of an empty plan or decision controls', async () => {
    await withApp(async ({ app, nodes }) => {
      app.transcript.user('# User plan')
      app.transcript.push({
        kind: 'turn',
        id: 'plain',
        status: 'done',
        rev: 1,
        startedAt: 1,
        blocks: [
          { kind: 'text', id: 'plain-text', text: 'Just a sentence.' },
          { kind: 'thinking', id: 'thought', text: '# Private reasoning', startedAt: 1 }
        ]
      })
      await app.slash('/plan')
      await rendered()
      expect(sheet(nodes)).toBeDefined()
      expect(body(nodes)).toBe('No heading-structured assistant plan found. Ask Hermes for a plan first.')
      expect(nodes('layer').some(n => n.props.key === 'approve' || n.props.key === 'refine')).toBe(false)
    })
  })

  it.each(['escape', 'button'])(
    'Close via %s restores exact composer draft/caret/focus, without main scroll changes',
    async close => {
      await withApp(async ({ app, surface, nodes, press, click }) => {
        seed(app)
        app.composer.set('  unsent\nUnicode 🦉 draft  ', 7)
        app.changed()
        await rendered()
        const main = nodes('main')
        const focus = vi.spyOn(surface, 'focus')
        const scroll = vi.spyOn(surface, 'scroll')
        await app.slash('/plan')
        await rendered()
        expect(focus).toHaveBeenLastCalledWith(null)
        await press('\x03')
        await press('\x1b[200~not inserted\x1b[201~')
        await surface.dispatch({
          ev: 'edit',
          id: INPUT_ID,
          sf: 'hermes',
          raw: {},
          from: 0,
          to: 0,
          text: 'hidden edit',
          cursor: 11,
          len: app.composer.text.length
        })?.()

        if (close === 'escape') {
          await press('\x1b[27u')
        } else {
          await click('close')()
        }

        await rendered()
        expect(sheet(nodes)).toBeUndefined()
        expect(app.composer.text).toBe('  unsent\nUnicode 🦉 draft  ')
        expect(app.composer.cursor).toBe(7)
        expect(focus).toHaveBeenLastCalledWith(INPUT_ID)
        expect(nodes('main')).toEqual(main)
        expect(scroll).not.toHaveBeenCalled()
      })
    }
  )

  it('Alt+Shift+P opens review and does not collide with temporary-model Alt+P', async () => {
    await withApp(async ({ app, nodes, press }) => {
      seed(app)
      await press('\x1b[112;4u')
      expect(sheet(nodes)).toBeDefined()
      const context = { composerEmpty: true, busy: false, queued: false, overlayOpen: false, completionOpen: false }
      expect(actionForKey({ name: 'p', alt: true, shift: false, ctrl: false, meta: false }, context)?.id).toBe(
        'app.model.selectTemporary'
      )
    })
  })

  it('queues decisions through the normal busy submit path instead of steering or granting approval', async () => {
    await withApp(async ({ app, click, request }) => {
      seed(app)
      app.busy = { label: 'Working…', since: {}, startedAt: 1 }
      await app.slash('/plan')
      await rendered()
      await click('approve')()
      expect(app.queue).toEqual(['Approved — proceed with the plan.'])
      expect(request.mock.calls.some(([method]) => method === 'prompt.submit' || method === 'request.answer')).toBe(
        false
      )
    })
  })

  it('keeps pending approval above review and rejects stale decisions after replacement/session changes', async () => {
    await withApp(async ({ app, nodes, click, request }) => {
      seed(app)
      await app.slash('/plan')
      await rendered()
      const stale = click('approve')
      await app.slash('/plan')
      await rendered()
      await stale()
      expect(sheet(nodes)).toBeDefined()
      const current = click('approve')
      app.sid = 'session-2'
      await current()

      const approval = {
        key: 'prompt:pending',
        modal: true,
        node: (id: string) =>
          node('overlay', { key: id.slice('layer.'.length), head: 'Approval required', modal: true }),
        onKey: () => true
      }

      app.open(approval)
      await app.slash('/plan')
      await rendered()
      expect(app.overlays.at(-1)).toBe(approval)
      expect(request.mock.calls.some(([method]) => method === 'prompt.submit' || method === 'request.answer')).toBe(
        false
      )
    })
  })

  it('drops the plan sheet on gateway session adoption and cannot submit a captured decision', async () => {
    await withApp(async ({ app, nodes, click, request }) => {
      seed(app)
      await app.slash('/plan')
      await rendered()
      const stale = click('approve')
      request.mockImplementation(async method => {
        if (method === 'setup.status') { return { provider_configured: true } }

        if (method === 'session.close') { return {} }

        if (method === 'session.create') { return { session_id: 'session-2' } }

        if (method === 'complete.slash') { return { items: [] } }
        throw new Error(`Unexpected fixture RPC: ${method}`)
      })
      await app.newSession()
      await rendered()
      await stale()
      expect(app.sid).toBe('session-2')
      expect(sheet(nodes)).toBeUndefined()
      expect(request.mock.calls.some(([method]) => method === 'prompt.submit')).toBe(false)
    })
  })

  it('Refine can be typed and submitted with keyboard ownership, without touching the composer', async () => {
    await withApp(async ({ app, press, nodes, request }) => {
      seed(app)
      app.composer.set('original draft', 3)
      await app.slash('/plan')
      await press('\x1b[114;3u')
      expect(nodes('layer').some(n => n.props.key === 'note')).toBe(true)
      await press('\x1b[200~Add rollback tests\x1b[201~')
      await press('\r')
      expect(request).toHaveBeenCalledWith('prompt.submit', { session_id: 'session-1', text: 'Refine the plan: Add rollback tests', image_paths: [] })
      expect(app.composer.text).toBe('original draft')
      expect(app.composer.cursor).toBe(3)
    })
  })

  it('preserves /plan <task> as the existing gateway plan-generation command', async () => {
    await withApp(async ({ app, request, nodes }) => {
      request.mockResolvedValueOnce({ type: 'send', message: 'canonical plan-mode prompt' })
      await app.slash('/plan implement feature')
      await rendered()
      expect(request).toHaveBeenCalledWith('slash.exec', { command: 'plan implement feature', session_id: 'session-1' })
      expect(request).toHaveBeenCalledWith('prompt.submit', {
        session_id: 'session-1',
        text: 'canonical plan-mode prompt',
        image_paths: []
      })
      expect(sheet(nodes)).toBeUndefined()
    })
  })

  it('ignores fenced code headings and keeps exact section bodies with duplicate titles', () => {
    const plan = parsePlan('Intro\n```md\n# Not a heading\n```\n# Real ###\nBody\n## Same\nA\n## Same\nB')!
    expect(plan.sections.map(s => s.title)).toEqual(['Real', 'Same', 'Same'])
    expect(plan.sections.at(-1)?.text).toBe('## Same\nB')
    expect(plan.preamble).toBe('Intro\n```md\n# Not a heading\n```\n')
    expect(parsePlan('```md\n# Only code\n```')).toBeUndefined()
    expect(latestPlan([])).toBeUndefined()
  })
})
