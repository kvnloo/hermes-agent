import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import * as fs from 'node:fs'
import * as path from 'node:path'

import type { Page } from '@playwright/test'

import {
  buildAppEnv,
  createSandbox,
  launchDesktop,
  type Sandbox,
  waitForAppReady,
  writeEnvFile,
  writeMockProviderConfig,
} from './fixtures'
import { startMockServer } from './mock-server'
import { expect, test } from './test'

const REPO_ROOT = path.resolve(import.meta.dirname, '..', '..', '..')
const DESKTOP_ROOT = path.resolve(import.meta.dirname, '..')
const SOURCE_FIX = 'd57a8374993ece30a0471839b037176392dbd191'
const WIDTHS = [1220, 320, 360, 390, 430]
const TASK_TITLE = 'E2E attention receipt sentinel'
const SETTLE_TITLE = 'E2E settle and wake sentinel'
const FAILURE_TITLE = 'E2E stale receipt sentinel'

function sha256(file: string): string {
  return createHash('sha256').update(fs.readFileSync(file)).digest('hex')
}

function hashIfFile(file: string | undefined): string | null {
  return file && fs.existsSync(file) && fs.statSync(file).isFile() ? sha256(file) : null
}

function productionDbSentinel(file: string | undefined): string | null {
  if (!file || !fs.existsSync(file)) {
    return null
  }

  return execFileSync('sqlite3', [file, "SELECT id,title,status FROM tasks ORDER BY created_at,id LIMIT 1; SELECT id,task_id,kind,payload FROM task_events ORDER BY id LIMIT 1;"], { encoding: 'utf8' })
}

function python<T>(sandbox: Sandbox, body: string): T {
  const script = `import json, os, time\nfrom hermes_cli import kanban_db as kb\n${body}`

  const output = execFileSync(process.env.PYTHON || 'python3', ['-c', script], {
    cwd: REPO_ROOT,
    encoding: 'utf8',
    env: {
      ...process.env,
      HERMES_HOME: sandbox.hermesHome,
      HERMES_KANBAN_DB: path.join(sandbox.root, 'kanban.db'),
      HERMES_KANBAN_BOARD: 'default',
    },
  })

  return JSON.parse(output.trim()) as T
}

function seed(sandbox: Sandbox): { failure: string; settle: string; snooze: string } {
  return python<{ failure: string; settle: string; snooze: string }>(sandbox, `
kb.init_db()
conn = kb.connect()
try:
    ids = {
        'snooze': kb.create_task(conn, title=${JSON.stringify(TASK_TITLE)}, body='isolated actual Electron E2E', created_by='e2e', initial_status='blocked'),
        'settle': kb.create_task(conn, title=${JSON.stringify(SETTLE_TITLE)}, body='isolated actual Electron E2E', created_by='e2e', initial_status='blocked'),
        'failure': kb.create_task(conn, title=${JSON.stringify(FAILURE_TITLE)}, body='isolated actual Electron E2E', created_by='e2e', initial_status='blocked'),
    }
    print(json.dumps(ids))
finally:
    conn.close()
`)
}

interface DbState {
  events: Array<{ kind: string; payload: string | null }>
  receipt: { revision: number; state: string } | null
}

function dbState(sandbox: Sandbox, taskId: string): DbState {
  return python<DbState>(sandbox, `
conn = kb.connect()
try:
    receipt = conn.execute("SELECT state, revision FROM attention_receipts WHERE subject_id=?", (${JSON.stringify(taskId)},)).fetchone()
    events = conn.execute("SELECT kind, payload FROM task_events WHERE task_id=? ORDER BY id", (${JSON.stringify(taskId)},)).fetchall()
    print(json.dumps({'receipt': dict(receipt) if receipt else None, 'events': [dict(row) for row in events]}))
finally:
    conn.close()
`)
}

