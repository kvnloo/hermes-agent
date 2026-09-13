/**
 * E2E test for the adoptedRunningTurn hydrate-leak fix (#T1e).
 *
 * Verify end-to-end (real Electron + real mock backend) that a locally-streamed
 * turn does NOT trigger an extra `getLatestSessionMessages` REST fetch at
 * turn-end. The bug's symptom was a redundant `/api/sessions/{id}/messages`
 * round-trip after a locally-streamed turn when `adoptedRunningTurn` was stale
 * true (leaked from a prior adopt→cancel). With the fix, the flag is cleared
 * at every turn boundary so the post-turn hydrate short-circuits.
 *
 * For a normal locally-streamed turn (the desktop created the session and
 * started the turn itself), `adoptedRunningTurn` is already false, so the
 * assertion here is the baseline: no extra /messages REST call fires between
 * submit and (a settling window after) the turn's reply.
 */

import { type MockBackendFixture, setupMockBackend, waitForAppReady } from './fixtures'
import { expect, test } from './test'

let fixture: MockBackendFixture | null = null

test.beforeAll(async () => {
  fixture = await setupMockBackend()
  await waitForAppReady(fixture!, 120_000)
})

test.afterAll(async () => {
  await fixture?.cleanup()
  fixture = null
})

test.describe('adoptedRunningTurn post-turn hydrate gate (T1e)', () => {
  test('a locally-streamed turn does NOT fire an extra getLatestSessionMessages REST fetch at turn-end', async () => {
    const page = fixture!.page

    // Tally `getLatestSessionMessages` REST calls (the hydrate endpoint).
    // The `getLatestSessionMessages` REST endpoint is
    // GET /api/sessions/{id}/messages?... captured here as the request URL
    // substring. We want to count only the calls that fire AFTER submit —
    // normal activation already made some before this test ran.
    let transcriptFetchCount = 0

    const onRequest = (request: { url: () => string; method: () => string }) => {
      const url = request.url()

      if (
        request.method() === 'GET' &&
        // Matches the getLatestSessionMessages / getSessionMessages REST shape.
        url.includes('/api/sessions/') &&
        url.includes('/messages')
      ) {
        transcriptFetchCount += 1
      }
    }

    page.on('request', onRequest)

    try {
      // Find the composer.
      const composer = page.locator('[contenteditable="true"]').first()
      await composer.waitFor({ state: 'visible', timeout: 10_000 })
      await composer.click()
      await composer.type('locally-streamed prompt for hydrate gate', { delay: 20 })
      await page.keyboard.press('Enter')

      // Wait for the mock canned reply to appear — the turn has completed.
      await page.waitForFunction(
        () => (document.body ?? {}).textContent?.includes('mock inference server'),
        undefined,
        { timeout: 60_000 }
      )

      // The bug's hydrateFromStoredSession fires synchronously inside
      // completeAssistantMessage (right after message.complete). The 300ms
      // sidebar-refresh coalesce + 250ms retry backoff bound any deferred
      // follow-ups. Wait generously past that so the assertion sees every
      // post-turn REST fetch that would have been triggered.
      await new Promise(resolve => setTimeout(resolve, 1500))
    } finally {
      page.off('request', onRequest)
    }

    // The hydrate endpoint must NOT have been called as part of completing a
    // turn this window streamed itself. A locally-streamed turn owns its full
    // reply in the in-memory transcript — there is nothing to repair from
    // stored history, so no /api/sessions/{id}/messages fetch should fire
    // between the prompt submit and post-turn settle.
    expect(transcriptFetchCount).toBe(0)
  })
})
