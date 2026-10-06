import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { readFileSync, statSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { buildTernCaptureReceipt, type TernCaptureMode } from '../../src/tern/experiments/captureReceipt.js'
import type { ExperimentViewportId } from '../../src/tern/experiments/fixture.js'

const args = process.argv.slice(2)
const value = (name: string) => {
  const index = args.indexOf(name)
  return index >= 0 ? args[index + 1] : undefined
}

const evidencePath = value('--evidence')
const viewport = value('--viewport') as ExperimentViewportId | undefined
const mode = value('--mode') as TernCaptureMode | undefined
const ternVersion = value('--tern-version')
const out = value('--out')
const timeRaw = value('--time-to-needs-user-ms')

if (!evidencePath || !viewport || !mode || !ternVersion || !['live-hermes', 'fixture-replay'].includes(mode)) {
  console.error(
    'Usage: tern:ux:capture-receipt --evidence <file> --viewport narrow|normal|wide ' +
      '--mode live-hermes|fixture-replay --tern-version <version> [--time-to-needs-user-ms N] [--out receipt.json]'
  )
  process.exit(2)
}

const absoluteEvidence = resolve(evidencePath)
const bytes = statSync(absoluteEvidence).size
const sha256 = createHash('sha256').update(readFileSync(absoluteEvidence)).digest('hex')
const commit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim()
const timeToNeedsUserMs = timeRaw === undefined ? undefined : Number(timeRaw)

if (timeToNeedsUserMs !== undefined && (!Number.isFinite(timeToNeedsUserMs) || timeToNeedsUserMs < 0)) {
  throw new Error('time-to-needs-user must be a non-negative number')
}

const receipt = buildTernCaptureReceipt({
  commit,
  evidence: { bytes, path: absoluteEvidence, sha256 },
  mode,
  ternVersion,
  viewport,
  ...(timeToNeedsUserMs !== undefined ? { glance: { timeToNeedsUserMs } } : {})
})

const output = JSON.stringify(receipt, null, 2) + '\n'

if (out) {
  writeFileSync(resolve(out), output, { flag: 'wx' })
} else {
  process.stdout.write(output)
}
