/**
 * Regression for origin #123437: quitting Desktop must not rewrite boot progress
 * to "Restarting desktop connection". The quit coordinator is the one caller that
 * previously inherited soft=false; every intentional soft re-home already passes
 * { soft: true }.
 *
 * main.ts is the Electron entry and is not imported by vitest; pin the quit-path
 * call site so a future edit that drops soft:true fails this suite.
 */
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

import { test } from 'vitest'

const MAIN = path.join(__dirname, 'main.ts')

function quitCoordinatorTeardownCall(source: string): string {
  const marker = 'const backendShutdown = createBackendShutdownCoordinator'
  const start = source.indexOf(marker)
  assert.ok(start >= 0, 'createBackendShutdownCoordinator quit site missing')
  const window = source.slice(start, start + 800)
  const match = window.match(/teardownPrimaryBackendAndWait\(([^)]*)\)/)
  assert.ok(match, 'quit coordinator does not call teardownPrimaryBackendAndWait')
  return match[0]
}

test('quit coordinator tears down primary with soft:true', () => {
  const source = fs.readFileSync(MAIN, 'utf8')
  const call = quitCoordinatorTeardownCall(source)
  assert.match(
    call,
    /\{\s*soft:\s*true\s*\}/,
    `quit path must pass { soft: true } so boot progress is not rewritten; got ${call}`
  )
})

test('Reconnect boot-progress copy stays soft-gated', () => {
  const source = fs.readFileSync(MAIN, 'utf8')
  assert.match(source, /message:\s*'Restarting desktop connection'/)
  // soft arm still skips the reconnect overlay
  assert.match(
    source,
    /if\s*\(\s*!soft\s*\)\s*\{\s*resetBootProgressForReconnect\(\)/s
  )
})
