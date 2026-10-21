#!/usr/bin/env node
import { readFileSync } from 'node:fs'
import { access } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { assertOwnedInert } from './types.ts'

const source = dirname(fileURLToPath(import.meta.url))
const mode = process.argv[2] ?? 'handshake'
const framework = process.env.E2E_FRAMEWORK_ROOT ?? '/mnt/zer0models/hermes-wt/e2e'
const bin = join(framework, 'packages/e2e/dist/cli/bin.js')
const config = join(source, 'e2e.bugbash.config.ts')
const clientRoot = join(framework, 'packages/e2e/node_modules/@modelcontextprotocol/client')

function ownedManifest(path) {
  const manifest = JSON.parse(readFileSync(path, 'utf8'))
  assertOwnedInert(manifest)
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
  const { client } = await connect({ ...process.env, CI: '' })
  let session
  try {
    const opened = await client.callTool({ name:'open_session', arguments:{ target:'isolated-tern' } })
    if (opened.isError) throw new Error(JSON.stringify(opened))
    const text = opened.content.filter(block => block.type === 'text').map(block => block.text).join('\n')
    session = /^Session ([^\s]+) open on target /.exec(text)?.[1]
    if (!session) throw new Error('MCP open_session did not return its session identifier.')
    const catalog = await client.callTool({ name:'tools', arguments:{ session } })
    const evidence = await client.callTool({ name:'call', arguments:{ session, tool:'native_evidence', args:{ label:'mcp-open-smoke' } } })
    if (catalog.isError || evidence.isError) throw new Error(JSON.stringify({ catalog, evidence }))
    process.stdout.write(`${JSON.stringify({ open_session:true, session, catalog, evidence }, null, 2)}\n`)
  } finally {
    try { if (session) await client.callTool({ name:'close_session', arguments:{ session } }) }
    finally { await client.close() }
  }
} else {
  process.stderr.write('Use handshake (default) or open.\n')
  process.exit(2)
}
