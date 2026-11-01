import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { DesktopConnectionsRegistry } from '@/global'

const released: string[] = []
const keepRoute = vi.fn((connectionId: string, _profile: string) => () => released.push(connectionId))
const openGatewayForAgent = vi.fn(async (_connectionId: string, _profile: string) => undefined)
const live = new Set<string>()
const opened = new Set<() => void>()
const onKeptRouteOpened = vi.fn((handler: () => void) => {
  opened.add(handler)
  return () => { opened.delete(handler) }
})

vi.mock('@/store/gateway', () => ({
  liveSecondaryConnectionIds: () => new Set(live),
  openGatewayForAgent
}))
vi.mock('@/store/gateway-kept-routes', () => ({ keepRoute, onKeptRouteOpened }))

const { $connectionsRegistry } = await import('@/store/connection-registry-state')
const { $primaryGatewayRoute } = await import('@/store/gateway-primary-route')
const { startPersistentGateways } = await import('./gateway-persistence')

const registry = (ids: string[]): DesktopConnectionsRegistry => ({
  connections: ids.map(id => ({
    id,
    kind: id === 'local' ? 'local' : 'remote',
    label: id,
    tokenPreview: null,
    tokenSet: false
  })),
  primary: 'local',
  secureTokenStorage: true,
  version: 2
})

let stop: () => void = () => undefined

function installProbe(bootstrapNeeded: boolean): void {
  ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
    probeLocalBackend: vi.fn(async () => ({ bootstrapNeeded }))
  }
}

beforeEach(() => {
  vi.useFakeTimers()
  released.length = 0
  live.clear()
  opened.clear()
  keepRoute.mockClear()
  openGatewayForAgent.mockClear()
  $primaryGatewayRoute.set({ connectionId: 'local', mode: 'local' })
  $connectionsRegistry.set(registry(['local', 'homelab', 'vps']))
})

afterEach(() => {
  stop()
  vi.useRealTimers()
  delete (window as unknown as { hermesDesktop?: unknown }).hermesDesktop
})

it('keeps every registered gateway the primary socket does not serve connected, and lets a removed one go', async () => {
  stop = startPersistentGateways()

  expect(keepRoute.mock.calls).toEqual([
    ['homelab', 'default'],
    ['vps', 'default']
  ])
  expect(openGatewayForAgent.mock.calls).toEqual([
    ['homelab', 'default'],
    ['vps', 'default']
  ])

  // Settle the first dials before exercising the next tick's single-flight guard.
  await vi.advanceTimersByTimeAsync(0)
  // A dropped socket is redialed on the next tick; a live one is left alone.
  live.add('homelab')
  openGatewayForAgent.mockClear()
  await vi.advanceTimersByTimeAsync(30_000)
  expect(openGatewayForAgent.mock.calls).toEqual([['vps', 'default']])

  $connectionsRegistry.set(registry(['local', 'homelab']))
  expect(released).toEqual(['vps'])
  expect(keepRoute).toHaveBeenCalledTimes(2)
})

it('with a remote primary, keeps This device only where Hermes is installed (never starts the installer)', async () => {
  $primaryGatewayRoute.set({ connectionId: 'homelab', mode: 'remote' })
  installProbe(true)
  stop = startPersistentGateways()
  await vi.advanceTimersByTimeAsync(0)

  expect(openGatewayForAgent.mock.calls).toEqual([['vps', 'default']])

  stop()
  openGatewayForAgent.mockClear()
  installProbe(false)
  stop = startPersistentGateways()
  await vi.advanceTimersByTimeAsync(0)

  expect(openGatewayForAgent.mock.calls).toEqual([
    ['vps', 'default'],
    ['local', 'default']
  ])
})


it('parks a permanent runtime protocol refusal without stopping transient gateway recovery', async () => {
  $primaryGatewayRoute.set({ connectionId: 'homelab', mode: 'remote' })
  installProbe(false)
  openGatewayForAgent.mockImplementation(async connectionId => {
    if (connectionId === 'local') {
      throw new Error('Error invoking remote method: Gateway incompatible (runtime_protocol)')
    }
    throw new Error('ECONNREFUSED')
  })

  stop = startPersistentGateways()
  await vi.advanceTimersByTimeAsync(60_000)

  const attempts = (id: string) => openGatewayForAgent.mock.calls.filter(([connection]) => connection === id).length
  expect(attempts('local')).toBe(1)
  expect(attempts('vps')).toBe(3)
})

it('a material connection edit re-arms a parked keeper and a manual reconnect restores future auto-redial', async () => {
  $connectionsRegistry.set(registry(['local', 'homelab']))
  let incompatible = true
  openGatewayForAgent.mockImplementation(async () => {
    if (incompatible) {
      throw new Error('Gateway incompatible (runtime_protocol)')
    }
  })

  stop = startPersistentGateways()
  await vi.advanceTimersByTimeAsync(60_000)
  expect(openGatewayForAgent).toHaveBeenCalledTimes(1)

  incompatible = false
  const changed = registry(['local', 'homelab'])
  changed.connections = changed.connections.map(entry => entry.id === 'homelab' ? { ...entry, host: 'new-host' } : entry)
  $connectionsRegistry.set(changed)
  await vi.advanceTimersByTimeAsync(0)
  expect(openGatewayForAgent).toHaveBeenCalledTimes(2)

  // The user explicitly reconnects the kept scope outside the keeper.
  live.add('homelab')
  for (const handler of opened) handler()
  live.delete('homelab')
  await vi.advanceTimersByTimeAsync(30_000)
  expect(openGatewayForAgent).toHaveBeenCalledTimes(3)
})

it('a secret-only edit re-arms without a registry fingerprint change', async () => {
  $connectionsRegistry.set(registry(['local', 'homelab']))
  const changeHandlers = new Set<(event: { connectionId: string; reason: 'updated' }) => void>()
  ;(window as unknown as { hermesDesktop: unknown }).hermesDesktop = {
    connections: {
      onChanged: (handler: (event: { connectionId: string; reason: 'updated' }) => void) => {
        changeHandlers.add(handler)
        return () => { changeHandlers.delete(handler) }
      }
    }
  }
  openGatewayForAgent.mockRejectedValueOnce(new Error('Gateway incompatible (runtime_protocol)'))

  stop = startPersistentGateways()
  await vi.advanceTimersByTimeAsync(60_000)
  expect(openGatewayForAgent).toHaveBeenCalledTimes(1)

  for (const handler of changeHandlers) handler({ connectionId: 'homelab', reason: 'updated' })
  await vi.advanceTimersByTimeAsync(30_000)
  expect(openGatewayForAgent).toHaveBeenCalledTimes(2)
})

it('does not stack keeper dials while one gateway resolution remains pending', async () => {
  $connectionsRegistry.set(registry(['local', 'homelab']))
  let finish!: () => void
  const pending = new Promise<void>(resolve => { finish = resolve })
  openGatewayForAgent.mockImplementation(() => pending)

  stop = startPersistentGateways()
  await vi.advanceTimersByTimeAsync(90_000)
  expect(openGatewayForAgent).toHaveBeenCalledTimes(1)
  finish()
  await vi.advanceTimersByTimeAsync(0)
})
