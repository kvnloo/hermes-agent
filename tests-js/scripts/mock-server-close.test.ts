import http from 'node:http'

import { expect, test } from 'vitest'

import { startMockServer } from './mock-server'

test('closing the mock ends an in-flight held completion', async () => {
  const mock = await startMockServer({ holdFirstCompletionContaining: 'E2E_CLOSE_HELD' })
  const request = http.request(`${mock.url}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
  })

  // Closing open connections is the behavior under test; the client will be aborted.
  request.on('error', () => undefined)
  request.on('response', response => {
    response.on('error', () => undefined)
    response.resume()
  })
  request.end(JSON.stringify({
    model: 'mock-model',
    stream: true,
    messages: [{ role: 'user', content: 'E2E_CLOSE_HELD' }],
  }))

  let closePromise: Promise<void> | undefined
  let timeout: NodeJS.Timeout | undefined

  try {
    await mock.waitForHeldCompletion()
    closePromise = mock.close()
    const closed = await Promise.race([
      closePromise.then(() => true),
      new Promise<boolean>(resolve => {
        timeout = setTimeout(() => resolve(false), 2_500)
      }),
    ])

    expect(closed).toBe(true)
  } finally {
    if (timeout) {
      clearTimeout(timeout)
    }
    request.destroy()
    await (closePromise ?? mock.close())
  }
}, 10_000)
