import { spawnSync } from 'node:child_process'
import * as fs from 'node:fs'
import * as path from 'node:path'
import { test, expect } from '@playwright/test'
import { buildAppEnv, createSandbox, launchDesktop, writeMockProviderConfig, writeEnvFile } from './fixtures'
import { startMockServer } from './mock-server'

const REPO = path.resolve(import.meta.dirname, '..', '..', '..')
const OUT = path.join(REPO, 'verification-artifacts', 'pr88752')

function seed(home: string) {
  const script = path.join(OUT, 'seed_attention.py')
  const result = spawnSync(path.join(REPO, '.venv', 'bin', 'python'), [script, home], { cwd: REPO, encoding: 'utf8' })
  if (result.status !== 0) throw new Error(`seed failed: ${result.stdout}\n${result.stderr}`)
}

test('actual Electron attention surfaces', async () => {
  fs.mkdirSync(OUT, { recursive: true })
  const mock = await startMockServer()
  const sandbox = createSandbox('attention-actual')
  writeMockProviderConfig(sandbox.hermesHome, mock.url)
  writeEnvFile(sandbox.hermesHome)
  seed(sandbox.hermesHome)
  const { app, page } = await launchDesktop(buildAppEnv(sandbox, { ELECTRON_OZONE_PLATFORM_HINT: 'headless' }))
  try {
    await page.waitForLoadState('domcontentloaded')
    await page.evaluate(() => localStorage.setItem('hermes.desktop.pluginDecisions.v2', JSON.stringify({ kanban: true })))
    await page.reload()
    await page.getByRole('button', { name: 'Kanban' }).click()
    await expect(page.getByText('Active actual task')).toBeVisible({ timeout: 20000 })
    for (const width of [320, 360, 390, 430, 1220]) {
      await app.evaluate(({ BrowserWindow }, size) => BrowserWindow.getAllWindows()[0]?.setContentSize(size.width, size.height), { width, height: 800 })
      await page.waitForTimeout(250)
      await page.screenshot({ path: path.join(OUT, `electron-${width}.png`), fullPage: true })
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true)
    }
    const trigger = page.getByRole('button', { name: 'Snooze…' }).first()
    await trigger.click()
    for (const name of ['1 hr', 'Tmrw 9am', '1 wk', '1 mo', 'Custom…']) {
      const box = await page.getByRole('button', { name }).boundingBox()
      expect(box?.height).toBeGreaterThanOrEqual(44)
      expect(box?.width).toBeGreaterThanOrEqual(44)
    }
    await page.screenshot({ path: path.join(OUT, 'electron-snooze-open.png'), fullPage: true })
    await page.getByRole('dialog', { name: 'Snooze task' }).press('Escape')
    await expect(trigger).toBeFocused()
    await trigger.click()
    await page.getByLabel('Exact local date and time').fill('2030-01-02T09:15')
    await page.getByRole('button', { name: 'Snooze', exact: true }).click()
    await expect(page.getByRole('status')).toContainText('Task snoozed')
    await expect(page.getByText('Active actual task')).toHaveCount(0)
    await page.screenshot({ path: path.join(OUT, 'electron-after-snooze.png'), fullPage: true })
  } finally {
    await app.close().catch(() => undefined)
    await mock.close()
    sandbox.cleanup()
  }
})
