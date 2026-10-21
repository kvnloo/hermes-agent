import { EventEmitter } from 'node:events'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import type { AttachedImageResult } from '@hermes/shared/gateway-events'
import { Session, type Surface, type Tree, View } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'
import { afterAll, describe, expect, it, type MockInstance, vi } from 'vitest'

import { App, INPUT_ID } from '../app.js'

import { acknowledgeFrames } from './helpers/paint.js'

const isolated = await vi.hoisted(async () => {
  const { mkdtempSync } = await import('node:fs')
  const { tmpdir } = await import('node:os')
  const { join } = await import('node:path')
  const home = mkdtempSync(join(tmpdir(), 'hermes-image-attach-'))
  const previous = process.env.HERMES_HOME
  const splash = process.env.HERMES_TUI_SPLASH
  process.env.HERMES_HOME = home
  process.env.HERMES_TUI_SPLASH = 'off'

  return { home, previous, splash }
})

const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aVmQAAAAASUVORK5CYII=', 'base64')
const tick = () => new Promise<void>(resolve => setImmediate(resolve))

async function settle() {
  for (let i = 0; i < 8; i++) {
    await tick()
  }
}

interface Fixture {
  app: App
  surface: Surface
  request: MockInstance<GatewayClient['request']>
  nodes(region?: string): Tree[]
  event(raw: Record<string, unknown>): Promise<void>
  paste(text: string): Promise<void>
  click(key: string): Promise<void>
  send(text?: string): Promise<void>
}

async function withApp(attach: () => Promise<AttachedImageResult>, run: (fixture: Fixture) => Promise<void>, media = true) {
  const input = new EventEmitter()
  const tern = new Session(input, { write() {} }, { exitHooks: false, record: '' })
  const connecting = tern.handshake()
  input.emit('data', `\x1b_tsp;r;${JSON.stringify({ ...tern.caps, kinds: [...tern.caps.kinds, ...(media ? ['media'] : [])], r: 'hello', v: 1, term: 'fixture', ver: '0' })}\x1b\\`)
  expect(await connecting).toBe(true)
  const gw = new GatewayClient()

  const request = vi.spyOn(gw, 'request').mockImplementation(async method => {
    if (method === 'image.attach' || method === 'image.attach_bytes') {
      return attach()
    }

    if (method === 'image.detach') {
      return { detached: true, count: 0 }
    }

    if (method === 'prompt.submit') {
      return { status: 'streaming', user_row_id: 42 }
    }

    if (method === 'complete.slash') {
      return { items: [] }
    }

    throw new Error(`Unexpected RPC: ${method}`)
  })

  const app = new App(tern, gw, 'test')
  app.sid = 'image-session'
  acknowledgeFrames(tern)
  const running = app.run()
  const surface = tern.surfaces[0]!
  let view: View | undefined
  const render = surface.render.bind(surface)

  surface.render = value => { view = View.from(value); render(value) }

  function flatten(tree: Tree): Tree[] {
    return [tree, ...tree.children.flatMap(flatten)]
  }

  const fixture: Fixture = {
    app, surface, request,
    nodes: region => view?.regions.filter(r => r && (!region || r.id === region)).flatMap(r => r?.children.flatMap(flatten) ?? []) ?? [],
    event: async raw => {
      input.emit('data', `\x1b_tsp;e;${JSON.stringify({ sf: 'hermes', ...raw })}\x1b\\`)
      await settle()
    },
    paste: async text => {
      input.emit('data', `\x1b[200~${text}\x1b[201~`)
      await settle()
    },
    click: async key => {
      const target = fixture.nodes('dock').find(n => n.props.key === key)
      expect(target, `Missing ${key} action`).toBeDefined()
      const action = surface.dispatch({ ev: 'action', act: 'click', sf: 'hermes', id: target!.id, raw: {} })
      expect(action).toBeTypeOf('function')
      await action!()
      await settle()
    },
    send: async (text = 'Describe this image') => {
      const action = surface.dispatch({ ev: 'send', sf: 'hermes', id: INPUT_ID, text, raw: {} })
      expect(action).toBeTypeOf('function')
      await action!()
      await settle()
    }
  }

  try {
    await run(fixture)
  } finally {
    app.quit()
    await running
  }
}

function labels(f: Fixture, region = 'dock') {
  return f.nodes(region).map(n => n.props.text).filter(t => typeof t === 'string').join('\n')
}

it('a two-file quoted drop renders two attachment chips and sends both paths, never literal draft text', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'hermes-two-drop-'))
  const paths = [join(dir, 'first image.png'), join(dir, 'second image.png')]
  paths.forEach(path => writeFileSync(path, png))
  let serial = 0

  try {
    await withApp(async () => ({ attached: true, path: `/confirmed/${++serial}.png`, bytes: png.length }), async f => {
      await f.paste(paths.map(path => `'${path}'`).join(' '))

      for (let i = 0; i < 30 && f.app.attachments.items.some(item => item.status === 'pending'); i++) { await new Promise(resolve => setTimeout(resolve, 5)); await settle() }
      expect(labels(f)).toContain('first image.png')
      expect(labels(f)).toContain('second image.png')
      expect(f.app.composer.text).toBe('')
      await f.send('Describe both')
      expect(f.request).toHaveBeenCalledWith('prompt.submit', { session_id: 'image-session', text: 'Describe both', image_paths: ['/confirmed/1.png', '/confirmed/2.png'] })
    })
  } finally { rmSync(dir, { recursive: true, force: true }) }
})

