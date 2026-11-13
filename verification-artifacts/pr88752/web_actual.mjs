import { chromium } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const out = path.resolve('verification-artifacts/pr88752')
fs.mkdirSync(out, { recursive: true })
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1220, height: 800 } })
const errors = []
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
await page.goto('http://127.0.0.1:18765/kanban', { waitUntil: 'networkidle' })
await page.getByText('Active actual task').waitFor({ timeout: 20000 })
for (const width of [320, 360, 390, 430, 1220]) {
  await page.setViewportSize({ width, height: 800 })
  await page.waitForTimeout(100)
  await page.screenshot({ path: path.join(out, `web-${width}.png`), fullPage: true })
  const geometry = await page.evaluate(() => ({ client: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }))
  if (geometry.scroll > geometry.client) throw new Error(`horizontal overflow at ${width}: ${JSON.stringify(geometry)}`)
}
await page.getByText('Settled').first().click()
if (await page.getByText('Settled actual task').count() !== 1) throw new Error('settled task missing or duplicated')
if (await page.getByText('Snoozed actual task').count() !== 0) throw new Error('snoozed task leaked into workflow')
await page.screenshot({ path: path.join(out, 'web-settled-open.png'), fullPage: true })
console.log(JSON.stringify({ ok: true, errors, title: await page.title(), url: page.url() }))
await browser.close()
