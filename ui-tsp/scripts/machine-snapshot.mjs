#!/usr/bin/env node
// Explicit, read-only Arch/Linux snapshot collector. Runs only when invoked
// by a human; /machine never runs this script or schedules a scan.
// Visual inspiration credit: HANCORE (@hancore_linux), rumb preview.
import { spawnSync } from 'node:child_process'
import { statfsSync } from 'node:fs'
import os from 'node:os'

const journal = process.argv.includes('--journal')
if (process.argv.some(arg => arg !== '--journal' && arg !== '--help' && arg !== '-h')) {
  process.stderr.write('Usage: node machine-snapshot.mjs [--journal]\n')
  process.exit(2)
}
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  process.stdout.write('Read-only JSON to stdout. Use --journal to aggregate your accessible error journal without exporting messages. No sudo, upgrades or network.\n')
  process.exit(0)
}
const run = (bin, args) => {
  const result = spawnSync(bin, args, { encoding: 'utf8', timeout: 5_000, maxBuffer: 1024 * 1024,
    env: { ...process.env, LC_ALL: 'C' } })
  return !result.error && result.status === 0 ? result.stdout : null
}
const updateText = process.platform === 'linux' ? run('pacman', ['-Qu']) : null
const installedText = process.platform === 'linux' ? run('pacman', ['-Qq']) : null
// Pacman output is plain text; do not treat a name as a risk classification.
const updates = (updateText ?? '').split(/\r?\n/).filter(Boolean).slice(0, 5000).flatMap(line => {
  const parts = line.trim().split(/\s+/)
  return parts.length >= 4 && parts[2] === '->'
    ? [{ package: parts[0], from: parts[1], to: parts[3], risk: 'unclassified' }]
    : []
})
let diskPercent = null, availableGiB = null
try {
  const stat = statfsSync(process.cwd(), { bigint: true })
  const blocks = Number(stat.blocks), blockSize = Number(stat.bsize)
  if (blocks > 0 && blockSize > 0) {
    diskPercent = Math.round(100 * (blocks - Number(stat.bfree)) / blocks * 10) / 10
    availableGiB = Math.round(Number(stat.bavail) * blockSize / 1024 ** 3 * 10) / 10
  }
} catch { /* unavailable is reported as unknown, never zero */ }

const incidents = new Map()
const events = []
let problemsChecked = false
if (journal && process.platform === 'linux') {
  const output = run('journalctl', ['--no-pager', '--since', 'today', '-p', 'err', '-o', 'json', '-n', '250'])
  if (output !== null) {
    problemsChecked = true
    for (const line of output.split(/\r?\n/)) {
      if (!line.trim()) { continue }
      try {
        const record = JSON.parse(line)
        const subject = String(record.SYSLOG_IDENTIFIER ?? record._COMM ?? 'unknown')
          .replace(/[\x00-\x1f]/g, '').slice(0, 72)
        incidents.set(subject, (incidents.get(subject) ?? 0) + 1)
        if (events.length < 8) {
          const ts = Number(record.__REALTIME_TIMESTAMP)
          events.push({
            time: Number.isFinite(ts) && ts > 0 ? new Date(ts / 1000).toISOString() : 'time unknown',
            source: subject,
            message: 'error observed (raw journal text withheld)'
          })
        }
      } catch { /* ignore malformed journal lines */ }
    }
  }
}
const problems = [...incidents].sort((a, b) => b[1] - a[1])
  .slice(0, 50).map(([subject, count]) => ({ subject, count, kind: 'error' }))
const report = {
  schema: 1,
  captured_at: new Date().toISOString(),
  machine: os.hostname(),
  os: `${os.type()} ${os.release()} ${os.arch()}`,
  updates_checked: updateText !== null,
  problems_checked: problemsChecked,
  disk_percent: diskPercent,
  available_gib: availableGiB,
  installed_packages: installedText === null ? null : installedText.split(/\r?\n/).filter(Boolean).length,
  updates, problems, events
}
process.stdout.write(JSON.stringify(report, null, 2) + '\n')
