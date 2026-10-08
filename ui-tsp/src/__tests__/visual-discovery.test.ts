import assert from 'node:assert/strict'
import { describe, it } from 'vitest'
import type { Entry, ToolCall, TurnEntry } from '../model.js'
import { parseVisualCandidate, recentVisualCandidates, VISUAL_DISCOVERY_LIMITS as limits } from '../visual-discovery.js'

const scope = '["stored","main"]'
const id = 'a'.repeat(64)
const hint = (extra: Record<string, unknown> = {}) => JSON.stringify({
  kind: 'hermes.visual.candidate', version: 1, id, path: '/tmp/candidate.hvisual.json', scope, ...extra
})
const call = (output = hint(), extra: Partial<ToolCall> = {}): ToolCall => ({
  id: 'tool-1', name: 'terminal', args: {}, argsText: '', context: '', startedAt: 0,
  status: 'done', result: { exit_code: 0, output }, ...extra
})
const turn = (calls: ToolCall[]): TurnEntry => ({
  kind: 'turn', id: 'turn-1', rev: 0, status: 'done', startedAt: 0,
  blocks: calls.map(call => ({ kind: 'tool', id: call.id, call }))
})

describe('reported OpenUI candidates', () => {
  it('accepts only the complete versioned prepare result, including paths with spaces', () => {
    const candidate = parseVisualCandidate(hint({ path: '/tmp/a b/c.hvisual.json' }), scope, 'tool-1')
    assert.equal(candidate?.path, '/tmp/a b/c.hvisual.json')
    assert.equal(candidate?.callId, 'tool-1')
    assert.equal(Object.isFrozen(candidate), true)
    for (const text of [hint() + '\nwarning', 'prefix\n' + hint(), '/tmp/candidate.hvisual.json', '[]', 'null', '{']) {
      assert.equal(parseVisualCandidate(text, scope, 'tool-1'), undefined)
    }
  })
  it('rejects unsupported fields, schemas, identities and scopes', () => {
    for (const extra of [{ version: 2 }, { kind: 'html_render' }, { id: 'short' }, { scope: 'other' },
      { scope: null }, { command: 'anything' }, { approved: true }]) {
      assert.equal(parseVisualCandidate(hint(extra), scope, 'tool-1'), undefined)
    }
    assert.equal(parseVisualCandidate(hint(), '', 'tool-1'), undefined)
    assert.equal(parseVisualCandidate(hint({ scope: 'x'.repeat(257) }), 'x'.repeat(257), 'tool-1'), undefined)
  })
  it('rejects unsafe display paths and oversized output before parsing', () => {
    for (const path of ['relative.hvisual.json', 'file:///tmp/a.hvisual.json', '/tmp/a.html',
      '/tmp/a\n.hvisual.json', '/tmp/a\u202e.hvisual.json', '/' + 'x'.repeat(4100) + '.hvisual.json']) {
      assert.equal(parseVisualCandidate(hint({ path }), scope, 'tool-1'), undefined)
    }
    assert.equal(parseVisualCandidate(' '.repeat(limits.outputChars) + hint(), scope, 'tool-1'), undefined)
  })
  it('uses only successful completed terminal results, not summaries, arguments or assistant text', () => {
    const calls = ['running', 'error', 'cancelled'].map(status => call(hint(), { status: status as ToolCall['status'] }))
    calls.push(call(hint(), { name: 'read_file' }), call('', { summary: hint(), resultText: hint(), args: { output: hint() } }))
    for (const result of [{ exit_code: 1, output: hint() }, { output: hint() },
      { exit_code: 0, output: hint(), error: 'bad' }, { exit_code: 0, output: hint(), isError: true }]) {
      calls.push(call('', { result }))
    }
    const entry = turn(calls)
    entry.blocks.push({ kind: 'text', id: 'prose', text: hint() })
    assert.deepEqual(recentVisualCandidates([entry], scope), [])
  })
  it('handles captured result objects or complete serialized result objects', () => {
    const captured = call('', { result: JSON.stringify({ exit_code: 0, output: hint() }) })
    assert.equal(recentVisualCandidates([turn([captured])], scope)[0]?.id, id)
    for (const result of ['{', 'x'.repeat(limits.outputChars + 1), null, []]) {
      assert.deepEqual(recentVisualCandidates([turn([call('', { result })])], scope), [])
    }
  })
  it('keeps newest-first order and deduplicates retries without mutating the transcript', () => {
    const first = call(), retry = call(hint(), { id: 'retry' })
    const newest = call(hint({ id: 'b'.repeat(64), path: '/tmp/second.hvisual.json' }), { id: 'new' })
    const entries = [turn([first, retry, newest])], before = JSON.stringify(entries)
    const candidates = recentVisualCandidates(entries, scope)
    assert.deepEqual(candidates.map(value => value.callId), ['new', 'retry'])
    assert.equal(Object.isFrozen(candidates), true)
    assert.equal(JSON.stringify(entries), before)
  })
  it('bounds returned candidates and entries inspected', () => {
    const candidates = Array.from({ length: 20 }, (_, n) => call(hint({ path: `/tmp/${n}.hvisual.json` }), { id: String(n) }))
    assert.equal(recentVisualCandidates([turn(candidates)], scope).length, limits.candidates)
    const notices: Entry[] = Array.from({ length: limits.entries }, (_, n) => ({ kind: 'notice', id: String(n), text: '', tone: 'info' }))
    assert.deepEqual(recentVisualCandidates([turn([call()]), ...notices], scope), [])
  })
  it('bounds blocks inspected even when a single turn is huge', () => {
    const entry = turn([call()])
    for (let n = 0; n < limits.blocks; n++) entry.blocks.push({ kind: 'text', id: String(n), text: '' })
    assert.deepEqual(recentVisualCandidates([entry], scope), [])
  })
  it('bounds aggregate JSON work, not just per-output size', () => {
    const entry = turn([call(), ...Array.from({ length: 9 }, () => call(' '.repeat(limits.outputChars)))])
    assert.deepEqual(recentVisualCandidates([entry], scope), [])
  })
})
