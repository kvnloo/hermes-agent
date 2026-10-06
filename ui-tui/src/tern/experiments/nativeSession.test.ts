import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import { TERN_UX_FIXTURE } from './fixture.js'
import { NativeFixtureSession, diffFixtureViews, type FixtureOp } from './nativeSession.js'
import { NativeFixtureInput } from './nativeInput.js'
import {
  INITIAL_NATIVE_FIXTURE, NATIVE_FIXTURE_SURFACE, fixtureNodes, fixturePanel,
  fixtureRequiredKinds, reduceNativeFixture, renderNativeFixture,
  type FixtureNode, type FixtureView
} from './nativeView.js'

const hello = { r: 'hello' as const, v: 1, term: 'tern', kinds: fixtureRequiredKinds(), features: ['dock'], credits: 1 }
const at = (step: number) => renderNativeFixture({ ...INITIAL_NATIVE_FIXTURE, step })

/** Independent document consumer: reject a malformed operation instead of hiding it. */
function replay(root: FixtureNode, ops: FixtureOp[]): void {
  const find = (id: string): FixtureNode => {
    const visit = (node: FixtureNode): FixtureNode | undefined =>
      node.id === id ? node : node.c?.map(visit).find(Boolean)
    const found = visit(root)
    assert.ok(found, `unknown node ${id}`)
    return found
  }
  const detach = (id: string): FixtureNode => {
    const target = find(id)
    const walk = (node: FixtureNode): boolean => {
      const index = node.c?.findIndex(child => child.id === id) ?? -1
      if (index >= 0) { node.c!.splice(index, 1); return true }
      return node.c?.some(walk) ?? false
    }
    assert.ok(walk(root), `cannot detach ${id}`)
    return target
  }
  for (const op of ops) {
    if (op[0] === 'add' || op[0] === 'move') {
      const node = op[0] === 'add' ? structuredClone(op[4]) : detach(op[1])
      assert.equal(node.id, op[1])
      const parent = find(op[2])
      parent.c ??= []
      const index = op[3] === null ? parent.c.length : parent.c.findIndex(child => child.id === op[3])
      assert.ok(index >= 0)
      parent.c.splice(index, 0, node)
    } else if (op[0] === 'del') {
      detach(op[1])
    } else if (op[0] === 'set') {
      const props = find(op[1]).p ??= {}
      for (const [key, value] of Object.entries(op[2])) {
        if (value === null) delete props[key]
        else props[key] = structuredClone(value)
      }
    } else {
      const props = find(op[1]).p ??= {}
      props.text = (op[2] === 'append' ? String(props.text ?? '') : '') + op[3]
    }
    const ids: string[] = []
    const walk = (node: FixtureNode) => { ids.push(node.id); node.c?.forEach(walk) }
    walk(root)
    assert.equal(new Set(ids).size, ids.length, 'duplicate document IDs')
  }
}

function harness() {
  const writes: { verb: string; value: Record<string, unknown> }[] = []
  const session = new NativeFixtureSession(hello, (verb, value) => writes.push({ verb, value }))
  session.start()
  const frames = () => writes.filter(message => message.verb === 'f')
  const ack = (s: number) => session.event({ ev: 'ack', sf: NATIVE_FIXTURE_SURFACE, s })
  return { session, writes, frames, ack }
}

