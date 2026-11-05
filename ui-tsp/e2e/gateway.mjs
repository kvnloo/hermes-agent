#!/usr/bin/env node
// Transparent timing/recording shim around the REAL gateway. Never constructs app replies.
import { spawn } from 'node:child_process'
import { accessSync, appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { createServer, connect } from 'node:net'
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
// Modes: the gateway shim (spawned by the frontend, wraps the real Python helper) or, with
// --ws-proxy, the long-lived WebSocket recorder it starts for the attach-style gateway.
const proxyMode = process.argv[2] === '--ws-proxy'
const child = proxyMode ? null : spawn(m.python, process.argv.slice(2), { cwd: m.srcRoot ?? m.root, env: { ...process.env, HERMES_PYTHON: m.python, HERMES_PYTHON_SRC_ROOT: m.srcRoot ?? m.root }, stdio: ['pipe','pipe','inherit'] })
if (!proxyMode) writeFileSync(join(m.proof, 'gateway-process.json'), JSON.stringify({ proxy:process.pid, gateway:child.pid }), { mode:0o600 })
const requests = new Map()
const held = []
let stopped = false
function deny(body, reason) {
  if (stopped) return
  stopped = true
  log('denied', { id:body.id, method:body.method, reason })
  child?.kill('SIGTERM')
  if (proxyMode) for (const c of wsClients) c.destroy()
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
    row.send()
    log('delivered', row.body)
  }
}
// Explicit fixture replay: notifications only, never substitutes for real RPC replies.
let fixtureLines = 0
const fixtureTypes = new Set(['message.start', 'message.delta', 'reasoning.delta', 'tool.start', 'tool.complete', 'message.complete', 'todo.updated'])
function replay() {
  if (!m.fixtureEvents || stopped) return
  let text
  try { text = readFileSync(m.fixtureEvents, 'utf8') } catch (error) { if (error.code === 'ENOENT') return; throw error }
  const lines = text.split('\n').slice(0, -1)
  for (; fixtureLines < lines.length; fixtureLines++) {
    const params = JSON.parse(lines[fixtureLines])
    if (!fixtureTypes.has(params.type) || typeof params.session_id !== 'string') throw new Error('Invalid fixture notification')
    const body = { jsonrpc:'2.0', method:'event', params }
    log('fixture-replay', body)
    if (wsClients.length) wsClients[0].write(wsFrame(JSON.stringify(body)))
    else process.stdout.write(JSON.stringify(body) + '\n')
  }
}
const ticker = setInterval(() => { flush(); replay() }, 25)
// The Tern plugin frontend asks for reasoning streaming on every new session
// (frontend/src/session/thoughts.ts). It names one session and a display word; the real gateway
// decides (Hermes 22063fc answers 4002 unknown key and writes nothing). The settings journey's
// byte-identical config readback still catches any future write.
function thoughtsToggle(params) {
  return params.key === 'show_reasoning' && typeof params.session_id === 'string' && ['on', 'off'].includes(params.value) &&
    Object.keys(params).every(key => ['key', 'session_id', 'value'].includes(key))
}
// One client->gateway policy for both transports. Returns true when the request may be forwarded.
function admit(line) {
  const body = JSON.parse(line)
  log('request', body)
  const params = body.params ?? {}
  const forbidden = (!body.method && ('result' in body || 'error' in body)) || body.method === 'prompt.submit' || (body.method === 'slash.exec' && !(params.command === 'context' && typeof params.session_id === 'string' && Object.keys(params).every(key => ['command','session_id'].includes(key)))) || /approval|consent|permission|auth\./.test(body.method ?? '') || (body.method?.startsWith('model.') && body.method !== 'model.options') || params.confirmed === true || (body.method === 'config.set' && !(params.key === 'reasoning' && params.scope === 'session') && !thoughtsToggle(params))
  if (forbidden) {
    deny(body, 'No server-request replies, turns, grants, approvals, or global live-config writes in this suite.')
    return false
  }
  if (stopped) return false
  if (body.id !== undefined) requests.set(body.id, body)
  return true
}
// One gateway->client policy for both transports; `send` delivers the original bytes.
function observe(line, send) {
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
    held.push({ line, body, token:current.token, send })
    log('held', { id:body.id, method:request.method, token:current.token })
  } else {
    send()
    log('delivered', body)
  }
  if (body.id !== undefined) requests.delete(body.id)
}
let attachPending = null
if (!proxyMode) {
createInterface({ input:process.stdin }).on('line', line => { if (admit(line)) child.stdin.write(line + '\n') })
createInterface({ input:child.stdout }).on('line', line => {
  // Hermes >= the WebSocket gateway prints one attach handshake ({url, protocols}) and then speaks
  // JSON-RPC over that socket. Route the frontend through a recording proxy with the same policy.
  let attach = null
  try { attach = JSON.parse(line) } catch {}
  if (attach && typeof attach.url === 'string' && attach.url.startsWith('ws://') && attach.id === undefined && !attach.method) {
    // The frontend execFile()s this helper and reads its whole stdout, so the recorder must outlive
    // it: reuse or start one detached proxy per upstream (same env => same owned-scope cleanup).
    attachPending = ensureProxy(attach).then(rewritten => {
      log('attach', { upstream:attach.url, proxy:rewritten.url })
      process.stdout.write(JSON.stringify(rewritten) + '\n')
    }).catch(error => deny({}, `WebSocket recorder failed: ${error}`))
    return
  }
  observe(line, () => process.stdout.write(line + '\n'))
})
process.stdin.on('end', () => child.stdin.end())
child.on('exit', code => { clearInterval(ticker); Promise.resolve(attachPending).finally(() => process.exit(stopped ? 1 : code ?? 1)) })
process.on('SIGTERM', () => child.kill('SIGTERM'))
process.on('SIGINT', () => child.kill('SIGINT'))
process.on('exit', () => child.kill('SIGTERM'))
} else {
  // Recorder daemon: argv[3] is the upstream grant JSON.
  const attach = JSON.parse(process.argv[3])
  wsProxy(attach).then(rewritten => writeFileSync(join(m.proof, 'ws-proxy.json'), JSON.stringify({ upstream:attach.url, url:rewritten.url, pid:process.pid }), { mode:0o600 }))
    .catch(error => { log('denied', { reason:`WebSocket recorder failed: ${error}` }); process.exit(1) })
}


