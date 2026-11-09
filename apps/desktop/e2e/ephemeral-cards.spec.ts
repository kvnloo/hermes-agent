/**
 * E2E: ephemeral-ui cards grow from real MCP tool calls.
 *
 * The mock model (E2E_EPHEMERAL_ACME) runs one turn that calls three MCP tools on the sample-app
 * servers in e2e/fixtures/sample-apps-mcp.py: Gmail, Google Calendar and GitHub. The real backend
 * registers them as mcp__<app>__<tool> and executes them; the renderer must:
 *   - grow each app's card under its tool row, one per step, while the turn runs;
 *   - dissolve a card into a one-line receipt once the agent has moved on and its ring runs out;
 *   - on pin, collapse the card into a chip on the input bar that opens it in a popup;
 *   - never send anything: the chip's Add to chat only puts one line in the composer.
 *
 * Prerequisite: `pnpm run build` must have been run so dist/ exists.
 */

import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, type Page, test } from '@playwright/test'

import { EPHEMERAL_GH_TRIGGER, EPHEMERAL_TRIGGER, EPHEMERAL_WRITTEN_TRIGGER, restartMockServer } from '../../../tests-js/scripts/mock-server'

import { type MockBackendFixture, setupMockBackend, waitForAppReady } from './fixtures'

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '../../..')
const server = path.join(here, 'fixtures', 'sample-apps-mcp.py')

// The MCP servers run under the backend's own interpreter (it ships the mcp package).
const python =
  process.env.HERMES_DESKTOP_PYTHON ??
  ['.venv/bin/python', 'venv/bin/python'].map(rel => path.join(repoRoot, rel)).find(candidate => existsSync(candidate)) ??
  'python3'

const mcpServers = ['gmail', 'google_calendar', 'github']
  .map(app => `  ${app}:\n    command: ${JSON.stringify(python)}\n    args: [${JSON.stringify(server)}, ${app}]`)
  .join('\n')

// Tool search would defer the MCP tools behind a search step the scripted model does not take.
const EXTRA_CONFIG = `auxiliary:\n  title_generation:\n    enabled: false\ntools:\n  tool_search: false\nmcp_servers:\n${mcpServers}\n`
const FINAL = 'You are mostly set for the Acme review'

const phase = (page: Page, kind: string) =>
  page.evaluate(k => document.querySelector<HTMLElement>(`[data-ephemeral-call="${k}"]`)?.dataset.ephemeralPhase ?? '', kind)

