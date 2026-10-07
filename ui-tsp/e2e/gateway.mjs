#!/usr/bin/env node
// Transparent timing/recording shim around the REAL gateway. Never constructs app replies.
import { spawn } from 'node:child_process'
import { accessSync, appendFileSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { createInterface } from 'node:readline'
import { fileURLToPath } from 'node:url'
const m = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'manifest.json'), 'utf8'))
try {
  accessSync(join(m.root, '.env'))
  throw new Error('Refusing a project dotenv fallback outside the inert fixture.')
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}
const log = (dir, body) => appendFileSync(m.record, JSON.stringify({ time: Date.now(), dir, body }) + '\n', { mode: 0o600 })
const child = spawn(m.python, process.argv.slice(2), { cwd: m.root, env: { ...process.env, HERMES_PYTHON: m.python, HERMES_PYTHON_SRC_ROOT: m.root }, stdio: ['pipe','pipe','inherit'] })
writeFileSync(join(m.proof, 'gateway-process.json'), JSON.stringify({ proxy:process.pid, gateway:child.pid }), { mode:0o600 })
const requests = new Map()
const held = []
let stopped = false
function deny(body, reason) {
  if (stopped) return
  stopped = true
  log('denied', { id:body.id, method:body.method, reason })
  child.kill('SIGTERM')
  process.exitCode = 1
  process.stdin.pause()
}
function gate() {
  let content
  try { content = readFileSync(m.gate, 'utf8') } catch (error) {
    if (error.code === 'ENOENT') return null
    throw error
  }
  const value = JSON.parse(content)
  if (Date.now() >= value.expires) {
    deny({}, `Response hold expired before explicit release: ${value.token}`)
  }
  return value
}
function flush() {
  const current = gate()
  if (stopped) return
  while (held.length && (!current || current.token !== held[0].token)) {
    const row = held.shift()
    process.stdout.write(row.line + '\n')
    log('delivered', row.body)
  }
}
const ticker = setInterval(flush, 25)
createInterface({ input:process.stdin }).on('line', line => {
  const body = JSON.parse(line)
  log('request', body)
  const params = body.params ?? {}
  const forbidden = (!body.method && ('result' in body || 'error' in body)) || body.method === 'prompt.submit' || body.method === 'slash.exec' || /approval|consent|permission|auth\./.test(body.method ?? '') || (body.method?.startsWith('model.') && body.method !== 'model.options') || params.confirmed === true || (body.method === 'config.set' && (params.key !== 'reasoning' || params.scope !== 'session'))
  if (forbidden) {
    deny(body, 'No server-request replies, turns, grants, approvals, or global live-config writes in this suite.')
    return
  }
  if (stopped) return
  if (body.id !== undefined) requests.set(body.id, body)
  child.stdin.write(line + '\n')
})
createInterface({ input:child.stdout }).on('line', line => {
  const body = JSON.parse(line)
  if (body.method && body.id !== undefined) {
    deny(body, 'Server-originated requests are not permitted in this inert suite.')
    return
  }
  if (stopped) return
  log('response', body)
  const request = requests.get(body.id)
  const current = gate()
  if (request && current && request.method === current.method && (!current.key || request.params?.key === current.key)) {
    held.push({ line, body, token:current.token })
    log('held', { id:body.id, method:request.method, token:current.token })
  } else {
    process.stdout.write(line + '\n')
    log('delivered', body)
  }
  if (body.id !== undefined) requests.delete(body.id)
})
process.stdin.on('end', () => child.stdin.end())
child.on('exit', code => { clearInterval(ticker); process.exit(stopped ? 1 : code ?? 1) })
process.on('SIGTERM', () => child.kill('SIGTERM'))
process.on('SIGINT', () => child.kill('SIGINT'))
process.on('exit', () => child.kill('SIGTERM'))