describe('native A fixture projection', () => {
  it('represents every fixture state deterministically with one read-only composer', () => {
    for (let step = 0; step < TERN_UX_FIXTURE.length; step++) {
      assert.deepEqual(at(step), at(step))
      const nodes = fixtureNodes(at(step))
      assert.equal(new Set(nodes.map(node => node.id)).size, nodes.length)
      const editors = nodes.filter(node => node.k === 'editor')
      assert.equal(editors.length, 1)
      assert.equal(editors[0].p?.readonly, true)
      assert.equal(editors[0].p?.sendable, false)
      assert.ok(nodes.some(node => node.id === 'lab:notice'))
    }
  })
  it('opens and dismisses an inspector without advancing the task or changing its composer', () => {
    const before = { ...INITIAL_NATIVE_FIXTURE, step: 3 }
    const opened = reduceNativeFixture(before, 'models')
    assert.equal(opened.step, before.step)
    assert.equal(fixturePanel(opened), 'models')
    assert.deepEqual(renderNativeFixture(opened).main, renderNativeFixture(before).main)
    const changed = reduceNativeFixture(opened, 'model-1')
    const closed = reduceNativeFixture(changed, 'return-chat')
    assert.equal(closed.step, before.step)
    assert.equal(closed.model, 'fixture/alternate')
    assert.equal(fixturePanel(closed), null)
  })
  it('preserves failed history rather than repainting the failed attempt as success', () => {
    for (const step of [8, 9, 13]) {
      const nodes = fixtureNodes(at(step))
      assert.equal(nodes.find(node => node.id === 'test:first')?.p?.status, 'error')
      assert.equal(nodes.find(node => node.id === 'test:retry')?.p?.status, step === 8 ? 'running' : 'done')
    }
  })
  it('uses a targeted append for streamed text and never remounts the composer on navigation', () => {
    const ops = diffFixtureViews(at(2), at(3))
    assert.ok(ops.some(op => op[0] === 'text' && op[1] === 'answer' && op[2] === 'append'))
    assert.deepEqual(diffFixtureViews(at(3), at(3)), [])
    for (let step = 1; step < TERN_UX_FIXTURE.length; step++) {
      assert.ok(!diffFixtureViews(at(step - 1), at(step)).some(op =>
        (op[0] === 'add' || op[0] === 'del') && ['main', 'dock', 'composer', 'composer:editor'].includes(op[1])))
    }
  })
  it('replays every state forwards, backwards and reset to the exact semantic tree', () => {
    const root: FixtureNode = { id: NATIVE_FIXTURE_SURFACE, k: 'col', c: [] }
    let previous: FixtureView | null = null
    const order = [...TERN_UX_FIXTURE.keys(), ...[...TERN_UX_FIXTURE.keys()].reverse(), 7, 10, 0]
    for (const step of order) {
      const next = at(step)
      replay(root, diffFixtureViews(previous, next))
      assert.deepEqual(root.c, Object.values(next))
      previous = next
    }
  })
})

