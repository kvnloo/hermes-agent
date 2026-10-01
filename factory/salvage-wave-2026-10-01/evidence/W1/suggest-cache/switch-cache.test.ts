import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { McpCatalogEntry, SkillInfo } from '@/types/hermes'

// Behaviour contract: the composer's skill + MCP suggestion providers keep a
// 5-minute module cache of profile-scoped REST reads. A switch to another
// backend (profile switch, or a connection switch that keeps the same profile
// key) must not keep answering with the previous backend's data.
//
// Only the REST reads and the provider registry are mocked; the providers,
// profile store and gateway-switch wipe run for real.
vi.mock(import('@/hermes'), async importOriginal => {
  const actual = await importOriginal()

  return { ...actual, getMcpCatalog: vi.fn(), getSkills: vi.fn(), listMcpServers: vi.fn() }
})

vi.mock(import('@/store/composer-suggestions'), async importOriginal => {
  const actual = await importOriginal()

  return { ...actual, registerDraftProvider: vi.fn() }
})

vi.mock(import('@/lib/query-client'), async importOriginal => {
  const actual = await importOriginal()

  return { ...actual, invalidateProfileScopedQueries: vi.fn() }
})

// Providers load first (as when the composer registers them), then the stores
// that drive a switch.
const { getMcpCatalog, getSkills, listMcpServers } = await import('@/hermes')
const composer = await import('@/store/composer-suggestions')
const { invalidateSkillSuggestionIndex } = await import('./skill')
const { invalidateMcpSuggestionIndex } = await import('./mcp')
const { $activeGatewayProfile } = await import('@/store/profile')
const { wipeSessionListsForGatewaySwitch } = await import('@/store/gateway-switch')

type Provider = (ctx: { sessionId: string | null; text: string }) => Promise<{ id: string }[]>

function provider(name: string): Provider {
  const call = vi.mocked(composer.registerDraftProvider).mock.calls.findLast(([id]) => id === name)

  if (!call) {
    throw new Error(`${name} draft provider was not registered`)
  }

  return call[1] as unknown as Provider
}

const skillIds = async (text: string) => (await provider('skill')({ sessionId: null, text })).map(s => s.id)
const mcpIds = async (text: string) => (await provider('mcp')({ sessionId: null, text })).map(s => s.id)

const skill = (name: string): SkillInfo => ({ category: 'test', description: '', enabled: true, name })

const LINEAR = {
  auth_type: 'oauth',
  name: 'linear',
  suggest: { hosts: [], keywords: ['linear'] },
  transport: 'http',
  url: 'https://mcp.linear.app/mcp'
} as unknown as McpCatalogEntry

const SKILL_DRAFT = 'make this pr ready please'
const MCP_DRAFT = 'check the linear board please'

// Backend A: has the pr-ready skill, linear NOT configured (pill offered).
// Backend B: no pr-ready skill, linear already configured (no pill).
function serveBackendA() {
  vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])
  vi.mocked(listMcpServers).mockResolvedValue({ servers: [] } as never)
}

function serveBackendB() {
  vi.mocked(getSkills).mockResolvedValue([skill('code-review')])
  vi.mocked(listMcpServers).mockResolvedValue({ servers: [{ name: 'linear' }] } as never)
}

beforeEach(() => {
  vi.mocked(getMcpCatalog).mockResolvedValue({ entries: [LINEAR] } as never)
  $activeGatewayProfile.set('default')
  invalidateSkillSuggestionIndex()
  invalidateMcpSuggestionIndex()
  serveBackendA()
})

afterEach(() => {
  $activeGatewayProfile.set('default')
  invalidateSkillSuggestionIndex()
  invalidateMcpSuggestionIndex()
  vi.mocked(getSkills).mockReset()
  vi.mocked(listMcpServers).mockReset()
  vi.mocked(getMcpCatalog).mockReset()
})

describe('suggestion caches on profile switch', () => {
  it('does not offer the previous profile skill or MCP pills after switching profiles', async () => {
    expect(await skillIds(SKILL_DRAFT)).toEqual(['pr-ready'])
    expect(await mcpIds(MCP_DRAFT)).toEqual(['linear'])

    serveBackendB()
    $activeGatewayProfile.set('work')

    // Stale cache would still answer with backend A: "Use skill pr-ready" for a
    // skill B lacks, and "Add Linear" for a server B already has configured.
    expect.soft(await skillIds(SKILL_DRAFT)).toEqual([])
    expect.soft(await mcpIds(MCP_DRAFT)).toEqual([])
  })

  it('keeps the caches when the profile is re-set to the same key', async () => {
    await skillIds(SKILL_DRAFT)
    await mcpIds(MCP_DRAFT)

    $activeGatewayProfile.set('default')
    await skillIds(SKILL_DRAFT)
    await mcpIds(MCP_DRAFT)

    expect(getSkills).toHaveBeenCalledTimes(1)
    expect(listMcpServers).toHaveBeenCalledTimes(1)
  })
})

describe('suggestion caches on connection switch with an unchanged profile key', () => {
  it('does not offer the previous connection skill or MCP pills', async () => {
    expect(await skillIds(SKILL_DRAFT)).toEqual(['pr-ready'])
    expect(await mcpIds(MCP_DRAFT)).toEqual(['linear'])

    // Both connections expose "default": no $activeGatewayProfile change, only
    // the shared connection-switch wipe runs.
    serveBackendB()
    wipeSessionListsForGatewaySwitch()

    expect.soft(await skillIds(SKILL_DRAFT)).toEqual([])
    expect.soft(await mcpIds(MCP_DRAFT)).toEqual([])
  })
})
