import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'
import { openModelPicker } from '../overlays/models.js'
import { openSessionPicker } from '../overlays/sessions.js'
const isolated = await vi.hoisted(async () => {
  // History binds its home at module load, before the App constructor runs.
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-overlay-ownership-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))
const flush = async () => {
  await rendered()
  await rendered()
}
const nativeViews = new WeakMap<Surface, View>()

function mockRequests(
  gw: GatewayClient,
  respond: (method: string, params: Record<string, unknown>) => unknown | Promise<unknown>
) {
  const request = vi.fn(async (method: string, params: Record<string, unknown> = {}) => respond(method, params))
  gw.request = request as unknown as GatewayClient['request']

  return request
}

function sendText(surface: Surface, text: string) {
  const handler = surface.dispatch({ ev: 'send', id: INPUT_ID, raw: {}, sf: 'hermes', text })

  if (!handler) {
    throw new Error('The composer fixture did not install its send handler')
  }

  handler()
}

function denyEvent(surface: Surface, id: string) {
  const key = `prompt:${id}`

  const root = nativeViews.get(surface)?.regions[2]?.children.find(node => {
    const nodeKey = node.props.key

    return typeof nodeKey === 'string' && (nodeKey === key || nodeKey.startsWith(`${key}:`))
  })

  if (!root) {
    throw new Error('The approval fixture did not render its native root')
  }

  return { act: 'click', ev: 'action', id: `${root.id}.body.actions.deny`, raw: {}, sf: 'hermes' } as const
}

function approval(id: string, sessionId = 'session-1') {
  const replies: unknown[] = []
  const failures: { code: number; message: string }[] = []

  const req: ServerRequest = {
    fail: (code, message) => { failures.push({ code, message }) },
    id,
    method: 'approval',
    params: { command: 'printf fixture', request_id: `approval-${id}`, session_id: sessionId },
    respond: value => { replies.push(value) }
  }

  return { failures, replies, req }
}

function deny(surface: Surface, id: string) {
  const handler = surface.dispatch(denyEvent(surface, id))

  if (!handler) {
    throw new Error('The approval fixture did not install its deny action')
  }

  return handler
}

