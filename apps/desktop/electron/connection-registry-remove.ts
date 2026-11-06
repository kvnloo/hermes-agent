import { applyConnectionConfigAtomically } from './connection-config-apply'
import { type ConnectionRegistry, reconcileRegistryDrift, removeConnection } from './connection-registry'

interface ConnectionRemovalWriters {
  writeConfig: (config: Record<string, any>) => void
  writeRegistry: (registry: ConnectionRegistry) => void
}

/** Persist the saved-connection removal before tearing down its live resources. */
export async function removeSavedConnection(
  id: string,
  registry: ConnectionRegistry,
  config: Record<string, any>,
  writers: ConnectionRemovalWriters
): Promise<ConnectionRegistry> {
  const nextRegistry = removeConnection(registry, id)
  // Use the reader's identity policy: clear only a global legacy route that
  // this deletion would cause it to re-import. An unrelated removal, a route
  // still represented by another entry, and pre-existing drift stay untouched.
  const before = reconcileRegistryDrift(registry, config)
  const after = reconcileRegistryDrift(nextRegistry, config)

  // A saved SSH route can have a same-host peer with a different key.
  // Deleting the active route must not let drift repair overwrite that peer.
  const wouldRewriteSshPeer = config.mode === 'ssh' && !before.changed && after.changed
  if (
    before.registry.connections.length === registry.connections.length &&
    (after.registry.connections.length > nextRegistry.connections.length || wouldRewriteSshPeer)
  ) {
    await applyConnectionConfigAtomically({
      previousConfig: config,
      previousRegistry: registry,
      nextConfig: { ...config, mode: 'local', remote: {} },
      nextRegistry,
      ...writers,
      apply: async () => undefined
    })
  } else {
    writers.writeRegistry(nextRegistry)
  }

  return nextRegistry
}
