// Real App dispatch/presentation with explicit deterministic gateway replies; no model calls.
import { appendFileSync, readFileSync } from 'node:fs'

import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'

import { App } from '../../app.js'

const control = process.argv[2]!
const tern = new Session(process.stdin, process.stdout, { app: 'hermes', features: ['edit', 'undo', 'send'], record: '' })
if (!await tern.handshake()) { throw new Error('Tern handshake required') }
const gw = new GatewayClient()
let generation = 1
const reports: Record<string, string> = {
  skills: 'Skills commands\n┌────────────────┬─────────────────────────┐\n│ Command        │ Description             │\n├────────────────┼─────────────────────────┤\n│ /skills list   │ List installed skills   │\n│ /skills search │ Search skill hub        │\n└────────────────┴─────────────────────────┘',
  usage: 'Session Token Usage\n────────────────────────────────────────\nModel: fixture-model\nInput tokens:                 100\nOutput tokens:                20\nTotal tokens:                 120\nAPI calls:                    1',
  context: 'Conversation: 2 messages\n  user: 1, assistant: 1, tool: 0, system: 0\nModel: fixture-model\nProvider: fixture'
}
gw.request = async <T>(method: string, params?: unknown): Promise<T> => {
  appendFileSync(control+'.rpc.jsonl', JSON.stringify({ method, params })+'\n')
  let value: unknown = {}
  if (method === 'setup.status') { value = { provider_configured: true } }
  if (method === 'session.create') { value = { session_id: `fixture-${++generation}` } }
  if (method === 'complete.slash') {
    const text = (params as {text: string}).text
    value = { items: text === '/q' ? [{ text: '/q', display: '/q', kind: 'command', meta: 'Queue a prompt (alias for /queue)' }] : [], replace_from: 1 }
  }
  if (method === 'slash.exec') {
    const name = (params as {command: string}).command.split(' ')[0]!
    value = { output: name === 'context' && generation > 1 ? 'Conversation is empty (no messages yet).' : reports[name] ?? 'No queued prompts.' }
  }
  if (method === 'operations.report') {
    value = { view: 'mcp-list', state: 'ready', scope: 'isolated fixture', message: 'Read-only Hermes inventory.', read_only: true,
      rows: [{ name: 'fixture-ctx', details: ['Environment configured (values withheld)', 'Literal *name* and [brackets] are data.'] }] }
  }
  return value as T
}
const app = new App(tern, gw, 'slash-fixture')
app.sid = 'fixture-1'
app.info = { model: 'fixture-model', provider: 'fixture' }
const running = app.run()
app.transcript.notice('SLASH_FIXTURE_READY — gateway replies are deterministic fixtures')
app.changed()
let previous = ''
const timer = setInterval(async () => {
  const next = readFileSync(control, 'utf8').trim()
  if (next === previous) { return }
  previous = next
  for (const overlay of [...app.overlays]) { app.close(overlay) }
  if (next === 'fixture:seed') {
    generation = 1
    app.sid = 'fixture-1'
    app.transcript.clear()
    app.composer.set('')
  } else if (next.startsWith('complete:')) {
    app.composer.set(next.slice(9))
  } else {
    app.composer.set('')
    await app.slash(next)
  }
  app.changed()
}, 100)
try { await running } finally { clearInterval(timer) }
