import { describe, expect, it, vi } from 'vitest'
import type { Key } from '@stencil-hq/tern'
import type { Overlay } from '../overlay.js'
import { openVisual } from '../overlays/visual.js'
import type { PreparedVisual } from '../visuals.js'

function host() {
  return {
    sid: 'runtime' as string | null, storedSid: 'stored' as string | null, info: { branch: 'main' },
    overlays: [] as Overlay[], composer: { text: 'keep this draft' },
    gw: { request: vi.fn() }, changed: vi.fn(),
    open(o: Overlay) {
      const prior = this.overlays.find(value => value.key === o.key)
      if (prior) this.close(prior)
      this.overlays.push(o)
    },
    close(o: Overlay) { this.overlays = this.overlays.filter(value => value !== o) }
  }
}
const visual: PreparedVisual = {
  id: 'a'.repeat(64), title: 'Prepared fixture', mode: 'code',
  path: '/tmp/candidate.hvisual.json', href: 'file:///tmp/candidate.hvisual.json',
  metrics: [{ key: 'code', label: 'Text lines', value: 12 }]
}
const tree = (o: Overlay) => JSON.stringify(o.node('layer.visual-preview:1'))
const escape = { name: 'escape', text: '', ctrl: false, alt: false, shift: false, meta: false } as Key

describe('visual sheet uses the current frontend owner', () => {
  it('shows the exact scope without IO; sessionless help does not load', async () => {
    const app = host(), load = vi.fn()
    await openVisual(app, '', load)
    expect(tree(app.overlays[0]!)).toContain('stored')
    app.sid = null
    await openVisual(app, '/tmp/candidate.hvisual.json', load)
    expect(load).not.toHaveBeenCalled()
  })
  it('mounts the prepared summary and file route without sending prompts or changing the draft', async () => {
    const app = host()
    await openVisual(app, visual.path, async () => visual)
    const rendered = tree(app.overlays[0]!)
    expect(rendered).toContain(visual.href)
    expect(rendered).toContain(visual.title)
    expect(rendered).toContain('not visually verified or published')
    expect(app.composer.text).toBe('keep this draft')
    expect(app.gw.request).not.toHaveBeenCalled()
  })
  it('Escape aborts a pending read; its late completion never reopens the sheet', async () => {
    const app = host(), pending = Promise.withResolvers<PreparedVisual>()
    let signal: AbortSignal | undefined
    const run = openVisual(app, visual.path, async (_path, _scope, abort) => { signal = abort; return pending.promise })
    app.overlays[0]!.onKey(escape)
    expect(signal?.aborted).toBe(true)
    pending.resolve(visual)
    await run
    expect(app.overlays).toHaveLength(0)
    expect(app.changed).not.toHaveBeenCalled()
  })
  it('an old read or error cannot mutate a same-key replacement', async () => {
    const app = host(), pending = Promise.withResolvers<PreparedVisual>()
    const first = openVisual(app, visual.path, () => pending.promise)
    const old = app.overlays[0]!
    await openVisual(app, visual.path, async () => ({ ...visual, title: 'Replacement' }))
    app.changed.mockClear()
    pending.reject(new Error('old failure'))
    await first
    old.onKey(escape)
    expect(tree(app.overlays[0]!)).toContain('Replacement')
    expect(app.changed).not.toHaveBeenCalled()
  })
  it('does not steal ownership from an approval opened while the read is pending', async () => {
    const app = host(), pending = Promise.withResolvers<PreparedVisual>()
    const run = openVisual(app, visual.path, () => pending.promise)
    const approval = { key: 'approval', modal: true, node: () => undefined, onKey: () => true } as unknown as Overlay
    app.open(approval)
    pending.resolve(visual)
    await run
    expect(app.overlays.at(-1)).toBe(approval)
    expect(app.overlays).toHaveLength(2)
  })
  it('drops cross-session completion and hides already loaded links on branch changes', async () => {
    const app = host(), pending = Promise.withResolvers<PreparedVisual>()
    const run = openVisual(app, visual.path, () => pending.promise)
    app.sid = 'another-runtime'
    pending.resolve(visual)
    await run
    expect(app.changed).not.toHaveBeenCalled()
    expect(tree(app.overlays[0]!)).not.toContain(visual.href)
    await openVisual(app, visual.path, async () => visual)
    const loaded = app.overlays[0]!
    app.info.branch = 'different'
    expect(tree(loaded)).toContain('Session or branch changed')
    app.info.branch = 'main'
    expect(tree(loaded)).not.toContain(visual.href)
  })
})
