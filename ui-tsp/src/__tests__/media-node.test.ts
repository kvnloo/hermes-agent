import { EventEmitter } from 'node:events'
import { rmSync } from 'node:fs'

import { Session, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, vi } from 'vitest'

import { App } from '../app.js'
import { mediaNode } from '../tern-media.js'
import { toolFoldState } from '../view/tools.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-media-'))
  const previous = process.env.HERMES_HOME
  process.env.HERMES_HOME = home

  return { home, previous }
})

const rendered = () => new Promise<void>(resolve => setImmediate(resolve))

interface ReadResult {
  path: string
  result?: Record<string, unknown>
  status?: 'done' | 'error' | 'running'
}

async function withReads(media: boolean, reads: ReadResult[], check: (nodes: Tree[]) => void) {
  const previousSplash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_TUI_SPLASH = '0'
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({
    ...tern.caps, kinds: [...tern.caps.kinds.filter(kind => kind !== 'media'), ...(media ? ['media'] : [])],
    features: [], r: 'hello', v: 1, term: 'fixture', ver: '0'
  })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'complete.slash') { return { items: [] } }

    throw new Error(`Unexpected fixture RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'media-session'
  app.info = { cwd: '/project' }
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  const render = surface.render.bind(surface)
  let latest: View | undefined

  surface.render = view => {
    latest = View.from(view)
    render(view)
  }

  try {
    for (const [index, read] of reads.entries()) {
      const payload = { tool_id: `read-${index}`, name: 'read_file', args: { path: read.path } }
      gw.emit('event', { type: 'tool.start', session_id: app.sid, payload })

      if (read.status !== 'running') {
        gw.emit('event', {
          type: 'tool.complete', session_id: app.sid,
          payload: { ...payload, result: read.result ?? {}, success: read.status !== 'error' }
        })
      }
    }

    await rendered()
    await rendered()
    const flatten = (nodes: readonly Tree[]): Tree[] => nodes.flatMap(node => [node, ...flatten(node.children)])
    check(flatten(latest?.regions.find(region => region?.id === 'main')?.children ?? []))
  } finally {
    app.quit()
    await running
    request.mockRestore()

    if (previousSplash === undefined) { delete process.env.HERMES_TUI_SPLASH }
    else { process.env.HERMES_TUI_SPLASH = previousSplash }
  }
}

afterAll(() => {
  if (isolated.previous === undefined) { delete process.env.HERMES_HOME }
  else { process.env.HERMES_HOME = isolated.previous }

  rmSync(isolated.home, { force: true, recursive: true })
})

describe('native read media', () => {
  it('preserves the pinned SDK optional revision and linked-view props', () => {
    expect(mediaNode({ path: 'a.glb', rev: 'HEAD', link: 'compare' }).toJSON()).toEqual({
      k: 'media', p: { key: 'media', path: 'a.glb', rev: 'HEAD', link: 'compare' }
    })
  })

  it('keeps a media-only read eligible for the existing tool fold action', () => {
    expect(toolFoldState({
      args: { path: 'a.pdf' }, argsText: '', context: '', id: 'read', name: 'read_file',
      startedAt: 0, status: 'done', result: {}
    }, '/project', true)).toEqual({ collapsible: true, collapsed: false })
  })

  it('emits a PDF media node only when the terminal advertises the media kind', async () => {
    await withReads(true, [{ path: 'a.pdf', result: { content: 'Extracted PDF text', mime: 'application/pdf' } }], nodes => {
      expect(nodes.find(node => node.kind === 'media')?.props.path).toBe('/project/a.pdf')
      const tool = nodes.find(node => node.kind === 'tool')
      expect(tool?.props).toMatchObject({ name: 'read', status: 'done', collapsed: false })
      expect(tool?.props.preview).toBeUndefined()
      expect(nodes.find(node => node.kind === 'code')?.props.text).toBe('Extracted PDF text')
    })
  })

  it('falls back to an image node or a file link without media capability', async () => {
    await withReads(false, [{ path: 'a.png' }, { path: 'a.pdf' }], nodes => {
      expect(nodes.filter(node => node.kind === 'media')).toHaveLength(0)
      expect(nodes.find(node => node.kind === 'image')?.props.path).toBe('/project/a.png')
      const pdf = nodes.find(node => node.kind === 'tool' && node.props.target === 'a.pdf')
      expect(pdf?.props.href).toBe('file:///project/a.pdf')
    })
  })

  it('never emits media for unknown extensions, even when a supported MIME is reported', async () => {
    await withReads(true, ['a.unknown', 'README', '.pdf'].map(path => ({ path, result: { mime: 'application/pdf' } })), nodes => {
      expect(nodes.filter(node => node.kind === 'media')).toHaveLength(0)
    })
  })

  it('serializes the SDK media wire shape without invented blob or MIME props', async () => {
    await withReads(true, [{ path: '/project/a.pdf' }], nodes => {
      expect(nodes.find(node => node.kind === 'media')?.node.toJSON()).toEqual({
        k: 'media', p: { key: 'media', path: '/project/a.pdf' }
      })
    })
  })

  it.each(['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'avif', 'pdf', 'mp4', 'webm', 'mov', 'mp3', 'wav', 'ogg', 'flac', 'glb', 'gltf', 'obj', 'usd', 'usda', 'usdc', 'usdz'])(
    'uses native media for a successful .%s read', async ext => {
      await withReads(true, [{ path: `a.${ext.toUpperCase()}` }], nodes => {
        expect(nodes.find(node => node.kind === 'media')?.props.path).toBe(`/project/a.${ext.toUpperCase()}`)
      })
    }
  )

  it.each([
    ['a.png', 'image/png; charset=binary', true],
    ['a.pdf', 'application/octet-stream', true],
    ['a.glb', 'model/gltf-binary', true],
    ['a.gltf', 'model/gltf+json', true],
    ['a.obj', 'model/obj', true],
    ['a.usdz', 'model/vnd.usdz+zip', true],
    ['a.mp4', 'video/mp4', true],
    ['a.wav', 'audio/wav', true],
    ['a.pdf', 'text/plain', false],
    ['a.png', 'application/pdf', false],
    ['a.glb', 'text/html', false]
  ])('honors the reported MIME for %s (%s)', async (path, mime, supported) => {
    await withReads(true, [{ path, result: { mime_type: mime } }], nodes => {
      expect(nodes.some(node => node.kind === 'media')).toBe(supported)
    })
  })

  it('does not preview running or failed reads, or unsafe/nonlocal paths', async () => {
    await withReads(true, [
      { path: 'loading.pdf', status: 'running' },
      { path: 'failed.pdf', status: 'error', result: { error: 'Permission denied' } },
      { path: 'https://example.org/a.pdf' },
      { path: '//example.org/a.pdf' },
      { path: 'a\u0000.pdf' }
    ], nodes => {
      expect(nodes.filter(node => node.kind === 'media' || node.kind === 'image')).toHaveLength(0)
      expect(nodes.find(node => node.props.target === 'loading.pdf')?.props.status).toBe('running')
      expect(nodes.find(node => node.props.target === 'failed.pdf')?.props).toMatchObject({ status: 'error', note: 'Permission denied' })
    })
  })
})
