/**
 * E2E: ephemeral-ui kit cards inside a real Hermes Desktop chat turn.
 *
 * The mock provider answers with an `openui-v2` Board holding EphemeralCards panels. The test
 * drives the full chain (electron -> hermes serve -> provider -> renderer), then checks the cards
 * inside their sandboxed frames: every one of the kit's 50 card.v0 kinds draws without a failure
 * tile or horizontal overflow, a pick inside a card reaches the host, and "Add to chat" puts it in
 * the composer without sending anything.
 *
 * Prerequisite: `pnpm run build` must have been run so dist/ exists.
 */

import { MOCK_REPLY } from '../../../tests-js/scripts/mock-server'
import { EPHEMERAL_UI_KINDS } from '../src/components/assistant-ui/embeds/ephemeral-ui-kinds.generated'

import { type MockBackendFixture, setupMockBackend, waitForAppReady } from './fixtures'
import { expect, test } from './test'

const DEMO_TRIGGER = 'E2E_EUI_DEMO'
const ALL_TRIGGER = 'E2E_EUI_ALL'

const DEMO_FENCE = [
  '```openui-v2',
  'root = Board("Morning triage", "Sample data from the ephemeral-ui kit: mail, CI, an approval and a session trace.", [kit])',
  'kit = EphemeralCards("Triage cards", [{kind: "inbox", app: "gmail"}, {kind: "ci", app: "github"}, {kind: "approve"}, {kind: "trace-summary"}])',
  '```',
  '',
  'These are the kit\'s sample cards; pick anything to add it to the chat.'
].join('\n')

// Five panels of ten cards cover all 50 kinds in one board (8 panels x 12 cards is the limit).
const groups = Array.from({ length: 5 }, (_, i) => EPHEMERAL_UI_KINDS.slice(i * 10, i * 10 + 10))

const ALL_FENCE = [
  '```openui-v2',
  `root = Board("Every ephemeral-ui card", "All ${EPHEMERAL_UI_KINDS.length} card kinds. Sample data.", [${groups.map((_, i) => 'g' + i).join(', ')}])`,
  ...groups.map((kinds, i) => `g${i} = EphemeralCards("Cards ${i * 10 + 1}-${i * 10 + kinds.length}", [${kinds.map(kind => `{kind: "${kind}"}`).join(', ')}])`),
  '```',
  '',
  'All kit cards, sample data.'
].join('\n')

let fixture: MockBackendFixture | null = null

test.beforeAll(async () => {
  fixture = await setupMockBackend({
    mockServer: {
      replyForPrompt: prompt => (prompt.includes(ALL_TRIGGER) ? ALL_FENCE : prompt.includes(DEMO_TRIGGER) ? DEMO_FENCE : MOCK_REPLY)
    }
  })
  await waitForAppReady(fixture!, 120_000)
})

test.afterAll(async () => {
  await fixture?.cleanup()
  fixture = null
})

async function send(text: string) {
  const page = fixture!.page
  const composer = page.locator('[contenteditable="true"]').first()
  await watchFrames()
  await composer.click()
  // Start from an empty draft: an earlier test may have added a card pick to it.
  await page.keyboard.press('ControlOrMeta+A')
  await page.keyboard.press('Backspace')
  await composer.type(text)
  await page.keyboard.press('Enter')
}

// The thread re-keys a finished turn's rows (when the gateway binds the stored turn, and again on
// a later history read a few seconds on), which remounts every embed in it. Interactions wait for
// a quiet window with no frame added or removed. send() arms the watch before the turn starts.
async function watchFrames() {
  await fixture!.page.evaluate(() => {
    const w = window as unknown as { __euiFrameChange?: number }
    w.__euiFrameChange = performance.now()

    if ((w as { __euiWatching?: boolean }).__euiWatching) {return
    ;}

(w as { __euiWatching?: boolean }).__euiWatching = true
    new MutationObserver(records => {
      const touched = records.some(r =>
        [...r.addedNodes, ...r.removedNodes].some(n => n instanceof Element && (n.tagName === 'IFRAME' || !!n.querySelector('iframe'))))

      if (touched) {w.__euiFrameChange = performance.now()}
    }).observe(document.body, { childList: true, subtree: true })
  })
}

