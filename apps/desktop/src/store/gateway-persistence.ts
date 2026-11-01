import { isGatewayReauthRequired, LOCAL_CONNECTION_ID } from '@hermes/shared'

import type { DesktopConnectionsRegistry, DesktopRegistryConnection } from '@/global'
import { isPermanentLocalGatewayEnsureError } from '@/lib/local-gateway-ensure-failure'
import { $connectionsRegistry } from '@/store/connection-registry-state'
import { isMissingConnectionError, isMissingProfileError } from '@/store/gateway-dial-failures'
import { liveSecondaryConnectionIds, openGatewayForAgent } from '@/store/gateway'
import { keepRoute, onKeptRouteOpened } from '@/store/gateway-kept-routes'
import { $primaryGatewayRoute, type PrimaryGatewayRoute } from '@/store/gateway-primary-route'

// Every registered gateway stays connected for as long as the window lives: its
// home socket is dialed at startup, kept against the idle pruner, and redialed
// when it drops. Picking a gateway or opening one of its sessions then costs no
// dial, and the unified Sessions list (Electron splices every pooled backend's
// rows) shows every gateway at once instead of only the one in front.
const HOME_PROFILE = 'default'
const REDIAL_INTERVAL_MS = 30_000

/** The window's primary socket already holds this gateway open; a second socket
 *  to the same backend would duplicate its event stream. */
function servedByPrimary(connection: DesktopRegistryConnection, primary: PrimaryGatewayRoute): boolean {
  if (primary.connectionId) {
    return primary.connectionId === connection.id
  }

  return connection.id === LOCAL_CONNECTION_ID && primary.mode !== 'remote'
}

/** The registry connections that need their own kept socket. */
export function persistentGatewayIds(
  registry: DesktopConnectionsRegistry | null,
  primary: PrimaryGatewayRoute
): string[] {
  return (registry?.connections ?? []).filter(connection => !servedByPrimary(connection, primary)).map(c => c.id)
}

/** Dialing This device where Hermes is not installed would start the installer
 *  unseen; only a confirmed click may do that. A missing probe fails closed. */
async function localInstalled(): Promise<boolean> {
  const probe = window.hermesDesktop?.probeLocalBackend

  return probe ? (await probe()).bootstrapNeeded !== true : false
}

async function dial(connectionId: string): Promise<void> {
  if (connectionId === LOCAL_CONNECTION_ID && !(await localInstalled())) {
    return
  }

  // A gateway that is down or needs sign-in fails this dial; the next tick
  // (every REDIAL_INTERVAL_MS) tries again.
  await openGatewayForAgent(connectionId, HOME_PROFILE)
}

/** Start keeping every registered gateway connected. Returns the teardown. */
export function startPersistentGateways(): () => void {
  const pins = new Map<string, () => void>()
  // A keeper tick must not re-arm a scope the reconnect ladder has parked as
  // permanently incompatible. Configuration edits or an explicit successful
  // reconnect can re-arm it; transient failures keep retrying.
  const parked = new Map<string, string>()
  const revisions = new Map<string, number>()
  const dialing = new Set<string>()
  let stopped = false

  const reconcile = () => {
    const registry = $connectionsRegistry.get()
    const wanted = new Set(persistentGatewayIds(registry, $primaryGatewayRoute.get()))
    const signatures = new Map((registry?.connections ?? []).map(entry => [entry.id, JSON.stringify(entry)]))

    for (const [connectionId, release] of pins) {
      if (!wanted.has(connectionId)) {
        pins.delete(connectionId)
        parked.delete(connectionId)
        release()
      }
    }

    const live = liveSecondaryConnectionIds()

    for (const connectionId of wanted) {
      if (!pins.has(connectionId)) {
        pins.set(connectionId, keepRoute(connectionId, HOME_PROFILE))
      }

      if (live.has(connectionId)) {
        parked.delete(connectionId)
        continue
      }

      const signature = signatures.get(connectionId)
      if (signature === undefined) {
        continue
      }

      if (parked.has(connectionId) && parked.get(connectionId) !== signature) {
        parked.delete(connectionId)
      }

      if (parked.has(connectionId) || dialing.has(connectionId)) {
        continue
      }

      const revision = revisions.get(connectionId) ?? 0
      dialing.add(connectionId)
      void dial(connectionId)
        .catch(error => {
          if (
            stopped ||
            !pins.has(connectionId) ||
            liveSecondaryConnectionIds().has(connectionId) ||
            (revisions.get(connectionId) ?? 0) !== revision
          ) {
            return
          }

          if (
            isPermanentLocalGatewayEnsureError(error) ||
            isMissingConnectionError(error) ||
            isMissingProfileError(error) ||
            isGatewayReauthRequired(error)
          ) {
            // A late failure from an edited connection cannot park its new route.
            const current = $connectionsRegistry.get()?.connections.find(entry => entry.id === connectionId)
            if (current && JSON.stringify(current) === signature) {
              parked.set(connectionId, signature)
            }
          }
        })
        .finally(() => dialing.delete(connectionId))
    }
  }

  // Explicit user reconnects may recover a parked route without changing the
  // registry entry; a later disconnect must resume normal automatic redial.
  const offOpened = onKeptRouteOpened(() => {
    for (const connectionId of liveSecondaryConnectionIds()) {
      parked.delete(connectionId)
    }
  })

  // Secret-only edits can retain the same renderer-visible registry fingerprint.
  const offChanged = window.hermesDesktop?.connections?.onChanged?.(({ connectionId, reason }) => {
    revisions.set(connectionId, (revisions.get(connectionId) ?? 0) + 1)
    if (reason !== 'removed') {
      parked.delete(connectionId)
    }
  })

  const offRegistry = $connectionsRegistry.subscribe(reconcile)
  const offPrimary = $primaryGatewayRoute.listen(reconcile)
  const timer = setInterval(reconcile, REDIAL_INTERVAL_MS)

  return () => {
    stopped = true
    clearInterval(timer)
    offRegistry()
    offPrimary()
    offOpened()
    offChanged?.()

    for (const release of pins.values()) {
      release()
    }

    pins.clear()
  }
}

let stopKeeping: (() => void) | null = null

/** The window-lifetime keeper: starts once, later calls are no-ops. */
export function keepGatewaysConnected(): void {
  stopKeeping ??= startPersistentGateways()
}

import.meta.hot?.dispose(() => {
  stopKeeping?.()
  stopKeeping = null
})
