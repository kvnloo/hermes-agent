import assert from 'node:assert/strict'
import { spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'vitest'
import { runElectronBuilder } from './run-electron-builder.mjs'
import { publishPackagingInputs } from './prepared-packaging.mjs'
import { recordNativeInputs } from './prepared-native-deps.mjs'

test('copied icons toolset runs a CommonJS script beneath the ESM desktop package', async () => {
  const source = path.resolve(import.meta.dirname, '../../..')
  const out = fs.mkdtempSync(path.join(os.tmpdir(), 'builder-icons-commonjs-'))
  let copiedIcons
  try {
    const electron = path.join(out, 'electron.zip')
    fs.writeFileSync(electron, 'fixture archive')
    const icons = path.join(out, 'icons')
    fs.mkdirSync(icons)
    fs.writeFileSync(path.join(icons, 'icon-tool.js'),
      'const fs = require("node:fs"); process.stdout.write(fs.existsSync(__filename) ? "commonjs ok" : "missing")\n')

    const manifest = await publishPackagingInputs({
      source, out, target: `${process.platform}-${process.arch}`, formats: ['dir'],
      electron, toolsets: { icons },
    })
    const nativeDeps = path.join(out, 'native')
    fs.mkdirSync(path.join(nativeDeps, 'node-pty'), { recursive: true })
    fs.writeFileSync(path.join(nativeDeps, 'node-pty/package.json'), '{}\n')
    recordNativeInputs({ source, out: nativeDeps, platform: process.platform, arch: process.arch })

    let builderArgs
    const result = runElectronBuilder(['--prepared', manifest, '--native-deps', nativeDeps, '--dir'], {
      spawn: (_node, args) => { builderArgs = args; return { status: 0 } },
    })
    assert.equal(result, 0)
    const prefix = '-c.toolsets.icons.url=file://'
    const argument = builderArgs.find(arg => arg.startsWith(prefix))
    assert.ok(argument, 'electron-builder must receive the copied icons toolset')
    copiedIcons = argument.slice(prefix.length)

    const run = spawnSync(process.execPath, [path.join(copiedIcons, 'icon-tool.js')], { encoding: 'utf8' })
    assert.equal(run.status, 0, run.stderr)
    assert.equal(run.stdout, 'commonjs ok')
  } finally {
    if (copiedIcons) fs.rmSync(copiedIcons, { recursive: true, force: true })
    fs.rmSync(out, { recursive: true, force: true })
  }
})
