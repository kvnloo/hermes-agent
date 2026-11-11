/* global document, window, ResizeObserver */
// Boot for one sandboxed ephemeral-ui card (bundled by build-kit.mjs; `@eui` resolves to the kit's
// js/ folder). The kit's own make() draws the card and its shell carries the lifetime: a ring that
// runs out, then the card dissolves into a one-line receipt. Clicking the ring pins the card.
//
// Host contract: window.__EUI_CARD = {
//   channel: string (echoed on every message),
//   scheme: 'light' | 'dark',
//   palette?: { bg, fg, card, ... } (hex colours from the desktop theme),
//   card: { kind, app },
//   pinned?: boolean (draw it already kept, with no lifetime)
// }
// The host may post { source: 'hermes-eui-host', channel, type: 'ttl', ms } to start the lifetime
// once the card's task is done. The document posts { source: 'hermes-eui', channel, type, ... }:
// 'ready' { summary }, 'height' { value }, 'intent' { detail }, 'dissolved' { summary }, 'error'.
import { quiet, rng, Run } from '@eui/motion.js'
import { apply, loadThemes, state } from '@eui/themes.js'
import { catalog, loadApps } from '@eui/shell.js'
import { intentReady } from '@eui/intent-data.js'
import { KINDS_A } from '@eui/kinds-a.js'
import { KINDS_B } from '@eui/kinds-b.js'
import { KINDS_T } from '@eui/kinds-t.js'
import { KINDS_I } from '@eui/kinds-i.js'
import { KINDS_DOCK } from '@eui/kinds-dock.js'

const KINDS = { ...KINDS_A, ...KINDS_B, ...KINDS_T, ...KINDS_I, ...KINDS_DOCK }
const DATA = JSON.parse(document.getElementById('eui-data').textContent)
const CONFIG = window.__EUI_CARD ?? { channel: '', scheme: 'dark', card: null }
const root = document.getElementById('eui-root')

// The kit fetches its fixtures relative to its site; serve them from the bundled copy only.
window.fetch = url => {
  const key = String(url).replace(/^\.?\//, '').split('?')[0]
  return key in DATA
    ? Promise.resolve(new Response(JSON.stringify(DATA[key]), { headers: { 'content-type': 'application/json' } }))
    : Promise.reject(new TypeError(`Offline card document has no ${key}`))
}

// An opaque sandbox origin has no storage; the kit's theme and social state stay in memory.
try {
  window.localStorage.getItem('eui')
} catch {
  const memory = new Map()
  Object.defineProperty(window, 'localStorage', {
    configurable: true,
    value: {
      getItem: key => (memory.has(key) ? memory.get(key) : null),
      setItem: (key, value) => memory.set(key, String(value)),
      removeItem: key => memory.delete(key)
    }
  })
}
// Theme changes cross-fade with view transitions in the kit site; a card frame repaints directly.
delete document.startViewTransition

function post(message) {
  try {
    if (window.parent !== window) window.parent.postMessage({ source: 'hermes-eui', channel: CONFIG.channel, ...message }, '*')
  } catch {
    // Host gone.
  }
}

function fail(kind, reason) {
  const tile = document.createElement('div')
  tile.className = 'eui-fail'
  tile.setAttribute('role', 'alert')
  tile.textContent = `${kind}: ${reason}`
  root.replaceChildren(tile)
  post({ type: 'error', kind, reason })
}

const isIntentKind = kind => kind.startsWith('intent') || kind.startsWith('intel')

let card = null
let lifetime = null // { ms, anim } once the host starts the ring
let pinned = false
let syncing = false

function startLifetime(ms) {
  if (!card?.startTTL || pinned || card.classList.contains('gone')) return
  lifetime?.anim?.cancel()
  lifetime = { ms, anim: card.startTTL(ms, () => post({ type: 'dissolved', summary: card.summary })) }
}

// Touching the card means the person is still on it: the ring starts over.
const keepAlive = () => {
  if (lifetime && !pinned && lifetime.anim?.playState === 'running') startLifetime(lifetime.ms)
}

async function boot() {
  const spec = CONFIG.card
  if (!spec) return fail('document', 'no card')
  await Promise.all([loadApps(), loadThemes()])
  const base = CONFIG.scheme === 'light' ? 'hermes-nous' : 'hermes-nous-dark'
  state.base = state.themes.find(theme => theme.id === base) ?? state.base
  state.over = { ...(CONFIG.palette ?? {}), scheme: CONFIG.scheme }
  apply(false)
  const K = KINDS[spec.kind]
  if (!K) return fail(spec.kind, 'not in this kit build')
  const app = catalog.byId[spec.app] ?? { id: spec.app, name: spec.app, hex: null }
  const input = isIntentKind(spec.kind) ? await intentReady() : undefined
  const options = {
    onReview: request =>
      post({ type: 'intent', detail: { kind: spec.kind, action: 'request_review', label: 'Review requested (not approved)', ids: [`card:${spec.kind}`], request } })
  }
  const made = K.make(app, rng(app.id + spec.kind), input, options)
  card = made.el
  root.replaceChildren(card)
  made.done?.catch?.(error => fail(spec.kind, error?.message ?? String(error)))
  if (made.play) quiet(Promise.resolve(made.play(new Run())))
  if (CONFIG.pinned) {
    syncing = true
    card.querySelector('.eu-ttl')?.click()
    syncing = false
  }
  document.documentElement.dataset.ready = 'true'
  post({ type: 'ready', summary: card.summary ?? '' })
}

// Every card intent (typed ids only) goes to the host; the host decides what reaches the agent.
document.addEventListener('eui:intent', event => {
  const detail = event.detail ?? {}
  if (detail.action === 'pin' || detail.action === 'unpin') pinned = detail.action === 'pin'
  if (!syncing) post({ type: 'intent', detail: { ...detail, summary: card?.summary ?? '' } })
  keepAlive()
})
root.addEventListener('pointerdown', keepAlive)
root.addEventListener('keydown', keepAlive)
window.addEventListener('message', event => {
  const data = event.data
  if (!data || data.source !== 'hermes-eui-host' || data.channel !== CONFIG.channel) return
  if (data.type === 'ttl' && Number.isFinite(data.ms)) startLifetime(Math.max(500, Math.min(120000, data.ms)))
})
let lastHeight = 0
new ResizeObserver(() => {
  const height = Math.ceil(root.getBoundingClientRect().height) + 2
  if (height !== lastHeight) post({ type: 'height', value: (lastHeight = height) })
}).observe(root)
boot().catch(error => fail('document', error?.message ?? String(error)))
