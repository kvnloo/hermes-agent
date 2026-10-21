import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { PlanStatusResult } from '@hermes/shared/gateway-events'
import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'
import * as editor from '../external-editor.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-plan-decisions-'))
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

const paint = async () => {
  await new Promise<void>(resolve => setImmediate(resolve))
  await new Promise<void>(resolve => setImmediate(resolve))
}

type Tree = NonNullable<View['regions'][number]>['children'][number]
const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(n => [n, ...flatten(n.children)])

const initial = (): PlanStatusResult => ({
  enabled: true,
  generating: false,
  plan: {
    id: 'immutable-plan',
    revision: 3,
    text: '# Build\nChange one file\n## Verify\nRun tests',
    annotations: [],
    decision: 'pending'
  }
})

async function mount() {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const handshake = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await handshake).toBe(true)
  const gw = new GatewayClient()
  let status = initial()

  const request = vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'plan.status') {
      return structuredClone(status)
    }

    if (method === 'plan.mode') {
      status = { enabled: params?.enabled === true, generating: false, plan: null }

      return structuredClone(status)
    }

    if (method.startsWith('plan.')) {
      if (!status.plan || params?.plan_id !== status.plan.id || params?.revision !== status.plan.revision) {
        throw new Error('Plan changed; reopen review')
      }

      if (method === 'plan.edit') {
        status.plan.text = String(params?.text)
        status.plan.annotations = []
        status.plan.revision++
      }

      if (method === 'plan.annotate') {
        status.plan.annotations = [{ section: Number(params?.section), text: String(params?.text) }]
        status.plan.revision++
      }

      if (method === 'plan.decide') {
        status.plan.decision = params?.intent === 'approve' ? 'approved' : 'refined'
        status.enabled = params?.intent !== 'approve'
      }

      return structuredClone(status)
    }

    throw new Error(`Unexpected RPC ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  app.composer.set('hidden draft 🦉', 4)
  acknowledgeFrames(tern)
  const running = app.run()
  const surface: Surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => {
    view = View.from(next)
    render(next)
  }

  const nodes = () => flatten(view.regions.find(r => r?.id === 'layer')?.children ?? [])

  const click = (key: string) => {
    const n = nodes().find(n => n.props.key === key)

    if (!n) {
      throw new Error(`Missing ${key}`)
    }

    const fn = surface.dispatch({ ev: 'action', act: 'click', id: n.id, sf: 'hermes', raw: {} })

    if (!fn) {
      throw new Error(`No callback ${key}`)
    }

    return fn
  }

  return {
    app,
    surface,
    nodes,
    click,
    request,
    status: (next: PlanStatusResult) => {
      status = next
    },
    open: async () => {
      await app.reviewPlan()
      await paint()
    },
    press: async (bytes: string) => {
      input.emit('data', bytes)
      await paint()
    },
    edit: async (text: string) => {
      const field = nodes().find(n => n.props.key === 'note')!
      await surface.dispatch({
        ev: 'edit',
        id: field.id,
        sf: 'hermes',
        raw: {},
        from: 0,
        to: String(field.props.text).length,
        text,
        cursor: text.length,
        len: String(field.props.text).length
      })?.()
      await paint()
    },
    dispose: async () => {
      app.quit()
      await running
      vi.restoreAllMocks()
    }
  }
}

async function withApp(run: (f: Awaited<ReturnType<typeof mount>>) => Promise<void>) {
  const f = await mount()

  try {
    await run(f)
  } finally {
    await f.dispose()
  }
}

const planCalls = (f: Awaited<ReturnType<typeof mount>>, method: string) =>
  f.request.mock.calls.filter(([m]) => m === method)

describe('revision-bound plan decisions', () => {
  it('renders bounded multiline plan editing and keeps feedback independent from other editors', async () => {
    await withApp(async f => {
      await f.open()
      await f.click('edit-plan')()
      await paint()
      const editor = f.nodes().find(n => n.props.key === 'note')!
      expect(editor.kind).toBe('editor')
      expect(editor.props.maxLines).toBe(10)
      expect(editor.props.text).toContain('\n## Verify')
      await f.click('review')()
      await paint()
      await f.click('refine')()
      await paint()
      expect(f.nodes().find(n => n.props.key === 'note')?.props.text).toBe('')
      await f.edit('private feedback')
      await f.click('review')()
      await paint()
      await f.click('annotate')()
      await paint()
      await f.edit('section-only note')
      await f.click('refine')()
      await paint()
      await f.click('refine')()
      await paint()
      expect(f.nodes().find(n => n.props.key === 'note')?.props.text).toBe('private feedback')
    })
  })

  it('uses a private external-editor file and removes it after success or cancellation', async () => {
    const { readFile, stat, writeFile } = await import('node:fs/promises')
    let file = ''
    expect(
      await editor.editTextExternal('# Original', async path => {
        file = path
        expect(await readFile(path, 'utf8')).toBe('# Original')
        await writeFile(path, '# Actual edit')
      })
    ).toBe('# Actual edit')
    await expect(stat(file)).rejects.toThrow()
    await expect(
      editor.editTextExternal('# Keep', path => {
        file = path
        throw new Error('Editor cancelled')
      })
    ).rejects.toThrow('Editor cancelled')
    await expect(stat(file)).rejects.toThrow()
  })
  it('shows authoritative mode and identity, and toggles only through the gateway', async () => {
    await withApp(async f => {
      await f.open()
      expect(f.nodes().find(n => n.props.key === 'authority')?.props.text).toContain('immutable-plan · revision 3')
      await f.click('mode')()
      await paint()
      expect(f.request).toHaveBeenCalledWith('plan.mode', { session_id: 'session-1', enabled: false })
      expect(f.nodes().some(n => n.props.key === 'approve')).toBe(false)
      expect(f.app.composer.text).toBe('hidden draft 🦉')
    })
  })

  it('saves selected section annotations as a new backend revision', async () => {
    await withApp(async f => {
      await f.open()
      await f.click('section-1')()
      await paint()
      await f.click('annotate')()
      await paint()
      await f.edit('Cover rollback')
      await f.click('refine')()
      await paint()
      expect(f.request).toHaveBeenCalledWith('plan.annotate', {
        session_id: 'session-1',
        plan_id: 'immutable-plan',
        revision: 3,
        section: 1,
        text: 'Cover rollback'
      })
      expect(f.nodes().find(n => n.props.role === 'omp.plan.annotation')?.props.text).toBe('Note: Cover rollback')
      expect(f.nodes().find(n => n.props.key === 'authority')?.props.text).toContain('revision 4')
    })
  })

  it('edit and refine round-trip uses the edited revision without replacing the hidden draft', async () => {
    await withApp(async f => {
      await f.open()
      await f.click('edit-plan')()
      await paint()
      await f.edit('# Smaller\nOne change')
      await f.click('refine')()
      await paint()
      expect(f.request).toHaveBeenCalledWith('plan.edit', {
        session_id: 'session-1',
        plan_id: 'immutable-plan',
        revision: 3,
        text: '# Smaller\nOne change'
      })
      await f.click('refine')()
      await paint()
      await f.edit('Add a failure test')
      await f.click('refine')()
      await paint()
      expect(f.request).toHaveBeenCalledWith('plan.decide', {
        session_id: 'session-1',
        plan_id: 'immutable-plan',
        revision: 4,
        intent: 'refine',
        feedback: 'Add a failure test'
      })
      expect(planCalls(f, 'prompt.submit')).toHaveLength(0)
      expect(f.app.composer.text).toBe('hidden draft 🦉')
      expect(f.app.composer.cursor).toBe(4)
    })
  })

  it('approves exact revision once, including a repeated native pointer callback', async () => {
    await withApp(async f => {
      await f.open()
      const approve = f.click('approve')
      await approve()
      await approve()
      await paint()
      await approve()
      expect(planCalls(f, 'plan.decide')).toEqual([
        [
          'plan.decide',
          { session_id: 'session-1', plan_id: 'immutable-plan', revision: 3, intent: 'approve', feedback: '' }
        ]
      ])
      expect(planCalls(f, 'prompt.submit')).toHaveLength(0)
    })
  })

  it('a pointer captured before a revision edit cannot approve the new revision', async () => {
    await withApp(async f => {
      await f.open()
      const stale = f.click('approve')
      await f.click('edit-plan')()
      await paint()
      await f.edit('# Changed\nNew bytes')
      await f.click('refine')()
      await paint()
      await stale()
      await paint()
      expect(planCalls(f, 'plan.decide')).toHaveLength(0)
      expect(f.nodes().some(n => n.props.key === 'approve')).toBe(true)
    })
  })

  it('session changes and replaced sheets reject captured pointers', async () => {
    await withApp(async f => {
      await f.open()
      const stale = f.click('approve')
      await f.open()
      await stale()
      const current = f.click('approve')
      f.app.sid = 'session-2'
      await current()
      expect(planCalls(f, 'plan.decide')).toHaveLength(0)
    })
  })

  it('backend-stale decisions keep the review and expose the error', async () => {
    await withApp(async f => {
      await f.open()
      f.status({ ...initial(), plan: { ...initial().plan!, revision: 9 } })
      await f.click('approve')()
      await paint()
      expect(f.nodes().find(n => n.props.key === 'error')?.props.text).toContain('Plan changed')
      expect(f.app.composer.text).toBe('hidden draft 🦉')
    })
  })

  it.each([false, true])(
    'empty/interrupted or generating status has no decision controls (generating=%s)',
    async generating => {
      await withApp(async f => {
        f.status({ enabled: true, generating, plan: null })
        await f.open()
        expect(f.nodes().some(n => n.props.key === 'approve' || n.props.key === 'refine')).toBe(false)
        expect(f.nodes().find(n => n.props.key === 'authority')?.props.text).toContain(
          generating ? 'Generating' : 'No authoritative plan'
        )
      })
    }
  )

  it('external editor round-trip applies a revision-bound edit and rejects stale closure results', async () => {
    await withApp(async f => {
      const edit = vi.spyOn(editor, 'editTextExternal').mockResolvedValue('# External\nEdited')
      await f.open()
      await f.click('external-editor')()
      await paint()
      expect(edit).toHaveBeenCalledWith(initial().plan?.text)
      expect(f.request).toHaveBeenCalledWith('plan.edit', {
        session_id: 'session-1',
        plan_id: 'immutable-plan',
        revision: 3,
        text: '# External\nEdited'
      })

      let finish: (text: string) => void = () => {
        throw new Error('Editor not started')
      }

      edit.mockImplementation(
        () =>
          new Promise(resolve => {
            finish = resolve
          })
      )
      await f.click('external-editor')()
      await paint()
      await f.click('close')()
      await paint()
      finish('# Stale\nNot applied')
      await paint()
      expect(planCalls(f, 'plan.edit')).toHaveLength(1)
      expect(f.app.composer.text).toBe('hidden draft 🦉')
    })
  })

  it('hidden composer native edits, paste and send cannot change or submit its draft', async () => {
    await withApp(async f => {
      await f.open()
      await f.press('\x1b[200~not a draft\x1b[201~')
      await f.press('\r')
      await f.surface.dispatch({
        ev: 'edit',
        id: INPUT_ID,
        sf: 'hermes',
        raw: {},
        from: 0,
        to: 0,
        text: 'hidden',
        cursor: 6,
        len: f.app.composer.text.length
      })?.()
      expect(f.app.composer.text).toBe('hidden draft 🦉')
      expect(planCalls(f, 'prompt.submit')).toHaveLength(0)
    })
  })
})
