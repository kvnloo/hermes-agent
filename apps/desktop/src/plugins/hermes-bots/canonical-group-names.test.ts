import { beforeEach, expect, it, vi } from 'vitest'

const requestProfile = vi.hoisted(() => vi.fn())
vi.mock('@hermes/plugin-sdk', async () => ({
  host: { requestProfile },
  profileVisibleName: (await import('@hermes/shared')).profileVisibleName
}))

import { projectCanonicalGroupNames } from './canonical-group-names'
import type { CanonicalRoom } from './canonical-groups'

const route = { connectionId: 'source-a', profile: 'team-owner' }

const room: CanonicalRoom = {
  room_id: 'room', name: 'Team', members: [
    { member_id: 'seat', profile: 'worker', handle: 'frozen-worker', display_name: 'Stored primary name', target: { kind: 'local', profile: 'worker' } },
    { member_id: 'old-seat', profile: 'legacy', handle: 'frozen-legacy' },
    { member_id: 'peer-seat', profile: 'worker', handle: 'frozen-peer', display_name: 'Peer primary name', target: { kind: 'peer', peer_id: 'peer', profile: 'worker' } }
  ]
}

beforeEach(() => { requestProfile.mockReset() })

it.each([undefined, '', 'worker', ' worker '])('does not replace stored names and frozen handles with metadata-free profile IDs (%s)', async display_name => {
  requestProfile.mockResolvedValue({ profiles: [{ name: 'worker', display_name }, { name: 'legacy', title: ' ', display_name: '' }] })
  const result = await projectCanonicalGroupNames(route, room)
  expect(result).toEqual(room)
  expect(result.members[0].current_display_name).toBeUndefined()
})

it('changes only presentation fields on the local target and never mutates stored identities or peer targets', async () => {
  requestProfile.mockResolvedValue({ profiles: [
    { name: 'worker', ui_meta: { 'hermes-bots': { title: 'Current Bot title' } }, display_name: 'Core name' },
    { name: 'legacy', ui_meta: { 'hermes-bots': { title: 'Current legacy name' } } }
  ] })
  const before = structuredClone(room)
  const result = await projectCanonicalGroupNames(route, room)
  expect(result.members).toEqual([
    { ...room.members[0], display_name: 'Current Bot title', current_display_name: 'Current Bot title' },
    { ...room.members[1], display_name: 'Current legacy name', current_display_name: 'Current legacy name' },
    room.members[2]
  ])
  expect(result.members[0].target).toBe(room.members[0].target)
  expect(result.members[2]).toBe(room.members[2])
  expect(room).toEqual(before)
  expect(requestProfile).toHaveBeenCalledExactlyOnceWith({ ...route, targetProfile: route.profile, mode: 'remote' }, 'profiles.list', { profile: route.profile, include_sessions: false })
})

it.each(['missing method', 'disconnected'])('keeps stored presentation usable when profiles.list fails (%s)', async message => {
  requestProfile.mockRejectedValue(new Error(message))
  expect(await projectCanonicalGroupNames(route, room)).toEqual(room)
  expect(requestProfile).toHaveBeenCalledTimes(1)
})

it('does not read local profiles for a peer-only roster, including unknown future target kinds', async () => {
  for (const kind of ['peer', 'future-kind']) {
    const peerRoom = { ...room, members: [{ ...room.members[2], target: { kind, profile: 'worker' } }] }
    expect(await projectCanonicalGroupNames(route, peerRoom)).toBe(peerRoom)
  }

  expect(requestProfile).not.toHaveBeenCalled()
})

it('keeps legacy members distinct when their current visible names collide', async () => {
  const legacyRoom: CanonicalRoom = {
    room_id: 'legacy-collision', name: 'Team', members: [
      { member_id: 'seat-a', profile: 'alpha', handle: 'alpha-handle', display_name: 'Stored A', target: { kind: 'local', profile: 'alpha' } },
      { member_id: 'seat-b', profile: 'beta', handle: 'beta-handle', display_name: 'Stored B', target: { kind: 'local', profile: 'beta' } }
    ]
  }
  requestProfile.mockResolvedValue({ profiles: [
    { name: 'alpha', display_name: '同名' },
    { name: 'beta', ui_meta: { 'hermes-bots': { title: '同名' } }, display_name: 'Other' }
  ] })
  const stored = structuredClone(legacyRoom)
  const projected = await projectCanonicalGroupNames(route, legacyRoom)

  expect(projected.members).toEqual(
    legacyRoom.members.map(member => ({ ...member, display_name: '同名', current_display_name: '同名' }))
  )
  expect(projected.members[0].target).toBe(legacyRoom.members[0].target)
  expect(projected.members[1].target).toBe(legacyRoom.members[1].target)
  expect(legacyRoom).toEqual(stored)
  expect(requestProfile).toHaveBeenCalledExactlyOnceWith(
    { ...route, targetProfile: route.profile, mode: 'remote' },
    'profiles.list', { profile: route.profile, include_sessions: false }
  )
})
