#!/usr/bin/env node
import { readFileSync, realpathSync } from 'node:fs'
import { access } from 'node:fs/promises'
import { dirname, join, sep } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'

const source = dirname(fileURLToPath(import.meta.url))
const SENTINEL = 'isolated inert fixture; no turns or grants\n'
const mode = process.argv[2] ?? 'handshake'
const framework = process.env.E2E_FRAMEWORK_ROOT ?? '/mnt/zer0models/hermes-wt/e2e'
const bin = join(framework, 'packages/e2e/dist/cli/bin.js')
const config = join(source, 'e2e.bugbash.config.ts')
const clientRoot = join(framework, 'packages/e2e/node_modules/@modelcontextprotocol/client')

function ownedManifest(path) {
  const manifest = JSON.parse(readFileSync(path, 'utf8'))
  if (!manifest.runtime?.startsWith('/tmp/') || !manifest.display || manifest.display === 'wayland-0') {
    throw new Error('Owned isolated runtime/display is required; physical wayland-0 is refused.')
  }
  if (!manifest.proof?.startsWith('/tmp/') || manifest.proof === '/tmp') {
    throw new Error('Proof directory must be a private /tmp path.')
  }
  const proof = realpathSync(manifest.proof)
  const home = realpathSync(manifest.home)
  if (home !== proof && !home.startsWith(`${proof}${sep}`)) {
    throw new Error('Hermes home is not inside the owned proof directory.')
  }
  if (readFileSync(join(home, '.native-settings-e2e'), 'utf8') !== SENTINEL) {
    throw new Error('Owned inert sentinel is missing or not the native-settings fixture.')
  }
  return manifest
}

async function connect(env) {
  const pkg = JSON.parse(readFileSync(join(framework, 'packages/e2e/package.json'), 'utf8'))
  if (pkg.version !== '0.16.0') throw new Error(`Expected installed e2e 0.16.0, got ${pkg.version}`)
  await access(bin)
  const { Client } = await import(pathToFileURL(join(clientRoot, 'dist/index.mjs')).href)
  const { StdioClientTransport } = await import(pathToFileURL(join(clientRoot, 'dist/stdio.mjs')).href)
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [bin, 'mcp', '--config', config, '--target', 'isolated-tern', '--max-sessions', '1'],
    cwd: source,
    env,
    stderr: 'pipe',
  })
  let stderr = ''
  transport.stderr?.on('data', (chunk) => { stderr += chunk.toString() })
  const client = new Client({ name: 'hermes-native-bugbash', version: '0.0.0' })
  await client.connect(transport)
  return { client, stderr }
}

if (mode === 'handshake') {
  const env = { ...process.env, CI: '' }
  delete env.NATIVE_SETTINGS_MANIFEST
  const { client } = await connect(env)
  try {
    const { tools } = await client.listTools()
    const { resources } = await client.listResources()
    process.stdout.write(`${JSON.stringify({
      handshake: true,
      open_session: false,
      tools: tools.map((tool) => tool.name),
      resources: resources.map((resource) => resource.uri),
      instructions: client.getInstructions(),
    }, null, 2)}\n`)
  } finally {
    await client.close()
  }
} else if (mode === 'open') {
  const manifestPath = process.env.NATIVE_SETTINGS_MANIFEST
  if (!manifestPath) {
    process.stderr.write('open_session deferred: owned NATIVE_SETTINGS_MANIFEST is not ready.\n')
    process.exit(2)
  }
  ownedManifest(manifestPath)
  process.stderr.write('Manifest+sentinel accepted; open_session is still deferred until parent supplies six owned explorer manifests.\n')
  process.exit(2)
} else {
  process.stderr.write('Use handshake (default) or open.\n')
  process.exit(2)
}
