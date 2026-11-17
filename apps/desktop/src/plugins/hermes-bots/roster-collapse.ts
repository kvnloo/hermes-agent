import { atom } from '@hermes/plugin-sdk'

import { getPluginCtx } from './shared'

// Disclosures are local to this Desktop, never a bot or gateway configuration.
export const COLLAPSED_ROSTER_SECTIONS_KEY = 'collapsed-roster-sections-v1'
export const $collapsedRosterSections = atom<string[]>([])
let mutationRevision = 0

export function rosterCollapseRevision(): number {
  return mutationRevision
}

export function hydrateCollapsedRosterSections(value: unknown, readRevision: number): void {
  // An in-flight storage read must not undo a more recent user click.
  if (mutationRevision !== readRevision || !Array.isArray(value)) return

  const ids = value.filter((id): id is string => typeof id === 'string' && Boolean(id.trim())).map(id => id.trim())
  $collapsedRosterSections.set([...new Set(ids)].sort())
}

export function toggleCollapsedRosterSection(id: string): void {
  const key = id.trim()
  if (!key) return

  const next = new Set($collapsedRosterSections.get())
  if (next.has(key)) next.delete(key)
  else next.add(key)

  const ids = [...next].sort()
  mutationRevision++
  $collapsedRosterSections.set(ids)

  try {
    Promise.resolve(getPluginCtx()?.storage?.set?.(COLLAPSED_ROSTER_SECTIONS_KEY, ids)).catch(() => undefined)
  } catch {
    /* storage unavailable — current-window state still works */
  }
}