function externalSettle(sandbox: Sandbox, taskId: string, revision: number): void {
  python<unknown>(sandbox, `
conn = kb.connect()
try:
    with kb.write_txn(conn):
        now = int(time.time())
        observed = conn.execute("SELECT COALESCE(MAX(id), 0) FROM task_events WHERE task_id=?", (${JSON.stringify(taskId)},)).fetchone()[0]
        conn.execute("INSERT INTO attention_receipts (subject_kind,subject_id,state,wake_at,observed_event_id,actor,source,revision,created_at,updated_at) VALUES ('kanban_task',?,'settled',NULL,?,'e2e-racer','e2e',?,?,?)", (${JSON.stringify(taskId)}, observed, ${revision + 1}, now, now))
    print(json.dumps(True))
finally:
    conn.close()
`)
}

async function enableKanbanAndOpen(page: Page): Promise<void> {
  await page.evaluate(() => localStorage.setItem('hermes.desktop.pluginDecisions.v2', JSON.stringify({ kanban: true })))
  await page.reload()
  await page.waitForLoadState('domcontentloaded')
  await page.evaluate(() => { window.location.hash = '#/kanban' })
  await expect(page.getByText(TASK_TITLE)).toBeVisible({ timeout: 30_000 })
}

// Playwright requires an object-destructured fixture argument even when this
// spec intentionally launches its own Electron application.
// eslint-disable-next-line no-empty-pattern
test('actual Electron and isolated backend preserve attention controls and receipts', async ({}, testInfo) => {
  const productionDb = process.env.HERMES_KANBAN_DB
  const productionConfig = process.env.HERMES_HOME ? path.join(process.env.HERMES_HOME, 'config.yaml') : undefined
  const productionBefore = { dbSentinel: productionDbSentinel(productionDb), config: hashIfFile(productionConfig) }
  const sandbox = createSandbox('kanban-attention-real')
  const mock = await startMockServer()
  const taskIds = seed(sandbox)
  const evidenceDir = testInfo.outputPath('evidence')
  fs.mkdirSync(evidenceDir, { recursive: true })
  writeMockProviderConfig(sandbox.hermesHome, mock.url)
  writeEnvFile(sandbox.hermesHome)

  const env = buildAppEnv(sandbox, {
    HERMES_KANBAN_DB: path.join(sandbox.root, 'kanban.db'),
    HERMES_KANBAN_BOARD: 'default',
    HERMES_DESKTOP_E2E_HEADLESS: process.env.DISPLAY || process.env.WAYLAND_DISPLAY ? '0' : '1',
  })

  const launchedAt = Date.now()
  const fixture = await launchDesktop(env)

  try {
    await waitForAppReady({ ...fixture, sandbox, cleanup: async () => undefined })
    await enableKanbanAndOpen(fixture.page)
    const page = fixture.page
    const card = page.getByText(TASK_TITLE).locator('..')
    const status = page.locator('span[role="status"][aria-live="polite"].sr-only')

    await expect(status).toHaveCount(1)
    await page.emulateMedia({ reducedMotion: 'reduce' })
    expect(await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches)).toBe(true)

    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: 800 })
      const snooze = card.getByText('Snooze…')
      await expect(snooze).toBeVisible()
      await snooze.scrollIntoViewIfNeeded()
      await expect.poll(() => snooze.evaluate(element => {
        const rect = element.getBoundingClientRect()
        const center = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)

        return center === element || element.contains(center) || center?.closest('summary') === element
      }), { timeout: 30_000 }).toBe(true)

      const geometry = await snooze.evaluate(element => {
        const rect = element.getBoundingClientRect()
        const center = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
        const header = element.closest('article, [draggable="true"]')?.querySelector('header')

        return {
          height: rect.height,
          noOverflow: document.documentElement.scrollWidth <= window.innerWidth,
          targetIsSnooze: center === element || element.contains(center) || center?.closest('summary') === element,
          target: center ? `${center.tagName}:${center.textContent?.trim().slice(0, 40)}` : null,
          headerIntercepts: Boolean(header && (center === header || header.contains(center))),
        }
      })

      expect(geometry.targetIsSnooze, `elementFromPoint returned ${geometry.target}`).toBe(true)
      expect({ height: geometry.height, noOverflow: geometry.noOverflow, headerIntercepts: geometry.headerIntercepts }).toEqual({ height: 44, noOverflow: true, headerIntercepts: false })
      await snooze.click()
      const snoozeDialog = page.getByRole('dialog', { name: 'Snooze task' })
      await expect(snoozeDialog).toBeVisible()
      await snoozeDialog.press('Escape')
      await expect(snooze).toBeFocused()
      await snooze.press('Enter')
      await expect(snoozeDialog).toBeVisible()
      await page.screenshot({ path: path.join(evidenceDir, `electron-${width}.png`), fullPage: true })
      await snoozeDialog.press('Escape')
      await expect(snooze).toBeFocused()
    }

    await page.setViewportSize({ width: 390, height: 800 })
    externalSettle(sandbox, taskIds.failure, 0)
    expect(dbState(sandbox, taskIds.failure).receipt).toEqual({ revision: 1, state: 'settled' })

    await card.getByText('Snooze…').click()
    await page.getByRole('dialog', { name: 'Snooze task' }).getByRole('button', { name: '1 hr' }).click()
    await expect(status).toHaveText('Task snoozed')
    await expect(status).toHaveCount(1)
    expect(dbState(sandbox, taskIds.snooze).receipt).toEqual({ revision: 1, state: 'snoozed' })

    const settleCard = page.getByText(SETTLE_TITLE).locator('..')
    await settleCard.getByRole('button', { name: 'Settle' }).click()
    await expect(status).toHaveText('Attention settled')
    const settledDisclosure = page.locator('summary').filter({ hasText: /^Settled ·/ }).first()
    await settledDisclosure.focus()
    await settledDisclosure.press('Enter')
    await expect(settledDisclosure).toBeFocused()
    await expect(settleCard.getByRole('button', { name: 'Wake' })).toBeVisible()
    await settleCard.getByRole('button', { name: 'Wake' }).click()
    await expect(status).toHaveText('Task awake')
    expect(dbState(sandbox, taskIds.settle).receipt).toEqual({ revision: 2, state: 'active' })

    const snoozeState = dbState(sandbox, taskIds.snooze)
    const settleState = dbState(sandbox, taskIds.settle)
    expect(snoozeState.events.filter(event => event.kind.startsWith('attention_')).map(event => event.kind)).toEqual(['attention_snooze'])
    expect(settleState.events.filter(event => event.kind.startsWith('attention_')).map(event => event.kind)).toEqual(['attention_settle', 'attention_wake'])

    const electronPid = fixture.app.process().pid
    const electronVersion = await fixture.app.evaluate(() => process.versions.electron)
    const backendLog = path.join(sandbox.hermesHome, 'logs', 'desktop.log')

    const manifest = {
      schema: 1,
      sourceFix: SOURCE_FIX,
      sourceFixTree: execFileSync('git', ['show', '-s', '--format=%T', SOURCE_FIX], { cwd: REPO_ROOT, encoding: 'utf8' }).trim(),
      testedHead: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim(),
      buildStampSha256: hashIfFile(path.join(DESKTOP_ROOT, 'dist', 'build-stamp.json')),
      rendererSha256: sha256(path.join(DESKTOP_ROOT, 'dist', 'index.html')),
      electronMainSha256: sha256(path.join(DESKTOP_ROOT, 'dist', 'electron-main.mjs')),
      electronVersion,
      electronPid,
      launchedAt,
      isolatedHermesHome: true,
      isolatedKanbanDb: true,
      taskIds: '<redacted-e2e-tasks>',
      widths: WIDTHS,
      finalReceipts: { snooze: snoozeState.receipt, settle: settleState.receipt },
      attentionEvents: ['attention_snooze', 'attention_settle', 'attention_wake'],
      backendLogPresent: fs.existsSync(backendLog),
      productionSentinelUnchanged: {
        db: productionDbSentinel(productionDb) === productionBefore.dbSentinel,
        config: hashIfFile(productionConfig) === productionBefore.config,
      },
      screenshots: fs.readdirSync(evidenceDir).sort().map(filename => ({ filename, sha256: sha256(path.join(evidenceDir, filename)) })),
    }

    expect(manifest.electronVersion).toBe('40.10.2')
    expect(manifest.productionSentinelUnchanged).toEqual({ db: true, config: true })
    fs.writeFileSync(path.join(evidenceDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)
  } finally {
    await fixture.app.close().catch(() => undefined)
    await mock.close()

    if (process.env.KEEP_KANBAN_ATTENTION_E2E !== '1') {sandbox.cleanup()}
  }
})
