#!/usr/bin/env node
import { execFile, spawn } from 'node:child_process'
import { access, chmod, copyFile, mkdir, readFile, realpath, symlink, writeFile } from 'node:fs/promises'
import { dirname, isAbsolute, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parseArgs, promisify } from 'node:util'

const exec = promisify(execFile)

const source = dirname(fileURLToPath(import.meta.url))
const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: Object.fromEntries(['entry', 'root', 'control', 'pane', 'proof-dir', 'python', 'framework-root'].map(name => [name, { type: 'string' }]))
})
const mode = positionals[0]
if (!['prepare', 'run'].includes(mode) || positionals.length !== 1) throw new Error('Use prepare or run, with --entry --root --control --pane --proof-dir --python [--framework-root].')
for (const name of ['entry', 'root', 'control', 'pane', 'proof-dir', 'python']) if (!values[name]) throw new Error(`Missing --${name}`)
const root = await realpath(values.root)
try {
  await access(join(root, '.env'))
  throw new Error('Refusing a checkout with a project dotenv fallback; no non-fixture env files may be loaded or sanitized.')
} catch (error) {
  if (error.code !== 'ENOENT') throw error
}
const entry = await realpath(values.entry)
// Keep the venv executable spelling: realpath would bypass its pyvenv.cfg.
const python = resolve(values.python)
await access(python)
const proof = resolve(values['proof-dir'])
const control = values.control.replace(/^127\.0\.0\.1:/, '')
const pane = values.pane
if (!/^\d+$/.test(control) || !/^\d+$/.test(pane)) throw new Error('This adapter requires an explicit numeric loopback control port and private local PTY pane id.')
if (!entry.startsWith(`${root}/`)) throw new Error('--entry must belong to --root (the integrated native-settings checkout).')
if (!isAbsolute(values.python)) throw new Error('--python must be an absolute real Python executable.')
if (!proof.startsWith('/tmp/') || proof === '/tmp') throw new Error('--proof-dir must be a private directory under /tmp, outside all git worktrees.')
const framework = await realpath(values['framework-root'] ?? '/mnt/zer0models/hermes-wt/e2e')
const pkg = JSON.parse(await readFile(join(framework, 'packages/e2e/package.json'), 'utf8'))
if (pkg.version !== '0.16.0') throw new Error(`Expected installed e2e 0.16.0, got ${pkg.version}`)
const bin = join(framework, 'packages/e2e/dist/cli/bin.js')
await access(bin)
await mkdir(proof, { recursive: true, mode: 0o700 })
const canonicalProof = await realpath(proof)
if (canonicalProof !== proof) throw new Error('Proof directory must not resolve through a symlink.')
if (![root, source, framework].every(path => relative(path, proof).startsWith('..'))) throw new Error('Proof output must remain outside source checkouts.')
await chmod(proof, 0o700)
const manifestPath = join(proof, 'manifest.json')
const manifest = {
  root, entry, python, control, pane, proof,
  home: join(proof, 'hermes-home'),
  record: join(proof, 'gateway.jsonl'),
  tsp: join(proof, 'tsp.jsonl'),
  gate: join(proof, 'response-gate.json'),
  launch: join(proof, 'launch-native.mjs'),
  project: join(proof, 'suite'),
  runtime: process.env.XDG_RUNTIME_DIR,
  display: process.env.WAYLAND_DISPLAY
}
if (!manifest.runtime?.startsWith('/tmp/') || !manifest.display || manifest.display === 'wayland-0') throw new Error('Parent must supply the verified isolated XDG_RUNTIME_DIR and WAYLAND_DISPLAY, not the physical display.')
const { stdout: nativeStdout } = await exec('tern', ['ctl', '--control', control, 'state'], { timeout: 10000, maxBuffer: 32 * 1024 * 1024, killSignal: 'SIGKILL' })
const native = JSON.parse(nativeStdout)
if (native?.ok !== true) throw new Error('Native control state is not available for pane ownership.')
const focused = native.focused
if (focused === null || typeof focused !== 'object' || Array.isArray(focused)) throw new Error('Native control did not name a focused pane.')
if (String(focused.id) !== pane) throw new Error('Refusing a pane that is not the focused harness target.')
if (!Array.isArray(native.panes) || !native.panes.some(item => String(item?.id) === pane)) throw new Error('Refusing a pane that is not present on this isolated control window.')
if (Array.isArray(native.panes) && native.panes.some(item => typeof item?.running === 'string' && item.running.includes('launch-native.mjs') && String(item.id) !== pane)) {
  throw new Error('Refusing because another pane already runs a harness launcher.')
}
if (mode === 'prepare') {
  const cwd = focused.cwd
  if (typeof cwd !== 'string' || !cwd.startsWith('/tmp/') || cwd === '/tmp' || cwd.startsWith(`${root}/`) || cwd === root) {
    throw new Error('Refusing an existing user/manual/conversation pane. Create a new idle pane whose cwd is a private /tmp harness directory, then prepare.')
  }
  if (focused.busy !== false || (focused.running != null && focused.running !== '')) {
    throw new Error('Refusing an occupied pane; allocate a fresh idle harness pane.')
  }
  try { await access(manifestPath); throw new Error('Proof directory already prepared. Use run or a fresh proof directory; never overwrite a profile in use.') } catch (error) { if (!(error instanceof Error) || !('code' in error) || error.code !== 'ENOENT') throw error }
  await mkdir(manifest.home, { mode: 0o700 })
  // This is the real application's inert launch config, not a response fixture.
  await writeFile(join(manifest.home, 'config.yaml'), `model:\n  default: native-settings-e2e\n  provider: custom\n  base_url: http://127.0.0.1:9/v1\n  api_key: inert-e2e-not-a-credential\nagent:\n  reasoning_effort: low\n  max_turns: 7\n  environment_hint: e2e-initial-hint\ndisplay:\n  show_reasoning: false\n  skin: mono\n  resume_display: minimal\nterminal:\n  backend: local\nauth:\n  adopt_external_logins: false\napprovals:\n  mode: manual\ntelemetry:\n  shared_metrics:\n    enabled: false\n    send: false\nlogging:\n  level: ERROR\ne2e_preserve:\n  marker: native-settings-isolated\n  template: '\${E2E_UNRESOLVED_TEMPLATE}'\n`, { mode: 0o600 })
  await writeFile(join(manifest.home, '.native-settings-e2e'), 'isolated inert fixture; no turns or grants\n', { mode: 0o600 })
  await mkdir(join(proof, 'managed-empty'), { mode: 0o700 })
  const foreign = join(proof, 'host-home/.hermes/profiles/foreign')
  await mkdir(foreign, { recursive: true, mode: 0o700 })
  await writeFile(join(foreign, 'config.yaml'), 'agent:\n  max_turns: 91\n  reasoning_effort: none\ne2e_preserve: foreign-island\n', { mode: 0o600 })
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2), { mode: 0o600 })
  for (const name of ['gateway.mjs', 'state.py']) await copyFile(join(source, name), join(proof, name))
  await chmod(join(proof, 'gateway.mjs'), 0o700)
  await writeFile(manifest.launch, `#!/usr/bin/env node
import { spawn } from 'node:child_process'
import { readFileSync } from 'node:fs'
const m = JSON.parse(readFileSync(${JSON.stringify(manifestPath)}, 'utf8'))
process.chdir(m.root)
const env = {
  ...Object.fromEntries(['PATH','TERM','TERM_PROGRAM','COLORTERM','LANG','LC_ALL','TZ'].flatMap(key => process.env[key] === undefined ? [] : [[key,process.env[key]]])),
  HOME:${JSON.stringify(join(proof, 'host-home'))},
  XDG_CONFIG_HOME:${JSON.stringify(join(proof, 'host-home/.config'))},
  XDG_CACHE_HOME:${JSON.stringify(join(proof, 'host-home/.cache'))},
  HERMES_HOME:m.home,
  HERMES_MANAGED_DIR:${JSON.stringify(join(proof, 'managed-empty'))},
  HERMES_PYTHON:${JSON.stringify(join(proof, 'gateway.mjs'))},
  HERMES_PYTHON_SRC_ROOT:m.root,
  HERMES_TUI_CWD:m.root,
  TERN_TSP_RECORD:m.tsp,
  XDG_RUNTIME_DIR:m.runtime,
  WAYLAND_DISPLAY:m.display
}
env.OPENAI_API_KEY='inert-e2e-not-a-credential'
const child=spawn(process.execPath,[m.entry],{cwd:m.root,env,stdio:'inherit'})
child.on('exit',code=>process.exit(code ?? 1))
`, { mode: 0o700 })
  await mkdir(manifest.project, { mode: 0o700 })
  for (const name of ['adapter.ts', 'native-settings.e2e.ts', 'config.ts', 'types.ts', 'tsconfig.json']) await copyFile(join(source, name), join(manifest.project, name))
  await writeFile(join(manifest.project, 'package.json'), JSON.stringify({ name: 'hermes-native-settings-private-proof', private: true, type: 'module' }), { mode: 0o600 })
  await symlink(join(framework, 'node_modules'), join(manifest.project, 'node_modules'), 'dir')
  const shellArg = value => "'" + value.replaceAll("'", "'\\''") + "'"
  const command = `cd ${shellArg(root)} && ${shellArg(manifest.launch)}`
  console.log(`Parent launch ONCE (first verify focused.id=${pane}, busy=false, running=null):\ntern ctl --control ${control} ${shellArg(`run ${JSON.stringify(command)}`)}\nParent run:\n${shellArg(process.execPath)} ${shellArg(join(source, 'run.mjs'))} run --root ${shellArg(root)} --entry ${shellArg(entry)} --python ${shellArg(python)} --control ${control} --pane ${pane} --proof-dir ${shellArg(proof)} --framework-root ${shellArg(framework)}`)
} else {
  const saved = JSON.parse(await readFile(manifestPath, 'utf8'))
  for (const key of ['root','entry','python','control','pane','proof','runtime','display']) if (saved[key] !== manifest[key]) throw new Error(`Prepared ${key} differs from run. Use the exact prepared isolated target.`)
  if (typeof focused.running !== 'string' || !focused.running.includes(manifest.launch)) {
    throw new Error('Refusing to run against a pane that is not executing the prepared harness launcher.')
  }
  if (String(focused.id) !== saved.pane) throw new Error('Prepared pane is not the focused harness-owned pane.')
  // Refresh suite code only. Never replace the live application's profile/record.
  for (const name of ['adapter.ts', 'native-settings.e2e.ts', 'config.ts', 'types.ts', 'tsconfig.json']) await copyFile(join(source, name), join(manifest.project, name))
  const child = spawn(process.execPath, [bin, 'run', '--config', join(manifest.project, 'config.ts'), '--workers', '1', '--retries', '0', '--no-cache'], { cwd: manifest.project, env: { ...process.env, NATIVE_SETTINGS_MANIFEST: manifestPath }, stdio: 'inherit' })
  child.on('exit', code => process.exit(code ?? 1))
}
