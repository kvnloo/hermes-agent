import { expect, it } from 'vitest'

import { configForLocalPrimary } from './connection-primary-route'
import { normalizeRegistry, setPrimaryConnection } from './connection-registry'

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
