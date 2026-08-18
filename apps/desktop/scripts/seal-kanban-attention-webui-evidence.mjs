#!/usr/bin/env node
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

import { validateInteractionEvidence } from './kanban-attention-evidence-validation.mjs'

const [packetArg] = process.argv.slice(2)
if (!packetArg) throw new Error('usage: seal-kanban-attention-webui-evidence.mjs <packet-directory>')
const packet = path.resolve(packetArg)
const manifestPath = path.join(packet, 'manifest.json')
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))
const sha256 = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex')
const excluded = new Set(['manifest.json', 'manifest.receipt.json'])
const files = fs.readdirSync(packet, { withFileTypes: true })
  .filter(entry => entry.isFile() && !excluded.has(entry.name))
  .map(entry => path.join(packet, entry.name))
  .sort()
const payloads = files.map(file => ({ path: path.basename(file), bytes: fs.statSync(file).size, sha256: sha256(file) }))
const captures = payloads.filter(item => /^webui-(1220|320|360|390|430)-(closed|open)\.png$/.test(item.path))
if (captures.length !== 10) throw new Error(`expected closed and open captures at five widths, found ${captures.length}`)
if (!payloads.some(item => item.path === 'server.log')) throw new Error('missing server.log')
validateInteractionEvidence(manifest)
manifest.schema = 2
manifest.generatedBy = 'actual standalone Hermes dashboard + Playwright system Chromium; sealed by apps/desktop/scripts/seal-kanban-attention-webui-evidence.mjs'
manifest.payloads = payloads
const text = `${JSON.stringify(manifest, null, 2)}\n`
fs.writeFileSync(manifestPath, text)
const receipt = { schema: 1, artifact: 'manifest.json', bytes: Buffer.byteLength(text), sha256: sha256(manifestPath), payloadCount: payloads.length }
fs.writeFileSync(path.join(packet, 'manifest.receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`)
console.log(JSON.stringify(receipt))
