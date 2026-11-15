import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { McpTestResult } from '@/hermes'
import { probeCache } from '@/lib/mcp-probe-cache'
import type { McpServers } from '@/lib/mcp-servers'

import { useMcpProbes, type UseMcpProbesOptions } from './use-mcp-probes'

const mocks = vi.hoisted(() => ({ testMcpServer: vi.fn(), getUsageAnalytics: vi.fn() }))
vi.mock('@/hermes', () => mocks)

const ok: McpTestResult = { ok: true, tools: [] }

const options = (servers: McpServers, epoch = { current: 0 }): UseMcpProbesOptions => ({
  servers,
  appProfile: null,
  scopeProfileKey: 'default',
  profileEpoch: epoch
})

beforeEach(() => {
  probeCache.clear()
  mocks.testMcpServer.mockReset()
  mocks.getUsageAnalytics.mockReset().mockResolvedValue({ tools: [] })
})

afterEach(() => {
  cleanup()
  probeCache.clear()
})

it('caps automatic requests across mounts, coalesces duplicates, and frees slots on failure', async () => {
  const requests: Array<{ resolve: (value: McpTestResult) => void; reject: (error: Error) => void }> = []
  mocks.testMcpServer.mockImplementation(
    () => new Promise<McpTestResult>((resolve, reject) => requests.push({ resolve, reject }))
  )

  const all = Object.fromEntries(
    Array.from({ length: 7 }, (_, i) => [`s${i}`, { url: `https://example.com/s${i}` }])
  )
  const first = renderHook(() => useMcpProbes(options(Object.fromEntries(Object.entries(all).slice(0, 5)))))
  const second = renderHook(() => useMcpProbes(options({ s0: all.s0, s5: all.s5, s6: all.s6 })))
  await act(async () => {})

  expect(mocks.testMcpServer).toHaveBeenCalledTimes(4)
  await act(async () => requests[0].resolve(ok))
  expect(mocks.testMcpServer).toHaveBeenCalledTimes(5)
  await act(async () => requests[1].reject(new Error('offline')))
  expect(mocks.testMcpServer).toHaveBeenCalledTimes(6)

  for (let i = 2; i < 7; i++) {
    await act(async () => requests[i].resolve(ok))
  }

  expect(mocks.testMcpServer).toHaveBeenCalledTimes(7)
  expect(first.result.current.probes.s1).toEqual({ ok: false, error: 'offline', tools: [] })
  expect(first.result.current.probes.s0).toEqual(ok)
  expect(second.result.current.probes.s0).toEqual(ok)
  expect(second.result.current.probes.s6).toEqual(ok)
})

it('retires queued work when its profile epoch changes', async () => {
  const resolvers: Array<(value: McpTestResult) => void> = []
  mocks.testMcpServer.mockImplementation(
    () => new Promise<McpTestResult>(resolve => resolvers.push(resolve))
  )
  const epoch = { current: 0 }
  const servers = Object.fromEntries(
    Array.from({ length: 7 }, (_, i) => [`retired${i}`, { command: 'node' }])
  )
  const { result } = renderHook(() => useMcpProbes(options(servers, epoch)))
  await act(async () => {})
  expect(mocks.testMcpServer).toHaveBeenCalledTimes(4)

  act(() => {
    epoch.current += 1
    result.current.resetForProfileSwitch()
  })
  await act(async () => resolvers.forEach(resolve => resolve(ok)))

  expect(mocks.testMcpServer).toHaveBeenCalledTimes(4)
  expect(result.current.probes).toEqual({})
})
