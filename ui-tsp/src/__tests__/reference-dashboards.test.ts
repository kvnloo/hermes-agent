import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import type { Key } from '@stencil-hq/tern'
import { afterEach, describe, it } from 'vitest'

import type { Overlay } from '../overlay.js'
import { openReferenceDashboard } from '../overlays/reference-dashboard.js'
import { graphEdges, graphMatches, parseGraph, parseMachine, readGraph, readMachine, type Snapshot } from '../reference-dashboards.js'

const temp: string[] = []
const project = () => {
  const path = mkdtempSync(join(tmpdir(), 'hermes-reference-'))
  temp.push(path)
  return path
}
afterEach(() => { for (const path of temp.splice(0)) { rmSync(path, { force: true, recursive: true }) } })
const key = (name: string) => ({ name, text: '', ctrl: false, alt: false, shift: false, meta: false }) as Key
const fixture = {
  nodes: [
    { id: 'main', label: 'entry', source_file: 'src/entry.ts' },
    { id: 'util', label: 'helper', source_file: 'src/util.ts' },
    { id: 'main', label: 'duplicate-ignored' },
    { id: 'unused', label: 'empty' }
  ],
  links: [
    { source: 'main', target: 'util', relation: 'calls', confidence: 'EXTRACTED' },
    { source: 'util', target: 'main', relation: 'calls', confidence: 'something-weird' },
    { source: 'main', target: 'orphan', relation: 'calls', confidence: 'INFERRED' }
  ]
}
const machine = {
  schema: 1, captured_at: '2026-10-20T14:00:00Z', machine: 'omarchy-host', os: 'Arch Linux',
  updates_checked: true, problems_checked: false, installed_packages: 1234,
  disk_percent: 62.4, available_gib: 169.0,
  updates: [{ package: 'kernel', from: '6.0', to: '6.1', risk: 'unclassified' }],
  problems: [], events: []
}
function host() {
  return {
    sid: 'session' as string | null,
    overlays: [] as Overlay[],
    composer: { text: 'preserve this draft' },
    changes: 0,
    requests: 0,
    open(overlay: Overlay) {
      const prior = this.overlays.find(o => o.key === overlay.key)
      if (prior) { this.close(prior) }
      this.overlays.push(overlay)
    },
    close(overlay: Overlay) {
      this.overlays = this.overlays.filter(o => o !== overlay)
      overlay.onClose?.()
    },
    changed() { this.changes++ }
  }
}
const tick = () => new Promise<void>(resolve => setImmediate(resolve))
const tree = (overlay: Overlay) => JSON.stringify(overlay.node('layer.' + overlay.key + ':1'))

describe('Graphify data is bounded architecture provenance, never invented agent edges', () => {
  it('dedupes graph nodes, skips orphan links, normalizes provenance and sorts hubs', () => {
    const data = parseGraph(fixture)
    assert.equal(data.status, 'ready')
    if (data.status !== 'ready') { return }
    assert.equal(data.value.nodes.length, 3)
    assert.equal(data.value.links.length, 2)
    assert.deepEqual(data.value.nodes.slice(0, 2).map(n => n.degree), [2, 2])
    assert.deepEqual(data.value.links.map(link => link.confidence), ['EXTRACTED', 'UNKNOWN'])
    assert.equal(graphEdges(data.value, 'main', 1).length, 1)
    assert.deepEqual(graphMatches(data.value, 'util').map(n => n.id), ['util'])
    assert.deepEqual(graphMatches(data.value, 'DOES_NOT_EXIST'), [])
  })
  it('rejects unknown shape and oversized arrays without assuming default empty', () => {
    assert.equal(parseGraph({}).status, 'invalid')
    assert.equal(parseGraph({ nodes: [], links: {} }).status, 'invalid')
    assert.equal(parseGraph({ nodes: Array.from({ length: 30_001 }) }).status, 'oversize')
  })
  it('reads only a fixed project-local Graphify graph and fails closed on symlinks', async () => {
    const folder = project()
    mkdirSync(join(folder, 'graphify-out'))
    writeFileSync(join(folder, 'graphify-out', 'graph.json'), JSON.stringify(fixture))
    const loaded = await readGraph(folder)
    assert.equal(loaded.status, 'ready')
    if (loaded.status === 'ready') {
      assert.equal(loaded.value.links.length, 2)
    }
    const external = project()
    writeFileSync(join(external, 'graph.json'), JSON.stringify(fixture))
    rmSync(join(folder, 'graphify-out', 'graph.json'))
    symlinkSync(join(external, 'graph.json'), join(folder, 'graphify-out', 'graph.json'))
    assert.equal((await readGraph(folder)).status, 'unsafe')
  })
  it('makes missing, invalid, and over-16MiB graph files explicit', async () => {
    const folder = project()
    assert.equal((await readGraph(folder)).status, 'missing')
    mkdirSync(join(folder, 'graphify-out'))
    writeFileSync(join(folder, 'graphify-out', 'graph.json'), '{bad')
    assert.equal((await readGraph(folder)).status, 'invalid')
    writeFileSync(join(folder, 'graphify-out', 'graph.json'), ' '.repeat(16 * 1024 * 1024 + 1))
    assert.equal((await readGraph(folder)).status, 'oversize')
  })
})

