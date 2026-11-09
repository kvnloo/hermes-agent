/**
 * The v1 `connection.json` side of a registry primary switch.
 *
 * Boot resolves `connection.json`'s app-global route BEFORE the v2 registry primary
 * (`resolveDesktopRemoteRoute`), so the two files must be kept in step or the stale one wins:
 * promoting This device while a global remote route is still on disk leaves every launch
 * dialing the gateway the user just promoted away from — the primary transport stays remote,
 * `globalRemoteActive()` stays true, and each profile that does not exist locally is refused
 * on the forced-local branch (`Profile "<name>" no longer exists.`).
 *
 * Removal already resets that route (`forgetRemovedGlobalRoute`), and Settings → Gateway Apply
 * writes v1 and imports it into the registry (`registerGlobalRoute`). A promotion of This
 * device never wrote v1 at all, and `reconcileRegistryDrift` deliberately leaves the
 * "route registered, primary names another source" case alone, so this module owns the
 * missing direction: registry → `connection.json`.
 */
import { modeIsRemoteLike } from './connection-config'
import type { ConnectionRegistry } from './connection-registry'
import { forgetRemovedGlobalRoute, withoutGlobalRoute } from './connection-registry-remove'

export interface PrimaryRouteIo {
  readConfig: () => Record<string, any>
  writeConfig: (config: Record<string, any>) => void
  log: (message: string) => void
}

/**
 * `connection.json` after promoting a LOCAL primary, or null when it needs no change.
 *
 * Only an app-global route is cleared. Per-profile overrides are separate routing decisions
 * and survive (`withoutGlobalRoute` keeps them).
 */
export function configForLocalPrimary(
  registry: ConnectionRegistry,
  config: Record<string, any>
): null | Record<string, any> {
  const primary = registry.connections.find(connection => connection.id === registry.primary)

  if (primary?.kind !== 'local') {
    return null
  }

  const routed = config?.mode === 'ssh' || modeIsRemoteLike(config?.mode)

  return routed ? withoutGlobalRoute(config) : null
}

/** Retire the app-global route once This machine is the primary, in the same step as the switch. */
export function applyLocalPrimaryRoute(registry: ConnectionRegistry, io: PrimaryRouteIo): void {
  const next = configForLocalPrimary(registry, io.readConfig())

  if (!next) {
    return
  }

  io.writeConfig(next)
  io.log('[connections] This device is the primary; connection.json route reset to local')
}

/**
 * Boot sweep: reset a route whose gateway left the saved list. Strict read, so an unreadable
 * store never reads as "every gateway was removed"; a failure is logged, never thrown.
 */
export function resetRemovedGlobalRoute(registry: ConnectionRegistry, io: PrimaryRouteIo): void {
  try {
    forgetRemovedGlobalRoute(registry, io)
  } catch (error) {
    io.log(`[connections] could not reset a removed gateway's route: ${(error as Error).message}`)
  }
}
