import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import type { ServerRequest } from '@hermes/shared/json-rpc-channel'
import { Session, type Surface, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-clarify-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = '0'

  return { home, previous, splash }
})

const tick = () => new Promise<void>(resolve => setImmediate(resolve))
const altH = '\x1b[104;3u'
const enter = '\x1b[13u'
const paste = (text: string) => `\x1b[200~${text}\x1b[201~`
const views = new WeakMap<Surface, View>()
const png = 'data:image/png;base64,iVBORw0KGgo='

function nodes(surface: Surface) {
  const all = views.get(surface)?.regions.flatMap(region => region?.children ?? []) ?? []

  for (let i = 0; i < all.length; i++) {
    all.push(...all[i]!.children)
  }

  return all
}

function target(surface: Surface, key: string) {
  const node =
    nodes(surface).find(n => (key === 'input' ? n.props.role === 'omp.ask.note' : n.props.key === key)) ??
    nodes(surface).find(n => n.props.key === key)

  if (!node) {
    throw new Error(`Missing node: ${key}`)
  }

  return node
}

function click(surface: Surface, key: string) {
  const handler = surface.dispatch({ act: 'click', ev: 'action', id: target(surface, key).id, raw: {}, sf: 'hermes' })

  if (!handler) {
    throw new Error(`Missing action: ${key}`)
  }

  return handler
}