describe('native A fixture session', () => {
  it('does not emit unsupported kinds or open on an incompatible hello', () => {
    for (const bad of [{ ...hello, v: 2 }, { ...hello, kinds: ['col'] }, { ...hello, credits: 0 }, { ...hello, features: [] }]) {
      assert.throws(() => new NativeFixtureSession(bad, () => assert.fail('must not write')))
    }
  })
  it('keeps one surface and one pending latest view under a single frame credit', () => {
    const { session, writes, frames, ack } = harness()
    session.dispatch('next'); session.dispatch('next'); session.dispatch('next')
    assert.equal(frames().length, 1)
    ack(1)
    assert.equal(frames().length, 2)
    const root: FixtureNode = { id: NATIVE_FIXTURE_SURFACE, k: 'col', c: [] }
    for (const frame of frames()) replay(root, frame.value.ops as FixtureOp[])
    assert.deepEqual(root.c, Object.values(at(3)))
    assert.equal(writes.filter(message => message.verb === 'o').length, 1)
    session.close(); ack(2); session.dispatch('next')
    assert.equal(frames().length, 2)
    assert.equal(writes.filter(message => message.verb === 'x').length, 1)
  })
  it('drops a stale pending update when the user returns to the already-sent state', () => {
    const { session, frames, ack } = harness()
    session.dispatch('next'); session.dispatch('previous'); ack(1)
    assert.equal(frames().length, 1)
    assert.equal(session.state.step, 0)
  })
  it('ignores foreign, future, fractional and duplicate acknowledgements', () => {
    const { session, frames, ack } = harness()
    session.dispatch('next')
    session.event({ ev: 'ack', sf: 'other', s: 1 }); ack(99); ack(0.5); ack(-1)
    assert.equal(frames().length, 1)
    ack(1); ack(1)
    assert.equal(frames().length, 2)
  })
  it('gates pointer actions against currently visible controls and keeps send inert', () => {
    const { session } = harness()
    const event = (id: string, act: string) => session.event({ ev: 'action', sf: NATIVE_FIXTURE_SURFACE, id, act })
    event('approval:allow', 'allow')
    session.event({ ev: 'send', sf: NATIVE_FIXTURE_SURFACE, id: 'composer:editor', text: 'run anything' })
    assert.equal(session.state.decision, null)
    for (let i = 0; i < 7; i++) session.dispatch('next')
    event('approval:allow', 'allow')
    assert.equal(session.state.decision, 'allow')
    assert.equal(session.state.step, 7)
    session.dispatch('next'); event('approval:deny', 'deny')
    assert.equal(session.state.decision, 'allow')
  })
  it('preserves a user fold across later task updates', () => {
    const { session, frames, ack } = harness()
    for (let i = 0; i < 4; i++) session.dispatch('next')
    ack(1)
    session.event({ ev: 'toggle', sf: NATIVE_FIXTURE_SURFACE, id: 'read', collapsed: false })
    session.dispatch('next'); ack(2)
    const root: FixtureNode = { id: NATIVE_FIXTURE_SURFACE, k: 'col', c: [] }
    for (const frame of frames()) replay(root, frame.value.ops as FixtureOp[])
    assert.equal(root.c?.[0].c?.find(node => node.id === 'read')?.p?.collapsed, false)
  })
  it('coalesces while hidden and stops after a document error or retention loss', () => {
    const { session, frames, ack } = harness()
    session.event({ ev: 'visible', sf: NATIVE_FIXTURE_SURFACE, visible: false })
    session.dispatch('next'); ack(1)
    assert.equal(frames().length, 1)
    session.event({ ev: 'visible', sf: NATIVE_FIXTURE_SURFACE, visible: true })
    assert.equal(frames().length, 2)
    assert.equal(session.event({ ev: 'gone', sf: NATIVE_FIXTURE_SURFACE, ids: ['main'] }), 'invalidated')
    session.dispatch('next'); ack(2)
    assert.equal(frames().length, 2)
    const other = harness()
    assert.equal(other.session.event({ ev: 'error', sf: NATIVE_FIXTURE_SURFACE, msg: 'bad op' }), 'invalidated')
  })
})

describe('native preview input', () => {
  it('keeps protocol payload text out of keyboard commands even at every chunk boundary', () => {
    const wire = '\x1b_tsp;e;{"ev":"action","act":"quit"}\x1b\\n'
    for (let split = 0; split <= wire.length; split++) {
      const input = new NativeFixtureInput()
      assert.deepEqual([...input.feed(wire.slice(0, split)), ...input.feed(wire.slice(split))], [
        { kind: 'apc', value: 'tsp;e;{"ev":"action","act":"quit"}' }, { kind: 'key', value: 'next' }
      ])
    }
  })
  it('recognizes DA1, OSC 877, arrow keys and quit without echoing terminal input', () => {
    const input = new NativeFixtureInput()
    assert.deepEqual(input.feed('\x1b[?1;2c\x1b]877;tsp;r;{}\x07\x1b[D\x1b[Cq'), [
      { kind: 'barrier' }, { kind: 'apc', value: 'tsp;r;{}' },
      { kind: 'key', value: 'previous' }, { kind: 'key', value: 'next' }, { kind: 'key', value: 'quit' }
    ])
  })
  it('ignores bracketed paste, unsupported escapes and limits unterminated replies', () => {
    const input = new NativeFixtureInput()
    assert.deepEqual(input.feed('\x1b[200~qnr'), [])
    assert.deepEqual(input.feed('p\x1b[201~\x1b[99un'), [{ kind: 'key', value: 'next' }])
    assert.throws(() => new NativeFixtureInput().feed('\x1b_' + 'x'.repeat(262145)), /limit/)
  })
})