describe('HANCORE-inspired machine report is snapshot-only', () => {
  it('rejects fabricated absent timestamp and unknown arrays', () => {
    assert.equal(parseMachine({ schema: 1, updates: [], problems: [], events: [] }).status, 'invalid')
    assert.equal(parseMachine({ ...machine, events: 7 }).status, 'invalid')
  })
  it('does not recategorize unclassified package risk or unscanned incident history', () => {
    const data = parseMachine(machine)
    assert.equal(data.status, 'ready')
    if (data.status !== 'ready') { return }
    assert.equal(data.value.problemsChecked, false)
    assert.equal(data.value.updates[0]?.risk, 'unclassified')
    assert.equal(data.value.diskPercent, 62.4)
  })
  it('reads a JSON report without starting pacman/journalctl or a model', async () => {
    const folder = project()
    assert.equal((await readMachine(folder)).status, 'missing')
    mkdirSync(join(folder, '.hermes-dashboard'))
    writeFileSync(join(folder, '.hermes-dashboard', 'machine.json'), JSON.stringify(machine))
    assert.equal((await readMachine(folder)).status, 'ready')
  })
})

describe('reference sheets stay native and session-scoped', () => {
  it('renders a map inspection and preserves draft, keyboard selection, and close', async () => {
    const app = host()
    const map = parseGraph(fixture) as Snapshot<import('../reference-dashboards.js').CodeGraph>
    const overlay = openReferenceDashboard(app, 'map', '', {
      map: async () => map, machine: async () => parseMachine(machine)
    })
    await tick()
    assert.match(tree(overlay), /Code map/)
    assert.match(tree(overlay), /Graphify-Labs/)
    assert.match(tree(overlay), /INFERRED|EXTRACTED/)
    overlay.onKey(key('down'))
    overlay.onKey(key('escape'))
    assert.equal(app.overlays.length, 0)
    assert.equal(app.composer.text, 'preserve this draft')
  })
  it('does not fake scan status; shows actual captured timestamp and unclassified risk', async () => {
    const app = host()
    const overlay = openReferenceDashboard(app, 'machine', '', {
      map: async () => parseGraph(fixture), machine: async () => parseMachine(machine)
    })
    await tick()
    const rendered = tree(overlay)
    assert.match(rendered, /HANCORE/)
    assert.match(rendered, /NOT LIVE/)
    assert.match(rendered, /not scanned/)
    assert.match(rendered, /unclassified/)
    overlay.onKey(key('escape'))
    assert.equal(app.overlays.length, 0)
  })
  it('drops a late read on close and does not reopen a different session', async () => {
    const app = host()
    const pending = Promise.withResolvers<Snapshot<import('../reference-dashboards.js').CodeGraph>>()
    const overlay = openReferenceDashboard(app, 'map', '', {
      map: () => pending.promise, machine: async () => parseMachine(machine)
    })
    app.sid = 'other-session'
    pending.resolve(parseGraph(fixture))
    await tick()
    assert.match(tree(overlay), /Session changed/)
    overlay.onKey(key('escape'))
    assert.equal(app.composer.text, 'preserve this draft')
  })
})
