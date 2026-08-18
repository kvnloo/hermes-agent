#!/usr/bin/env node
import { createHash } from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'

const [packetArg] = process.argv.slice(2)
if (!packetArg) throw new Error('usage: seal-kanban-attention-evidence.mjs <packet-directory>')
const packet = path.resolve(packetArg)
const runtimePath = path.join(packet, 'runtime.json')
const runtime = JSON.parse(fs.readFileSync(runtimePath, 'utf8'))
const sha256 = file => createHash('sha256').update(fs.readFileSync(file)).digest('hex')
const rel = file => path.relative(packet, file).split(path.sep).join('/')

const excluded = new Set(['manifest.json', 'manifest.receipt.json'])
const walk = dir => fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
  const file = path.join(dir, entry.name)
  return entry.isDirectory() ? walk(file) : [file]
})
const files = walk(packet).filter(file => !excluded.has(rel(file))).sort((a, b) => rel(a).localeCompare(rel(b)))
const payloads = files.map(file => ({ path: rel(file), bytes: fs.statSync(file).size, sha256: sha256(file) }))
const byPath = Object.fromEntries(payloads.map(item => [item.path, item]))
const screenshots = payloads.filter(item => /^screenshots\/electron-(1220|320|360|390|430)\.png$/.test(item.path))
if (screenshots.length !== 5) throw new Error(`expected five screenshots, found ${screenshots.length}`)

const sourceCommit = execFileSync('git', ['rev-parse', 'HEAD'], { cwd: runtime.repoRoot, encoding: 'utf8' }).trim()
const sourceTree = execFileSync('git', ['show', '-s', '--format=%T', sourceCommit], { cwd: runtime.repoRoot, encoding: 'utf8' }).trim()
const required = ['build/install-stamp.json', 'build/index.html', 'build/electron-main.mjs', 'database/kanban.db', 'logs/backend.log', 'logs/electron.stdout.log', 'logs/electron.stderr.log', 'interaction-trace.json', 'launch.json', 'process.json', 'production-sentinel-before.json', 'production-sentinel-after.json', 'database/schema.sql', 'database/logical-before.json', 'database/logical-after.json']
for (const name of required) if (!byPath[name]) throw new Error(`missing required payload: ${name}`)
if (runtime.sourceCommit !== sourceCommit || runtime.sourceTree !== sourceTree) throw new Error('runtime source identity does not match sealing checkout')

const manifest = {
  schema: 2,
  generatedBy: 'apps/desktop/scripts/seal-kanban-attention-evidence.mjs',
  source: { commit: sourceCommit, tree: sourceTree },
  build: {
    installStampSha256: byPath['build/install-stamp.json'].sha256,
    rendererSha256: byPath['build/index.html'].sha256,
    electronMainSha256: byPath['build/electron-main.mjs'].sha256,
  },
  runtime: {
    startedAt: runtime.startedAt,
    endedAt: runtime.endedAt,
    electronVersion: runtime.electronVersion,
    electronNodeVersion: runtime.electronNodeVersion,
    harnessNodeVersion: process.version,
    electronPid: runtime.electronPid,
    exitCode: runtime.exitCode,
  },
  database: {
    sha256: byPath['database/kanban.db'].sha256,
    sqliteVersion: runtime.sqliteVersion,
    schemaVersion: runtime.schemaVersion,
    privacyAudit: runtime.privacyAudit,
  },
  productionSentinelUnchanged: runtime.productionSentinelUnchanged,
  interactionVerdict: runtime.interactionVerdict,
  screenshots: screenshots.map(item => ({ path: item.path, bytes: item.bytes, sha256: item.sha256 })),
  payloads,
}
const manifestText = `${JSON.stringify(manifest, null, 2)}\n`
fs.writeFileSync(path.join(packet, 'manifest.json'), manifestText)
const receipt = {
  schema: 1,
  artifact: 'manifest.json',
  bytes: Buffer.byteLength(manifestText),
  sha256: sha256(path.join(packet, 'manifest.json')),
  payloadCount: payloads.length,
}
fs.writeFileSync(path.join(packet, 'manifest.receipt.json'), `${JSON.stringify(receipt, null, 2)}\n`)
console.log(JSON.stringify(receipt))
