import { beforeEach, describe, expect, it, vi } from 'vitest'

const { stored } = vi.hoisted(() => ({ stored: new Map<string, unknown>() }))

vi.mock('@hermes/plugin-sdk', async () => ({ atom: (await import('nanostores')).atom }))
vi.mock('./shared', () => ({
  getPluginCtx: () => ({
    storage: {
      set: (key: string, value: unknown) => {
        stored.set(key, value)
        return Promise.resolve()
      }
    }
  })
}))

async function reload() {
  vi.resetModules()
  return import('./roster-collapse')
}

beforeEach(() => stored.clear())

describe('Bot roster disclosure preference', () => {
  it('retains independent collapsed sections across pane remounts and reloads', async () => {
    const original = await reload()
    original.toggleCollapsedRosterSection('gateway:work')
    original.toggleCollapsedRosterSection('group-chats')
    expect(original.$collapsedRosterSections.get()).toEqual(['gateway:work', 'group-chats'])
    expect(stored.get(original.COLLAPSED_ROSTER_SECTIONS_KEY)).toEqual(['gateway:work', 'group-chats'])

    // A pane remount reads the same module atom; a full reload hydrates from storage.
    const restored = await reload()
    restored.hydrateCollapsedRosterSections(
      stored.get(restored.COLLAPSED_ROSTER_SECTIONS_KEY),
      restored.rosterCollapseRevision()
    )
    expect(restored.$collapsedRosterSections.get()).toEqual(['gateway:work', 'group-chats'])

    restored.toggleCollapsedRosterSection('gateway:work')
    expect(stored.get(restored.COLLAPSED_ROSTER_SECTIONS_KEY)).toEqual(['group-chats'])
  })

  it('does not replace a click with a late boot-time storage result', async () => {
    const state = await reload()
    const readRevision = state.rosterCollapseRevision()
    state.toggleCollapsedRosterSection('gateway:new')
    state.hydrateCollapsedRosterSections(['group-chats'], readRevision)
    expect(state.$collapsedRosterSections.get()).toEqual(['gateway:new'])
  })
})
