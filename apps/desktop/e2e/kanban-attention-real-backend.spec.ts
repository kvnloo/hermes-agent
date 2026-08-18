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
  projected: { revision: number; state: string }
  receipt: { revision: number; state: string } | null
}

function dbState(sandbox: Sandbox, taskId: string): DbState {
  return python<DbState>(sandbox, `
conn = kb.connect()
try:
    receipt = conn.execute("SELECT state, revision FROM attention_receipts WHERE subject_id=?", (${JSON.stringify(taskId)},)).fetchone()
    events = conn.execute("SELECT kind, payload FROM task_events WHERE task_id=? ORDER BY id", (${JSON.stringify(taskId)},)).fetchall()
    print(json.dumps({'receipt': dict(receipt) if receipt else None, 'projected': kb.project_task_attention(conn, ${JSON.stringify(taskId)}), 'events': [dict(row) for row in events]}))
finally:
    conn.close()
`)
}

function externalAdvance(sandbox: Sandbox, taskId: string, action: 'settle' | 'wake', revision: number): void {
  python<unknown>(sandbox, `
conn = kb.connect()
try:
    with kb.write_txn(conn):
        now = int(time.time())
        state = {'settle': 'settled', 'wake': 'active'}[${JSON.stringify(action)}]
        observed = conn.execute("SELECT COALESCE(MAX(id), 0) FROM task_events WHERE task_id=?", (${JSON.stringify(taskId)},)).fetchone()[0]
        conn.execute("INSERT INTO attention_receipts (subject_kind,subject_id,state,wake_at,observed_event_id,actor,source,revision,created_at,updated_at) VALUES ('kanban_task',?,?,NULL,?,'e2e-racer','e2e',?,?,?) ON CONFLICT(subject_kind,subject_id) DO UPDATE SET state=excluded.state,wake_at=NULL,observed_event_id=excluded.observed_event_id,actor=excluded.actor,source=excluded.source,revision=excluded.revision,updated_at=excluded.updated_at", (${JSON.stringify(taskId)}, state, observed, ${revision + 1}, now, now))
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
  const logicalBefore = Object.fromEntries(Object.entries(taskIds).map(([name, id]) => [name, dbState(sandbox, id)]))
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
  const electronProcess = fixture.app.process()
  const stdout: Buffer[] = []
  const stderr: Buffer[] = []
  electronProcess.stdout?.on('data', chunk => stdout.push(Buffer.from(chunk)))
  electronProcess.stderr?.on('data', chunk => stderr.push(Buffer.from(chunk)))
  let runtimeEvidence: Record<string, unknown> | undefined

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
      const snooze = card.getByRole('button', { name: '1 hour' })
      await expect(snooze).toBeVisible()
      await expect(card.getByRole('button', { name: 'Tomorrow at 9 AM local time' })).toBeVisible()
      await expect(card.getByRole('button', { name: '1 week' })).toBeVisible()
      await expect(card.getByRole('button', { name: '1 month' })).toBeVisible()
      const custom = card.getByRole('button', { name: 'Custom+' })
      await expect(custom).toHaveAttribute('aria-expanded', 'false')
      await snooze.scrollIntoViewIfNeeded()
      await expect.poll(() => snooze.evaluate(element => {
        const rect = element.getBoundingClientRect()
        const center = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)

        return center === element || element.contains(center)
      }), { timeout: 30_000 }).toBe(true)

      const geometry = await snooze.evaluate(element => {
        const rect = element.getBoundingClientRect()
        const center = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2)
        const header = element.closest('article, [draggable="true"]')?.querySelector('header')

        return {
          height: rect.height,
          noOverflow: document.documentElement.scrollWidth <= window.innerWidth,
          targetIsSnooze: center === element || element.contains(center),
          target: center ? `${center.tagName}:${center.textContent?.trim().slice(0, 40)}` : null,
          headerIntercepts: Boolean(header && (center === header || header.contains(center))),
        }
      })

      expect(geometry.targetIsSnooze, `elementFromPoint returned ${geometry.target}`).toBe(true)
      expect({ height: geometry.height, noOverflow: geometry.noOverflow, headerIntercepts: geometry.headerIntercepts }).toEqual({ height: 44, noOverflow: true, headerIntercepts: false })
      await page.screenshot({ path: path.join(evidenceDir, `electron-${width}.png`), fullPage: true })
      await custom.focus()
      await custom.press('Enter')
      await expect(custom).toHaveAttribute('aria-expanded', 'true')
      await card.getByLabel('Custom wake time').press('Escape')
      await expect(custom).toHaveAttribute('aria-expanded', 'false')
    }

    await page.setViewportSize({ width: 390, height: 800 })
    const failureCard = page.getByText(FAILURE_TITLE).locator('..')
    const staleMessage = 'This task changed elsewhere. Your action was not applied.'

    externalAdvance(sandbox, taskIds.failure, 'settle', 0)
    const externallySettled = dbState(sandbox, taskIds.failure)
    expect(externallySettled.receipt).toEqual({ revision: 1, state: 'settled' })
    expect(externallySettled.projected).toMatchObject({ revision: 1, state: 'settled' })
    expect(externallySettled.events.filter(event => event.kind.startsWith('attention_'))).toHaveLength(0)

    await failureCard.getByRole('button', { name: 'Settle' }).click()
    await expect(status).toHaveText(staleMessage)
    expect(dbState(sandbox, taskIds.failure)).toEqual(externallySettled)
    await expect(page.getByText(FAILURE_TITLE)).toHaveCount(1)
    const reconciledWake = page.getByRole('button', { name: 'Wake' })
    await expect(reconciledWake).toHaveCount(1)

    externalAdvance(sandbox, taskIds.failure, 'wake', 1)
    const externallyAwake = dbState(sandbox, taskIds.failure)
    expect(externallyAwake.receipt).toEqual({ revision: 2, state: 'active' })
    expect(externallyAwake.projected).toMatchObject({ revision: 2, state: 'active' })
    expect(externallyAwake.events.filter(event => event.kind.startsWith('attention_'))).toHaveLength(0)

    await reconciledWake.click()
    await expect(status).toHaveText(staleMessage)
    expect(dbState(sandbox, taskIds.failure)).toEqual(externallyAwake)
    await expect(page.getByText(FAILURE_TITLE)).toHaveCount(1)
    await expect(page.getByRole('button', { name: 'Settle' })).toHaveCount(3)
    await expect(status).toHaveCount(1)

    await card.getByRole('button', { name: '1 hour' }).click()
    await expect(status).toContainText('Task snoozed until')
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

    const electronPid = electronProcess.pid
    const electronVersion = await fixture.app.evaluate(() => process.versions.electron)
    const backendLog = path.join(sandbox.hermesHome, 'logs', 'desktop.log')

    const logicalAfter = Object.fromEntries(Object.entries(taskIds).map(([name, id]) => [name, dbState(sandbox, id)]))
    runtimeEvidence = {
      sourceCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim(),
      sourceTree: execFileSync('git', ['show', '-s', '--format=%T', 'HEAD'], { cwd: REPO_ROOT, encoding: 'utf8' }).trim(),
      startedAt: new Date(launchedAt).toISOString(),
      electronVersion,
      electronNodeVersion: await fixture.app.evaluate(() => process.versions.node),
      electronPid,
      backendLogPresent: fs.existsSync(backendLog),
      logicalBefore,
      logicalAfter,
      productionBefore,
      productionSentinelUnchanged: {
        db: productionDbSentinel(productionDb) === productionBefore.dbSentinel,
        config: hashIfFile(productionConfig) === productionBefore.config,
      },
      interactionVerdict: {
        widths: WIDTHS,
        finalReceipts: { failure: logicalAfter.failure.receipt, snooze: snoozeState.receipt, settle: settleState.receipt },
        failedActionAttentionEvents: logicalAfter.failure.events.filter(event => event.kind.startsWith('attention_')).length,
        staleFailureAnnouncement: staleMessage,
      },
    }

    expect(runtimeEvidence.electronVersion).toBe('40.10.2')
    expect(runtimeEvidence.productionSentinelUnchanged).toEqual({ db: true, config: true })
  } finally {
    await fixture.app.close().catch(() => undefined)
    await mock.close()

    const packet = process.env.KANBAN_ATTENTION_EVIDENCE_PACKET
    if (packet && runtimeEvidence) {
      fs.rmSync(packet, { recursive: true, force: true })
      for (const directory of ['build', 'database', 'logs', 'screenshots']) fs.mkdirSync(path.join(packet, directory), { recursive: true })
      for (const filename of fs.readdirSync(evidenceDir).filter(name => name.endsWith('.png'))) fs.copyFileSync(path.join(evidenceDir, filename), path.join(packet, 'screenshots', filename))
      fs.copyFileSync(path.join(DESKTOP_ROOT, 'build', 'install-stamp.json'), path.join(packet, 'build', 'install-stamp.json'))
      fs.copyFileSync(path.join(DESKTOP_ROOT, 'dist', 'index.html'), path.join(packet, 'build', 'index.html'))
      fs.copyFileSync(path.join(DESKTOP_ROOT, 'dist', 'electron-main.mjs'), path.join(packet, 'build', 'electron-main.mjs'))
      const database = path.join(sandbox.root, 'kanban.db')
      execFileSync('sqlite3', [database, 'PRAGMA wal_checkpoint(TRUNCATE);'])
      fs.copyFileSync(database, path.join(packet, 'database', 'kanban.db'))
      fs.writeFileSync(path.join(packet, 'database', 'schema.sql'), execFileSync('sqlite3', [database, '.schema'], { encoding: 'utf8' }))
      fs.writeFileSync(path.join(packet, 'database', 'logical-before.json'), `${JSON.stringify(runtimeEvidence.logicalBefore, null, 2)}\n`)
      fs.writeFileSync(path.join(packet, 'database', 'logical-after.json'), `${JSON.stringify(runtimeEvidence.logicalAfter, null, 2)}\n`)
      const backendLog = path.join(sandbox.hermesHome, 'logs', 'desktop.log')
      fs.copyFileSync(backendLog, path.join(packet, 'logs', 'backend.log'))
      fs.writeFileSync(path.join(packet, 'logs', 'electron.stdout.log'), Buffer.concat(stdout))
      fs.writeFileSync(path.join(packet, 'logs', 'electron.stderr.log'), Buffer.concat(stderr))
      const endedAt = new Date().toISOString()
      const processRecord = { pid: runtimeEvidence.electronPid, startedAt: runtimeEvidence.startedAt, endedAt, exitCode: electronProcess.exitCode }
      const launch = { command: 'electron', args: [DESKTOP_ROOT, '--disable-gpu', '--no-sandbox', ...(env.WAYLAND_DISPLAY && !env.DISPLAY ? ['--ozone-platform=wayland'] : []), ...(env.HERMES_DESKTOP_E2E_HEADLESS === '1' ? ['--headless'] : [])], cwd: DESKTOP_ROOT, environment: Object.fromEntries(['DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR', 'HERMES_HOME', 'HERMES_KANBAN_DB', 'HERMES_KANBAN_BOARD', 'HERMES_DESKTOP_E2E_HEADLESS'].filter(key => env[key]).map(key => [key, key === 'HERMES_HOME' || key === 'HERMES_KANBAN_DB' ? `<isolated>/${path.basename(env[key])}` : env[key]])) }
      fs.writeFileSync(path.join(packet, 'launch.json'), `${JSON.stringify(launch, null, 2)}\n`)
      fs.writeFileSync(path.join(packet, 'process.json'), `${JSON.stringify(processRecord, null, 2)}\n`)
      fs.writeFileSync(path.join(packet, 'production-sentinel-before.json'), `${JSON.stringify(runtimeEvidence.productionBefore, null, 2)}\n`)
      const productionAfter = { dbSentinel: productionDbSentinel(productionDb), config: hashIfFile(productionConfig) }
      fs.writeFileSync(path.join(packet, 'production-sentinel-after.json'), `${JSON.stringify(productionAfter, null, 2)}\n`)
      fs.writeFileSync(path.join(packet, 'interaction-trace.json'), `${JSON.stringify(runtimeEvidence.interactionVerdict, null, 2)}\n`)
      const privacyRows = execFileSync('sqlite3', ['-json', database, 'SELECT title,body,created_by FROM tasks ORDER BY title;'], { encoding: 'utf8' })
      const privacyAudit = { syntheticOnly: !/(?:@|\/home\/|\/Users\/)/.test(privacyRows), rows: JSON.parse(privacyRows) }
      const completeRuntime = { ...runtimeEvidence, endedAt, exitCode: electronProcess.exitCode, repoRoot: REPO_ROOT, sqliteVersion: execFileSync('sqlite3', ['--version'], { encoding: 'utf8' }).trim(), schemaVersion: Number(execFileSync('sqlite3', [database, 'PRAGMA user_version;'], { encoding: 'utf8' }).trim()), privacyAudit }
      if (!privacyAudit.syntheticOnly) throw new Error('isolated database privacy audit failed')
      fs.writeFileSync(path.join(packet, 'runtime.json'), `${JSON.stringify(completeRuntime, null, 2)}\n`)
      execFileSync(process.execPath, [path.join(DESKTOP_ROOT, 'scripts', 'seal-kanban-attention-evidence.mjs'), packet], { cwd: REPO_ROOT, stdio: 'inherit' })
    }

    if (process.env.KEEP_KANBAN_ATTENTION_E2E !== '1') {sandbox.cleanup()}
  }
})
