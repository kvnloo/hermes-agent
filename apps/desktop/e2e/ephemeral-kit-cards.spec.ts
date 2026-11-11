/**
 * E2E: every vendored ephemeral-ui card, booted the way Hermes Desktop boots it.
 *
 * Each card is the same offline document the desktop builds (document.ts) inside the same
 * sandbox (`allow-scripts`, opaque origin), hosted by a page that speaks the host side of the
 * card protocol. For every kind the spec checks that the card:
 *   - boots (ready), in light and dark, with a sane height and no error, page error or console error;
 *   - never touches the network (the document is offline; any request is a failure);
 *   - has no dead controls: each visible control either changes the card or emits an intent the
 *     desktop accepts (parseEphemeralMessage keeps it), never one it would silently drop;
 *   - dissolves into a receipt once the host starts its ring, and never while pinned.
 *
 * Runs in plain Chromium (no Electron, no backend): `pnpm exec playwright test e2e/ephemeral-kit-cards.spec.ts`.
 */

import { type Browser, chromium, expect, type Frame, type Page, test } from '@playwright/test'

import { ephemeralCardDocument } from '../src/components/assistant-ui/ephemeral/document'
import { EPHEMERAL_UI_CONNECTORS, EPHEMERAL_UI_KINDS } from '../src/components/assistant-ui/ephemeral/kit-meta.generated'
import { parseEphemeralMessage } from '../src/components/assistant-ui/ephemeral/model'

const CHANNEL = 'kitspec'

// The app a connector draws each kind with; kinds no connector names yet are drawn as the kit would.
const APP_FOR_KIND = new Map<string, string>()

for (const entry of Object.values(EPHEMERAL_UI_CONNECTORS)) {
  for (const [, kind] of entry.tools) {
    if (kind && !APP_FOR_KIND.has(kind)) {
      APP_FOR_KIND.set(kind, entry.app)
    }
  }
}

const appFor = (kind: string) => APP_FOR_KIND.get(kind) ?? 'github'

// Host page: one sandboxed frame, every message it posts recorded with the parent's parse result.
const HOST = `<!doctype html><html><body style="margin:0;width:560px">
<iframe id="card" sandbox="allow-scripts" style="width:560px;height:200px;border:0"></iframe>
<script>
  window.__msgs = []
  addEventListener('message', e => {
    if (e.source !== document.getElementById('card').contentWindow) return
    window.__msgs.push(e.data)
    if (e.data && e.data.type === 'height') document.getElementById('card').style.height = e.data.value + 'px'
  })
  window.__load = html => new Promise(r => { const f = document.getElementById('card'); f.onload = () => r(); window.__msgs = []; f.srcdoc = html })
  window.__ttl = ms => document.getElementById('card').contentWindow.postMessage({ source: 'hermes-eui-host', channel: '${CHANNEL}', type: 'ttl', ms }, '*')
</script></body></html>`

interface Msg {
  type?: string
  value?: number
  kind?: string
  reason?: string
  detail?: { action?: string; label?: string }
}

interface Boot {
  page: Page
  frame: Frame
  errors: string[]
  requests: string[]
}

let browser: Browser

test.beforeAll(async () => {
  browser = await chromium.launch()
})

test.afterAll(async () => {
  await browser?.close()
})

