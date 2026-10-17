#!/usr/bin/env node
// The existing App/SDK replay, with pinned pre-retention App and identical fixtures.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { appendFileSync, mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { cpus, hostname, loadavg, release, tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = resolve(process.argv[2] ?? join(root, 'bench/retention-results'))
const base = process.argv.find(arg => arg.startsWith('--base='))?.slice(7) ?? '5de5221469e1b04cbd42f25151cbb677a8bb4e7b'
mkdirSync(out, { recursive: true })
const scratch = mkdtempSync(join(tmpdir(), 'retention-compare-'))
const variants = [['before', base], ['after', undefined]]
const metadata = {
  machine: hostname(), cpu: cpus()[0]?.model, kernel: release(), node: process.version,
  base, head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  dirty: execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }),
  loadBefore: loadavg(), runs: 5,
  method: 'five AB/BA fresh-process rounds; history order alternates; 5,000 deltas, 20 tools; synthetic ACKs; all wire verified'
}
const bundles = variants.map(([name, ref]) => [name, execFileSync(process.execPath,
  [join(root, 'bench/run.mjs'), '--build-only', ...(ref ? [`--source-ref=${ref}`] : [])],
  { encoding: 'utf8' }).trim()])
const raw = join(out, 'runs.jsonl')
writeFileSync(raw, '')
const rows = []
for (let round = 0; round < 5; round++) {
  for (let offset = 0; offset < 2; offset++) {
    const [variant, bundle] = bundles[(round + offset) % 2]
    const lines = execFileSync(process.execPath, [bundle, '--retention', ...(round % 2 ? ['--reverse-history'] : [])], {
      encoding: 'utf8', env: { ...process.env, HERMES_HOME: scratch, HERMES_TUI_SPLASH: '0',
        HERMES_TUI_QUERY: '', HERMES_TUI_IMAGE: '', HERMES_PYTHON_SRC_ROOT: resolve(root, '..') }
    }).trim().split('\n')
    assert.equal(lines.length, 2)
    for (const line of lines) {
      const row = { ...JSON.parse(line), variant, round }
      assert.equal(row.droppedSemanticEvents, 0)
      rows.push(row)
      appendFileSync(raw, JSON.stringify(row) + '\n')
      console.log(JSON.stringify(row))
    }
  }
}
assert.equal(rows.length, 20)
const median = values => [...values].sort((a, b) => a - b)[2]
const summary = []
for (const [variant] of variants) {
  for (const history of [200, 2000]) {
    const group = rows.filter(row => row.variant === variant && row.history === history)
    const values = group.map(row => row.streamingBuildP95Ms)
    summary.push({ variant, history, runs: group.length,
      p95Ms: median(values), minP95Ms: Math.min(...values), maxP95Ms: Math.max(...values),
      streamingBytes: [...new Set(group.map(row => row.streamingBytes))],
      totalBytes: [...new Set(group.map(row => row.bytes))],
      replayMs: median(group.map(row => row.wallMs)),
      frames: [...new Set(group.map(row => row.streamingFrames))] })
  }
}
const after = summary.filter(row => row.variant === 'after')
const ratio = after[1].p95Ms / after[0].p95Ms
metadata.loadAfter = loadavg()
writeFileSync(join(out, 'machine.json'), JSON.stringify(metadata, null, 2) + '\n')
writeFileSync(join(out, 'summary.json'), JSON.stringify({ rows: summary, p95Ratio: ratio, gate: ratio <= 1.5 }, null, 2) + '\n')
assert(ratio <= 1.5, `retention p95 ratio ${ratio} exceeds 1.5`)
console.log(JSON.stringify({ summary, ratio, gate: 'pass' }))
