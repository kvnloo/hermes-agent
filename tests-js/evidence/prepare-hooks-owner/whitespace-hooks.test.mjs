import { spawnSync } from 'node:child_process'
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import assert from 'node:assert/strict'
import test from 'node:test'

// Supplemental contract for aortegamel's preservation guard. Pass the actual
// package.json under test; no Git/npm/Lefthook behavior is mocked.
const prepare = JSON.parse(readFileSync(process.env.PREPARE_PACKAGE, 'utf8')).scripts.prepare
for (const value of [' ', '']) {
  test(`included hooksPath ${JSON.stringify(value)} remains configured and untouched`, () => {
    const root = mkdtempSync(join(tmpdir(), 'hooks presence '))
    try {
      const home = join(root, 'home'), cwd = join(root, 'repo')
      mkdirSync(home); mkdirSync(cwd)
      const env = { PATH: process.env.PATH, HOME: home, USERPROFILE: home,
        GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: join(home, '.gitconfig'),
        npm_config_cache: join(root, 'cache'), npm_config_userconfig: join(home, '.npmrc'),
        npm_config_globalconfig: join(home, 'npmrc'), npm_config_update_notifier: 'false' }
      const run = (command, ...args) => {
        const result = spawnSync(command, args, { cwd, env, encoding: 'utf8', timeout: 30000 })
        assert.ifError(result.error)
        assert.equal(result.status, 0, result.stderr)
        return result.stdout
      }
      run('git', 'init', '--quiet')
      assert.equal(run('lefthook', 'version').trim(), '2.1.14')
      const included = join(home, 'included.gitconfig')
      run('git', 'config', '--file', included, 'core.hooksPath', value)
      run('git', 'config', '--global', 'include.path', included)
      assert.equal(run('git', 'config', '--get', 'core.hooksPath'), `${value}\n`)
      const hooks = join(cwd, value)
      mkdirSync(hooks, { recursive: true })
      const sentinel = join(hooks, 'pre-commit')
      writeFileSync(sentinel, '#!/bin/sh\n# user-owned sentinel\nexit 0\n', { mode: 0o755 })
      writeFileSync(join(cwd, 'package.json'), JSON.stringify({ name: 'fixture', version: '1.0.0', private: true, scripts: { prepare } }))
      writeFileSync(join(cwd, 'lefthook.yml'), 'pre-commit:\n  commands:\n    fixture:\n      run: "echo fixture"\n')
      const paths = [sentinel, included, join(home, '.gitconfig'), join(cwd, '.git/config')]
      const before = paths.map(path => readFileSync(path))
      const entries = readdirSync(hooks)
      const output = run('npm', 'run', 'prepare')
      paths.forEach((path, i) => assert.ok(readFileSync(path).equals(before[i]), `${path} changed`))
      assert.deepEqual(readdirSync(hooks), entries, 'no backup or additional hook')
      // Empty is present too: do not rely on Lefthook failing accidentally.
      assert.match(output, /^prepare: custom core.hooksPath set, skipping lefthook install$/m)
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })
}
