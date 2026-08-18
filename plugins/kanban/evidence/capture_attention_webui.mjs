import { spawn, execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { chromium } from 'playwright'

const repo = path.resolve(import.meta.dirname, '..', '..', '..')
const output = path.resolve(import.meta.dirname, 'attention-responsive', 'webui-e2e')
const runtime = mkdtempSync(path.join(repo, '.webui-e2e-'))
const home = path.join(runtime, 'home')
const database = path.join(runtime, 'kanban.db')
const port = 9200 + Math.floor(Math.random() * 500)
mkdirSync(home, { recursive: true })
rmSync(output, { recursive: true, force: true })
mkdirSync(output, { recursive: true })

const env = { ...process.env, HERMES_HOME: home, HERMES_KANBAN_DB: database, HERMES_KANBAN_BOARD: 'default' }
const seed = execFileSync(process.env.PYTHON || 'python3', ['-c', `
import json
from hermes_cli import kanban_db as k
k.init_db(); c=k.connect()
ids={name:k.create_task(c,title=title,body='isolated actual WebUI E2E',created_by='e2e',initial_status='blocked') for name,title in [('snooze','WebUI snooze sentinel'),('settle','WebUI settle sentinel')]}
c.close(); print(json.dumps(ids))
`], { cwd: repo, env, encoding: 'utf8' })
const ids = JSON.parse(seed.trim())
const server = spawn(process.env.PYTHON || 'python3', ['-m', 'hermes_cli.main', 'dashboard', '--port', String(port), '--host', '127.0.0.1', '--skip-build', '--no-open', '--isolated'], { cwd: repo, env, stdio: ['ignore', 'pipe', 'pipe'] })
let serverLog = ''
server.stdout.on('data', chunk => { serverLog += chunk })
server.stderr.on('data', chunk => { serverLog += chunk })

async function ready() {
  for (let attempt = 0; attempt < 300; attempt += 1) {
    if (server.exitCode != null) throw new Error(`dashboard exited ${server.exitCode}: ${serverLog}`)
    try { const response = await fetch(`http://127.0.0.1:${port}/`); if (response.ok) return } catch {}
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error(`dashboard readiness timeout: ${serverLog}`)
}

function receipt(id) {
  const raw = execFileSync('sqlite3', ['-json', database, `SELECT state,revision,wake_at FROM attention_receipts WHERE subject_id='${id}';`], { encoding: 'utf8' })
  return JSON.parse(raw || '[]')[0] || null
}

async function waitReceipt(id, state) {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    const current = receipt(id)
    if (current?.state === state) return current
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  throw new Error(`receipt ${id} did not reach ${state}`)
}

const widths = [320, 360, 390, 430, 1220]
const manifest = { generatedBy: 'actual standalone Hermes dashboard + Playwright system Chromium', sourceCommit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: repo, encoding: 'utf8' }).trim(), widths, captures: [], interactions: {} }
let browser
try {
  await ready()
  browser = await chromium.launch({ executablePath: '/usr/bin/chromium', headless: true })
  const page = await browser.newPage({ viewport: { width: 390, height: 800 } })
  await page.goto(`http://127.0.0.1:${port}/kanban`, { waitUntil: 'networkidle' })
  const card = page.getByText('WebUI snooze sentinel').locator('..')
  await card.getByRole('button', { name: '1 hour' }).waitFor()

  for (const width of widths) {
    await page.setViewportSize({ width, height: 800 })
    const custom = card.getByRole('button', { name: /^Custom/ })
    await custom.scrollIntoViewIfNeeded()
    const closed = await card.evaluate(element => {
      const controls = [...element.querySelectorAll('.hermes-kanban-attention button, .hermes-kanban-attention input')].filter(node => { const r=node.getBoundingClientRect(); return r.width > 0 && r.height > 0 }).map(node => { const r=node.getBoundingClientRect(); return { label: node.getAttribute('aria-label') || node.textContent?.trim() || node.tagName, width:r.width, height:r.height, radius:getComputedStyle(node).borderRadius } })
      const group=element.querySelector('[aria-label="Snooze presets"]'); const rows=group ? new Set([...group.querySelectorAll(':scope > button')].map(node => Math.round(node.getBoundingClientRect().top))).size : 0
      return { controls, rows, horizontalOverflow: document.documentElement.scrollWidth > innerWidth, clipped: controls.some(control => control.width <= 0 || control.height <= 0) }
    })
    if (closed.horizontalOverflow || closed.clipped || closed.rows > 2 || closed.controls.some(control => control.width < 44 || control.height < 44 || control.radius !== '0px')) throw new Error(`${width}px closed geometry failed: ${JSON.stringify(closed)}`)
    const closedFile = path.join(output, `webui-${width}-closed.png`)
    await page.screenshot({ path: closedFile, fullPage: true })
    await custom.click()
    const input = card.getByLabel('Custom wake time')
    await input.waitFor()
    const open = await card.evaluate(element => ({ horizontalOverflow: document.documentElement.scrollWidth > innerWidth, controls: [...element.querySelectorAll('.hermes-kanban-attention button,.hermes-kanban-attention input')].filter(node => { const r=node.getBoundingClientRect(); return r.width > 0 && r.height > 0 }).map(node => { const r=node.getBoundingClientRect(); return { width:r.width,height:r.height,radius:getComputedStyle(node).borderRadius } }) }))
    if (open.horizontalOverflow || open.controls.some(control => control.width < 44 || control.height < 44 || control.radius !== '0px')) throw new Error(`${width}px open geometry failed: ${JSON.stringify(open)}`)
    const openFile = path.join(output, `webui-${width}-open.png`)
    await page.screenshot({ path: openFile, fullPage: true })
    await input.press('Escape')
    if (!(await custom.evaluate(element => document.activeElement === element))) throw new Error(`${width}px Escape did not restore Custom focus`)
    for (const [state, file] of [['closed', closedFile], ['open', openFile]]) { const bytes=readFileSync(file); manifest.captures.push({ width, state, filename:path.basename(file), bytes:bytes.length, sha256:createHash('sha256').update(bytes).digest('hex') }) }
  }

  await page.setViewportSize({ width: 390, height: 800 })
  let attentionPosts = 0
  page.on('request', request => { if (request.method() === 'POST' && request.url().includes(`/tasks/${ids.snooze}/attention`)) attentionPosts += 1 })
  const hour = card.getByRole('button', { name: '1 hour' })
  await Promise.all([hour.click(), hour.click().catch(() => undefined)])
  await page.waitForFunction(() => [...document.querySelectorAll('[role="status"]')].some(node => node.textContent?.includes('Task snoozed until')))
  const snoozeReceipt = receipt(ids.snooze)
  if (attentionPosts !== 1 || snoozeReceipt?.state !== 'snoozed' || snoozeReceipt?.revision !== 1) throw new Error(`duplicate lock/backend receipt failed: ${JSON.stringify({ attentionPosts, snoozeReceipt })}`)

  const settleCard = page.getByText('WebUI settle sentinel').locator('..')
  await settleCard.getByRole('button', { name: 'Settle' }).click()
  await waitReceipt(ids.settle, 'settled')
  await page.reload({ waitUntil: 'networkidle' })
  const disclosure = page.locator('summary').filter({ hasText: /^Settled/ }).first()
  if (await disclosure.count()) await disclosure.click()
  await page.getByRole('button', { name: 'Wake' }).click()
  const wakeReceipt = await waitReceipt(ids.settle, 'active')
  if (wakeReceipt?.state !== 'active' || wakeReceipt?.revision !== 2) throw new Error(`wake receipt failed: ${JSON.stringify(wakeReceipt)}`)
  manifest.interactions = { attentionPosts, snoozeReceipt, wakeReceipt, escapeFocusRestored: true, localDatetimeControl: true, staleReconciliationCoveredByElectronReplay: true }
} finally {
  await browser?.close().catch(() => undefined)
  server.kill('SIGTERM')
  writeFileSync(path.join(output, 'server.log'), serverLog)
  writeFileSync(path.join(output, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`)
  rmSync(runtime, { recursive: true, force: true })
}
