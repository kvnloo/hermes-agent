import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { JobsListResult, JobSnapshot } from '@hermes/shared/gateway-events'
import type { Surface } from '@stencil-hq/tern'
import { Session, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { localCommand } from '../commands.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-jobs-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

async function rendered() {
  for (let i = 0; i < 5; i++) {
    await new Promise<void>(resolve => setImmediate(resolve))
  }
}

interface Fixture {
  jobs: JobSnapshot[]
  read?(): Promise<JobsListResult>
  cancel?(id: string): Promise<unknown>
}

const job = (id: string, extra: Partial<JobSnapshot> = {}): JobSnapshot => ({
  can_cancel: true, id, kind: 'process', owner_session_id: 'session-1', started: 123, state: 'running', title: `Build ${id}`, ...extra
})

async function withApp(fixture: Fixture, run: (h: {
  app: App
  nodes(): NonNullable<View['regions'][number]>['children']
  click(role: string): Promise<void>
  clickKey(key: string): Promise<void>
  select(id: string): Promise<void>
  requests: { method: string; params: unknown }[]
  event(type: string, sid?: string, payload?: Record<string, unknown>): Promise<void>
}) => Promise<void>) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const requests: { method: string; params: unknown }[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    requests.push({ method, params })

    const handlers: Record<string, () => unknown> = {
      'complete.slash': () => ({ items: [] }),
      'jobs.list': () => fixture.read ? fixture.read() : { jobs: structuredClone(fixture.jobs) },
      'jobs.tail': () => ({ available: true, job_id: (params as { job_id: string }).job_id, text: 'compiler output\nfinished step', truncated: false }),
      'jobs.cancel': () => fixture.cancel?.((params as { job_id: string }).job_id) ?? { accepted: true, job_id: (params as { job_id: string }).job_id }
    }

    if (!handlers[method]) {
      throw new Error(`Unexpected fixture RPC: ${method}`)
    }

    return handlers[method]()
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface: Surface = tern.surfaces[0]!
  let view = new View()
  const render = surface.render.bind(surface)

  surface.render = next => { view = View.from(next); render(next) }

  const nodes = () => {
    const collect = (children: NonNullable<typeof view.regions[number]>['children']): typeof children => children.flatMap(node => [node, ...collect(node.children)])

    return view.regions.flatMap(region => region ? collect(region.children) : [])
  }

  const clickNode = async (node: ReturnType<typeof nodes>[number] | undefined) => {
    expect(node, 'expected a native action in the surface tree').toBeDefined()
    await surface.dispatch({ act: 'click', ev: 'action', id: node!.id, raw: {}, sf: 'hermes' })?.()
    await rendered()
  }

  try {
    await run({
      app, nodes, requests,
      click: role => clickNode(nodes().find(node => node.props.role === role)),
      clickKey: key => clickNode(nodes().findLast(node => node.props.key === key)),
      event: async (type, sid = app.sid ?? '', payload = {}) => {
        gw.emit('event', { payload, session_id: sid, type })
        await rendered()
      },
      select: async id => {
        const list = nodes().find(node => node.props.role === 'omp.jobs.list')!
        await surface.dispatch({ ev: 'select', id: list.id, item: `${list.id}.${id}`, raw: {}, sf: 'hermes' })?.()
        await rendered()
      }
    })
  } finally {
    vi.useRealTimers()
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

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('background jobs sheet', () => {
  it('opens through /jobs and lists owned processes and subagents with live output', async () => {
    await withApp({ jobs: [job('build'), job('child', { kind: 'subagent', parent_id: 'build' }), job('foreign', { owner_session_id: 'other' })] }, async h => {
      await localCommand('jobs')!.run(h.app, '')
      await rendered()
      const rows = h.nodes().filter(node => node.props.role === 'omp.jobs.item')
      expect(rows.map(node => node.props.key)).toEqual(['build', 'child'])
      expect(h.nodes().some(node => node.props.text === 'compiler output\nfinished step')).toBe(true)
      expect(h.requests.find(request => request.method === 'jobs.tail')?.params).toEqual({ job_id: 'build', lines: 100, session_id: 'session-1' })
      await h.select('child')
      expect(h.requests.filter(request => request.method === 'jobs.tail').at(-1)?.params).toMatchObject({ job_id: 'child' })
    })
  })

  it('offers Cancel only for an owned running job, confirms it, and sends the exact id once', async () => {
    const cancel = vi.fn(async () => ({ accepted: true, job_id: 'running' }))
    await withApp({ cancel, jobs: [job('done', { state: 'completed' }), job('running'), job('foreign', { owner_session_id: 'other' })] }, async h => {
      h.app.jobs.show()
      await rendered()
      expect(h.nodes().some(node => node.props.key === 'cancel')).toBe(false)
      await h.select('running')
      await h.clickKey('cancel')
      expect(cancel).not.toHaveBeenCalled()
      expect(h.nodes().some(node => node.props.text === 'Cancel this background job?')).toBe(true)
      await h.clickKey('ok')
      expect(cancel).toHaveBeenCalledExactlyOnceWith('running')
      expect(h.requests.find(request => request.method === 'jobs.cancel')?.params).toEqual({ job_id: 'running', session_id: 'session-1' })
    })
  })

  it('cancels deferred refresh immediately on close and never polls while idle', async () => {
    await withApp({ jobs: [job('build')] }, async h => {
      vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] })
      h.app.jobs.show()
      await rendered()
      const reads = () => h.requests.filter(request => request.method.startsWith('jobs.')).length
      const initial = reads()
      await vi.advanceTimersByTimeAsync(10000)
      expect(reads()).toBe(initial)
      await h.event('agent.terminal.output')
      await rendered()
      const afterEvent = reads()
      await h.event('agent.terminal.output')
      await h.clickKey('close')
      await vi.advanceTimersByTimeAsync(10000)
      await h.event('agent.terminal.output')
      expect(reads()).toBe(afterEvent)
    })
  })

  it('shows the running-job dock count, opens from its chip, and hides it at zero', async () => {
    const fixture = { jobs: [job('a'), job('b', { kind: 'subagent' }), job('done', { state: 'failed' })] }
    await withApp(fixture, async h => {
      h.app.jobs.adopt(h.app.sid)
      await rendered()
      expect(h.nodes().find(node => node.props.role === 'omp.composer.jobs')?.props.text).toBe('2 jobs')
      await h.click('omp.composer.jobs')
      expect(h.nodes().some(node => node.props.role === 'omp.jobs.list')).toBe(true)
      await h.clickKey('close')
      fixture.jobs = [job('a', { state: 'completed' }), job('done', { state: 'failed' })]
      await h.event('jobs.changed')
      expect(h.nodes().some(node => node.props.role === 'omp.composer.jobs')).toBe(false)
    })
  })

  it('keeps report notices and the running-job chip together, with independent sheet actions', async () => {
    await withApp({ jobs: [job('build')] }, async h => {
      h.app.jobs.adopt(h.app.sid)
      await rendered()
      await h.event('background.complete', undefined, { task_id: 'side-result', text: '# Build report\n\nDiagnostics retained.' })
      expect(h.nodes().find(node => node.props.role === 'omp.composer.jobs')?.props.text).toBe('1 job')
      expect(h.nodes().some(node => node.props.role === 'omp.report.notice')).toBe(true)
      expect(h.app.transcript.entries.some(entry => entry.kind === 'panel')).toBe(false)
      await h.click('omp.composer.jobs')
      expect(h.nodes().some(node => node.props.role === 'omp.jobs.list')).toBe(true)
      await h.clickKey('close')
      await h.click('omp.report.view')
      expect(h.app.overlays.at(-1)?.key).toBe('report')
      expect(h.nodes().some(node => node.props.text === '# Build report\n\nDiagnostics retained.')).toBe(true)
      expect(h.nodes().find(node => node.props.role === 'omp.composer.jobs')?.props.text).toBe('1 job')
    })
  })

  it('ignores foreign events and drops a late load when the session changes', async () => {
    const late = Promise.withResolvers<JobsListResult>()
    let reads = 0
    await withApp({ jobs: [], read: async () => ++reads === 1 ? late.promise : { jobs: [job('new', { owner_session_id: 'session-2' })] } }, async h => {
      h.app.jobs.show()
      await h.event('tool.complete', 'foreign')
      expect(reads).toBe(1)
      h.app.sid = 'session-2'
      h.app.jobs.adopt('session-2')
      late.resolve({ jobs: [job('old')] })
      await rendered()
      h.app.jobs.show()
      await rendered()
      expect(h.nodes().some(node => node.props.key === 'old')).toBe(false)
      expect(h.app.jobs.count).toBe(1)
    })
  })

  it('does not tail or schedule work when an outstanding list completes after close', async () => {
    const late = Promise.withResolvers<JobsListResult>()
    await withApp({ jobs: [], read: async () => late.promise }, async h => {
      vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] })
      h.app.jobs.show()
      await rendered()
      await h.event('agent.terminal.output')
      h.app.close(h.app.jobs)
      const count = h.requests.length
      late.resolve({ jobs: [job('build')] })
      await rendered()
      await vi.advanceTimersByTimeAsync(10000)
      expect(h.requests).toHaveLength(count)
      expect(h.requests.some(request => request.method === 'jobs.tail')).toBe(false)
    })
  })

  it('shows cancellation failures without hiding the still-running job', async () => {
    await withApp({ jobs: [job('build')], cancel: async () => { throw new Error('Job still running') } }, async h => {
      h.app.jobs.show()
      await rendered()
      await h.clickKey('cancel')
      await h.clickKey('ok')
      expect(h.nodes().some(node => node.props.text === 'Job still running')).toBe(true)
      expect(h.app.jobs.count).toBe(1)
    })
  })
  it('shows truthful status tones for queued, failed, completed and cancelled jobs', async () => {
    const cases = [
      { id: 'queued', state: 'queued', tone: 'warning' },
      { id: 'pending', state: 'pending', tone: 'warning' },
      { id: 'failed', state: 'failed', tone: 'error' },
      { id: 'completed', state: 'completed', tone: 'success' },
      { id: 'cancelled', state: 'cancelled', tone: 'muted' },
      { id: 'running', state: 'running', tone: undefined }
    ] as const

    await withApp({ jobs: cases.map(({ id, state }) => job(id, { state })) }, async h => {
      h.app.jobs.show()
      await rendered()

      for (const { id, state, tone } of cases) {
        await h.select(id)
        const status = h.nodes().find(node => node.props.role === 'omp.jobs.state')
        expect(status?.props.text).toBe(state)
        expect(status?.props.tone).toBe(tone)
      }

      expect(h.app.jobs.count).toBe(3)
      expect(h.requests.some(request => request.method === 'jobs.cancel')).toBe(false)
    })
  })
})
