// Presentation and dispatch fixture. No model or network calls.
import { Session } from '@stencil-hq/tern'
import { GatewayClient } from '@tui/gatewayClient.js'

import { App } from '../../app.js'

const tern = new Session(process.stdin, process.stdout, { app: 'hermes', features: ['edit', 'undo', 'send'], record: '' })

if (!await tern.handshake()) {throw new Error('Tern handshake required')}
const gw = new GatewayClient()
let visible = true
let saved = true

gw.request = async <T>(method: string, params?: Record<string, unknown>): Promise<T> => {
  let result: unknown = {}

  if (method === 'settings.get') {
    result = { profile: 'f4-fixture', fields: {
      'display.show_reasoning': { category: 'display', default: true, description: 'Show reasoning during the active turn.', type: 'boolean', value: saved }
    } }
  } else if (method === 'settings.set') {
    saved = params?.value === true
    result = { key: params?.key, value: saved }
  } else if (method === 'config.set') {
    visible = params?.value !== 'hide'
    result = { value: params?.value }
  } else if (method === 'config.get') {
    result = { value: 'medium', display: visible ? 'show' : 'hide' }
  } else if (method === 'complete.slash') {
    result = { items: [] }
  }

  return result as T
}

const app = new App(tern, gw, 'fixture')
app.sid = 'f4-fixture'
app.info = { model: 'fixture', cwd: process.cwd(), reasoning_effort: 'medium' }
const running = app.run()
app.transcript.clear()
app.composer.take('F4_ALREADY_SENT')
const text = '[RELATIVE_README](README.md#L1-L2), [FILE_README](file://' + process.cwd() + '/README.md#L1-L2), [WEB_CONTROL](https://example.com).'
app.transcript.start(0)
app.transcript.text(text, 1)
app.transcript.complete({ status: 'complete', text }, 2)
app.transcript.start(Date.now())
app.transcript.reasoning('F4 reasoning before Settings. ', Date.now())
app.changed()

let tick = 0
const timer = setInterval(() => {
  if (visible) {
    app.transcript.reasoning(`Delta ${++tick}. `, Date.now())
    app.changed()
  }
}, 2000)

try { await running } finally { clearInterval(timer) }