const confirm = async (): Promise<AttachedImageResult> => ({ attached: true, path: '/confirmed/pasted.png', bytes: png.length })
const pastePng = (f: Fixture) => f.event({ ev: 'paste', data: png.toString('base64'), mime: 'image/png', name: 'Clipboard shot' })

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

describe('image paste and attachment chips', () => {
  it('paints pending then attached after the gateway confirms a pasted PNG', async () => {
    const gate = Promise.withResolvers<AttachedImageResult>()
    await withApp(() => gate.promise, async f => {
      await pastePng(f)
      expect(labels(f)).toContain('Clipboard shot')
      expect(labels(f)).toContain(`${png.length} B · pending`)
      gate.resolve(await confirm())
      await settle()
      expect(labels(f)).toContain('attached')
      expect(f.request).toHaveBeenCalledWith('image.attach_bytes', expect.objectContaining({ content_base64: png.toString('base64'), session_id: 'image-session' }))
    })
  })

  it('× detaches the confirmed path and excludes it from the submitted ids', async () => {
    await withApp(confirm, async f => {
      await pastePng(f)
      await f.click('remove')
      expect(labels(f)).not.toContain('Clipboard shot')
      expect(f.request).toHaveBeenCalledWith('image.detach', { session_id: 'image-session', path: '/confirmed/pasted.png' })
      await f.send()
      expect(f.request).toHaveBeenCalledWith('prompt.submit', expect.objectContaining({ image_paths: [] }))
    })
  })

  it('retains a failed chip and retries the real attach RPC', async () => {
    let calls = 0
    await withApp(async () => {
      if (++calls === 1) {
        throw new Error('Upload refused')
      }

      return confirm()
    }, async f => {
      await pastePng(f)
      expect(labels(f)).toContain('failed')
      expect(labels(f)).toContain('Upload refused')
      await f.send('Keep my draft')
      expect(f.request.mock.calls.filter(([m]) => m === 'prompt.submit')).toHaveLength(0)
      await f.click('retry')
      expect(calls).toBe(2)
      expect(labels(f)).toContain('attached')
    })
  })

  it('submits confirmed ids, clears composer chips and paints user chips with native media', async () => {
    await withApp(confirm, async f => {
      await pastePng(f)
      await f.send()
      expect(f.request).toHaveBeenCalledWith('prompt.submit', { session_id: 'image-session', text: 'Describe this image', image_paths: ['/confirmed/pasted.png'] })
      expect(f.app.attachments.items).toEqual([])
      expect(labels(f)).not.toContain('Clipboard shot')
      expect(labels(f, 'main')).toContain('Clipboard shot')
      expect(f.nodes('main').find(n => n.kind === 'media')?.props.path).toBe('/confirmed/pasted.png')
      expect(f.app.transcript.entries.find(e => e.kind === 'user')).toMatchObject({ rowId: 42, attachments: [{ id: '/confirmed/pasted.png', name: 'Clipboard shot' }] })
    })
  })

  it('handles a real bracketed file drop by magic bytes, not extension, and preserves normal paste', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'hermes-drop-'))
    const path = join(dir, 'picture with spaces.png')
    writeFileSync(path, png)

    try {
      await withApp(confirm, async f => {
        await f.paste('ordinary\nmultiline text')
        expect(f.app.composer.text).toBe('ordinary\nmultiline text')
        await f.paste(`'${path}'`)
        await vi.waitFor(() => expect(f.request).toHaveBeenCalledWith('image.attach', { session_id: 'image-session', path }))
        await settle()
        expect(labels(f)).toContain('picture with spaces.png')
        await f.send()
        expect(f.nodes('main').find(n => n.kind === 'image')?.props.path).toBe('/confirmed/pasted.png')
      }, false)
    } finally {
      rmSync(dir, { force: true, recursive: true })
    }
  })

  it('rejects a forged image MIME with nonimage bytes and preserves its failed chip', async () => {
    await withApp(confirm, async f => {
      await f.event({ ev: 'drop', data: Buffer.from('not an image').toString('base64'), mime: 'image/png', name: 'fake.png' })
      expect(labels(f)).toContain('failed')
      expect(labels(f)).toContain('magic bytes')
      expect(f.request.mock.calls.filter(([m]) => m.startsWith('image.'))).toHaveLength(0)
    })
  })

  it('cleans up a removed pending upload after its late confirmation without resurrecting a chip', async () => {
    const gate = Promise.withResolvers<AttachedImageResult>()
    await withApp(() => gate.promise, async f => {
      await pastePng(f)
      await f.click('remove')
      gate.resolve(await confirm())
      await settle()
      expect(f.request).toHaveBeenCalledWith('image.detach', expect.objectContaining({ path: '/confirmed/pasted.png' }))
      expect(f.app.attachments.items).toEqual([])
      await f.send()
      expect(f.request).toHaveBeenCalledWith('prompt.submit', expect.objectContaining({ image_paths: [] }))
    })
  })

  it('uploads a renamed image using its magic-derived format and exact full bytes', async () => {
    const dir = mkdtempSync(join(tmpdir(), 'hermes-renamed-image-'))
    const path = join(dir, 'renamed.dat')
    writeFileSync(path, png)

    try {
      await withApp(confirm, async f => {
        await f.paste(path)
        await vi.waitFor(() => expect(f.request).toHaveBeenCalledWith('image.attach_bytes', {
          content_base64: png.toString('base64'), filename: 'pasted.png', session_id: 'image-session'
        }))
        await settle()
        expect(labels(f)).toContain('renamed.dat')
        expect(labels(f)).toContain('attached')
      })
    } finally {
      rmSync(dir, { force: true, recursive: true })
    }
  })

  it('accepts a bracketed data-URL paste without turning image bytes into prompt text', async () => {
    await withApp(confirm, async f => {
      await f.paste(`data:image/png;base64,${png.toString('base64')}`)
      expect(f.app.composer.text).toBe('')
      expect(labels(f)).toContain('Pasted image')
      await f.send('   ')
      expect(f.request).toHaveBeenCalledWith('prompt.submit', expect.objectContaining({
        text: 'What do you see in this image?', image_paths: ['/confirmed/pasted.png']
      }))
    })
  })

  it('accepts native selection paste but ignores stale edit events', async () => {
    await withApp(confirm, async f => {
      const data = `data:image/png;base64,${png.toString('base64')}`
      f.app.composer.set('keep selected suffix')
      await f.event({ ev: 'edit', id: INPUT_ID, from: 5, to: 13, text: data, cursor: 5 + data.length, len: 999 })
      expect(f.app.attachments.items).toEqual([])
      await f.event({ ev: 'edit', id: INPUT_ID, from: 5, to: 13, text: data, cursor: 5 + data.length, len: f.app.composer.text.length })
      expect(f.app.composer.text).toBe('keep  suffix')
      expect(f.app.composer.cursor).toBe(5)
      expect(labels(f)).toContain('Pasted image')
    })
  })

  it('retains a failed removal with a retry instead of sending a hidden staged image', async () => {
    await withApp(confirm, async f => {
      await pastePng(f)
      f.request.mockRejectedValueOnce(new Error('Detach unavailable'))
      await f.click('remove')
      expect(labels(f)).toContain('failed')
      expect(labels(f)).toContain('Detach unavailable')
      await f.send()
      expect(f.request.mock.calls.some(([m]) => m === 'prompt.submit')).toBe(false)
      await f.click('retry')
      expect(f.app.attachments.items).toEqual([])
      expect(f.request.mock.calls.filter(([m]) => m === 'image.detach')).toHaveLength(2)
    })
  })

  it('restores image chips and draft if prompt admission fails', async () => {
    await withApp(confirm, async f => {
      await pastePng(f)
      f.request.mockRejectedValueOnce(new Error('Session storage unavailable'))
      await f.send('Preserve this prompt')
      expect(f.app.composer.text).toBe('Preserve this prompt')
      expect(labels(f)).toContain('Clipboard shot')
      expect(labels(f)).toContain('attached')
    })
  })

  it.each(['queue', 'steer'] as const)('queues an image-backed follow-up without losing images with busy=%s', async mode => {
    await withApp(confirm, async f => {
      await pastePng(f)
      f.app.busy = { label: 'Running tool', since: {}, startedAt: Date.now() }
      f.app.busyInput.mode = mode
      await f.send()
      expect(f.request).toHaveBeenCalledWith('prompt.submit', expect.objectContaining({ queued: true, image_paths: ['/confirmed/pasted.png'] }))
      expect(f.app.queue).toEqual([])
      expect(f.app.attachments.items).toEqual([])
    })
  })

  it('ignores image events for another surface and deduplicates an already queued source', async () => {
    await withApp(confirm, async f => {
      await f.event({ ev: 'paste', sf: 'other', data: png.toString('base64'), mime: 'image/png' })
      expect(f.app.attachments.items).toEqual([])
      await pastePng(f)
      await pastePng(f)
      expect(f.app.attachments.items).toHaveLength(1)
      expect(f.request.mock.calls.filter(([m]) => m === 'image.attach_bytes')).toHaveLength(1)
    })
  })

  it('keeps pending and failed images from being silently submitted', async () => {
    const gate = Promise.withResolvers<AttachedImageResult>()
    await withApp(() => gate.promise, async f => {
      await pastePng(f)
      f.app.composer.set('unsent draft')
      await f.send('unsent draft')
      expect(f.app.composer.text).toBe('unsent draft')
      expect(f.request.mock.calls.some(([m]) => m === 'prompt.submit')).toBe(false)
      gate.resolve(await confirm())
      await settle()
    })
  })
})
