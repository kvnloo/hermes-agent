import { randomUUID } from 'node:crypto'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { expect, it } from 'vitest'

import type { ComposerToken } from '../app/interfaces.js'
import { expandTokens } from '../domain/attachments.js'
import { queueItem } from '../hooks/useQueue.js'
import { loadPendingInputs, savePendingInput } from '../lib/pendingInputs.js'

// A pending-input journal outlives the composer process. Saving a JS closure in
// memory cannot restore the expanded text when the queued visible interpolation
// runs in the next process.
function roundTrip(display: string, tokens: ComposerToken[]) {
  const home = mkdtempSync(join(tmpdir(), 'hermes-paste-journal-'))
  const destination = {
    sid: 'session-1', storedSid: 'stored-1', profile: 'default', profileHome: home
  }
  const text = expandTokens(tokens)(display)
  const item = {
    ...queueItem(text, display, expandTokens(tokens)),
    submissionId: randomUUID(), destination
  }
  try {
    savePendingInput(item)
    const [restored] = loadPendingInputs(destination)
    expect(restored).toBeDefined()
    expect(restored!.text).toBe(text)
    return { item, restored: restored!, text }
  } finally {
    rmSync(home, { recursive: true, force: true })
  }
}

it('cold recovery preserves paste bytes through user-visible interpolation without executing pasted syntax', () => {
  const label = '[[ pasted text [2 lines] ]]'
  const payload = '  leading\nuntrusted {!touch /tmp/DO_NOT_RUN}  '
  const display = `show {!date} then ${label} after`
  const tokens: ComposerToken[] = [{ kind: 'paste', label, text: payload }]
  const { item, restored } = roundTrip(display, tokens)

  expect(restored.expansionSnapshot).toEqual([{ label, value: payload }])
  const completedDisplay = display.replace('{!date}', 'Friday')
  const expected = expandTokens(tokens)(completedDisplay)

  // Both the queued instance and the restored queue item must have a stable,
  // non-consuming expansion, so busy retries cannot turn the label into input.
  expect(item.expand!(completedDisplay)).toBe(expected)
  expect(restored.expand!(completedDisplay)).toBe(expected)
  expect(restored.expand!(completedDisplay)).toBe(expected)
  expect(expected).toContain('{!touch /tmp/DO_NOT_RUN}')
  expect(expected).not.toContain(label)
})

it('repeated identical collapsed labels retain distinct paste payloads after a cold restart', () => {
  const label = '[[ pasted text [1 line] ]]'
  const display = `begin ${label} and ${label} end`
  const tokens: ComposerToken[] = [
    { kind: 'paste', label, text: 'FIRST' },
    { kind: 'paste', label, text: 'SECOND' }
  ]
  const { restored } = roundTrip(display, tokens)
  expect(restored.expand!(display)).toBe('begin FIRST and SECOND end')
  expect(restored.expand!(display)).toBe('begin FIRST and SECOND end')
})

it('an image token remains only an attachment placeholder, not transcript text', () => {
  const label = '[[ image 1 ]]'
  const display = `inspect ${label} now`
  const tokens: ComposerToken[] = [
    { kind: 'image', index: 1, label, path: '/tmp/attachment.png', mime: 'image/png' }
  ]
  const { restored } = roundTrip(display, tokens)
  expect(restored.expand!(display)).toBe('inspect now')
})

it('cold recovery expands later paste tokens when visible interpolation consumes an earlier label', () => {
  const consumed = '[[ pasted text [1 line] ]]'
  const retained = '[[ pasted text [2 lines] ]]'
  const display = `query {!echo ${consumed}} then ${retained}`
  const tokens: ComposerToken[] = [
    { kind: 'paste', label: consumed, text: 'not part of the interpolated result' },
    { kind: 'paste', label: retained, text: 'SECOND PAYLOAD' }
  ]
  const { restored } = roundTrip(display, tokens)
  const resolved = `query DONE then ${retained}`
  expect(restored.expand!(resolved)).toBe('query DONE then SECOND PAYLOAD')
  expect(restored.expand!(resolved)).toBe('query DONE then SECOND PAYLOAD')
})

it('cold recovery removes remaining image placeholders after earlier tokens are interpolated away', () => {
  const consumed = '[[ pasted text [1 line] ]]'
  const image = '[[ image 1 ]]'
  const display = `query {!echo ${consumed}} then ${image}`
  const tokens: ComposerToken[] = [
    { kind: 'paste', label: consumed, text: 'not part of the interpolated result' },
    { kind: 'image', index: 1, label: image, path: '/tmp/attachment.png', mime: 'image/png' }
  ]
  const { restored } = roundTrip(display, tokens)
  expect(restored.expand!(`query DONE then ${image}`)).toBe('query DONE then')
})
