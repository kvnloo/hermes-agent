import { randomUUID } from 'node:crypto'
import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { PassThrough } from 'node:stream'

import { renderSync, Text } from '@hermes/ink'
import { createElement } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { ComposerToken } from '../app/interfaces.js'
import { turnController } from '../app/turnController.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { prepareSubmission, useSubmission } from '../app/useSubmission.js'
import { GatewayClient } from '../gatewayClient.js'
import { queueItem, useQueue } from '../hooks/useQueue.js'
import { loadPendingInputs, migratePendingInputs, savePendingInput } from '../lib/pendingInputs.js'

let home: string

beforeEach(() => {
  home = mkdtempSync(join(tmpdir(), 'hermes-paste-journal-'))
  vi.stubEnv('HERMES_HOME', home)
  resetUiState()
  patchUiState({
    sid: 'session-1',
    info: { model: 'test', stored_session_id: 'stored-1', profile_name: 'default', skills: {}, tools: {} }
  })
})

afterEach(() => {
  turnController.fullReset()
  resetUiState()
  vi.restoreAllMocks()
  vi.unstubAllEnvs()
  rmSync(home, { recursive: true, force: true })
})

// Current HEAD persists already-expanded text, not the connector's removed expand closure.
function roundTrip(display: string, tokens: ComposerToken[]) {
  const destination = { sid: 'session-1', storedSid: 'stored-1', profile: 'default', profileHome: home }
  const prepared = prepareSubmission(display, tokens)

  const item = {
    ...queueItem(prepared.text, display),
    attachments: prepared.attachments,
    submissionId: randomUUID(),
    destination
  }

  savePendingInput(item)
  const [restored] = loadPendingInputs(destination)
  expect(restored).toBeDefined()

  if (!restored) { throw new Error('pending input was not restored') }

  return { item, restored, destination }
}

it('cold recovery preserves paste bytes and collapsed display through repeated journal writes', () => {
  const label = '[[ pasted text [2 lines] ]]'
  const payload = '  leading\nuntrusted {!PASTE_MUST_STAY_LITERAL}  '
  const display = `show ${label} after`
  const { restored, destination } = roundTrip(display, [{ kind: 'paste', label, text: payload }])
  expect(restored.text).toBe(`show ${payload} after`)
  expect(restored.display).toBe(display)
  savePendingInput(restored)
  expect(loadPendingInputs(destination)[0]?.text).toBe(`show ${payload} after`)
})

it('cold recovery retains distinct payloads for repeated identical collapsed labels', () => {
  const label = '[[ pasted text [1 line] ]]'

  const { restored } = roundTrip(`begin ${label} and ${label} end`, [
    { kind: 'paste', label, text: 'FIRST' },
    { kind: 'paste', label, text: 'SECOND' }
  ])

  expect(restored.text).toBe('begin FIRST and SECOND end')
})

it('cold recovery keeps an image as an attachment instead of transcript text', () => {
  const label = '[[ image 1 ]]'
  const path = join(home, 'attachment.png')

  const { restored } = roundTrip(`inspect ${label} now`, [
    { kind: 'image', index: 1, label, path, mime: 'image/png' }
  ])

  expect(restored.text).toBe('inspect now')
  expect(restored.attachments).toEqual([{ path, mime: 'image/png' }])
})

it('cold recovery carries expanded bytes to the resumed stored-session owner', () => {
  const label = '[[ pasted text [1 line] ]]'

  const { item, destination } = roundTrip(`before ${label} after`, [
    { kind: 'paste', label, text: 'FULL PAYLOAD' }
  ])

  const successor = { ...destination, sid: 'session-2' }
  migratePendingInputs({ ...destination, sid: 'cold-runtime' }, successor.sid, successor.storedSid)
  const [restored] = loadPendingInputs(successor)
  expect(restored).toMatchObject({ submissionId: item.submissionId, text: 'before FULL PAYLOAD after', destination: successor })
})

it('cold recovery sends only visible interpolation to shell.exec and keeps pasted syntax literal', async () => {
  const label = '[[ pasted text [2 lines] ]]'
  const payload = '  leading\nuntrusted {!PASTE_MUST_STAY_LITERAL}  '
  const display = `show {!VISIBLE_ONLY} then ${label} after`
  const { restored } = roundTrip(display, [{ kind: 'paste', label, text: payload }])
  const calls: Array<{ method: string; params: unknown }> = []
  const gw = new GatewayClient()
  // No connection is opened. Every outbound call stops at this spy.
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    if (method === 'shell.exec') { return { stdout: 'Friday', stderr: '', code: 0 } }

    if (method === 'input.detect_drop') { return { matched: false } }

    if (method === 'prompt.submit') { return { status: 'streaming' } }
    throw new Error(`unexpected RPC: ${method}`)
  })
  let queue!: ReturnType<typeof useQueue>
  let submission!: ReturnType<typeof useSubmission>

  const unused = () => { throw new Error('unexpected composer action') }

  function Harness() {
    queue = useQueue()
    submission = useSubmission({
      appendMessage: vi.fn(),
      composerActions: {
        appendPaste: unused, appendText: unused, attachClipboardImage: unused, attachImagePath: unused,
        attachImagePaths: unused, clearIn: unused, handleTextPaste: unused, openEditor: unused,
        pushHistory: unused, restoreDraft: unused, setInput: unused, setInputBuf: unused,
        setQueueEdit: queue.setQueueEdit, stage: queue.stage, dequeue: queue.dequeue, enqueue: queue.enqueue,
        prependQueue: queue.prependQ, takeQueue: queue.takeQ, removeQueue: queue.removeQ,
        queueDraft: queue.queueDraft, setCompIdx: unused, setComposerTokens: unused, setHistoryIdx: unused,
        syncTokens: unused, collapsePaste: unused, togglePaste: unused
      },
      composerRefs: {
        historyDraftRef: { current: '' }, historyRef: { current: [] }, queueRef: queue.queueRef,
        queueEditRef: queue.queueEditRef, tokensRef: { current: [] }, submitRef: { current: unused }
      },
      composerState: {
        compIdx: 0, compReplace: 0, completions: [], historyIdx: null, input: '', inputBuf: [],
        queuedDisplay: [], queueEditIdx: null, pasteExpanded: false, tokens: []
      },
      gw, setLastUserMsg: vi.fn(), slashRef: { current: () => true }, submitRef: { current: unused }, sys: vi.fn()
    })

    return createElement(Text, null, queue.queuedDisplay.join('|'))
  }

  // Same in-memory streams as the existing submissionDestinationRenderer tests.
  const instance = renderSync(createElement(Harness), {
    stdin: new PassThrough() as NodeJS.ReadStream,
    stdout: Object.assign(new PassThrough(), { columns: 80, rows: 20, isTTY: false }) as NodeJS.WriteStream,
    stderr: new PassThrough() as NodeJS.WriteStream,
    patchConsole: false
  })

  try {
    expect(queue.queueRef.current[0]?.text).toBe(restored.text)
    const item = queue.dequeue()
    expect(item).toBeDefined()

    if (!item) { throw new Error('restored input was not claimable') }
    submission.sendQueued(item)
    await new Promise(resolve => setImmediate(resolve))
    expect(calls.filter(call => call.method === 'shell.exec').map(call => call.params)).toEqual([
      { command: 'VISIBLE_ONLY', session_id: 'session-1' }
    ])
    expect(calls.find(call => call.method === 'prompt.submit')?.params).toMatchObject({
      text: `show Friday then ${payload} after`, submission_id: item.submissionId
    })
  } finally {
    instance.unmount()
  }
})
