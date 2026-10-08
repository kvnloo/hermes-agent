import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { afterEach, expect, test } from 'vitest'

// Supplements aortegamel's mock harness on liuhao1024's #135296; #135279
// (saralilyb) already describes the included-config overwrite hazard.
const prepare = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')).scripts.prepare
const roots = []
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true, maxRetries: 3 })
})

function run(command, args, cwd, env) {
  const result = spawnSync(command, args, { cwd, env, encoding: 'utf8', timeout: 30000 })
  expect(result.error, `${command}: ${result.stderr}`).toBeUndefined()
  expect(result.signal).toBeNull()
  return result
}

function fixture(layout, scope) {
  const root = mkdtempSync(join(tmpdir(), 'hermes real hooks '))
  roots.push(root)
  const home = join(root, 'home')
  const repository = join(root, 'repository')
  const hooks = join(home, 'custom hooks')
  for (const path of [home, repository, hooks]) mkdirSync(path, { recursive: true })
  // Allowlist: never inherit Git config overrides, npm settings or Hermes secrets.
  const env = { PATH: process.env.PATH, HOME: home, USERPROFILE: home,
    XDG_CONFIG_HOME: join(home, '.config'), GIT_CONFIG_NOSYSTEM: '1',
    GIT_CONFIG_GLOBAL: join(home, '.gitconfig'), GIT_TERMINAL_PROMPT: '0',
    GIT_AUTHOR_NAME: 'Fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid',
    GIT_COMMITTER_NAME: 'Fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid',
    npm_config_cache: join(root, 'npm-cache'), npm_config_userconfig: join(home, '.npmrc'),
    npm_config_globalconfig: join(root, 'npm-globalrc'), npm_config_audit: 'false',
    npm_config_fund: 'false', npm_config_update_notifier: 'false' }
  for (const key of ['SystemRoot', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP']) {
    if (process.env[key]) env[key] = process.env[key]
  }
  const git = (...args) => {
    const result = run('git', args, repository, env)
    expect(result.status, result.stderr).toBe(0)
    return result.stdout.trim()
  }
  git('init', '--quiet')
  git('commit', '--quiet', '--allow-empty', '-m', 'fixture')
  let cwd = repository
  if (layout === 'worktree') {
    cwd = join(root, 'linked worktree')
    git('worktree', 'add', '--quiet', '--detach', cwd)
    expect(readFileSync(join(cwd, '.git'), 'utf8')).toMatch(/^gitdir:/)
  }
  if (layout === 'copy') {
    cwd = join(root, 'source copy')
    mkdirSync(cwd)
  }
  writeFileSync(join(hooks, 'pre-commit'), '#!/bin/sh\n# user-owned sentinel\nexit 0\n', { mode: 0o755 })
  writeFileSync(join(home, '.gitconfig'), '# user global config\n')
  const included = join(home, 'included.gitconfig')
  if (scope === 'included') {
    writeFileSync(included, '# included user config\n')
    git('config', '--file', included, 'core.hooksPath', hooks)
    git('config', '--global', 'include.path', included)
  } else if (scope !== 'none') {
    git('config', `--${scope}`, 'core.hooksPath', hooks)
  }
  const files = [join(home, '.gitconfig'), join(repository, '.git/config'),
    ...(existsSync(included) ? [included] : [])]
  const before = files.map(path => readFileSync(path))
  const customHook = readFileSync(join(hooks, 'pre-commit'))
  writeFileSync(join(cwd, 'package.json'), JSON.stringify({ name: 'hooks-fixture',
    version: '1.0.0', private: true, scripts: { prepare } }))
  writeFileSync(join(cwd, 'lefthook.yml'), 'pre-commit:\n  commands:\n    fixture:\n      run: "echo fixture"\n')
  return { cwd, env, hooks, files, before, customHook, git }
}

// These are integration tests: real git, npm and locked lefthook must be on PATH.
// Missing dependencies fail visibly rather than producing a skipped/false-green run.
for (const layout of ['checkout', 'worktree']) {
  test.each(['global', 'local', 'included'])(`${layout}: preserve %s hooks and config byte-for-byte`, (scope) => {
    const f = fixture(layout, scope)
    expect(run('lefthook', ['version'], f.cwd, f.env).stdout.trim()).toBe('2.1.14')
    const result = run('npm', ['run', 'prepare'], f.cwd, f.env)
    expect(result.status, result.stderr).toBe(0)
    for (let i = 0; i < f.files.length; i++) expect(readFileSync(f.files[i])).toEqual(f.before[i])
    expect(readFileSync(join(f.hooks, 'pre-commit')).equals(f.customHook), `custom pre-commit overwritten; directory entries: ${readdirSync(f.hooks).join(', ')}`).toBe(true)
    expect(readdirSync(f.hooks)).toEqual(['pre-commit'])
    expect(result.stdout + result.stderr).toMatch(/core.hooksPath/)
    expect(result.stderr).toMatch(/lefthook install failed.*continuing without git hooks/)
  }, 60000)

  test(`${layout}: real hook installs in the repository`, () => {
    const f = fixture(layout, 'none')
    const result = run('npm', ['run', 'prepare'], f.cwd, f.env)
    expect(result.status, result.stderr).toBe(0)
    const hooksPath = run('git', ['rev-parse', '--git-path', 'hooks/pre-commit'], f.cwd, f.env)
    expect(hooksPath.status).toBe(0)
    expect(readFileSync(resolve(f.cwd, hooksPath.stdout.trim()), 'utf8')).toContain('lefthook')
    expect(readFileSync(join(f.hooks, 'pre-commit')).equals(f.customHook), `custom pre-commit overwritten; directory entries: ${readdirSync(f.hooks).join(', ')}`).toBe(true)
  }, 60000)
}

test('source copy inside no Git repository leaves included custom hooks intact', () => {
  const f = fixture('copy', 'included')
  const result = run('npm', ['run', 'prepare'], f.cwd, f.env)
  expect(result.status, result.stderr).toBe(0)
  expect(readFileSync(join(f.hooks, 'pre-commit')).equals(f.customHook), `custom pre-commit overwritten; directory entries: ${readdirSync(f.hooks).join(', ')}`).toBe(true)
  expect(readdirSync(f.hooks)).toEqual(['pre-commit'])
  expect(result.stderr).not.toContain('lefthook')
}, 60000)

test('npm still surfaces genuine dependency and build failures', () => {
  const f = fixture('checkout', 'global')
  // npm ci requires a lock; this is a real dependency-stage failure, no stub.
  const dependency = run('npm', ['ci', '--offline'], f.cwd, f.env)
  expect(dependency.status).not.toBe(0)
  expect(dependency.stderr).toMatch(/package-lock.json|npm-shrinkwrap.json/)
  const manifest = JSON.parse(readFileSync(join(f.cwd, 'package.json'), 'utf8'))
  manifest.scripts.build = 'node --check broken.cjs'
  writeFileSync(join(f.cwd, 'package.json'), JSON.stringify(manifest))
  writeFileSync(join(f.cwd, 'broken.cjs'), 'function {\n')
  const build = run('npm', ['run', 'build'], f.cwd, f.env)
  expect(build.status).not.toBe(0)
  expect(build.stderr).toContain('SyntaxError')
}, 60000)
