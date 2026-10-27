import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'

import { expect, test } from './test'
import { buildAppEnv, type Sandbox } from './fixtures'

test('app env removes hostile Kanban selectors and pins the disposable database', () => {
  const originalEnv = { ...process.env }
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-desktop-env-'))
  try {
    const sandbox = {
      root,
      hermesHome: path.join(root, 'hermes-home'),
      userDataDir: path.join(root, 'user-data'),
    } as Sandbox
    const productionDb = path.join(root, 'production', 'kanban.db')
    process.env.HERMES_KANBAN_DB = productionDb
    process.env.Hermes_Kanban_Home = path.join(root, 'production-home')
    process.env.HERMES_KANBAN_BOARD = 'production'

    const env = buildAppEnv(sandbox, { hermes_kanban_board: 'also-production' })

    expect(env.HERMES_KANBAN_DB).toBe(path.join(sandbox.hermesHome, 'kanban.db'))
    expect(Object.keys(env).filter(key => key.toUpperCase().startsWith('HERMES_KANBAN_'))).toEqual([
      'HERMES_KANBAN_DB',
    ])
    fs.mkdirSync(sandbox.hermesHome, { recursive: true })
    const child = spawnSync(
      process.execPath,
      ['-e', "require('node:fs').writeFileSync(process.env.HERMES_KANBAN_DB, 'isolated')"],
      { env },
    )
    expect(child.status).toBe(0)
    expect(fs.existsSync(path.join(sandbox.hermesHome, 'kanban.db'))).toBe(true)
    expect(fs.existsSync(productionDb)).toBe(false)
  } finally {
    process.env = originalEnv
    fs.rmSync(root, { recursive: true, force: true })
  }
})