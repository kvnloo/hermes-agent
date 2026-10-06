import { existsSync, mkdirSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { EXPERIMENT_VIEWPORTS } from '../../src/tern/experiments/fixture.js'
import { recordNativePreview } from '../../src/tern/experiments/nativeRecording.js'

const defaultOut = fileURLToPath(new URL('../../../.hermes-sandbox/tern-ux-preview-a/', import.meta.url))
const out = resolve(process.argv[2] ?? defaultOut)

try {
  if (process.argv.length > 3) throw new Error('Usage: tern:ux:record [fresh-output-directory]')
  const files = EXPERIMENT_VIEWPORTS.flatMap(viewport => {
    const { records, manifest } = recordNativePreview(viewport.id)
    return [
      { path: resolve(out, `${viewport.id}.jsonl`), content: records.map(record => JSON.stringify(record)).join('\n') + '\n' },
      { path: resolve(out, `${viewport.id}.manifest.json`), content: JSON.stringify(manifest, null, 2) + '\n' }
    ]
  })
  const existing = files.find(file => existsSync(file.path))
  if (existing) throw new Error(`Refusing to overwrite ${existing.path}; choose a fresh output directory`)

  mkdirSync(out, { recursive: true })
  for (const file of files) {
    writeFileSync(file.path, file.content, { flag: 'wx' })
    console.log(file.path)
  }
  console.log('Authored replay only: no model calls, real Tern capture, or attention timings. Target dimensions do not resize a pane.')
} catch (error) {
  console.error(error instanceof Error ? error.message : String(error))
  process.exitCode = 1
}