test.describe('ephemeral-ui cards from MCP tool calls', () => {
  test.describe.configure({ mode: 'serial' })

  let fixture: MockBackendFixture

  test.beforeAll(async () => {
    restartMockServer()
    fixture = await setupMockBackend({ extraConfig: EXTRA_CONFIG })
    await waitForAppReady(fixture, 120_000)
  })

  test.afterAll(async () => {
    await fixture?.cleanup()
  })

  test('one card per step, dissolving to receipts; a pinned card docks on the input bar', async () => {
    test.setTimeout(240_000)
    const page = fixture.page
    const composer = page.locator('[contenteditable="true"]').first()
    await composer.waitFor({ state: 'visible', timeout: 20_000 })
    await composer.click()
    await composer.type(`Get me ready for the Acme review. ${EPHEMERAL_TRIGGER}`, { delay: 5 })
    await page.keyboard.press('Enter')

    // Each MCP call's row grows its app's card (sandboxed kit document).
    for (const [kind, title] of [
      ['inbox', 'Gmail card'],
      ['slots', 'Google Calendar card'],
      ['ci', 'GitHub card']
    ] as const) {
      // Born live: the card grows while the turn is still running, never straight into a receipt.
      await expect.poll(() => phase(page, kind), { timeout: 90_000, message: `${kind} card` }).toBe('live')
      await expect(page.locator(`[data-ephemeral-call="${kind}"] iframe[title="${title}"][sandbox="allow-scripts"]`)).toHaveCount(1, {
        timeout: 15_000
      })

      if (kind === 'slots') {
        // Pin the calendar card while it is live: it collapses into an input-bar chip.
        await page.locator('[data-ephemeral-call="slots"]').getByRole('button', { name: 'Pin to input bar' }).click()
        await expect(page.locator('[data-slot="ephemeral-pins"] [data-ephemeral-pin="slots"]')).toBeVisible()
        expect(await phase(page, 'slots')).toBe('pinned')
      }
    }

    await page.waitForFunction(text => (document.body.textContent ?? '').includes(text), FINAL, { timeout: 90_000 })

    // Unpinned cards dissolve into one-line receipts once their ring runs out.
    // The receipt names the real call; it never repeats the kit's scripted outcome ("Paid…", "Booked…").
    for (const [kind, receipt] of [
      ['inbox', 'Gmail · search threads'],
      ['ci', 'GitHub · get check runs']
    ] as const) {
      await expect.poll(() => phase(page, kind), { timeout: 30_000, message: `${kind} receipt` }).toBe('receipt')
      await expect(page.locator(`[data-ephemeral-call="${kind}"] [data-ephemeral-receipt]`)).toHaveText(new RegExp(receipt))
      await expect(page.locator(`[data-ephemeral-call="${kind}"] iframe`)).toHaveCount(0)
    }

    // The chip opens the pinned card in a popup above the input bar; Add to chat inserts, never sends.
    const sentBefore = await page.locator('[data-slot="aui_user-message-root"]').count()
    await page.locator('[data-ephemeral-pin="slots"]').click()
    await expect(page.locator('iframe[title="Google Calendar card (pinned)"]')).toBeVisible()
    await page.getByRole('button', { name: 'Add to chat' }).click()
    await expect(composer).toContainText('[ephemeral-ui slots · Google Calendar · sample data]')
    expect(await page.locator('[data-slot="aui_user-message-root"]').count()).toBe(sentBefore)

    // Unpin: the chip leaves the bar and the card is a receipt in the transcript.
    await page.getByRole('button', { name: 'Unpin' }).click()
    await expect(page.locator('[data-slot="ephemeral-pins"]')).toHaveCount(0)
    expect(await phase(page, 'slots')).toBe('receipt')
  })

  test('gh run in the terminal tool grows the GitHub CI card', async () => {
    test.setTimeout(120_000)
    const page = fixture.page
    const ciCalls = page.locator('[data-ephemeral-call="ci"]')
    const before = await ciCalls.count()
    const composer = page.locator('[contenteditable="true"]').first()
    await composer.click()
    await page.keyboard.press('ControlOrMeta+A')
    await page.keyboard.press('Backspace')
    await composer.type(`Is CI green? ${EPHEMERAL_GH_TRIGGER}`, { delay: 5 })
    await page.keyboard.press('Enter')

    await expect(ciCalls).toHaveCount(before + 1, { timeout: 60_000 })
    await expect(ciCalls.last().locator('iframe[title="GitHub card"][sandbox="allow-scripts"]')).toBeAttached()
    await expect(page.getByText('Done checking CI (sample).')).toBeVisible({ timeout: 60_000 })
  })

  test('a card the agent writes itself grows in the reply, takes a pick, and dissolves to a receipt', async () => {
    test.setTimeout(120_000)
    const page = fixture.page
    const composer = page.locator('[contenteditable="true"]').first()
    await composer.click()
    await page.keyboard.press('ControlOrMeta+A')
    await page.keyboard.press('Backspace')
    await composer.type(`Show me CI. ${EPHEMERAL_WRITTEN_TRIGGER}`, { delay: 5 })
    await page.keyboard.press('Enter')

    await expect(page.getByText('Lint fails on main; unit tests pass.')).toBeVisible({ timeout: 60_000 })
    const slot = page.locator('[data-ephemeral-call="card"]').last()
    await expect(slot.locator('iframe[title="GitHub card"][sandbox="allow-scripts"]')).toBeAttached({ timeout: 30_000 })
    const card = slot.frameLocator('iframe')
    await expect(card.getByText('CI on main')).toBeVisible({ timeout: 30_000 })
    await card.getByText('lint · failed').click()
    await slot.getByRole('button', { name: 'Add to chat' }).click()
    await expect(composer).toContainText('[ephemeral-ui card · GitHub · agent card] lint')

    // Its ring runs out after the turn: the card leaves a one-line receipt.
    await expect(slot).toHaveAttribute('data-ephemeral-phase', 'receipt', { timeout: 30_000 })
  })
})
