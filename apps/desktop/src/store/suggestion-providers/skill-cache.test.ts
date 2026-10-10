import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SkillInfo } from '@/types/hermes'

// Capture the draft provider callback so we can drive loadIndex() through the
// real code path. getSkills is overridden to control the skill catalog and count
// fetches; every other dependency (stores, the profile subscription) stays real
// so the subscription under test runs against the genuine $activeGatewayProfile.
vi.mock(import('@/hermes'), async importOriginal => {
  const actual = await importOriginal()

  return { ...actual, getSkills: vi.fn() }
})

vi.mock(import('@/store/composer-suggestions'), () => ({
  registerDraftProvider: vi.fn()
}))

const { getSkills } = await import('@/hermes')
const composer = await import('@/store/composer-suggestions')
const { $activeGatewayProfile } = await import('@/store/profile')
const { invalidateSkillSuggestionIndex } = await import('./skill')

const skill = (name: string): SkillInfo => ({ category: 'test', description: '', enabled: true, name })

/** Invoke the skill draft provider skill.ts registered, so loadIndex() is
 *  exercised. A draft that names a skill makes the provider call loadIndex();
 *  we observe cache hits/misses through the getSkills call count. */
async function sample(text: string): Promise<unknown[]> {
  const calls = vi.mocked(composer.registerDraftProvider).mock.calls

  const provider = calls.at(-1)?.[1] as
    ((ctx: { sessionId: string | null; text: string }) => Promise<unknown[]>) | undefined

  if (!provider) {
    throw new Error('skill draft provider was not registered')
  }

  return provider({ sessionId: null, text })
}

describe('skill suggestion index — cache + profile invalidation', () => {
  beforeEach(() => {
    vi.mocked(getSkills).mockReset()
    $activeGatewayProfile.set('default')
    invalidateSkillSuggestionIndex()
  })

  afterEach(() => {
    vi.mocked(getSkills).mockReset()
    $activeGatewayProfile.set('default')
    invalidateSkillSuggestionIndex()
  })

  it('populates the cache on the first sample and reuses it within the TTL', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    // Within the TTL the cache is served — no second fetch.
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)
  })

  it('invalidateSkillSuggestionIndex() forces a refetch on the next sample', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    invalidateSkillSuggestionIndex()

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(2)
  })

  it('drops the cache when $activeGatewayProfile changes to a different key', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    // A live profile swap publishes a different normalized key — the cache
    // must drop so the next sample fetches against the new backend.
    $activeGatewayProfile.set('work')
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(2)
  })

  it('does NOT refetch when the profile key is unchanged', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    // nanostores short-circuits a no-change set; even if it fired, the
    // normalized key equality would skip invalidation.
    $activeGatewayProfile.set('default')
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)
  })

  it('normalizes the profile key: empty and "default" are the same key', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    // normalizeProfileKey('') → 'default', so this is NOT a key change — the
    // cache survives. This is the shared-profile-key boundary the connection
    // switch path (wipeSessionListsForGatewaySwitch) must cover instead.
    $activeGatewayProfile.set('')
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)
  })

  it('normalizes whitespace: "  default  " and "default" are the same key', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    $activeGatewayProfile.set('  default  ')
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)
  })

  it('the initial subscription fire does not invalidate (cachedProfile starts null)', async () => {
    // The module-load subscription fires immediately with 'default'. Since
    // cachedProfile is null at first fire, no invalidation happens — a fresh
    // cache simply populates on first sample rather than churning. (This test
    // asserts the post-load state: a single sample fetches exactly once.)
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)
  })

  it('serves the new backend skills after a profile swap, not the old ones', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    // The new backend has a different skill set.
    vi.mocked(getSkills).mockResolvedValue([skill('code-review')])

    $activeGatewayProfile.set('staging')

    // After invalidation, the new skill catalog loads — a stale cache would
    // still serve 'pr-ready' and never call getSkills again.
    await sample('make this code review please')
    expect(getSkills).toHaveBeenCalledTimes(2)
  })

  it('a round-trip back to the original profile key re-invalidates each leg', async () => {
    vi.mocked(getSkills).mockResolvedValue([skill('pr-ready')])

    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(1)

    $activeGatewayProfile.set('work')
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(2)

    // Switching back to 'default' is yet another key change — the cache
    // populated under 'work' must not survive the return.
    $activeGatewayProfile.set('default')
    await sample('make this pr ready please')
    expect(getSkills).toHaveBeenCalledTimes(3)
  })
})
