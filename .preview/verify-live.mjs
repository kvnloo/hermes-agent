import fs from 'node:fs'
import crypto from 'node:crypto'
import { chromium } from '@playwright/test'

const url = 'https://0.taila30dc.ts.net:8450/kanban?cb=204de6a0'
const widths = [320, 360, 390, 430, 1280]
const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/chromium', args: ['--ignore-certificate-errors'] })
const results = []
for (const width of widths) {
  const page = await browser.newPage({ viewport: { width, height: width === 1280 ? 800 : 760 }, ignoreHTTPSErrors: true })
  await page.goto(url, { waitUntil: 'networkidle' })
  await page.waitForSelector('.hermes-kanban-column')
  const before = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth, columns: document.querySelectorAll('.hermes-kanban-column').length }))
  let interaction = 'desktop'
  if (width < 768) {
    const tabs = page.locator('[data-kanban-column-tab]')
    const count = await tabs.count()
    await tabs.nth(count - 1).click()
    await page.waitForTimeout(500)
    await tabs.nth(count - 1).press('Home')
    await page.waitForTimeout(300)
    await tabs.first().press('End')
    await page.waitForTimeout(500)
    const selected = await page.locator('[data-kanban-column-tab][aria-selected="true"]').getAttribute('data-kanban-column-tab')
    interaction = `click+Home+End selected=${selected}/${count - 1}`
  }
  const file = `/tmp/pr88716-live-${width}.png`
  await page.screenshot({ path: file, fullPage: true })
  const bytes = fs.readFileSync(file)
  results.push({ width, ...before, noBodyOverflow: before.body <= before.viewport, interaction, screenshot: file, bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex') })
  await page.close()
}
await browser.close()
console.log(JSON.stringify(results, null, 2))
if (results.some(x => !x.noBodyOverflow || x.columns < 5)) process.exit(1)
