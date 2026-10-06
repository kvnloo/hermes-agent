import { homedir } from 'node:os'
import { join } from 'node:path'
import { readFileSync } from 'node:fs'

export const TERN_USAGE_ID = 'hermes:usage'

export type UsageModelSpeed = {
  id: string
  tok_s: number | null
  ttft_ms?: number | null
  source: 'receipt' | 'derived' | 'missing'
}

export type UsageNetworkSnapshot = {
  savings: {
    solPi: number
    rlm: number
    z0intOffload: number
  }
  models: UsageModelSpeed[]
}

export function emptyUsage(): UsageNetworkSnapshot {
  return {
    savings: { solPi: 0, rlm: 0, z0intOffload: 0 },
    models: []
  }
}

const asCount = (value: unknown): number =>
  typeof value === 'number' && Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0

export function normalizeUsageSnapshot(raw: unknown): UsageNetworkSnapshot {
  if (!raw || typeof raw !== 'object') {
    return emptyUsage()
  }

  const row = raw as Record<string, unknown>
  const savings = (row.savings && typeof row.savings === 'object' ? row.savings : {}) as Record<
    string,
    unknown
  >
  const models = Array.isArray(row.models) ? row.models : []

  return {
    savings: {
      solPi: asCount(savings.solPi ?? savings.sol_pi),
      rlm: asCount(savings.rlm),
      z0intOffload: asCount(savings.z0intOffload ?? savings.z0int_offload)
    },
    models: models
      .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
      .map(item => ({
        id: typeof item.id === 'string' && item.id ? item.id : 'unknown',
        tok_s: typeof item.tok_s === 'number' && Number.isFinite(item.tok_s) ? item.tok_s : null,
        ttft_ms: typeof item.ttft_ms === 'number' && Number.isFinite(item.ttft_ms) ? item.ttft_ms : null,
        source: item.source === 'receipt' || item.source === 'derived' ? item.source : 'missing'
      }))
  }
}

export function loadUsageSnapshot(home = process.env.Z0INT_HOME || join(homedir(), '.z0int')): UsageNetworkSnapshot {
  try {
    return normalizeUsageSnapshot(
      JSON.parse(readFileSync(join(home, 'runtime', 'usage-surface.json'), 'utf8'))
    )
  } catch {
    return emptyUsage()
  }
}

const tokSLine = (model: UsageModelSpeed): string =>
  model.tok_s === null ? `${model.id} — tok/s` : `${model.id} ${Math.round(model.tok_s)} tok/s`

export function formatUsageSurfaceText(snapshot: UsageNetworkSnapshot): string[] {
  return [
    '/usage',
    `SoL-Pi ${snapshot.savings.solPi} tok saved`,
    `RLM ${snapshot.savings.rlm} tok saved`,
    `z0int ${snapshot.savings.z0intOffload} tok saved`,
    ...snapshot.models.map(tokSLine)
  ]
}

export function usageSurfaceNodes(snapshot: UsageNetworkSnapshot): Array<{
  id: string
  k: string
  c: Array<{ id: string; k: string; p: { text: string } }>
}> {
  return [
    {
      id: TERN_USAGE_ID,
      k: 'col',
      c: formatUsageSurfaceText(snapshot).map((text, index) => ({
        id: `${TERN_USAGE_ID}:${index}`,
        k: 'text',
        p: { text }
      }))
    }
  ]
}
