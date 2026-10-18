// Deterministic presentation-only fixture; no backend, microphone or model calls.
import { readFileSync } from 'node:fs'

import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'

import { App } from '../../app.js'

const tern = new Session(process.stdin, process.stdout, { app: 'hermes', features: ['edit', 'undo', 'send'], record: '' })

if (!await tern.handshake()) {throw new Error('Tern handshake required')}
const gw = new GatewayClient()

gw.request = async <T>(method: string): Promise<T> => {
  const value = method === 'model.options' ? {
    model: 'fixture-model', provider: 'ready-a', providers: [
      { slug: 'ready-a', name: 'Ready A', authenticated: true, models: ['fixture-model'] },
      { slug: 'locked-a', name: 'Locked A', authenticated: false, models: [] },
      { slug: 'ready-b', name: 'Ready B', authenticated: true, models: ['second-model'] },
      { slug: 'locked-b', name: 'Locked B', authenticated: false, models: [] },
      { slug: 'ready-c', name: 'Ready C', authenticated: true, models: ['third-model'] }
    ]
  } : {}

  return value as T
}

const app = new App(tern, gw, 'fixture')
app.sid = 'live-ux-fixture'
app.usage = { context_used: 3000, context_max: 100000, cost_usd: 0.12 }
app.info = { model: 'nvidia/nemotron-3.5-super-v1:free', provider: 'ready-a', cwd: '/fixture/long-project-directory', branch: 'fix/tern-live-ux-pass1', reasoning_effort: 'high' }
const running = app.run()
app.transcript.clear()
app.transcript.push({
  id: 'live-ux', kind: 'turn', rev: 1, status: 'done', startedAt: 1000, endedAt: 1041,
  usage: { context_used: 3000, context_max: 100000, cost_usd: 0.12 },
  blocks: [
    { id: 'empty', kind: 'thinking', text: ' \n\t ', startedAt: 1000, endedAt: 1001 },
    { id: 'command', kind: 'tool', call: { id: 'command', name: 'terminal', argsText: '', args: { command: 'printf LIVE_UX_SINGLE_COMMAND', workdir: '/fixture' }, context: 'printf LIVE_UX_SINGLE_COMMAND', startedAt: 1000, finishedAt: 1041, startedObserved: true, status: 'done', result: { output: 'LIVE_UX_OUTPUT', exit_code: 0 } } },
    { id: 'answer', kind: 'text', text: 'LIVE_UX_VISIBLE_ANSWER' }
  ]
})
app.changed()
const modeFile = process.argv[2]!
let busy = false

const timer = setInterval(() => {
  const next = readFileSync(modeFile, 'utf8').trim() === 'busy'

  if (next === busy) { return }
  busy = next
  app.busy = busy ? { since: {}, startedAt: Date.now(), label: 'Working' } : null
  app.changed()
}, 100)

try { await running } finally { clearInterval(timer) }
