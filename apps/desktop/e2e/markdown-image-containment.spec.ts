import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { MOCK_REPLY } from '../../../tests-js/scripts/mock-server'

import { setupMockBackend, waitForAppReady } from './fixtures'
import { expect, test } from './test'

const TRIGGER = 'E2E_COLD_SQUARE_MEDIA_148946'
const AFTER_IMAGE = 'Text immediately after the square image.'

test('a cold square MEDIA image stays inside its reserved transcript frame', async () => {
  test.setTimeout(180_000)
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'hermes-image-frame-'))
  const imagePath = path.join(directory, 'square.svg')
  fs.writeFileSync(
    imagePath,
    '<svg xmlns="http://www.w3.org/2000/svg" width="1536" height="1536">' +
      '<rect width="1536" height="1536" fill="navy"/></svg>'
  )

  let fixture: Awaited<ReturnType<typeof setupMockBackend>> | null = null

  try {
    fixture = await setupMockBackend({
      mockServer: {
        replyForPrompt: prompt =>
          prompt.includes(TRIGGER) ? `MEDIA:${imagePath}\n\n${AFTER_IMAGE}` : MOCK_REPLY
      }
    })
    await waitForAppReady(fixture, 120_000)

    const page = fixture.page
    const composer = page.locator('[contenteditable="true"]').first()
    await composer.fill(TRIGGER)
    await composer.press('Enter')

    const following = page.getByText(AFTER_IMAGE, { exact: true })
    await expect(following).toBeVisible()

    const img = page.locator('[data-slot="aui_markdown-image"] img').first()
    await expect.poll(() => img.evaluate(node => (node as HTMLImageElement).naturalWidth)).toBe(1536)

    // Real Chromium geometry: jsdom's style tests cannot resolve percentage
    // heights through the aspect-ratio frame. The cold frame stays 4:3 even
    // after a square image decodes; no painted image may escape it.
    const geometry = await img.evaluate(node => {
      const frame = node.closest('[data-slot="aui_markdown-image"]') as HTMLElement
      const imageRect = node.getBoundingClientRect()
      const frameRect = frame.getBoundingClientRect()

      return {
        ratio: frameRect.width / frameRect.height,
        imageBottom: imageRect.bottom,
        frameBottom: frameRect.bottom
      }
    })
    const followingBox = await following.boundingBox()

    expect(geometry.ratio).toBeCloseTo(4 / 3, 2)
    expect(geometry.imageBottom).toBeLessThanOrEqual(geometry.frameBottom + 1)
    expect(geometry.imageBottom).toBeLessThanOrEqual(followingBox!.y + 1)
  } finally {
    await fixture?.cleanup()
    fs.rmSync(directory, { recursive: true, force: true })
  }
})
