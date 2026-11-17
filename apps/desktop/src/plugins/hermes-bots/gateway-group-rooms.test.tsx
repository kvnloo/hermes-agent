/**
 * The Bots roster lists gateway Group Chats by itself: no Refresh button and
 * no raw transport text. Rooms appear once the socket opens; a failed read
 * keeps the last good list; a window whose connection has no registry id (a
 * legacy remote) lists none instead of "Canonical groups require an explicit
 * connection"; a backend without gateway Group Chats lists none.
 *
 * Real SDK components and stores; only the gateway transport is mocked.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { act, cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { atom } from 'nanostores'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import { translateBotsIn } from './i18n-test-helper'

const { active, connection, gateway, profileRoutes, requestProfile } = vi.hoisted(() => ({
  active: { profile: null as unknown },
  connection: { id: null as unknown },
  gateway: { state: null as unknown },
  profileRoutes: vi.fn(),
  requestProfile: vi.fn()
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()
  const state = atom('connecting')
  const connectionId = atom<null | string>('local')
  const profile = atom('default')
  active.profile = profile
  gateway.state = state
  connection.id = connectionId

  return {
    ...sdk,
    host: { ...sdk.host, profileRoutes, requestProfile, state: { ...sdk.host.state, connectionId, gateway: state, profile } },
    usePluginI18n: () => translateBotsIn('en')
  }
})

import { $canonicalGroupBindings, forgetCanonicalGroup, refreshGatewayGroupRooms } from './canonical-group-registry'
import { renderGatewayRooms } from './gateway-group-rooms-test-harness'

const gatewayState = () => gateway.state as ReturnType<typeof atom<string>>
const profileState = () => active.profile as ReturnType<typeof atom<string>>
const connectionId = () => connection.id as ReturnType<typeof atom<null | string>>
const room = { room_id: 'room-1', name: 'Launch crew', members: [], updated_at: Date.now() / 1000 }

beforeEach(() => {
  profileRoutes.mockResolvedValue([])
  requestProfile.mockImplementation(async () => {
    if (gatewayState().get() !== 'open') {
      throw new Error('Hermes gateway is not connected')
    }

    return { rooms: [room], next_offset: null }
  })
})

afterEach(() => {
  cleanup()
  $canonicalGroupBindings.set({})
  vi.clearAllMocks()
  gatewayState().set('connecting')
  connectionId().set('local')
  profileState().set('default')
})

it('lists rooms once the socket opens, with no Refresh button and no error text', async () => {
  renderGatewayRooms()
  await act(async () => { await Promise.resolve() })
  expect(requestProfile).not.toHaveBeenCalled()

  await act(async () => { gatewayState().set('open') })

  expect(await screen.findByRole('button', { name: 'Launch crew' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: /refresh/i })).toBeNull()
  expect(screen.queryByRole('alert')).toBeNull()
})


it('lists a default-owned room from a named member view and opens its actual owner', async () => {
  profileRoutes.mockResolvedValue([
    { connectionId: 'local', mode: 'local', profile: 'default', targetProfile: 'default' },
    { connectionId: 'local', mode: 'local', profile: 'talent-advisor', targetProfile: 'talent-advisor' },
    { connectionId: 'other-machine', mode: 'remote', profile: 'default', targetProfile: 'default' }
  ])
  requestProfile.mockImplementation(async (route, method, params) => {
    expect(method).toBe('groups.list')
    expect(params.profile).toBe(route.profile)
    if (route.connectionId !== 'local') {throw new Error('read escaped the selected connection')}

    // The gateway launch profile owns the ledger; the seated member does not.
    return { rooms: route.profile === 'default' ? [room] : [], next_offset: null }
  })
  profileState().set('talent-advisor')
  gatewayState().set('open')
  const opened = vi.fn()

  renderGatewayRooms(opened)
  fireEvent.click(await screen.findByRole('button', { name: 'Launch crew' }))

  expect(requestProfile.mock.calls.map(([route]) => route.profile)).toEqual(['default', 'talent-advisor'])
  expect(screen.getAllByRole('button', { name: 'Launch crew' })).toHaveLength(1)
  expect(opened).toHaveBeenCalledWith('canonical:local:default:room-1', 'key')
  expect($canonicalGroupBindings.get()['canonical:local:default:room-1']).toMatchObject({
    connectionId: 'local', profile: 'default', roomId: 'room-1'
  })
})

it('keeps the last good list when a re-read fails', async () => {
  gatewayState().set('open')
  renderGatewayRooms()
  await screen.findByRole('button', { name: 'Launch crew' })

  requestProfile.mockRejectedValue(new Error('groups.list exploded'))
  await act(async () => { refreshGatewayGroupRooms() })
  await waitFor(() => expect(requestProfile.mock.calls.length).toBeGreaterThan(1))

  expect(screen.getByRole('button', { name: 'Launch crew' })).toBeTruthy()
  expect(screen.queryByText(/exploded/)).toBeNull()
})

it('lists nothing, and says nothing, on a connection with no registry id or no gateway Group Chats', async () => {
  gatewayState().set('open')
  connectionId().set(null)
  const view = renderGatewayRooms()
  await act(async () => { await Promise.resolve() })

  expect(requestProfile).not.toHaveBeenCalled()
  expect(view.container.textContent).toBe('')

  view.unmount()
  connectionId().set('local')
  requestProfile.mockRejectedValue(Object.assign(new Error('unknown method: groups.list'), { code: -32601 }))
  const older = renderGatewayRooms()
  await waitFor(() => expect(requestProfile).toHaveBeenCalled())
  expect(older.container.textContent).toBe('')
})

it('a disbanded room never comes back: not from a slow read, a failed re-read or a bind', async () => {
  gatewayState().set('open')
  renderGatewayRooms()
  await screen.findByRole('button', { name: 'Launch crew' })
  expect($canonicalGroupBindings.get()).toEqual({})

  // The gateway still answers with the room (a read issued before the disband), then fails.
  forgetCanonicalGroup({ connectionId: 'local', profile: 'default', roomId: 'room-1', roomName: 'Launch crew' })
  requestProfile.mockResolvedValueOnce({ rooms: [room], next_offset: null }).mockRejectedValue(new Error('offline'))
  await act(async () => { refreshGatewayGroupRooms() })

  await waitFor(() => expect(screen.queryByRole('button', { name: 'Launch crew' })).toBeNull())
  expect($canonicalGroupBindings.get()).toEqual({})
})