// ---- WebSocket recorder (raw RFC 6455 framing; forwards original bytes once admitted) ----
const wsClients = []
function wsFrame(text) {
  const payload = Buffer.from(text)
  const n = payload.length
  const head = n < 126 ? Buffer.from([0x81, n]) : n < 65536 ? Buffer.from([0x81, 126, n >> 8, n & 255]) : Buffer.concat([Buffer.from([0x81, 127]), (() => { const b = Buffer.alloc(8); b.writeBigUInt64BE(BigInt(n)); return b })()])
  return Buffer.concat([head, payload])
}
// Splits a byte stream into whole frames; calls onMessage(textOrNull, rawBuffers) per message.
function frameReader(onMessage) {
  let buf = Buffer.alloc(0), parts = [], raws = [], opcode = 0
  return chunk => {
    buf = Buffer.concat([buf, chunk])
    for (;;) {
      if (buf.length < 2) return
      const fin = buf[0] & 0x80, op = buf[0] & 0x0f, masked = buf[1] & 0x80
      let len = buf[1] & 0x7f, off = 2
      if (len === 126) { if (buf.length < 4) return; len = buf.readUInt16BE(2); off = 4 }
      else if (len === 127) { if (buf.length < 10) return; len = Number(buf.readBigUInt64BE(2)); off = 10 }
      const maskAt = off; if (masked) off += 4
      if (buf.length < off + len) return
      const raw = buf.subarray(0, off + len)
      let payload = Buffer.from(buf.subarray(off, off + len))
      if (masked) for (let i = 0; i < payload.length; i++) payload[i] ^= buf[maskAt + (i & 3)]
      buf = buf.subarray(off + len)
      if (op >= 8) { onMessage(null, [raw], op); continue }
      if (op !== 0) opcode = op
      parts.push(payload); raws.push(raw)
      if (fin) { const text = opcode === 1 ? Buffer.concat(parts).toString('utf8') : null; const r = raws; parts = []; raws = []; onMessage(text, r, opcode) }
    }
  }
}
async function wsProxy(attach) {
  const upstream = new URL(attach.url)
  const server = createServer(client => {
    const up = connect(Number(upstream.port), upstream.hostname)
    let handshake = Buffer.alloc(0), upgraded = false
    const fromServer = frameReader((text, raws) => {
      if (text === null) { for (const r of raws) client.write(r); return }
      observe(text, () => { for (const r of raws) client.write(r) })
    })
    let serverHead = Buffer.alloc(0), serverUpgraded = false
    up.on('data', chunk => {
      if (serverUpgraded) return fromServer(chunk)
      serverHead = Buffer.concat([serverHead, chunk])
      const end = serverHead.indexOf('\r\n\r\n')
      if (end < 0) return
      log('ws-upgrade', { status: serverHead.subarray(0, serverHead.indexOf('\r\n')).toString('latin1') })
      client.write(serverHead.subarray(0, end + 4)); serverUpgraded = true
      const rest = serverHead.subarray(end + 4); if (rest.length) fromServer(rest)
    })
    const fromClient = frameReader((text, raws) => {
      if (text === null) { for (const r of raws) up.write(r); return }
      if (admit(text)) for (const r of raws) up.write(r)
    })
    client.on('data', chunk => {
      if (upgraded) return fromClient(chunk)
      handshake = Buffer.concat([handshake, chunk])
      const end = handshake.indexOf('\r\n\r\n')
      if (end < 0) return
      // Same request, upstream Host, and no permessage-deflate so frames stay readable.
      const head = handshake.subarray(0, end).toString('latin1').split('\r\n')
        .filter(h => !/^sec-websocket-extensions:/i.test(h))
        .map(h => /^host:/i.test(h) ? `Host: ${upstream.host}` : h).join('\r\n') + '\r\n\r\n'
      log('ws-connect', { request: head.split('\r\n')[0].replace(/ticket[^ ]*/,'ticket=<redacted>') })
      up.write(head); upgraded = true; wsClients.push(client)
      const rest = handshake.subarray(end + 4); if (rest.length) fromClient(rest)
    })
    up.on('error', e => log('ws-error', { side:'upstream', error:String(e) })); client.on('error', e => log('ws-error', { side:'client', error:String(e) }))
    const close = () => { client.destroy(); up.destroy(); const i = wsClients.indexOf(client); if (i >= 0) wsClients.splice(i, 1) }
    client.on('close', close); up.on('close', close); client.on('error', close); up.on('error', close)
  })
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve) })
  process.on('exit', () => server.close())
  const proxied = new URL(attach.url); proxied.port = String(server.address().port)
  return { ...attach, url: proxied.toString() }
}

async function ensureProxy(attach) {
  const file = join(m.proof, 'ws-proxy.json')
  const alive = pid => { try { process.kill(pid, 0); return true } catch { return false } }
  const read = () => { try { return JSON.parse(readFileSync(file, 'utf8')) } catch { return null } }
  let current = read()
  if (!current || current.upstream !== attach.url || !alive(current.pid)) {
    if (current && alive(current.pid)) process.kill(current.pid, 'SIGTERM')
    writeFileSync(file, '', { mode:0o600 })
    const daemon = spawn(process.execPath, [fileURLToPath(import.meta.url), '--ws-proxy', JSON.stringify(attach)], { detached:true, stdio:'ignore', env:process.env })
    daemon.unref()
    const end = Date.now() + 5000
    while (!(current = read()) && Date.now() < end) await new Promise(r => setTimeout(r, 50))
    if (!current) throw new Error('recorder did not start')
  }
  return { ...attach, url: current.url }
}
