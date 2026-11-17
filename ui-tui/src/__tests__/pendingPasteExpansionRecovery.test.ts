import { randomUUID } from 'node:crypto'
import { mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs'
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
  home = realpathSync(mkdtempSync(join(tmpdir(), 'hermes-paste-journal-')))
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
    ...queueItem(prepared.text, display, tokens),
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

const label = '[[ pasted text [2 lines] ]]'
const payload = '  leading\nuntrusted {!PASTE_MUST_STAY_LITERAL}  '
const display = `show {!VISIBLE_ONLY} then ${label} after`
const tokens: ComposerToken[] = [{ kind: 'paste', label, text: payload }]

interface DrainCase {
  name: string
  display: string
  tokens: ComposerToken[]
  expected: string
  commands: string[]
  admission?: 'offline' | 'busy' | 'slash'
  legacy?: boolean
  retry?: boolean
}

const cases: DrainCase[] = [
  { name: 'executes only visible interpolation', display, tokens,
    expected: `show Friday then ${payload} after`, commands: ['VISIBLE_ONLY'] },
  { name: 'keeps hidden interpolation literal without a visible command', display: `show ${label}`, tokens,
    expected: `show ${payload}`.trim(), commands: [] },
  { name: 'does not promote a pasted leading bang to a shell command', display: label,
    tokens: [{ kind: 'paste', label, text: '!PASTE_MUST_STAY_LITERAL' }],
    expected: '!PASTE_MUST_STAY_LITERAL', commands: [] },
  { name: 'keeps identical pasted and visible commands distinct', display: `${label} then {!VISIBLE_ONLY}`,
    tokens: [{ kind: 'paste', label, text: '{!VISIBLE_ONLY}' }],
    expected: '{!VISIBLE_ONLY} then Friday', commands: ['VISIBLE_ONLY'] },
  { name: 'retains repeated identical labels during interpolation', display: `{!VISIBLE_ONLY} ${label} and ${label}`,
    tokens: [{ kind: 'paste', label, text: 'FIRST' }, { kind: 'paste', label, text: 'SECOND' }],
    expected: 'Friday FIRST and SECOND', commands: ['VISIBLE_ONLY'] },
  { name: 'expands later tokens after a command consumes an earlier label',
    display: `query {!echo [[ pasted text [1 line] ]]} then ${label}`,
    tokens: [{ kind: 'paste', label: '[[ pasted text [1 line] ]]', text: 'CONSUMED' }, ...tokens],
    expected: `query Friday then ${payload}`.trim(), commands: ['echo [[ pasted text [1 line] ]]'] },
  { name: 'removes image labels after interpolation', display: 'query {!VISIBLE_ONLY} then [[ image 1 ]]',
    tokens: [{ kind: 'image', index: 1, label: '[[ image 1 ]]', path: 'attachment.png', mime: 'image/png' }],
    expected: 'query Friday then', commands: ['VISIBLE_ONLY'] },
  { name: 'retries prepared text after another cold restart without rerunning interpolation', display, tokens,
    expected: `show Friday then ${payload} after`, commands: ['VISIBLE_ONLY'], retry: true },
  { name: 'keeps legacy expanded text literal without guessing token boundaries', display, tokens,
    expected: `show {!VISIBLE_ONLY} then ${payload} after`, commands: [], legacy: true },
  ...(['offline', 'busy', 'slash'] as const).map(admission => ({
    name: `journals tokens through ${admission} admission before cold recovery`, display, tokens,
    expected: `show Friday then ${payload} after`, commands: ['VISIBLE_ONLY'], admission
  }))
]

it.each(cases)('cold recovery $name', async ({ display, tokens, expected, commands, admission, legacy, retry }) => {
  const prepared = prepareSubmission(display, tokens)
  let restored = admission ? undefined : roundTrip(display, tokens).restored

  if (restored && legacy) {
    delete restored.tokens
    savePendingInput(restored)
  }

  let composerTokens = admission ? tokens : []
  let submitAttempts = 0
  const calls: Array<{ method: string; params: unknown }> = []
  const gw = new GatewayClient()
  // No connection is opened. Every outbound call stops at this spy.
  vi.spyOn(gw, 'request').mockImplementation(async (method, params) => {
    calls.push({ method, params })

    if (method === 'shell.exec') { return { stdout: 'Friday', stderr: '', code: 0 } }

    if (method === 'input.detect_drop') { return { matched: false } }

    if (method === 'prompt.submit') {
      submitAttempts++

      if (retry && submitAttempts === 1) {
        throw new Error('session busy')
      }

      return { status: 'streaming' }
    }

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
        attachImagePaths: unused, clearIn: () => { composerTokens = [] }, handleTextPaste: unused, openEditor: unused,
        pushHistory: vi.fn(), restoreDraft: unused, setInput: unused, setInputBuf: unused,
        setQueueEdit: queue.setQueueEdit, stage: queue.stage, dequeue: queue.dequeue, enqueue: queue.enqueue,
        prependQueue: queue.prependQ, takeQueue: queue.takeQ, removeQueue: queue.removeQ,
        queueDraft: queue.queueDraft, setCompIdx: unused, setComposerTokens: unused, setHistoryIdx: unused,
        syncTokens: unused, collapsePaste: unused, togglePaste: unused
      },
      composerRefs: {
        historyDraftRef: { current: '' }, historyRef: { current: [] }, queueRef: queue.queueRef,
        queueEditRef: queue.queueEditRef, tokensRef: { current: composerTokens }, submitRef: { current: unused }
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
  const render = () => renderSync(createElement(Harness), {
    stdin: new PassThrough() as NodeJS.ReadStream,
    stdout: Object.assign(new PassThrough(), { columns: 80, rows: 20, isTTY: false }) as NodeJS.WriteStream,
    stderr: new PassThrough() as NodeJS.WriteStream,
    patchConsole: false
  })

  let instance = render()

  try {
    if (admission) {
      patchUiState({ gatewayConnected: admission !== 'offline', busy: admission === 'busy', busyInputMode: 'queue' })
      submission.dispatchSubmission(admission === 'slash' ? `/queue ${display}` : display)
      expect(queue.queueRef.current[0]?.text).toBe(prepared.text)
      const destination = queue.queueRef.current[0]?.destination
      expect(destination).toBeDefined()

      if (!destination) { throw new Error('admitted input has no destination') }
      restored = loadPendingInputs(destination)[0]
      expect(restored?.tokens).toEqual(tokens)
      instance.unmount()
      patchUiState({ gatewayConnected: true, busy: false })
      instance = render()
    }

    expect(queue.queueRef.current[0]?.text).toBe(restored?.text)
    const item = queue.dequeue()
    expect(item).toBeDefined()

    if (!item) { throw new Error('restored input was not claimable') }
    submission.sendQueued(item)
    await new Promise(resolve => setImmediate(resolve))
    expect(calls.filter(call => call.method === 'shell.exec').map(call => call.params)).toEqual(
      commands.map(command => ({ command, session_id: 'session-1' }))
    )
    expect(calls.find(call => call.method === 'prompt.submit')?.params).toMatchObject({
      text: expected, submission_id: item.submissionId
    })

    if (retry) {
      expect(item.destination).toBeDefined()

      if (!item.destination) { throw new Error('retry has no destination') }
      expect(loadPendingInputs(item.destination)[0]?.preparedText).toBe(expected)
      instance.unmount()
      instance = render()
      const recovered = queue.dequeue(true)
      expect(recovered?.preparedText).toBe(expected)

      if (!recovered) { throw new Error('retry was not claimable') }
      calls.length = 0
      submission.sendQueued(recovered)
      await new Promise(resolve => setImmediate(resolve))
      expect(calls.map(call => call.method)).toEqual(['prompt.submit'])
      expect(calls[0]?.params).toMatchObject({ text: expected, submission_id: item.submissionId })
    }
  } finally {
    instance.unmount()
  }
})

it('cold recovery rejects malformed token snapshots at the journal boundary', () => {
  const { item, destination } = roundTrip(label, tokens)
  const path = join(home, 'tui-pending-inputs', `${item.submissionId}.json`)
  const record = JSON.parse(readFileSync(path, 'utf8'))
  record.tokens = [{ kind: 'paste', label, text: 42 }]
  writeFileSync(path, JSON.stringify(record))
  expect(() => loadPendingInputs(destination)).toThrow()
})
