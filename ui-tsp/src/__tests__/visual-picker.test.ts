import assert from 'node:assert/strict'
import { describe, it } from 'vitest'
import type { Key } from '@stencil-hq/tern'
import type { Entry } from '../model.js'
import type { Overlay } from '../overlay.js'
import { openVisualPicker } from '../overlays/visual-picker.js'
import type { PreparedVisual } from '../visuals.js'

const scope = '["stored","main"]', id = 'a'.repeat(64)
const candidate: PreparedVisual = { id, title: 'Host computed', mode: 'code', path: '/tmp/candidate.hvisual.json',
  href: 'file:///tmp/candidate.hvisual.json', metrics: [{ key: 'code', label: 'Text lines', value: 12 }] }
const entries = (): Entry[] => [{ kind: 'turn', id: 'turn', rev: 0, startedAt: 0, status: 'done', blocks: [{
  kind: 'tool', id: 'tool', call: { id: 'tool', name: 'terminal', args: {}, argsText: '', context: '', startedAt: 0,
    status: 'done', result: { exit_code: 0, output: JSON.stringify({ kind: 'hermes.visual.candidate', version: 1,
      id, path: candidate.path, scope }) } }
}] }]
function host() {
  return {
    sid: 'runtime' as string | null, storedSid: 'stored', info: { branch: 'main' }, transcript: { entries: entries() },
    overlays: [] as Overlay[], composer: { text: 'unfinished draft' }, changes: 0,
    gw: { request: () => { throw new Error('No gateway request belongs in discovery') } },
    open(o: Overlay) { const previous = this.overlays.find(value => value.key === o.key); if (previous) this.close(previous); this.overlays.push(o) },
    close(o: Overlay) { this.overlays = this.overlays.filter(value => value !== o) },
    changed() { this.changes++ }
  }
}
const key = (name: string) => ({ name, text: '', ctrl: false, alt: false, shift: false, meta: false }) as Key
const tree = (o: Overlay) => JSON.stringify(o.node('layer.' + o.key + ':1'))
const tick = () => new Promise<void>(resolve => setImmediate(resolve))

describe('visual candidates reuse the live overlay path', () => {
  it('lists completed candidates without reading any files or changing the draft', async () => {
    const app = host(); let reads = 0
    await openVisualPicker(app, '', async () => { reads++; return candidate })
    assert.match(tree(app.overlays[0]!), /Recent visual candidates/)
    assert.match(tree(app.overlays[0]!), /candidate.hvisual.json/)
    assert.match(tree(app.overlays[0]!), /not validated, visually verified or published/)
    for (let n = 0; n < 20; n++) tree(app.overlays[0]!)
    assert.equal(reads, 0)
    assert.equal(app.composer.text, 'unfinished draft')
  })
  it('selects a reported file with Enter and validates once through the existing preview loader', async () => {
    const app = host(); const calls: unknown[] = []
    await openVisualPicker(app, '', async (path, owner) => { calls.push([path, owner]); return candidate })
    app.overlays[0]!.onKey(key('enter')); await tick()
    assert.deepEqual(calls, [[candidate.path, scope]])
    assert.equal(app.overlays.length, 1)
    assert.match(tree(app.overlays[0]!), /Host computed/)
    assert.match(tree(app.overlays[0]!), /not visually verified or published/)
    assert.equal(app.composer.text, 'unfinished draft')
  })
  it('does not accept a different valid bundle swapped into the reported path', async () => {
    const app = host()
    await openVisualPicker(app, '', async () => ({ ...candidate, id: 'b'.repeat(64) }))
    app.overlays[0]!.onKey(key('enter')); await tick()
    assert.match(tree(app.overlays[0]!), /no longer matches/)
    assert.doesNotMatch(tree(app.overlays[0]!), /file:\/\/\/tmp/)
  })
  it('keeps the explicit path and empty/sessionless help routes', async () => {
    const app = host(); let reads = 0
    const load = async () => { reads++; return candidate }
    await openVisualPicker(app, candidate.path, load)
    assert.match(tree(app.overlays[0]!), /Host computed/)
    app.transcript.entries = []
    await openVisualPicker(app, '', load)
    assert.match(tree(app.overlays[0]!), /scope argument/)
    app.sid = null
    await openVisualPicker(app, '', load)
    assert.match(tree(app.overlays[0]!), /Start a session/)
    assert.equal(reads, 1)
  })
  it('does not open a file from stale picker callbacks after replacement or a newer approval', async () => {
    const app = host(); let reads = 0
    const load = async () => { reads++; return candidate }
    await openVisualPicker(app, '', load)
    const stale = app.overlays[0]!
    await openVisualPicker(app, '', load)
    stale.onKey(key('enter')); await tick()
    const picker = app.overlays[0]!
    const approval = { key: 'approval', modal: true, node: picker.node, onKey: () => true } as Overlay
    app.open(approval)
    picker.onKey(key('enter')); await tick()
    assert.equal(reads, 0)
    assert.equal(app.overlays.at(-1), approval)
  })
  it('expires on observed session, branch and transcript replacement, including observed returns', async () => {
    for (const change of ['session', 'branch', 'transcript']) {
      const app = host(); let reads = 0
      await openVisualPicker(app, '', async () => { reads++; return candidate })
      const picker = app.overlays[0]!
      if (change === 'session') app.sid = 'new'
      else if (change === 'branch') app.info.branch = 'new'
      else app.transcript.entries = []
      assert.match(tree(picker), /changed/)
      assert.doesNotMatch(tree(picker), /candidate.hvisual.json/)
      app.sid = 'runtime'; app.info.branch = 'main'
      picker.onKey(key('enter')); await tick()
      assert.equal(reads, 0)
    }
  })
  it('Escape cancels a selected pending read; a late result cannot reopen it', async () => {
    const app = host(), pending = Promise.withResolvers<PreparedVisual>(); let signal: AbortSignal | undefined
    await openVisualPicker(app, '', async (_path, _scope, abort) => { signal = abort; return pending.promise })
    app.overlays[0]!.onKey(key('enter'))
    app.overlays.at(-1)!.onKey(key('escape'))
    assert.equal(signal?.aborted, true)
    pending.resolve(candidate); await tick()
    assert.equal(app.overlays.length, 0)
  })
  it('a transcript clear during validation cannot reveal the old candidate', async () => {
    const app = host(), pending = Promise.withResolvers<PreparedVisual>()
    await openVisualPicker(app, '', () => pending.promise)
    app.overlays[0]!.onKey(key('enter'))
    app.transcript.entries = []
    pending.resolve(candidate); await tick()
    assert.match(tree(app.overlays[0]!), /transcript changed/)
    assert.doesNotMatch(tree(app.overlays[0]!), /Host computed/)
  })
})
