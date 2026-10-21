// Read-only wire observation: retain the exact OSC52 bytes, forward every write unchanged.
import { appendFileSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
const proof = dirname(fileURLToPath(import.meta.url))
const m = JSON.parse(readFileSync(join(proof, 'manifest.json'), 'utf8'))
const original = process.stdout.write
process.stdout.write = function (chunk, ...args) {
  const bytes = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk)
  if (bytes.includes(Buffer.from('\x1b]52;'))) {
    appendFileSync(join(m.proof, 'clipboard-osc52.jsonl'), JSON.stringify({time:Date.now(),hex:bytes.toString('hex')})+'\n', {mode:0o600})
  }
  return original.call(this, chunk, ...args)
}
