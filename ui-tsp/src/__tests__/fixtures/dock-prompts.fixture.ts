// Presentation/dispatch fixture: no model, microphone or real command execution.
import { appendFileSync, readFileSync } from 'node:fs'

import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'

import { App } from '../../app.js'

const [modeFile, logFile] = process.argv.slice(2) as [string, string]
const log = (value: unknown) => appendFileSync(logFile, JSON.stringify(value) + '\n')
const tern = new Session(process.stdin, process.stdout, { app: 'hermes', features: ['edit', 'undo', 'send'], record: '' })
if (!await tern.handshake()) { throw new Error('Tern handshake required') }
const gw = new GatewayClient()
let capture = ''
gw.request = async <T>(method: string, params?: Record<string, unknown>): Promise<T> => {
  log({ method, params })
  if (method === 'voice.dictate.start') {
    capture = String(params?.capture_id)
    setTimeout(() => gw.emit('event', {
      type: 'voice.dictation', session_id: 'dock-fixture',
      payload: { capture_id: capture, state: 'recording', text: 'UNSENT_PARTIAL' }
    }), 10)
  }
  return {} as T
}
const app = new App(tern, gw, 'fixture')
app.sid = 'dock-fixture'
app.info = { model: 'nvidia/nemotron-3.5-super-vl:free', provider: 'openrouter', cwd: '/fixture' }
app.composer.vim.enabled = true
const running = app.run()
app.transcript.clear()
app.transcript.notice('DOCK_PROMPTS_FIXTURE — no model/audio calls')
app.changed()
let mode = ''
const timer = setInterval(() => {
  const next = readFileSync(modeFile, 'utf8').trim()
  if (next === mode) { return }
  mode = next
  app.overlays.slice().forEach(o => app.close(o))
  if (mode === 'vim') { app.dictation.reset(); app.changed(); return }
  const approval = mode === 'approval'
  if (mode === 'dictation') { app.dictation.toggle() }
  const params = approval ? {
    command: 'rm -rf /home/fixture/.hermes/profiles/clean/cache/scratch/approval-safety-owned-target-with-a-long-absolute-path/owned-disposable-directory-with-a-long-name/DO_NOT_RUN',
    description: 'Recursive removal permanently deletes the exact target directory and everything inside it. Review this command before allowing execution.',
    allow_permanent: true
  } : {
    supports_notes: true, deadline_at: null,
    questions: [{ qid: 'target', question: 'Which deployment target should receive this release?',
      choices: Array.from({ length: mode === 'dictation' ? 3 : 12 }, (_, i) => `Target ${i + 1} — ordinary deployment choice`) }]
  }
  gw.emit('request', { id: mode, method: approval ? 'approval' : 'clarify',
    params: { session_id: app.sid, ...params },
    respond: (result: unknown) => log({ answer: mode, result }), fail: (error: unknown) => log({ error }) })
  app.changed()
}, 100)
try { await running } finally { clearInterval(timer) }
