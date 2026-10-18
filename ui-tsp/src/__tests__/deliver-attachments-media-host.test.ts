import { EventEmitter } from 'node:events'
import { rmSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

import { Session, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, afterEach, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { Attachments } from '../attachments.js'
import { MEDIA_CACHE_ENTRIES, MEDIA_CONNECTION_BLOBS, type MediaPath } from '../media-delivery.js'
import { readMedia } from '../read-media.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-media-host-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

vi.mock('../../assets/logo.png', () => ({ default: new Uint8Array([137, 80, 78, 71]) }))

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVmQAAAAASUVORK5CYII=', 'base64')
const response = () => ({ content_base64: png.toString('base64'), mime: 'image/png', bytes: png.length })
const tick = () => new Promise<void>(resolve => setImmediate(resolve))

async function settle() { for (let i = 0; i < 8; i++) { await tick() } }
const source = (id = 'image', host: MediaPath['host'] = 'gateway'): MediaPath => ({ kind: 'path', host, id, path: `/gateway/${id}.png`, mime: 'image/png' })

interface Options {
  remote?: boolean
  blobs?: boolean
  ssh?: boolean
  read?(): Promise<unknown>
}

async function withApp(options: Options, run: (app: App, nodes: () => Tree[], click: (text: string) => Promise<void>, blob: ReturnType<typeof vi.spyOn>, gw: GatewayClient) => Promise<void>) {
  vi.stubEnv('HERMES_TUI_SPLASH', 'off')
  vi.stubEnv('SSH_CONNECTION', options.ssh ? 'fixture ssh connection' : '')
  vi.stubEnv('SSH_CLIENT', '')
  vi.stubEnv('SSH_TTY', '')
  const input = new EventEmitter()
  const output: string[] = []
  const tern = new Session(input, { write(data: string | Uint8Array) { output.push(String(data)) } }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, features: [...tern.caps.features.filter(f => f !== 'blobs'), ...(options.blobs === false ? [] : ['blobs'])], kinds: [...tern.caps.kinds, 'media'], r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const blob = vi.spyOn(tern, 'blob')
  const gw = new GatewayClient()
  vi.spyOn(gw, 'attached', 'get').mockReturnValue(options.remote ?? true)
  vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'media.image') { return options.read ? options.read() : response() }

    if (method === 'jobs.list') { return { jobs: [] } }

    if (method === 'complete.slash') { return { items: [] } }

    if (method === 'image.detach') { return { detached: true, count: 0 } }

    if (method === 'image.attach_bytes') { return { attached: true, path: '/gateway/image.png' } }
    throw new Error(`Unexpected RPC ${method}`)
  })
  const app = new App(tern, gw, 'test')
  app.sid = 'media-session'
  app.info = { cwd: '/gateway', terminal_backend: 'local' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view: View | undefined
  const render = surface.render.bind(surface)

  surface.render = value => { view = View.from(value); render(value) }
  const flatten = (tree: Tree): Tree[] => [tree, ...tree.children.flatMap(flatten)]
  const nodes = () => view?.regions.flatMap(region => region?.children.flatMap(flatten) ?? []) ?? []

  async function click(text: string) {
    const target = nodes().find(n => typeof n.props.text === 'string' && n.props.text.includes(text))
    expect(target, `Missing action ${text}`).toBeDefined()
    const action = surface.dispatch({ ev: 'action', act: 'click', sf: 'hermes', id: target!.id, raw: {} })
    expect(action).toBeTypeOf('function')
    await action!()
    await settle()
  }

  try {
    app.transcript.user('Describe', 0, [{ id: '/gateway/image.png', path: '/gateway/image.png', name: 'Image', mime: 'image/png', bytes: png.length }])
    app.changed()
    await settle()
    // The logo uses blobs too; only count transfers made by the test journey.
    blob.mockClear()
    await run(app, nodes, click, blob, gw)
    expect(output.length).toBeGreaterThan(0)
  } finally {
    app.quit()
    await running
  }
}

afterEach(() => { vi.unstubAllEnvs(); vi.restoreAllMocks() })
afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME } else { process.env.HERMES_HOME = isolated.previous }
  rmSync(isolated.home, { recursive: true, force: true })
})

