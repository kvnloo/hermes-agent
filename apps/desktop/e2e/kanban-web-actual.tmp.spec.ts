import { chromium, test, expect } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const OUT = path.resolve(import.meta.dirname, '..', '..', '..', 'verification-artifacts', 'pr88752')
test('standalone web actual backend', async () => {
  fs.mkdirSync(OUT, { recursive: true })
  const browser = await chromium.launch({ executablePath: path.resolve('node_modules/electron/dist/electron'), args: ['--no-sandbox'], headless: true })
  const page = await browser.newPage({ viewport: { width: 1220, height: 800 } })
  const errors: string[] = []
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
  await page.goto('http://127.0.0.1:18765/kanban', { waitUntil: 'networkidle' })
  await expect(page.getByText('Active actual task')).toBeVisible({ timeout: 20000 })
  for (const width of [320, 360, 390, 430, 1220]) {
    await page.setViewportSize({ width, height: 800 })
    await page.screenshot({ path: path.join(OUT, `web-${width}.png`), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
  }
  await page.getByText('Settled').first().click()
  await expect(page.getByText('Settled actual task')).toHaveCount(1)
  await expect(page.getByText('Snoozed actual task')).toHaveCount(0)
  await page.screenshot({ path: path.join(OUT, 'web-settled-open.png'), fullPage: true })
  expect(errors).toEqual([])
  await browser.close()
})