async function boot(kind: string, scheme: 'light' | 'dark', pinned = false): Promise<Boot> {
  const page = await browser.newPage({ viewport: { width: 600, height: 900 }, colorScheme: scheme })
  const errors: string[] = []
  const requests: string[] = []
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`))
  page.on('console', message => {
    if (message.type() === 'error') {
      errors.push(`console: ${message.text()}`)
    }
  })
  page.on('request', request => {
    const url = request.url()

    if (!/^(data|blob|about):/.test(url)) {
      requests.push(url)
    }
  })
  await page.setContent(HOST)
  const html = ephemeralCardDocument({ channel: CHANNEL, scheme, palette: {}, card: { kind, app: appFor(kind) }, pinned })
  await page.evaluate(doc => (window as unknown as { __load: (h: string) => Promise<void> }).__load(doc), html)
  await expect
    .poll(async () => (await messages(page)).some(m => m.type === 'ready' || m.type === 'error'), { timeout: 15_000, message: `${kind} boot` })
    .toBe(true)
  const frame = page.frames().find(f => f !== page.mainFrame())

  if (!frame) {
    throw new Error(`${kind}: no card frame`)
  }

  return { page, frame, errors, requests }
}

const messages = (page: Page) => page.evaluate(() => (window as unknown as { __msgs: Msg[] }).__msgs)

for (const kind of EPHEMERAL_UI_KINDS) {
  test.describe(`card ${kind}`, () => {
    for (const scheme of ['light', 'dark'] as const) {
      test(`boots offline in ${scheme}`, async () => {
        const { page, errors, requests } = await boot(kind, scheme)

        try {
          // Animated cards settle their height over their first second.
          await page.waitForTimeout(1200)
          const all = await messages(page)
          const failed = all.filter(m => m.type === 'error')
          expect(failed, `${kind} posted an error`).toEqual([])
          const heights = all.filter(m => m.type === 'height').map(m => m.value ?? 0)
          expect(heights.length, `${kind} never reported a height`).toBeGreaterThan(0)
          const last = heights.at(-1) ?? 0
          expect(last, `${kind} height`).toBeGreaterThan(60)
          expect(last, `${kind} height`).toBeLessThan(1600)
          expect(errors, `${kind} errors`).toEqual([])
          expect(requests, `${kind} reached the network`).toEqual([])

          // Every message the card posts is one the host understands.
          for (const raw of all) {
            expect(parseEphemeralMessage({ ...raw }, CHANNEL), `host drops ${JSON.stringify(raw).slice(0, 200)}`).not.toBeNull()
          }
        } finally {
          await page.close()
        }
      })
    }

    test('every control has a visible outcome the host accepts', async () => {
      test.setTimeout(180_000)
      const probe = await boot(kind, 'light')

      const count = await probe.frame.evaluate(() => {
        const sel = 'button, [role=button], [role=tab], [role=switch], [role=option], a.eu-btn'

        return [...document.querySelectorAll<HTMLElement>(sel)].filter(b => b.offsetParent && !b.classList.contains('eu-ttl')).length
      })

      await probe.page.close()
      const rows: { i: number; label: string; muts: number; intents: number; dropped: number }[] = []

      for (let i = 0; i < Math.min(count, 14); i++) {
        // A fresh card per control, as the kit's own dead-control probe does.
        const { page, frame } = await boot(kind, 'light')

        try {
          await page.waitForTimeout(900)
          const before = (await messages(page)).length

          const result = await frame.evaluate(async index => {
            const sel = 'button, [role=button], [role=tab], [role=switch], [role=option], a.eu-btn'
            const controls = [...document.querySelectorAll<HTMLElement>(sel)].filter(b => b.offsetParent && !b.classList.contains('eu-ttl'))
            const b = controls[index]

            if (!b) {return null}
            const label = (b.getAttribute('aria-label') || b.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 40)
            const disabled = b.hasAttribute('disabled') || b.getAttribute('aria-disabled') === 'true'
            let muts = 0
            const mo = new MutationObserver(list => (muts += list.length))
            mo.observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true })
            const wait = (ms: number) => new Promise(r => setTimeout(r, ms))

            if (b.classList.contains('hold')) {
              b.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
              await wait(1400)
              b.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }))
            } else {
              b.click()
            }

            await wait(450)
            mo.disconnect()

            return { label, muts, disabled }
          }, i)

          if (!result || result.disabled) {continue}
          const posted = (await messages(page)).slice(before).filter(m => m.type === 'intent')
          const dropped = posted.filter(m => parseEphemeralMessage({ ...m }, CHANNEL) === null).length
          rows.push({ i, label: result.label, muts: result.muts, intents: posted.length, dropped })
        } finally {
          await page.close()
        }
      }

      test.info().annotations.push({ type: 'controls', description: JSON.stringify(rows) })
      const dead = rows.filter(r => r.muts === 0 && r.intents === 0)
      expect(dead, `${kind}: controls with no outcome`).toEqual([])
      const dropped = rows.filter(r => r.dropped > 0)
      expect(dropped, `${kind}: intents the desktop would drop`).toEqual([])
    })

    test('dissolves into a receipt on its ring, never while pinned', async () => {
      const live = await boot(kind, 'light')

      try {
        await live.page.evaluate(() => (window as unknown as { __ttl: (ms: number) => void }).__ttl(700))
        await expect
          .poll(async () => (await messages(live.page)).find(m => m.type === 'dissolved'), { timeout: 6000, message: `${kind} dissolve` })
          .toBeTruthy()
      } finally {
        await live.page.close()
      }

      const kept = await boot(kind, 'light', true)

      try {
        await kept.page.evaluate(() => (window as unknown as { __ttl: (ms: number) => void }).__ttl(500))
        await kept.page.waitForTimeout(2000)
        expect((await messages(kept.page)).some(m => m.type === 'dissolved'), `${kind} dissolved while pinned`).toBe(false)
      } finally {
        await kept.page.close()
      }
    })
  })
}
