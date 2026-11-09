import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { expect, it, onTestFinished } from 'vitest'

import { applyLocalPrimaryRoute, configForLocalPrimary } from './connection-primary-route'
import { normalizeRegistry, setPrimaryConnection } from './connection-registry'
import { resolveDesktopRemoteRoute } from './desktop-remote-route'
import { writeSecretFileAtomic } from './hardening'

// Boot resolves connection.json's app-global route before the registry primary, so a
// promotion back to This device must retire that route in the same write. Without it the
// launch keeps dialing the gateway it was promoted away from, and every profile that only
// exists on that gateway is refused on the forced-local branch.

const registry = (primary = 'gw-b') =>
  normalizeRegistry({
    version: 2,
    primary,
    launchMode: 'last-used',
    lastUsed: primary,
    connections: [
      { id: 'local', kind: 'local', label: 'This device' },
      { id: 'gw-b', kind: 'remote', label: 'Gateway B', url: 'http://192.0.2.10:9119', authMode: 'token' }
    ]
  })

const globalRemote = {
  mode: 'remote',
  remote: { url: 'http://192.0.2.10:9119', authMode: 'token', token: 'ciphertext' },
  profiles: { research: { mode: 'remote', url: 'https://research.example.invalid', authMode: 'oauth' } }
}

it('promoting This device resets the v1 global route that still outranks it at boot', () => {
  const cleared = configForLocalPrimary(setPrimaryConnection(registry(), 'local'), globalRemote)

  expect(cleared?.mode).toBe('local')
  expect(cleared?.remote).toEqual({})
  // A per-profile override is not an app-global route, so it must survive the reset.
  expect(cleared?.profiles).toEqual(globalRemote.profiles)
})

it('promoting a remote gateway leaves connection.json alone', () => {
  const promoted = setPrimaryConnection(setPrimaryConnection(registry(), 'local'), 'gw-b')

  expect(configForLocalPrimary(promoted, globalRemote)).toBeNull()
})

it('an SSH app-global route is a route too', () => {
  const ssh = { mode: 'ssh', remote: { host: 'build.example.invalid', user: 'hermes' }, profiles: {} }

  expect(configForLocalPrimary(setPrimaryConnection(registry(), 'local'), ssh)?.mode).toBe('local')
})

it('a cloud app-global route is a route too', () => {
  const cloud = { mode: 'cloud', remote: { url: 'https://cloud.example.invalid', org: 'acme' }, profiles: {} }

  expect(configForLocalPrimary(setPrimaryConnection(registry(), 'local'), cloud)?.remote).toEqual({})
})

it('a local primary with no app-global route needs no rewrite', () => {
  const alreadyLocal = { mode: 'local', remote: {}, profiles: { research: { mode: 'local' } } }

  expect(configForLocalPrimary(setPrimaryConnection(registry(), 'local'), alreadyLocal)).toBeNull()
})

function persistedRemote() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-local-primary-'))
  onTestFinished(() => fs.rmSync(root, { recursive: true, force: true }))
  const configPath = path.join(root, 'connection.json')
  const registryPath = path.join(root, 'connections.json')
  const readConfig = () => JSON.parse(fs.readFileSync(configPath, 'utf8'))
  const readRegistry = () => normalizeRegistry(JSON.parse(fs.readFileSync(registryPath, 'utf8')))
  const writeConfig = (value: Record<string, any>) => writeSecretFileAtomic(configPath, JSON.stringify(value))
  const writeRegistry = (value: ReturnType<typeof registry>) =>
    writeSecretFileAtomic(registryPath, JSON.stringify(value))

  writeConfig(globalRemote)
  writeRegistry(registry())
  return { readConfig, readRegistry, writeConfig, writeRegistry }
}

it('persists both primary and boot route before reporting a successful local promotion', async () => {
  const state = persistedRemote()
  const local = setPrimaryConnection(state.readRegistry(), 'local')

  await applyLocalPrimaryRoute(local, { ...state, log: () => {} })

  expect(state.readRegistry().primary).toBe('local')
  expect(state.readConfig().mode).toBe('local')
  expect(state.readConfig().profiles).toEqual(globalRemote.profiles)
  expect(resolveDesktopRemoteRoute({ registry: state.readRegistry(), config: state.readConfig() })).toBeNull()
})

it.each(['config', 'registry'] as const)(
  'does not persist split boot/primary state when the %s write fails',
  async failingStore => {
    const state = persistedRemote()
    const failure = new Error('injected write failure')
    let failed = false
    const io = {
      readConfig: state.readConfig,
      readRegistry: state.readRegistry,
      writeConfig: (value: Record<string, any>) => {
        if (failingStore === 'config' && !failed) {
          failed = true
          throw failure
        }

        state.writeConfig(value)
      },
      writeRegistry: (value: ReturnType<typeof registry>) => {
        if (failingStore === 'registry' && !failed) {
          failed = true
          throw failure
        }

        state.writeRegistry(value)
      },
      log: () => {}
    }

    await expect(applyLocalPrimaryRoute(setPrimaryConnection(state.readRegistry(), 'local'), io)).rejects.toBe(failure)
    expect(state.readConfig()).toEqual(globalRemote)
    expect(state.readRegistry()).toEqual(registry())
    expect(resolveDesktopRemoteRoute({ registry: state.readRegistry(), config: state.readConfig() })?.source).toBe(
      'settings'
    )
  }
)