async function withApp(run: (app: App, gw: GatewayClient, surface: Surface) => Promise<void>) {
  const tern = new Session(new EventEmitter(), { write() {} }, { exitHooks: false, record: '' })
  const gw = new GatewayClient()
  const app = new App(tern, gw, 'test')
  app.sid = 'session-1'
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)

  surface.render = view => {
    nativeViews.set(surface, View.from(view))
    render(view)
  }

  try {
    await run(app, gw, surface)
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

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('native overlay ownership', () => {
  it('does not answer a withdrawn approval from its retained native view', async () => {
    await withApp(async (app, gw, surface) => {
      const pending = approval('first')
      gw.emit('request', pending.req)
      await rendered()
      gw.emit('event', { payload: { request_ids: ['approval-first'] }, session_id: 'session-1', type: 'approval.cancelled' })

      // Tern can still dispatch from the last rendered view before the next render.
      await deny(surface, 'first')()
      expect(pending.replies).toEqual([])
      expect(app.overlays).toEqual([])
    })
  })

  it('rejects a queued callback after a same-key prompt replacement', async () => {
    await withApp(async (app, gw, surface) => {
      const old = approval('same')
      gw.emit('request', old.req)
      await rendered()
      const stale = deny(surface, 'same')
      const next = approval('same')
      gw.emit('request', next.req)
      await rendered()

      await stale()
      expect(old.replies).toEqual([])
      expect(next.replies).toEqual([])
      expect(app.overlays).toHaveLength(1)
      await deny(surface, 'same')()
      expect(next.replies).toEqual([{ choice: 'deny' }])
      expect(app.overlays).toEqual([])
    })
  })

  it('keeps a covered prompt pending until it owns the top layer again', async () => {
    await withApp(async (_app, gw, surface) => {
      const lower = approval('lower')
      gw.emit('request', lower.req)
      await rendered()
      const lowerAction = deny(surface, 'lower')
      const upper = approval('upper')
      gw.emit('request', upper.req)
      await rendered()

      await lowerAction()
      expect(lower.replies).toEqual([])
      await deny(surface, 'upper')()
      expect(upper.replies).toEqual([{ choice: 'deny' }])
      await lowerAction()
      expect(lower.replies).toEqual([{ choice: 'deny' }])
    })
  })

  it('rejects an old native id after a same-key replacement render', async () => {
    await withApp(async (_app, gw, surface) => {
      const old = approval('same')
      gw.emit('request', old.req)
      await rendered()
      const oldEvent = denyEvent(surface, 'same')
      const next = approval('same')
      gw.emit('request', next.req)
      await rendered()

      // Native input can arrive from the previous painted view while credits are blocked.
      await surface.dispatch(oldEvent)?.()
      expect(old.replies).toEqual([])
      expect(next.replies).toEqual([])
      await deny(surface, 'same')()
      expect(next.replies).toEqual([{ choice: 'deny' }])
    })
  })

  it('answers only once when two native callbacks were queued before close', async () => {
    await withApp(async (_app, gw, surface) => {
      const pending = approval('first')
      gw.emit('request', pending.req)
      await rendered()
      const first = deny(surface, 'first')
      const second = deny(surface, 'first')

      await first()
      await second()
      expect(pending.replies).toEqual([{ choice: 'deny' }])
    })
  })
  it('does not submit a late slash send to a replacement session', async () => {
    await withApp(async (app, gw, surface) => {
      const slash = Promise.withResolvers<unknown>()
      const request = mockRequests(gw, method => {
        if (method === 'slash.exec') {
          return slash.promise
        }

        if (method === 'session.resume') {
          return { info: { stored_session_id: 'stored-new' }, messages: [], running: false, session_id: 'new' }
        }

        return {}
      })

      sendText(surface, '/prompt fixture')
      await app.resume('stored-new')
      slash.resolve({ message: 'prompt created for OLD session', type: 'send' })
      await flush()

      expect(request).not.toHaveBeenCalledWith('prompt.submit', expect.objectContaining({ session_id: 'new' }))
      expect(app.transcript.entries.some(entry => entry.kind === 'user' && entry.text === 'prompt created for OLD session')).toBe(
        false
      )
    })
  })

  it('drops stale slash output, warnings and failures after a session switch', async () => {
    await withApp(async (app, gw, surface) => {
      const output = Promise.withResolvers<unknown>()
      const failure = Promise.withResolvers<unknown>()
      const request = mockRequests(gw, (method, params) => {
        if (method === 'slash.exec') {
          return params.command === 'old-output' ? output.promise : failure.promise
        }

        if (method === 'session.resume') {
          return { info: { stored_session_id: 'stored-new' }, messages: [], running: false, session_id: 'new' }
        }

        return {}
      })

      sendText(surface, '/old-output')
      sendText(surface, '/old-failure')
      await app.resume('stored-new')
      output.resolve({ output: 'old command output', warning: 'old command warning' })
      failure.reject(new Error('old command failure'))
      await flush()

      expect(request).not.toHaveBeenCalledWith('command.dispatch', expect.anything())
      expect(
        app.transcript.entries.some(
          entry =>
            (entry.kind === 'panel' && entry.text === 'old command output') ||
            (entry.kind === 'notice' && ['old command warning', 'old command failure'].includes(entry.text))
        )
      ).toBe(false)
    })
  })

  it('dispatches skill and bundle payloads without exposing expanded prompt bodies', async () => {
    await withApp(async (app, gw, surface) => {
      const skillBody = 'Expanded private skill instructions'
      const bundleBody = 'Expanded bundle instructions'
      const request = mockRequests(gw, (method, params) => {
        if (method === 'slash.exec' && params.command === 'example-skill --fast') {
          throw Object.assign(new Error('skill command: use command.dispatch for /example-skill'), { code: 4018 })
        }

        if (method === 'slash.exec') {
          return { display: '/bundle deploy', message: bundleBody, notice: 'Bundle dispatched', type: 'send' }
        }

        if (method === 'command.dispatch') {
          return { display: '/example-skill --fast', message: skillBody, name: 'example-skill', type: 'skill' }
        }

        if (method === 'prompt.submit') {
          return { user_row_id: 42 }
        }

        return {}
      })

      sendText(surface, '/example-skill --fast')
      await flush()
      gw.emit('event', { payload: { status: 'complete', text: 'skill answer' }, session_id: 'session-1', type: 'message.complete' })
      await flush()
      sendText(surface, '/bundle deploy')
      await flush()
      expect(request).toHaveBeenCalledWith('command.dispatch', {
        arg: '--fast',
        name: 'example-skill',
        session_id: 'session-1'
      })
      const prompts = request.mock.calls
        .filter(([method]) => method === 'prompt.submit')
        .map(([, params]) => params?.text)
      const shown = app.transcript.entries.flatMap(entry => (entry.kind === 'user' ? [entry.text] : []))

      expect(prompts).toEqual([skillBody, bundleBody])
      expect(shown).toEqual(['/example-skill --fast', '/bundle deploy'])
      expect(JSON.stringify(app.transcript.entries)).not.toContain(skillBody)
      expect(JSON.stringify(app.transcript.entries)).not.toContain(bundleBody)
      expect(app.transcript.entries.some(entry => entry.kind === 'notice' && entry.text === 'Bundle dispatched')).toBe(true)
    })
  })

  it('does not re-dispatch commands already forwarded by slash.exec', async () => {
    await withApp(async (app, gw, surface) => {
      const request = mockRequests(gw, method => {
        if (method === 'slash.exec') {
          throw Object.assign(new Error('retry cannot safely reconstruct its source'), { code: 4018 })
        }

        return {}
      })

      sendText(surface, '/retry')
      await flush()

      expect(request).not.toHaveBeenCalledWith('command.dispatch', expect.anything())
      expect(app.transcript.entries.some(entry => entry.kind === 'notice' && entry.tone === 'error')).toBe(true)
    })
  })

  it('replays destination completion events that arrive before resume adoption', async () => {
    await withApp(async (app, gw) => {
      const resume = Promise.withResolvers<unknown>()
      mockRequests(gw, method => (method === 'session.resume' ? resume.promise : {}))
      const switching = app.resume('stored-new')

      gw.emit('event', { payload: { text: 'final output' }, session_id: 'new', type: 'message.delta' })
      gw.emit('event', { payload: { status: 'complete', text: 'final output' }, session_id: 'new', type: 'message.complete' })
      resume.resolve({
        info: { stored_session_id: 'stored-new' },
        inflight: { assistant: 'partial', streaming: true, user: 'question' },
        messages: [],
        running: true,
        session_id: 'new',
        status: 'working'
      })

      await switching
      await flush()

      expect(app.busy).toBeNull()
      const transcript = app.transcript.entries
        .flatMap(entry =>
          entry.kind === 'turn' ? entry.blocks.flatMap(block => (block.kind === 'text' ? [block.text] : [])) : []
        )
        .join('')
      expect(transcript).toContain('final output')
    })
  })

  it('withdraws held requests canceled before a resumed session is adopted', async () => {
    await withApp(async (app, gw) => {
      const resume = Promise.withResolvers<unknown>()
      mockRequests(gw, method => (method === 'session.resume' ? resume.promise : {}))
      const switching = app.resume('stored-new')
      const pending = approval('held-approval', 'new')

      gw.emit('request', pending.req)
      gw.emit('event', {
        payload: { id: 'held-approval', method: 'approval', reason: 'timeout' },
        session_id: 'new',
        type: 'request.cancel'
      })
      resume.resolve({
        info: { stored_session_id: 'stored-new' },
        messages: [],
        running: false,
        session_id: 'new',
        status: 'idle'
      })

      await switching
      await flush()

      expect(app.overlays).toEqual([])
      expect(pending.replies).toEqual([])
    })
  })

  it('does not reopen an approval canceled before its held request arrives', async () => {
    await withApp(async (app, gw) => {
      const resume = Promise.withResolvers<unknown>()
      mockRequests(gw, method => (method === 'session.resume' ? resume.promise : {}))
      const switching = app.resume('stored-new')

      gw.emit('event', {
        payload: { request_ids: ['approval-before-request'] },
        session_id: 'new',
        type: 'approval.cancelled'
      })
      gw.emit('request', {
        fail: () => { throw new Error('Canceled request must not be failed') },
        id: 'later-approval',
        method: 'approval',
        params: { command: 'printf fixture', request_id: 'approval-before-request', session_id: 'new' },
        respond: () => { throw new Error('Canceled request must not be shown') }
      } satisfies ServerRequest)
      resume.resolve({
        info: { stored_session_id: 'stored-new' },
        messages: [],
        running: false,
        session_id: 'new',
        status: 'idle'
      })

      await switching
      await flush()

      expect(app.overlays).toEqual([])
    })
  })

  it('returns switch-time prompts to the composer when resume fails instead of sending them to the previous session', async () => {
    await withApp(async (app, gw, surface) => {
      const reply = Promise.withResolvers<unknown>()
      const oldHistory = ['existing old-session prompt']

      mockRequests(gw, (method, params) => {
        if (method === 'session.resume') {
          return reply.promise
        }

        if (method === 'prompt.submit') {
          oldHistory.push(String(params.text))
        }

        return {}
      })

      const resumed = app.resume('destination').catch(() => false)

      sendText(surface, 'prompt intended for destination')
      reply.reject(new Error('Destination is unavailable'))
      await resumed
      await flush()

      expect(app.sid).toBe('session-1')
      expect(oldHistory).toEqual(['existing old-session prompt'])
      expect(app.composer.text).toBe('prompt intended for destination')
      expect(app.transcript.entries.some(entry => entry.kind === 'user')).toBe(false)
    })
  })

  it('settles an obsolete held approval without granting it after a superseding same-session resume', async () => {
    await withApp(async (app, gw) => {
      const older = Promise.withResolvers<unknown>()
      let resumes = 0
      let outcome: 'pending' | 'refused' | 'granted' = 'pending'

      mockRequests(gw, method => method === 'session.resume'
        ? ++resumes === 1 ? older.promise : { info: {}, messages: [], running: false, session_id: 'session-1' }
        : {})

      const pending = app.resume('stored')
      const { req } = approval('obsolete')

      req.fail = () => { outcome = 'refused' }
      req.respond = () => { outcome = 'granted' }
      gw.emit('request', req)
      await app.resume('stored')
      older.resolve({ info: {}, messages: [], running: false, session_id: 'session-1' })
      await pending

      expect(outcome).toBe('refused')
      expect(app.overlays).toEqual([])
    })
  })

  it('queues a delayed skill expansion behind a newer active turn without exposing its private payload', async () => {
    await withApp(async (app, gw, surface) => {
      const dispatch = Promise.withResolvers<unknown>()
      const started = Promise.withResolvers<void>()

      mockRequests(gw, method => {
        if (method === 'slash.exec') {
          started.resolve()

          return dispatch.promise
        }

        return {}
      })

      sendText(surface, '/skill')
      await started.promise
      sendText(surface, 'newer normal prompt')
      await flush()
      const active = app.busy

      dispatch.resolve({ display: '/skill', message: 'private skill instructions', name: 'skill', type: 'skill' })
      await flush()

      expect(app.busy).toBe(active)
      expect(app.transcript.entries.flatMap(entry => entry.kind === 'user' ? [entry.text] : [])).toEqual(['newer normal prompt'])
      gw.emit('event', { payload: { status: 'complete', text: 'normal answer' }, session_id: 'session-1', type: 'message.complete' })
      await flush()

      expect(app.transcript.entries.flatMap(entry => entry.kind === 'user' ? [entry.text] : [])).toEqual(['newer normal prompt', '/skill'])
      expect(app.transcript.entries.some(entry => entry.kind === 'user' && entry.text === 'private skill instructions')).toBe(false)
    })
  })

  it('does not publish an older reattach failure in a newly adopted session', async () => {
    await withApp(async (app, gw) => {
      const older = Promise.withResolvers<unknown>()
      const started = Promise.withResolvers<void>()

      mockRequests(gw, (method, params) => {
        if (method !== 'session.resume') {
          return {}
        }
        if (params.session_id === 'old-stored') {
          started.resolve()

          return older.promise
        }

        return { info: { model: 'new-owner-model' }, messages: [], running: false, session_id: 'replacement' }
      })

      app.storedSid = 'old-stored'
      gw.emit('event', { payload: {}, type: 'gateway.ready' })
      await started.promise
      await app.resume('replacement-stored')
      older.reject(new Error('Old reattach failed'))
      await flush()

      expect(app.sid).toBe('replacement')
      expect(app.transcript.entries.some(entry => entry.kind === 'notice')).toBe(false)
    })
  })

  it('does not let a late Help catalog cover a newer model picker', async () => {
    await withApp(async (app, gw, surface) => {
      const catalog = Promise.withResolvers<unknown>()
      const started = Promise.withResolvers<void>()

      mockRequests(gw, method => {
        if (method === 'commands.catalog') {
          started.resolve()

          return catalog.promise
        }

        if (method === 'model.options') {
          return { providers: [] }
        }

        return {}
      })

      sendText(surface, '/help')
      await started.promise
      openModelPicker(app)
      const picker = app.overlays.at(-1)

      catalog.resolve({ pairs: [['/help', 'Commands']], warning: 'late catalog warning' })
      await flush()

      expect(app.overlays).toEqual([picker])
      expect(app.transcript.entries.some(entry => entry.kind === 'notice')).toBe(false)
    })
  })

  it('rewinds an older loaded durable user boundary instead of the latest turn', async () => {
    await withApp(async (app, gw, surface) => {
      let history = [
        { role: 'user', row_id: 101, text: 'first' },
        { role: 'assistant', row_id: 102, text: 'first answer' },
        { role: 'user', row_id: 201, text: 'second' },
        { role: 'assistant', row_id: 202, text: 'second answer' },
        { role: 'user', row_id: 301, text: 'third' },
        { role: 'assistant', row_id: 302, text: 'third answer' }
      ]

      mockRequests(gw, (method, params) => {
        if (method === 'session.undo') {
          const target = params.row_id ?? history.findLast(row => row.role === 'user')?.row_id
          const boundary = history.findIndex(row => row.role === 'user' && row.row_id === target)

          if (boundary < 0) {
            throw new Error('The selected durable user boundary does not exist')
          }

          const removed = history.length - boundary

          history = history.slice(0, boundary)

          return { count: history.length, messages: history, removed }
        }

        return {}
      })

      app.transcript.load(history)
      app.changed()
      await rendered()
      const second = app.transcript.entries.find(entry => entry.kind === 'user' && entry.text === 'second')

      if (!second || second.kind !== 'user') {
        throw new Error('The older transcript user entry is missing')
      }

      const action = surface.dispatch({
        act: 'click',
        ev: 'action',
        id: `main.${second.id}.tools.rewind`,
        raw: {},
        sf: 'hermes'
      })

      if (!action) {
        throw new Error('The rewind row did not install its action')
      }

      action()
      await flush()

      expect(history.map(row => row.text)).toEqual(['first', 'first answer'])
      expect(app.transcript.entries.flatMap(entry => entry.kind === 'user' ? [entry.text] : [])).toEqual(['first'])
      expect(app.transcript.entries.flatMap(entry =>
        entry.kind === 'turn' ? entry.blocks.flatMap(block => block.kind === 'text' ? [block.text] : []) : []
      )).toEqual(['first answer'])
    })
  })

  it('serializes same-session prompts and events behind an exact rewind', async () => {
    await withApp(async (app, gw, surface) => {
      const undo = Promise.withResolvers<unknown>()
      const request = mockRequests(gw, method => {
        if (method === 'session.undo') {
          return undo.promise
        }

        if (method === 'prompt.submit') {
          return { user_row_id: 303 }
        }

        return {}
      })
      app.transcript.load([
        { role: 'user', row_id: 101, text: 'first' },
        { role: 'assistant', row_id: 102, text: 'first answer' },
        { role: 'user', row_id: 201, text: 'second' },
        { role: 'assistant', row_id: 202, text: 'second answer' }
      ])
      app.changed()
      await rendered()
      const first = app.transcript.entries.find(entry => entry.kind === 'user' && entry.text === 'first')

      if (!first || first.kind !== 'user') {
        throw new Error('The first transcript user entry is missing')
      }

      const rewind = () => {
        const action = surface.dispatch({
          act: 'click',
          ev: 'action',
          id: `main.${first.id}.tools.rewind`,
          raw: {},
          sf: 'hermes'
        })

        if (!action) {
          throw new Error('The rewind row did not install its action')
        }

        action()
      }

      app.busy = { label: 'Working…', since: {}, startedAt: Date.now() }
      rewind()
      expect(request).not.toHaveBeenCalledWith('session.undo', expect.anything())

      app.busy = null
      app.changed()
      await rendered()
      rewind()
      rewind()
      sendText(surface, 'new prompt')
      gw.emit('event', { payload: { message: 'newer same-session event' }, session_id: 'session-1', type: 'notice' })
      undo.resolve({
        count: 2,
        messages: [
          { role: 'user', row_id: 101, text: 'first' },
          { role: 'assistant', row_id: 102, text: 'first answer' }
        ],
        removed: 2
      })
      await flush()

      expect(request.mock.calls.filter(([method]) => method === 'session.undo')).toHaveLength(1)
      expect(request).toHaveBeenCalledWith('session.undo', { row_id: 101, session_id: 'session-1' })
      expect(request).toHaveBeenCalledWith('prompt.submit', expect.objectContaining({ text: 'new prompt' }))
      expect(app.transcript.entries.some(entry => entry.kind === 'user' && entry.text === 'second')).toBe(false)
      expect(app.transcript.entries.some(entry => entry.kind === 'user' && entry.text === 'new prompt')).toBe(true)
      expect(app.transcript.entries.some(entry => entry.kind === 'notice' && entry.text === 'newer same-session event')).toBe(
        true
      )
    })
  })

  it('rewinds an older submitted user boundary without losing earlier history', async () => {
    await withApp(async (app, gw, surface) => {
      const prior = [
        { role: 'user' as const, row_id: 101, text: 'first' },
        { role: 'assistant' as const, row_id: 102, text: 'first answer' }
      ]
      const durable = [...prior]
      let nextRowId = 301

      mockRequests(gw, (method, params) => {
        if (method === 'prompt.submit') {
          const rowId = nextRowId
          nextRowId += 100
          durable.push({ role: 'user', row_id: rowId, text: String(params.text) })

          return { user_row_id: rowId }
        }

        if (method === 'session.undo') {
          const rowId = params.row_id ?? durable.at(-1)?.row_id
          const boundary = durable.findIndex(message => message.row_id === rowId && message.role === 'user')

          if (boundary < 0) {
            throw new Error('Invalid durable rewind boundary')
          }

          const removed = durable.length - boundary
          durable.splice(boundary)

          return { count: durable.length, messages: durable.slice(), removed }
        }

        return {}
      })
      app.transcript.load(prior)
      app.changed()
      await rendered()

      sendText(surface, 'fresh prompt')
      await flush()
      gw.emit('event', { payload: { status: 'complete', text: 'answer' }, session_id: 'session-1', type: 'message.complete' })
      await flush()
      sendText(surface, 'later prompt')
      await flush()
      gw.emit('event', { payload: { status: 'complete', text: 'later answer' }, session_id: 'session-1', type: 'message.complete' })
      await flush()

      const user = app.transcript.entries.find(entry => entry.kind === 'user' && entry.text === 'fresh prompt')

      if (!user || user.kind !== 'user') {
        throw new Error('The submitted transcript user entry is missing')
      }

      const action = surface.dispatch({
        act: 'click',
        ev: 'action',
        id: `main.${user.id}.tools.rewind`,
        raw: {},
        sf: 'hermes'
      })

      if (!action) {
        throw new Error('The submitted rewind row did not install its action')
      }

      action()
      await flush()

      expect(app.transcript.entries.filter(entry => entry.kind === 'user').map(entry => entry.text)).toEqual(['first'])
      expect(durable).toEqual(prior)
    })
  })

  it.each(['approval.cancelled', 'request.cancel'] as const)(
    'withdraws held %s traffic before a superseding resume adopts the same destination',
    async kind => {
      await withApp(async (app, gw, surface) => {
        const first = Promise.withResolvers<unknown>()
        const second = Promise.withResolvers<unknown>()
        let resumes = 0

        mockRequests(gw, method => method === 'session.resume'
          ? (resumes++ === 0 ? first.promise : second.promise)
          : {})

        const oldResume = app.resume('new')
        const cancelled = approval('held', 'new')
        gw.emit('request', cancelled.req)

        if (kind === 'approval.cancelled') {
          gw.emit('event', { payload: { request_ids: ['approval-held'] }, session_id: 'new', type: kind })
        } else {
          gw.emit('event', { payload: { id: 'held', method: 'approval', reason: 'timeout' }, session_id: 'new', type: kind })
        }

        const replacement = app.resume('new')
        second.resolve({ info: { reasoning_effort: 'low' }, messages: [], running: false, session_id: 'new' })
        await replacement
        first.resolve({ info: { reasoning_effort: 'high' }, messages: [], running: false, session_id: 'new' })
        await oldResume
        await flush()

        expect(app.overlays).toEqual([])
        expect(app.info?.reasoning_effort).toBe('low')

        const fresh = approval('held', 'new')
        gw.emit('request', fresh.req)
        await rendered()
        await deny(surface, 'held')()

        expect(cancelled.replies).toEqual([])
        expect(fresh.replies).toEqual([{ choice: 'deny' }])
      })
    }
  )

  it.each(['show', 'set'] as const)('ignores an older local reasoning %s after a same-id resume', async mode => {
    await withApp(async (app, gw, surface) => {
      const reply = Promise.withResolvers<unknown>()

      mockRequests(gw, method => {
        if (method === 'config.get') {
          return mode === 'show' ? reply.promise : { key: 'reasoning', value: 'high' }
        }

        if (method === 'config.set') {
          return reply.promise
        }

        if (method === 'session.resume') {
          return { info: { reasoning_effort: 'low' }, messages: [], running: false, session_id: 'session-1' }
        }

        return {}
      })

      sendText(surface, mode === 'show' ? '/reasoning' : '/reasoning high')
      await flush()
      await app.resume('session-1')
      reply.resolve({ display: 'show', key: 'reasoning', value: 'high' })
      await flush()

      expect(app.info?.reasoning_effort).toBe('low')
      expect(app.transcript.entries.some(entry => entry.kind === 'panel')).toBe(false)
    })
  })

  it('replays same-session completion after adopting the resume snapshot', async () => {
    await withApp(async (app, gw) => {
      const reply = Promise.withResolvers<unknown>()
      mockRequests(gw, method => method === 'session.resume' ? reply.promise : {})

      const resumed = app.resume('session-1')
      gw.emit('event', { payload: { text: 'final output' }, session_id: 'session-1', type: 'message.delta' })
      gw.emit('event', { payload: { status: 'complete', text: 'final output' }, session_id: 'session-1', type: 'message.complete' })
      reply.resolve({
        info: { reasoning_effort: 'low' },
        inflight: { assistant: 'stale partial', streaming: true, user: 'question' },
        running: true,
        session_id: 'session-1'
      })
      await resumed
      await flush()

      expect(app.busy).toBeNull()
      expect(app.transcript.entries.flatMap(entry =>
        entry.kind === 'turn' ? entry.blocks.flatMap(block => block.kind === 'text' ? [block.text] : []) : []
      ).join('\n')).toContain('final output')
    })
  })

  it.each(['changed', 'confirm'] as const)('ignores an older local model %s reply after a same-id resume', async outcome => {
    await withApp(async (app, gw, surface) => {
      const reply = Promise.withResolvers<unknown>()
      const started = Promise.withResolvers<void>()

      mockRequests(gw, method => {
        if (method === 'config.set') {
          started.resolve()

          return reply.promise
        }

        if (method === 'session.resume') {
          return { info: { model: 'new-owner-model' }, messages: [], running: false, session_id: 'session-1' }
        }

        return {}
      })

      sendText(surface, '/model old-model')
      await started.promise
      await app.resume('session-1')
      reply.resolve(outcome === 'confirm'
        ? { confirm_message: 'old confirmation', confirm_required: true }
        : { value: 'old-model', warning: 'old model warning' })
      await flush()

      expect(app.info?.model).toBe('new-owner-model')
      expect(app.overlays).toEqual([])
      expect(app.transcript.entries.some(entry => entry.kind === 'notice')).toBe(false)
    })
  })

  it('refuses a queued model picker activation from an older same-session generation', async () => {
    await withApp(async (app, gw, surface) => {
      let selected = ''

      mockRequests(gw, (method, params) => {
        if (method === 'model.options') {
          return { model: 'initial', provider: 'fixture', providers: [{ models: ['old-model'], name: 'Fixture', slug: 'fixture' }] }
        }

        if (method === 'config.set') {
          selected = String(params.value)

          return { value: 'old-model' }
        }

        if (method === 'session.resume') {
          return { info: { model: 'new-owner-model' }, messages: [], running: false, session_id: 'session-1' }
        }

        return {}
      })

      openModelPicker(app)
      await flush()

      const root = nativeViews.get(surface)?.regions[2]?.children.find(
        node => typeof node.props.key === 'string' && node.props.key.startsWith('models:')
      )

      if (!root) {
        throw new Error('The model picker is not rendered')
      }

      const activation = surface.dispatch({ ev: 'activate', id: root.id, item: 'fixture\told-model', raw: {}, sf: 'hermes' })

      if (!activation) {
        throw new Error('The model picker did not bind its activation')
      }

      await app.resume('session-1')
      activation()
      await flush()

      expect(app.info?.model).toBe('new-owner-model')
      expect(selected).toBe('')
    })
  })

  it('rejects an older Help result after a same-id resume', async () => {
    await withApp(async (app, gw, surface) => {
      const catalog = Promise.withResolvers<unknown>()
      const started = Promise.withResolvers<void>()

      mockRequests(gw, method => {
        if (method === 'commands.catalog') {
          started.resolve()
          return catalog.promise
        }

        if (method === 'session.resume') {
          return { info: { reasoning_effort: 'low' }, messages: [], running: false, session_id: 'session-1' }
        }

        return {}
      })

      sendText(surface, '/help')
      await started.promise
      await app.resume('session-1')
      catalog.resolve({ categories: [], pairs: [], warning: 'old catalog warning' })
      await flush()

      expect(app.overlays).toEqual([])
      expect(app.transcript.entries.some(entry => entry.kind === 'notice' && entry.text === 'old catalog warning')).toBe(false)
    })
  })

  it('shows an explicit resume failure and remains able to resume another session', async () => {
    await withApp(async (app, gw, surface) => {
      mockRequests(gw, (method, params) => {
        if (method === 'session.resume') {
          if (params.session_id === 'missing') {
            throw new Error('resume fixture missing')
          }

          return { info: { reasoning_effort: 'low' }, messages: [], running: false, session_id: 'replacement' }
        }

        return {}
      })

      sendText(surface, '/resume missing')
      await flush()

      expect(app.sid).toBe('session-1')
      expect(app.transcript.entries.some(entry => entry.kind === 'notice' && entry.text === 'resume fixture missing')).toBe(true)
      expect(await app.resume('replacement')).toBe(true)
      expect(app.sid).toBe('replacement')
    })
  })

  it('keeps the session picker open with a recoverable error when resume fails', async () => {
    await withApp(async (app, gw, surface) => {
      mockRequests(gw, method => {
        if (method === 'session.list') {
          return {
            sessions: [{ id: 'deleted', message_count: 1, preview: 'A saved prompt', started_at: 1, title: 'Deleted' }]
          }
        }

        if (method === 'session.resume') {
          throw new Error('session is no longer available')
        }

        return {}
      })
      openSessionPicker(app)
      await flush()
      const picker = app.overlays.at(-1)

      if (!picker) {
        throw new Error('The session picker did not open')
      }

      picker.onKey({ alt: false, ctrl: false, meta: false, name: 'enter', shift: false })
      await flush()

      const node = nativeViews.get(surface)?.regions[2]?.children.find(
        child => typeof child.props.key === 'string' && child.props.key.startsWith('sessions:')
      )

      expect(app.overlays).toHaveLength(1)
      expect(node?.props).toMatchObject({
        message: expect.stringContaining('session is no longer available'),
        state: 'ready'
      })
    })
  })

  it('keeps a busy-session /resume handled locally when switching is refused', async () => {
    await withApp(async (app, gw, surface) => {
      const request = mockRequests(gw, () => ({}))
      app.busy = { label: 'Working…', since: {}, startedAt: Date.now() }

      sendText(surface, '/resume unavailable')
      await flush()

      expect(request).not.toHaveBeenCalledWith('slash.exec', expect.anything())
      expect(request).not.toHaveBeenCalledWith('session.resume', expect.anything())
    })
  })
})
