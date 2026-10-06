import { readdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { verifyTernCaptureMatrix, type CaptureReceiptLike } from '../../src/tern/experiments/captureMatrix.js'

const dir = resolve(process.argv[2] ?? '')
if (!process.argv[2]) {
  console.error('Usage: tern:ux:verify-captures <receipt-directory>')
  process.exit(2)
}

const receipts = readdirSync(dir)
  .filter(name => name.endsWith('.json'))
  .sort()
  .map(name => JSON.parse(readFileSync(resolve(dir, name), 'utf8')) as CaptureReceiptLike)

process.stdout.write(JSON.stringify(verifyTernCaptureMatrix(receipts), null, 2) + '\n')
