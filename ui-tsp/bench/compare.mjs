#!/usr/bin/env node
import { execFileSync } from 'node:child_process'
import { appendFileSync, mkdirSync, writeFileSync, mkdtempSync } from 'node:fs'
import { cpus, hostname, loadavg, release, tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const out = resolve(process.argv[2] ?? join(root, 'bench/results'))
mkdirSync(out, { recursive: true })
const scratch = mkdtempSync(join(tmpdir(), 'frame-compare-'))
const variants = [
  ['baseline', 'b7fa64fe82'],
  ['donor', 'b2ff496021'],
  ['candidate', undefined]
]
const metadata = {
  machine: hostname(),
  cpu: cpus()[0]?.model,
  kernel: release(),
  node: process.version,
  baseline: variants[0][1],
  donor: variants[1][1],
  head: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  dirty: execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }),
  loadBefore: loadavg(),
  runs: 5,
  method: 'fresh processes; rotating ABC/BCA/CAB order; four identical scenario traces per process; no profiler'
}
const bundles = variants.map(([name, ref]) => [
  name,
  execFileSync(
    process.execPath,
    [join(root, 'bench/run.mjs'), '--build-only', ...(ref ? [`--source-ref=${ref}`] : [])],
    { encoding: 'utf8' }
  ).trim()
])
const raw = join(out, 'runs.jsonl')
writeFileSync(raw, '')
for (let round = 0; round < 5; round++) {
  for (let offset = 0; offset < bundles.length; offset++) {
    const [variant, bundle] = bundles[(round + offset) % bundles.length]
    const lines = execFileSync(process.execPath, [bundle], {
      encoding: 'utf8',
      env: {
        ...process.env,
        HERMES_HOME: scratch,
        HERMES_TUI_SPLASH: '0',
        HERMES_TUI_QUERY: '',
        HERMES_TUI_IMAGE: '',
        HERMES_PYTHON_SRC_ROOT: resolve(root, '..')
      }
    })
      .trim()
      .split('\n')
    for (const line of lines) {
      const result = { ...JSON.parse(line), variant, round }
      appendFileSync(raw, JSON.stringify(result) + '\n')
      console.log(JSON.stringify(result))
    }
  }
}
metadata.loadAfter = loadavg()
writeFileSync(join(out, 'machine.json'), JSON.stringify(metadata, null, 2) + '\n')
