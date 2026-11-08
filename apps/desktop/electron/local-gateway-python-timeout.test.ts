import type * as ChildProcessAPI from 'node:child_process'
import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'

import { afterEach, expect, test, vi } from 'vitest'

import { isStaleLocalGatewayError } from './local-gateway'
import { closeGatewayTicketBridges, mintGatewayTicketWithPython } from './local-gateway-python'

// Regression for NousResearch/hermes-agent#151351. Exercise the real bridge
// protocol and its timers with a controlled helper stream, without faking the OS.
const helper = vi.hoisted(() => ({
  spawns: 0,
  kills: 0,
  requests: [] as string[],
  stdout: null as PassThrough | null
}))

vi.mock('node:child_process', async importOriginal => {
  const actual = await importOriginal<typeof ChildProcessAPI>()

  return { ...actual, spawn: () => {
    const stdin = new PassThrough()
    const stdout = new PassThrough()
    const stderr = new PassThrough()
    stdin.on('data', chunk => helper.requests.push(String(chunk)))
    helper.stdout = stdout
    helper.spawns++

    return Object.assign(new EventEmitter(), {
      stdin, stdout, stderr,
      kill: () => { helper.kills++; return true }
    })
  } }
})

afterEach(() => {
  closeGatewayTicketBridges()
  vi.useRealTimers()
  helper.stdout?.destroy()
  helper.stdout = null
  helper.spawns = 0
  helper.kills = 0
  helper.requests.length = 0
})

test('a slow ticket cannot kill another pending ticket or trigger a stale-owner re-ensure', async () => {
  vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
  const endpoint = { profile_id: '/ticket-fixture', instance_id: 'owner', runtime_protocol: 1 }
  const backend = { command: 'python-fixture' }
  const first = mintGatewayTicketWithPython(backend, '/fixture', endpoint, 'native-http')
    .then(() => { throw new Error('expected timeout') }, error => error as Error)

  await vi.advanceTimersByTimeAsync(9_000)
  const second = mintGatewayTicketWithPython(backend, '/fixture', endpoint, 'native-http')
  expect(helper.spawns).toBe(1)
  expect(helper.requests).toHaveLength(2)

  await vi.advanceTimersByTimeAsync(1_000)
  const failure = await first
  expect(failure.message).toBe('Hermes ticket helper request timed out')
  expect(isStaleLocalGatewayError(failure)).toBe(false)
  expect(helper.kills).toBe(0)

  const ids = helper.requests.map(line => JSON.parse(line).id as number)
  helper.stdout!.write(JSON.stringify({ id: ids[0], ticket: 'late' }) + '\n')
  helper.stdout!.write(JSON.stringify({ id: ids[1], ticket: 'healthy' }) + '\n')

  await expect(second).resolves.toBe('healthy')
  expect(helper.kills).toBe(0)
})
