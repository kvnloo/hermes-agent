import { describe, expect, it, vi } from 'vitest'

import type { ComposerToken } from '../app/interfaces.js'
import { submitPrompt, type SubmitPromptDeps } from '../app/submissionCore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { prepareSubmission } from '../app/useSubmission.js'
import { expandTokens } from '../domain/attachments.js'
import type { GatewayClient } from '../gatewayClient.js'
import { queueItem } from '../hooks/useQueue.js'
import { hasInterpolation } from '../protocol/interpolation.js'

describe('busy/no-session queue stores the expanded paste, not the collapsed label', () => {
  const label = '[[ log [2 lines] ]]'
  const payload = 'line one\nline two'
  const tokens: ComposerToken[] = [{ kind: 'paste', label, text: payload }]
  const full = `review this: ${label}`

  it('the queue item delivers the expanded paste at drain when live tokens are cleared', () => {
    const submission = prepareSubmission(full, tokens)
    const item = queueItem(submission.text, full)

    expect(item).toEqual({ display: `review this: ${label}`, text: `review this: ${payload}` })
    expect(expandTokens([])(item.text)).toBe(`review this: ${payload}`)
  })
})

describe('sendQueued gates shell/interpolation on the display, not the expanded text', () => {
  it('a paste whose payload begins with "!" is not shell-executed at drain', () => {
    const pasteLabel = '[[ [2 lines] ]]'
    const pastePayload = '!echo pwned\nsecond line'
    const tokens: ComposerToken[] = [{ kind: 'paste', label: pasteLabel, text: pastePayload }]
    const full = pasteLabel
    const submission = prepareSubmission(full, tokens)
    const item = queueItem(submission.text, full)

    expect(item.text.startsWith('!')).toBe(true)
    expect(item.display.startsWith('!')).toBe(false)
  })

  it('a !shell command with a collapsed paste is shell-executed with the expanded payload', () => {
    const pasteLabel = '[[ log [2 lines] ]]'
    const pastePayload = 'line one\nline two'
    const tokens: ComposerToken[] = [{ kind: 'paste', label: pasteLabel, text: pastePayload }]
    const full = `!ls ${pasteLabel}`
    const expandedArg = `!ls ${pastePayload}`
    const item = queueItem(expandedArg, full)

    expect(item.display.startsWith('!')).toBe(true)
    expect(item.text.slice(1).trim()).toBe(`ls ${pastePayload}`)
    expect(expandTokens(tokens)(item.display)).toBe(expandedArg)
  })

  it('a paste whose payload contains {!...} does not trigger interpolation at drain', () => {
    const pasteLabel = '[[ copied log [1 lines] ]]'
    const pastePayload = 'untrusted {!touch /tmp/pwned}'
    const tokens: ComposerToken[] = [{ kind: 'paste', label: pasteLabel, text: pastePayload }]
    const full = pasteLabel
    const submission = prepareSubmission(full, tokens)
    const item = queueItem(submission.text, full)

    expect(hasInterpolation(item.display)).toBe(false)
    expect(hasInterpolation(item.text)).toBe(true)
    expect(expandTokens([])(item.text)).toBe(pastePayload)
  })

  it('a visible {!...} alongside a paste does trigger interpolation at drain', () => {
    const pasteLabel = '[[ log [2 lines] ]]'
    const pastePayload = 'line one\nline two'
    const tokens: ComposerToken[] = [{ kind: 'paste', label: pasteLabel, text: pastePayload }]
    const full = `show {!date} for ${pasteLabel}`
    const submission = prepareSubmission(full, tokens)
    const item = queueItem(submission.text, full)

    expect(hasInterpolation(item.display)).toBe(true)
    expect(item.display).toBe(full)
    expect(item.text).toBe(`show {!date} for ${pastePayload}`)
  })
})

describe('the submit pipeline ships the expanded paste to the model and the label to the transcript', () => {
  const appendMessage = vi.fn()
  const submitted: { text: string }[] = []

  const gw = {
    request: vi.fn(async (method: string, params?: { text?: string }) => {
      if (method === 'prompt.submit' && params?.text !== undefined) {
        submitted.push({ text: params.text })
      }

      return Promise.resolve({ status: 'streaming' })
    })
  } as unknown as GatewayClient

  const deps: SubmitPromptDeps = {
    appendMessage,
    enqueue: vi.fn(),
    expand: (t: string) => t,
    gw,
    setLastUserMsg: vi.fn(),
    sys: vi.fn()
  }

  it('prompt.submit receives the expanded payload and the user bubble shows the collapsed label', async () => {
    resetUiState()
    patchUiState({ sid: 'sess-1' })
    appendMessage.mockClear()
    submitted.length = 0

    const label = '[[ log [2 lines] ]]'
    const payload = 'line one\nline two'
    const tokens: ComposerToken[] = [{ kind: 'paste', label, text: payload }]
    const full = `review this: ${label}`
    const submission = prepareSubmission(full, tokens)
    const item = queueItem(submission.text, full)

    submitPrompt(item.text, deps, true, item.display, { skipDetectDrop: true })
    await Promise.resolve()
    await Promise.resolve()

    expect(appendMessage).toHaveBeenCalledWith({ role: 'user', text: full })
    expect(submitted).toEqual([{ text: `review this: ${payload}` }])
  })
})
