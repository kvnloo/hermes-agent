import { chromium } from 'playwright'
import { createHash } from 'node:crypto'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const url = 'https://0.taila30dc.ts.net:8449/kanban'
const output = path.resolve('.preview/evidence')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true })
const results = []
for (const width of [320, 360, 390, 430]) {
  const page = await browser.newPage({ viewport: { width, height: 760 }, deviceScaleFactor: 1 })
  const errors = []
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()) })
  page.on('pageerror', err => errors.push(err.message))
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 })
  await page.getByText('Active attention — try Settle or Snooze', { exact: true }).waitFor()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  const filename = `webui-live-${width}.png`
  await page.screenshot({ path: path.join(output, filename), fullPage: true })
  const bytes = await readFile(path.join(output, filename))
  results.push({ width, filename, bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'), overflow, errors })
  await page.close()
}

const page = await browser.newPage({ viewport: { width: 390, height: 760 }, deviceScaleFactor: 1 })
await page.goto(url, { waitUntil: 'networkidle' })
const activeCard = page.locator('.hermes-kanban-card').filter({ hasText: 'Active attention — try Settle or Snooze' })
await activeCard.getByText('Snooze…', { exact: true }).click()
const snoozeVisible = await activeCard.getByRole('button', { name: '1 hour' }).isVisible()
await activeCard.getByRole('button', { name: '1 hour' }).evaluate(el => el.click())
await page.locator('details.hermes-kanban-settled > summary').click()
const settledCard = page.locator('.hermes-kanban-card').filter({ hasText: 'Settled attention — try Wake' })
await settledCard.getByRole('button', { name: 'Wake' }).waitFor()
const wakeVisibleAfterSnooze = await settledCard.getByRole('button', { name: 'Wake' }).isVisible()
await settledCard.getByRole('button', { name: 'Wake' }).evaluate(el => el.click())
await settledCard.getByRole('button', { name: 'Settle' }).waitFor()
const settleVisibleAfterWake = await settledCard.getByRole('button', { name: 'Settle' }).isVisible()
const interactionFile = 'webui-live-interactions-390.png'
await page.screenshot({ path: path.join(output, interactionFile), fullPage: true })
const interactionBytes = await readFile(path.join(output, interactionFile))
const interactions = { snoozeVisible, wakeVisibleAfterSnooze, settleVisibleAfterWake, filename: interactionFile, bytes: interactionBytes.length, sha256: createHash('sha256').update(interactionBytes).digest('hex') }
await browser.close()
await writeFile(path.join(output, 'manifest.json'), `${JSON.stringify({ url, head: '6d5f34c45e9154fa47df6fef6d8866d15176c6fe', surface: 'shipped standalone WebUI plugin in dashboard host', privacySafeFixture: true, captures: results, interactions }, null, 2)}\n`)
console.log(JSON.stringify({ captures: results, interactions }, null, 2))
