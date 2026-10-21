// Real App presentation with deterministic gateway responses; no model calls.
import { readFileSync } from 'node:fs'

import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'

import { App } from '../../app.js'

const tern = new Session(process.stdin, process.stdout, { app: 'hermes', features: ['edit', 'undo', 'send'], record: '' })

if (!await tern.handshake()) { throw new Error('Tern handshake required') }
const gw = new GatewayClient()
const plan = { enabled: true, generating: false, plan: { id: 'f3-plan', revision: 1, text: '# Goal\n\nBuild the keyboard path.\n\n## Test\n\nRun rendered regressions.\n\n## Finish\n\nReview captures.', annotations: [], decision: 'pending' } }

gw.request = async <T>(method: string, params?: Record<string, unknown>): Promise<T> => {
  if (method === 'prompt.submit' && mode === 'denial') {
    setTimeout(() => {
      app.transcript.text('F3_DENIED_SAFELY')
      app.transcript.complete({ text: 'F3_DENIED_SAFELY', status: 'complete' })
      app.busy = null
      app.changed()
    }, 150)
  }
  if (method === 'request.answer') { return { status: 'ok' } as T }

  if (method === 'image.attach') { return { attached: true, path: params?.path, bytes: 68 } as T }

  const value = method === 'plan.status' ? plan : method === 'commands.catalog' ? { categories: [{ name: 'Final commands', pairs: [['/f3-last-command', 'F3_HELP_END_MARKER']] }] } : method === 'settings.get' ? {
    profile: 'fixture', fields: Object.fromEntries(['general', 'display', 'tools', 'voice', 'memory'].map(category => [category, { key: category, category, label: `${category} option`, type: 'boolean', value: true, default: false }]))
  } : method === 'complete.slash' ? { items: [] } : {}

  return value as T
}

const app = new App(tern, gw, 'fixture')
app.sid = 'f3-fixture'
app.info = { model: 'fixture', provider: 'fixture', cwd: '/fixture', reasoning_effort: 'high' }
const running = app.run()
app.transcript.clear()
app.transcript.user('F3 user prompt')
app.transcript.push({ id: 'f3-answer', kind: 'turn', rev: 1, status: 'done', startedAt: 1000, endedAt: 1041, blocks: [{ id: 'answer', kind: 'text', text: 'F3_VISIBLE_ANSWER' }] })
app.changed()
let mode = ''

const timer = setInterval(() => {
  const next = readFileSync(process.argv[2]!, 'utf8').trim()

  if (next === mode) { return }
  mode = next

  for (const overlay of [...app.overlays]) { app.close(overlay) }

  if (mode === 'plan') { void app.reviewPlan() }

  if (mode === 'help') { void app.slash('/help') }

  if (mode === 'settings') { void app.slash('/settings') }

  if (mode === 'images') { app.composer.set(''); app.attachments.clear() }

  if (mode === 'denial') {
    app.composer.set('')
    app.attachments.clear()
    app.transcript.clear()
    app.transcript.start(1)
    app.transcript.text('F3 earlier tool work')
    app.busy = { label: 'Waiting for approval', startedAt: 1, since: {} }
    gw.emit('request', { id: 'f3-approval', method: 'approval', params: { command: 'printf safe-fixture', request_id: 'f3-approval', session_id: app.sid }, respond() {}, fail() {} })
  }

  app.changed()
}, 100)

try { await running } finally { clearInterval(timer) }
