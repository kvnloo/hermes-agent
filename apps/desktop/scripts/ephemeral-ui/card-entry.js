/* global document, window, ResizeObserver */
// Boot for one sandboxed ephemeral-ui card document (bundled by build-kit.mjs against a pinned
// kvnloo/ephemeral-ui checkout; `@eui` resolves to its js/ folder). The kit's own make() draws every
// card: this file only places the cards, themes them and reports back to Hermes Desktop.
//
// Host contract: window.__EUI_CARDS = {
//   channel: string (echoed on every message),
//   scheme: 'light' | 'dark',
//   palette?: { bg, fg, card, ... } (hex colours from the desktop theme),
//   cards: [{ kind, app, input?, options? }]
// }
// The document posts { source: 'hermes-eui', channel, type: 'height' | 'intent' | 'error' | 'ready', ... }.
import { quiet, rng, Run } from '@eui/motion.js'
import { apply, loadThemes, state } from '@eui/themes.js'
import { catalog, loadApps } from '@eui/shell.js'
import { intentReady } from '@eui/intent-data.js'
import { KINDS_A } from '@eui/kinds-a.js'
import { KINDS_B } from '@eui/kinds-b.js'
import { KINDS_T } from '@eui/kinds-t.js'
import { KINDS_I } from '@eui/kinds-i.js'
import { KINDS_INFRA } from '@eui/kinds-infra.js'

const KINDS = { ...KINDS_A, ...KINDS_B, ...KINDS_T, ...KINDS_I, ...KINDS_INFRA }
const DATA = JSON.parse(document.getElementById('eui-data').textContent)
const CONFIG = window.__EUI_CARDS ?? { channel: '', scheme: 'dark', cards: [] }

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

function failTile(kind, reason) {
  const tile = document.createElement('div')
  tile.className = 'eui-fail'
  tile.setAttribute('role', 'alert')
  tile.textContent = `${kind}: ${reason}`
  post({ type: 'error', kind, reason })
  return tile
}

const isIntentKind = kind => kind.startsWith('intent') || kind.startsWith('intel')

async function boot() {
  const config = CONFIG
  await Promise.all([loadApps(), loadThemes()])
  const base = config.scheme === 'light' ? 'hermes-nous' : 'hermes-nous-dark'
  state.base = state.themes.find(theme => theme.id === base) ?? state.base
  state.over = { ...(config.palette ?? {}), scheme: config.scheme }
  apply(false)
  const root = document.getElementById('eui-root')
  const intentInput = config.cards.some(card => isIntentKind(card.kind)) ? await intentReady() : null
  for (const card of config.cards) {
    const cell = document.createElement('section')
    cell.className = 'eui-cell'
    cell.dataset.kind = card.kind
    root.append(cell)
    const K = KINDS[card.kind]
    if (!K) {
      cell.append(failTile(card.kind, 'not in this kit build'))
      continue
    }
    const app = catalog.byId[card.app] ?? { id: card.app, name: card.app, hex: null }
    const options = {
      ...(card.options ?? {}),
      onReview: request =>
        post({
          type: 'intent',
          detail: {
            kind: card.kind,
            action: 'request_review',
            label: 'Review requested (not approved)',
            ids: [`card:${card.kind}`],
            request
          }
        })
    }
    try {
      const made = K.make(app, rng(app.id + card.kind), card.input ?? (isIntentKind(card.kind) ? intentInput : undefined), options)
      cell.append(made.el)
      made.done?.catch?.(error => cell.replaceChildren(failTile(card.kind, error?.message ?? String(error))))
      if (made.play) quiet(Promise.resolve(made.play(new Run())))
    } catch (error) {
      cell.append(failTile(card.kind, error?.message ?? String(error)))
    }
  }
  document.documentElement.dataset.ready = 'true'
  post({ type: 'ready', kinds: config.cards.map(card => card.kind) })
}

// Every card intent (typed ids only) goes to the host; the host decides what reaches the agent.
document.addEventListener('eui:intent', event => post({ type: 'intent', detail: event.detail }))
let lastHeight = 0
new ResizeObserver(() => {
  const height = Math.ceil(document.getElementById('eui-root').getBoundingClientRect().height) + 8
  if (height !== lastHeight) post({ type: 'height', value: (lastHeight = height) })
}).observe(document.getElementById('eui-root'))
boot().catch(error => document.getElementById('eui-root').append(failTile('document', error?.message ?? String(error))))