async function framesSettled(quietMs = 9000, timeoutMs = 60_000) {
  const page = fixture!.page
  await expect
    .poll(() => page.evaluate(() => performance.now() - (window as unknown as { __euiFrameChange: number }).__euiFrameChange), {
      intervals: [500],
      timeout: timeoutMs
    })
    .toBeGreaterThan(quietMs)
}

test.describe('ephemeral-ui cards', () => {
  test('a pick inside a kit card goes to the composer only when asked', async () => {
    const page = fixture!.page
    await send(`${DEMO_TRIGGER} show me my morning triage`)

    const region = page.getByRole('region', { name: 'Triage cards' })
    await expect(region).toBeVisible({ timeout: 60_000 })
    await expect(region.locator('iframe[sandbox="allow-scripts"]')).toHaveCount(1)
    const frame = page.frameLocator('iframe[title="Triage cards"]')
    await expect(frame.locator('html[data-ready="true"]')).toHaveCount(1, { timeout: 30_000 })
    await expect(frame.locator('.eui-cell')).toHaveCount(4)
    await expect(frame.locator('.eui-fail')).toHaveCount(0)
    await expect(frame.locator('.eui-cell[data-kind="inbox"] .eu-card')).toBeVisible()
    await framesSettled()
    await expect(frame.locator('html[data-ready="true"]')).toHaveCount(1, { timeout: 30_000 })
    await page.screenshot({ path: test.info().outputPath('triage-board.png') })

    // The first message is the card's own guess; picking another one corrects it and reports the pick.
    await frame.locator('.eui-cell[data-kind="inbox"] li').nth(1).click()
    await expect(region.getByText(/^Picked: /)).toBeVisible()
    await region.getByRole('button', { name: 'Add to chat' }).click()
    await expect(region.getByText('Added to the composer. Nothing was sent.', { exact: false })).toBeVisible()
    await expect(page.locator('[contenteditable="true"]').first()).toContainText('[ephemeral-ui inbox · gmail · sample data]')
    await page.screenshot({ path: test.info().outputPath('triage-added.png') })
  })

  test('draws all 50 card.v0 kinds without failures or overflow', async () => {
    const page = fixture!.page
    await send(`${ALL_TRIGGER} show every card`)
    await expect(page.getByRole('region', { name: 'Cards 41-50' })).toBeVisible({ timeout: 60_000 })
    await framesSettled()

    let drawn = 0

    for (const [i, kinds] of groups.entries()) {
      const title = `Cards ${i * 10 + 1}-${i * 10 + kinds.length}`
      await expect(page.getByRole('region', { name: title })).toBeVisible({ timeout: 60_000 })
      const frame = page.frameLocator(`iframe[title="${title}"]`)
      await expect(frame.locator('html[data-ready="true"]')).toHaveCount(1, { timeout: 30_000 })
      await expect(frame.locator('.eui-fail')).toHaveCount(0)

      for (const kind of kinds) {
        await expect(frame.locator(`.eui-cell[data-kind="${kind}"] > *`).first(), kind).toBeVisible()
      }

      const overflowing = await frame.locator('.eui-cell').evaluateAll(cells =>
        cells.filter(cell => cell.scrollWidth > cell.clientWidth + 1).map(cell => (cell as HTMLElement).dataset.kind))

      expect(overflowing, title).toEqual([])
      drawn += kinds.length
    }

    expect(drawn).toBe(EPHEMERAL_UI_KINDS.length)
    await page.screenshot({ path: test.info().outputPath('all-kinds.png'), fullPage: true })
  })
})