async function withApp(
  run: (h: {
    app: App
    gw: GatewayClient
    surface: Surface
    answers: unknown[]
    ask(id: string, params?: Record<string, unknown>, method?: string): void
    press(bytes?: string): Promise<void>
    edit(key: string, text: string): Promise<void>
  }) => Promise<void>,
  upload: () => Promise<unknown> = async () => ({ attached: true, path: '/workspace/note.png' })
) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit(
    'data',
    `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`
  )
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()
  const answers: unknown[] = []
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    if (method === 'voice.dictate.start' || method === 'voice.dictate.stop') {
      return {}
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    if (method === 'jobs.list') {
      return { jobs: [] }
    }

    if (method === 'file.attach') {
      return upload()
    }

    if (method === 'clarify.lock') {
      return { status: 'ok', remaining: ['q1'] }
    }

    if (method === 'prompt.submit') {
      return { status: 'accepted' }
    }

    throw new Error(`Unexpected RPC: ${method} ${JSON.stringify(params)}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 's1'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)

  surface.render = view => {
    views.set(surface, View.from(view))
    render(view)
  }

  const press = async (bytes = '') => {
    input.emit('data', bytes)
    await tick()
    await tick()
  }

  try {
    await run({
      app,
      gw,
      surface,
      answers,
      press,
      ask: (id, params = {}, method = 'clarify') => {
        const req: ServerRequest = {
          id,
          method,
          params: {
            session_id: 's1',
            questions: [{ qid: 'q0', question: 'Which?', choices: ['A (Recommended)', 'B'] }],
            ...params
          },
          respond: result => {
            answers.push({ id, result })
          },
          fail: () => {
            throw new Error('Unexpected request failure')
          }
        }

        gw.emit('request', req)
      },
      edit: async (key, text) => {
        await press()
        const node = target(surface, key)
        const from = typeof node.props.text === 'string' ? node.props.text.length : 0
        await surface.dispatch({
          ev: 'edit',
          id: node.id,
          from,
          to: from,
          len: from,
          text,
          cursor: from + text.length,
          raw: {},
          sf: 'hermes'
        })?.()
        await press()
      }
    })
  } finally {
    app.quit()
    await running
  }
}

afterAll(() => {
  for (const [key, value] of [
    ['HERMES_HOME', isolated.previous],
    ['HERMES_TUI_SPLASH', isolated.splash]
  ]) {
    if (value === undefined) {
      delete process.env[key!]
    } else {
      process.env[key!] = value
    }
  }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('clarify dock ownership, notes and deadlines', () => {
  it('first Escape discards dictation before clarification, including Vim and late final events', async () => {
    await withApp(async ({ app, gw, surface, ask, press, answers }) => {
      app.composer.vim.setEnabled(true)
      app.composer.set('keep draft', 4)
      app.dictation.toggle()
      await press()
      const start = vi.mocked(gw.request).mock.calls.find(([method]) => method === 'voice.dictate.start')![1]!
      const captureId = start.capture_id
      gw.emit('event', { type: 'voice.dictation', session_id: 's1', payload: {
        capture_id: captureId, state: 'recording', text: 'partial only'
      } })
      ask('during-capture')
      await press()
      expect(target(surface, 'status').props.text).toContain('Recording')
      await press('\x1b[27u')
      expect(gw.request).toHaveBeenCalledWith('voice.dictate.stop', {
        session_id: 's1', capture_id: captureId, cancel: true
      })
      expect(answers).toEqual([])
      expect(target(surface, 'question').props.text).toBe('Which?')
      expect(nodes(surface).some(n => String(n.props.role).startsWith('omp.composer.mic.recording'))).toBe(false)
      gw.emit('event', { type: 'voice.dictation', session_id: 's1', payload: {
        capture_id: captureId, state: 'idle', final: true, text: 'must be discarded'
      } })
      await press()
      expect(app.composer.text).toBe('keep draft')
      expect(app.composer.cursor).toBe(4)
      expect(app.composer.vim.mode).toBe('insert')
      await press('\x1b[27u')
      expect(answers).toEqual([{ id: 'during-capture', result: { answers: { q0: null } } }])
    })
  })

  it('renders question-named answer list and clarification-specific hint, visible and hidden', async () => {
    await withApp(async ({ surface, ask, press }) => {
      ask('named-list')
      await press()
      expect(nodes(surface).find(n => n.kind === 'list')?.props.aria).toBe('Answer choices: Which?')
      const hint = () => nodes(surface).find(n => n.props.role === 'omp.composer.hint')?.props.text
      expect(hint()).toBe('Answer question · alt+h show/hide')
      await press(altH)
      expect(hint()).toBe('Answer question · alt+h show/hide')
      expect(target(surface, 'waiting').props.text).toContain('Clarification waiting')
    })
  })

  it('docks nonmodally, hides/shows with registered Alt+H and preserves draft, choice and free text', async () => {
    await withApp(async ({ app, surface, ask, press, edit, answers }) => {
      app.composer.set('main draft', 4)
      ask('one')
      await press()
      expect(views.get(surface)?.regions[2]?.children).toHaveLength(0)
      expect(nodes(surface).some(n => n.props.value && JSON.stringify(n.props.value).includes('Recommended'))).toBe(
        true
      )
      await press('custom')
      expect(target(surface, 'answer').props.text).toBe('custom')
      const staleSubmit = click(surface, 'submit')
      await press(altH)
      staleSubmit()
      expect(answers).toEqual([])
      expect(target(surface, 'waiting').props.text).toContain('Clarification waiting')
      await edit('input', ' edited')
      await press(altH)
      expect(target(surface, 'answer').props.text).toBe('custom')
      expect(app.composer.text).toContain('edited')
      await press(enter)
      expect(answers).toEqual([{ id: 'one', result: { answers: { q0: 'custom' } } }])
    })
  })

  it('handles multiple questions, multi-select, recommended choice and skip; saves early answers', async () => {
    await withApp(async ({ ask, press, surface, gw, answers }) => {
      ask('batch', {
        questions: [
          { qid: 'q0', question: 'Pick many?', choices: ['A (Recommended)', 'B'], multi_select: true },
          { qid: 'q1', question: 'Optional?', choices: [] }
        ]
      })
      await press(' ')
      await press('\x1b[B')
      await press(' ')
      const staleSkip = click(surface, 'skip')
      await press(enter)
      staleSkip()
      expect(answers).toEqual([])
      expect(gw.request).toHaveBeenCalledWith('clarify.lock', {
        request_id: 'batch',
        question_id: 'q0',
        answer: '["A","B"]'
      })
      click(surface, 'skip')()
      await press()
      expect(answers).toEqual([{ id: 'batch', result: { answers: { q0: '["A","B"]', q1: null } } }])
    })
  })

  it('sends supported optional note/image refs, and failed upload blocks answers until removed', async () => {
    let fail = true
    await withApp(
      async ({ ask, press, edit, surface, answers, gw }) => {
        ask('notes', { supports_notes: true, supports_image_refs: true })
        await edit('input', 'because')
        await press(paste(png))
        expect(nodes(surface).some(n => n.props.text === 'upload failed')).toBe(true)
        click(surface, 'submit')()
        expect(answers).toEqual([])
        click(surface, 'remove')()
        await press()
        fail = false
        await press(paste(png))
        await press(enter)
        expect(answers).toEqual([
          {
            id: 'notes',
            result: { answers: { q0: 'A' }, notes: { q0: { text: 'because', image_paths: ['/workspace/note.png'] } } }
          }
        ])
        expect(gw.request).toHaveBeenCalledWith('file.attach', expect.objectContaining({ session_id: 's1' }))
        expect(gw.request).not.toHaveBeenCalledWith('image.attach_bytes', expect.anything())
      },
      async () => {
        if (fail) {
          throw new Error('upload failed')
        }

        return { attached: true, path: '/workspace/note.png' }
      }
    )
  })

  it('shows authoritative deadlines without idle timers; timeout/cancel revoke hidden stale callbacks', async () => {
    await withApp(async ({ ask, press, surface, gw, app, answers }) => {
      ask('timer', { deadline_at: 1800000000000 })
      await press()
      expect(target(surface, 'timer').props.text).toContain(new Date(1800000000000).toISOString())
      const stale = click(surface, 'submit')
      await press(altH)
      gw.emit('event', {
        type: 'request.cancel',
        session_id: 's1',
        payload: { id: 'timer', method: 'clarify', reason: 'timeout' }
      })
      await press()
      stale()
      expect(app.overlays).toHaveLength(0)
      expect(answers).toEqual([])
      ask('unlimited', { deadline_at: null })
      await press()
      expect(target(surface, 'timer').props.text).toContain('No time limit')
      click(surface, 'cancel')()
      expect(answers).toEqual([{ id: 'unlimited', result: {} }])
    })
  })

  it('queues asks FIFO and secret/approval preemption cannot answer or toggle the waiting ask', async () => {
    await withApp(async ({ ask, press, surface, answers, app }) => {
      ask('first')
      ask('second')
      await press()
      expect(target(surface, 'approval-queued').props.text).toContain('1 more')
      const stale = click(surface, 'submit')
      ask('secret', { env_var: 'FIXTURE' }, 'secret')
      await press(altH)
      stale()
      expect(answers).toEqual([])
      app.close(app.overlays.find(o => o.key === 'prompt:secret')!)
      ask('approval', { command: 'fixture' }, 'approval')
      await press(altH)
      stale()
      expect(answers).toEqual([])
      expect(nodes(surface).some(n => n.props.role === 'omp.editor.ask.approval')).toBe(true)
      app.close(app.overlays.find(o => o.key === 'prompt:approval')!)
      await press(enter)
      await press(enter)
      expect(answers).toEqual([
        { id: 'first', result: { answers: { q0: 'A' } } },
        { id: 'second', result: { answers: { q0: 'A' } } }
      ])
    })
  })

  it('keeps unsupported notes absent and foreign requests cannot claim this session', async () => {
    await withApp(async ({ ask, press, surface, answers }) => {
      ask('foreign', { session_id: 'other' })
      ask('legacy')
      await press()
      expect(nodes(surface).some(n => n.props.role === 'omp.ask.notes')).toBe(false)
      expect(target(surface, 'timer').props.text).toContain('not supplied')
      await press(enter)
      expect(answers).toEqual([{ id: 'legacy', result: { answers: { q0: 'A' } } }])
    })
  })

  it('restores locked answers and notes on replay, including explicitly clearing a saved note', async () => {
    await withApp(async ({ ask, press, surface, gw, answers }) => {
      ask('replay', {
        supports_notes: true,
        supports_image_refs: true,
        deadline_at: null,
        questions: [
          { qid: 'q0', question: 'Pick?', choices: ['A', 'B'] },
          { qid: 'q1', question: 'More?', choices: [] }
        ],
        answers: { q0: 'B' },
        notes: { q0: { text: 'saved', image_paths: [] } }
      })
      await press('\t')
      expect(
        nodes(surface).some(n => typeof n.props.selected === 'string' && n.props.selected.endsWith('option:1'))
      ).toBe(true)
      const note = target(surface, 'input')
      expect(note.props.text).toBe('saved')
      await surface.dispatch({
        ev: 'edit',
        id: note.id,
        from: 0,
        to: 5,
        len: 5,
        text: '',
        cursor: 0,
        raw: {},
        sf: 'hermes'
      })?.()
      click(surface, 'submit')()
      await press()
      expect(gw.request).toHaveBeenCalledWith('clarify.lock', {
        request_id: 'replay',
        question_id: 'q0',
        answer: 'B',
        note: { text: '', image_paths: [] }
      })
      click(surface, 'skip')()
      expect(answers).toEqual([
        { id: 'replay', result: { answers: { q0: 'B', q1: null }, notes: { q0: { text: '', image_paths: [] } } } }
      ])
    })
  })

  it('coalesces early answer locks and rejects a late acknowledgement after cancellation', async () => {
    const ack = Promise.withResolvers<unknown>()
    await withApp(async ({ ask, press, surface, gw, app, answers }) => {
      ask('locking', {
        questions: [
          { qid: 'q0', question: 'First?' },
          { qid: 'q1', question: 'Second?' }
        ]
      })
      await press()
      const stale = click(surface, 'submit')
      vi.mocked(gw.request).mockImplementationOnce(() => ack.promise)
      stale()
      stale()
      await press()
      expect(vi.mocked(gw.request).mock.calls.filter(([method]) => method === 'clarify.lock')).toHaveLength(1)
      gw.emit('event', {
        type: 'request.cancel',
        session_id: 's1',
        payload: { id: 'locking', method: 'clarify', reason: 'timeout' }
      })
      ack.resolve({ status: 'ok', remaining: ['q1'] })
      await press()
      expect(app.overlays).toHaveLength(0)
      expect(answers).toEqual([])
    })
  })

  it('cancelled in-flight image staging cannot resurrect the ask or pollute the composer', async () => {
    const upload = Promise.withResolvers<unknown>()
    await withApp(
      async ({ ask, press, surface, app, answers }) => {
        ask('late', { supports_notes: true, supports_image_refs: true })
        await press(paste(png))
        click(surface, 'cancel')()
        upload.resolve({ attached: true, path: '/workspace/late.png' })
        await press()
        expect(app.overlays).toHaveLength(0)
        expect(app.attachments.items).toHaveLength(0)
        expect(answers).toEqual([{ id: 'late', result: {} }])
      },
      () => upload.promise
    )
  })

  it('native composer edits while hidden remain edits, not answers', async () => {
    await withApp(async ({ app, ask, press, surface, answers, edit }) => {
      ask('draft')
      await press(altH)
      await edit('input', 'unsent draft')
      expect(app.composer.text).toBe('unsent draft')
      expect(answers).toEqual([])
      expect(target(surface, 'waiting').props.text).toContain('waiting')
      expect(INPUT_ID).toBe('dock.composer.line.input')
    })
  })
})