describe('attachments/media across hosts', () => {
  it('keeps the local path fast path unchanged and never reads a gateway path on the Tern host', async () => {
    await withApp({ remote: false }, async (_app, nodes, _click, blob) => {
      expect(nodes().find(n => n.kind === 'media')?.props.path).toBe('/gateway/image.png')
      expect(blob).not.toHaveBeenCalled()
    })
    await withApp({}, async (_app, nodes, click, blob, gw) => {
      expect(nodes().filter(n => (n.kind === 'media' || n.kind === 'image') && n.props.path)).toHaveLength(0)
      await click('Load image preview')
      expect(gw.request).toHaveBeenCalledWith('media.image', { session_id: 'media-session', path: '/gateway/image.png' })
      expect(blob).toHaveBeenCalledWith(png, 'image/png')
      const image = nodes().find(n => n.kind === 'image' && n.props.alt === '/gateway/image.png')
      expect(image?.props).toMatchObject({ blob: blob.mock.results[0]?.value })
      expect(image?.props.path).toBeUndefined()
    })
  })

  it('uses SDK image blobs over SSH, not remote video or 3D media paths', async () => {
    const path = join(isolated.home, 'ssh.png')
    writeFileSync(path, png)
    await withApp({ remote: false, ssh: true }, async (app, nodes, click, blob) => {
      app.transcript.load([{ role: 'user', text: `Caption\n@image:${path}`, row_id: 99 }])
      app.changed()
      await settle()
      await click('Load image preview')
      expect(blob).toHaveBeenCalledWith(png, 'image/png')
      expect(nodes().some(n => n.kind === 'media')).toBe(false)

      for (const name of ['a.mp4', 'a.glb']) {
        const preview = readMedia(name, '/compute', undefined, true, false, s => app.mediaDelivery.preview(s))
        expect(preview?.kind).toBe('text')
        expect(preview?.props.text).toContain('unavailable')
      }

      expect(readMedia('bad.png', '/', 'video/mp4', true, false)).toBeUndefined()
    })
  })

  it('delivers completed read images by exact tool identity, not a Tern-host file link', async () => {
    await withApp({}, async (app, nodes, click, blob, gw) => {
      app.transcript.clear()
      const payload = { tool_id: 'read-remote', name: 'read_file', args: { path: 'result.png' } }
      gw.emit('event', { type: 'tool.start', session_id: app.sid, payload })
      gw.emit('event', { type: 'tool.complete', session_id: app.sid, payload: { ...payload, result: { mime: 'image/png' }, success: true } })
      await settle()
      expect(nodes().find(n => n.kind === 'tool' && n.props.name === 'read')?.props.href).toBeUndefined()
      expect(nodes().some(n => n.kind === 'media' || n.kind === 'image' && n.props.path)).toBe(false)
      await click('Load image preview')
      expect(gw.request).toHaveBeenCalledWith('media.image', { session_id: 'media-session', path: '/gateway/result.png', tool_call_id: 'read-remote' })
      expect(blob).toHaveBeenCalledWith(png, 'image/png')
      expect(nodes().some(n => n.kind === 'image' && n.props.alt === '/gateway/result.png' && n.props.blob)).toBe(true)
    })
  })

  it('does not invent support without blob negotiation or for a separate compute host', async () => {
    await withApp({ blobs: false }, async (app, nodes, _click, blob, gw) => {
      expect(nodes().some(n => String(n.props.text).includes('unavailable'))).toBe(true)
      await app.mediaDelivery.load(source())
      expect(blob).not.toHaveBeenCalled()
      expect(gw.request).not.toHaveBeenCalledWith('media.image', expect.anything())
    })
    await withApp({}, async (app, _nodes, _click, blob) => {
      const descriptor = source('compute', 'compute')
      expect(app.mediaDelivery.preview(descriptor).props.text).toContain('unavailable')
      await app.mediaDelivery.load(descriptor)
      expect(blob).not.toHaveBeenCalled()
    })
  })

  it.each(['denied', 'stale'])('shows %s reads and retries without losing the durable attachment identity', async reason => {
    let attempt = 0
    await withApp({ read: async () => { if (++attempt === 1) { throw new Error(reason) };

 return response() } }, async (app, nodes, click, blob) => {
      await click('Load image preview')
      expect(nodes().some(n => String(n.props.text).includes(reason))).toBe(true)
      expect(blob).not.toHaveBeenCalled()
      await click('Retry preview')
      expect(blob).toHaveBeenCalledTimes(1)
      const user = app.transcript.entries.find(e => e.kind === 'user')
      expect(user?.kind === 'user' && user.attachments?.[0]?.id).toBe('/gateway/image.png')
    })
  })

  it('rejects MIME/magic mismatch and oversized bytes before SDK upload', async () => {
    await withApp({ read: async () => ({ ...response(), mime: 'image/jpeg' }) }, async (_app, nodes, click, blob) => {
      await click('Load image preview')
      expect(nodes().some(n => String(n.props.text).includes('mismatch'))).toBe(true)
      expect(blob).not.toHaveBeenCalled()
    })
    await withApp({ read: async () => ({ content_base64: 'A'.repeat(28 * 1024 * 1024), mime: 'image/png', bytes: 0 }) }, async (_app, nodes, click, blob) => {
      await click('Load image preview')
      expect(nodes().some(n => String(n.props.text).includes('oversized'))).toBe(true)
      expect(blob).not.toHaveBeenCalled()
    })
  })

  it('restores persisted attachment IDs and drops only trailing canonical directives', async () => {
    await withApp({}, async (app, nodes, click, blob) => {
      app.transcript.load([{ role: 'user', row_id: 123, text: 'Caption\n@image:`/gateway/image with spaces.png`' }])
      app.changed()
      await settle()
      expect(app.transcript.entries.find(e => e.kind === 'user')).toMatchObject({ rowId: 123, text: 'Caption', attachments: [{ id: '/gateway/image with spaces.png' }] })
      await click('Load image preview')
      expect(blob).toHaveBeenCalledTimes(1)
      expect(nodes().some(n => n.kind === 'image' && n.props.blob)).toBe(true)
    })
  })

  it('bounds cache metadata, evicts on demand, and caps the SDK connection ID lifetime', async () => {
    await withApp({}, async (app, _nodes, _click, blob) => {
      const first = source('0')
      await app.mediaDelivery.load(first)

      for (let i = 1; i <= MEDIA_CACHE_ENTRIES; i++) { await app.mediaDelivery.load(source(String(i))) }
      expect(app.mediaDelivery.preview(first).kind).toBe('text')
      expect(app.mediaDelivery.preview(source(String(MEDIA_CACHE_ENTRIES))).kind).toBe('image')

      for (let i = MEDIA_CACHE_ENTRIES + 1; i < MEDIA_CONNECTION_BLOBS; i++) { await app.mediaDelivery.load(source(String(i))) }
      app.mediaDelivery.clear()
      await app.mediaDelivery.load(source('one-too-many'))
      expect(blob).toHaveBeenCalledTimes(MEDIA_CONNECTION_BLOBS)
      expect(app.mediaDelivery.preview(source('one-too-many')).props.text).toContain('budget reached')
    })
  })

  it('discards pending reads after removal, session change, and quit; no retry timer', async () => {
    for (const action of ['remove', 'session', 'quit']) {
      const gate = Promise.withResolvers<unknown>()
      await withApp({ read: () => gate.promise }, async (app, _nodes, _click, blob) => {
        const descriptor = source()
        const loading = app.mediaDelivery.load(descriptor)
        await settle()

        if (action === 'remove') { app.mediaDelivery.forget(descriptor) }

        if (action === 'session') { app.sid = 'different'; app.mediaDelivery.clear() }

        if (action === 'quit') { app.quit() }
        gate.resolve(response())
        await loading
        expect(blob).not.toHaveBeenCalled()
      })
    }
  })

  it('keeps removed in-flight uploads inside the composer admission budget', async () => {
    const gw = new GatewayClient()
    const gate = Promise.withResolvers<unknown>()

    const request = vi.spyOn(gw, 'request').mockImplementation(async method => method === 'image.detach'
      ? { detached: true, count: 0 } : gate.promise)

    const notice = vi.fn()
    const attachments = new Attachments(gw, () => {}, notice)
    const pending: Promise<void>[] = []

    for (let i = 0; i < 8; i++) {
      const data = Buffer.concat([png, Buffer.from([i])]).toString('base64')
      pending.push(attachments.add({ data: `data:image/png;base64,${data}`, name: `image ${i}` }, 'owned'))
      await attachments.remove(attachments.items[0]!.id)
    }

    await attachments.add({ data: `data:image/png;base64,${png.toString('base64')}`, name: 'overflow' }, 'owned')
    expect(request.mock.calls.filter(([method]) => method === 'image.attach_bytes')).toHaveLength(8)
    expect(notice).toHaveBeenCalledWith(expect.stringContaining('budget reached'))
    gate.resolve({ attached: true, path: '/gateway/late.png' })
    await Promise.all(pending)
    expect(attachments.items).toHaveLength(0)
    expect(request.mock.calls.filter(([method]) => method === 'image.detach')).toHaveLength(8)
  })

  it('uploads local files as bytes to a remote gateway, releases retained payloads, and bounds composer refs', async () => {
    const path = join(isolated.home, 'misnamed.jpg')
    writeFileSync(path, png)
    await withApp({}, async (_app, _nodes, _click, _blob, gw) => {
      const attachments = new Attachments(gw, () => {}, () => {})
      await attachments.add({ path, name: 'wrong suffix' }, 'media-session')
      expect(gw.request).toHaveBeenCalledWith('image.attach_bytes', expect.objectContaining({ content_base64: png.toString('base64'), filename: 'pasted.png' }))
      expect(attachments.items[0]?.source).toMatchObject({ host: 'gateway', path: '/gateway/image.png' })
      const data = `data:image/png;base64,${png.toString('base64')}`
      await attachments.add({ data, name: 'Pasted' }, 'media-session')
      await attachments.add({ data, name: 'Pasted again' }, 'media-session')
      expect(attachments.items).toHaveLength(2)

      for (let i = 0; i < 10; i++) { await attachments.add({ path: `/missing/${i}.png`, name: `${i}` }, 'media-session') }
      expect(attachments.items).toHaveLength(8)
      await attachments.remove(attachments.items[0]!.id)
      expect(gw.request).toHaveBeenCalledWith('image.detach', { session_id: 'media-session', path: '/gateway/image.png' })
    })
  })
})
