// W2 probe (evidence only, not proposed for upstream): same mounted harness as
// queuedPasteSubmission.test.tsx, plus captured sys() lines and the
// auto-drain path (useMainApp's effect: dequeue() then sendQueued(head)).
// The gateway is fake; shell.exec is only recorded, never executed.
import { PassThrough } from 'node:stream'

import { renderSync, Text } from '@hermes/ink'
import React from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { ComposerActions, ComposerRefs, ComposerState, ComposerToken } from '../app/interfaces.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { useSubmission } from '../app/useSubmission.js'
import { useQueue } from '../hooks/useQueue.js'
import { pasteTokenLabel } from '../lib/text.js'

const settle = async () => {
  for (let i = 0; i < 5; i += 1) {
    await new Promise(resolve => setTimeout(resolve, 0))
  }
}

const paste = (text: string): ComposerToken => ({
  kind: 'paste',
  label: pasteTokenLabel(text, text.split('\n').length),
  text
})

function mount(tokens: ComposerToken[]) {
  const tokensRef = { current: tokens }
  const prompts: string[] = []
  const shell: string[] = []
  const sysLines: string[] = []
  const transcript: string[] = []
  let api!: ReturnType<typeof useSubmission>
  let queue!: ReturnType<typeof useQueue>

  const gw = {
    request: vi.fn(async (method: string, params: { command?: string; text?: string }) => {
      if (method === 'prompt.submit' || method === 'session.steer') {
        prompts.push(params.text!)
      }

      if (method === 'session.steer') {
        return { status: 'queued' }
      }

      if (method === 'shell.exec') {
        shell.push(params.command!)

        return { code: 0, stderr: '', stdout: 'Fri' }
      }

      return method === 'input.detect_drop' ? { matched: false } : {}
    })
  }

  function Harness() {
    queue = useQueue()

    const composerActions = {
      clearIn: () => {
        tokensRef.current = []
        queue.setQueueEdit(null)
      },
      dequeue: queue.dequeue,
      enqueue: queue.enqueue,
      prependQueue: queue.prependQ,
      pushHistory: () => {},
      setQueueEdit: queue.setQueueEdit,
      takeQueue: queue.takeQ
    } as unknown as ComposerActions

    api = useSubmission({
      appendMessage: msg => transcript.push(msg.text),
      composerActions,
      composerRefs: {
        queueEditRef: queue.queueEditRef,
        queueRef: queue.queueRef,
        tokensRef
      } as unknown as ComposerRefs,
      composerState: {
        compIdx: 0,
        compReplace: 0,
        completions: [],
        input: '',
        inputBuf: []
      } as unknown as ComposerState,
      gw: gw as never,
      setLastUserMsg: () => {},
      slashRef: { current: () => true },
      submitRef: { current: () => {} },
      sys: line => sysLines.push(line)
    })

    return <Text>{queue.queuedDisplay.join('|') || 'empty queue'}</Text>
  }

  const stdout = new PassThrough()
  Object.assign(stdout, { columns: 80, isTTY: false, rows: 20 })

  const instance = renderSync(<Harness />, {
    patchConsole: false,
    stderr: new PassThrough() as unknown as NodeJS.WriteStream,
    stdin: new PassThrough() as unknown as NodeJS.ReadStream,
    stdout: stdout as unknown as NodeJS.WriteStream
  })

  return {
    // useMainApp's idle drain effect: dequeue() then sendQueued(head).
    autoDrain: () => {
      const head = queue.dequeue()

      if (head) {
        ;(api.sendQueued as (value: unknown) => void)(head)
      }
    },
    doubleEnterDrain: () => {
      api.submit('')
      api.submit('')
    },
    // useInputHandlers.cycleQueue: select a queued item and load its display
    // into the composer (no tokens are restored), then the user presses Enter.
    editAndSubmitQueued: (index: number) => {
      queue.setQueueEdit(index)
      api.submit(queue.queueRef.current[index]!.display)
    },
    prompts,
    queueLength: () => queue.queueRef.current.length,
    shell,
    submit: (value: string) => api.submit(value),
    sysLines,
    transcript,
    unmount: () => instance.unmount()
  }
}

afterEach(resetUiState)

const log = paste('line one\nline two\nline three\nline four\nline five')
const bang = paste(`!echo pwned\n${'z\n'.repeat(5)}end`)

describe('probe: orphaned placeholder (the #99042 contract)', () => {
  it('an idle submit whose collapsed label has no token is refused with a warning, not sent', async () => {
    patchUiState({ busy: false, sid: 'session-1' })
    const ui = mount([])

    try {
      ui.submit(`review this: ${log.label}`)
      await settle()
      expect(ui.prompts).toEqual([])
      expect(ui.sysLines.some(line => line.includes('cannot submit'))).toBe(true)
    } finally {
      ui.unmount()
    }
  })
})

describe('probe: auto-drain path (useMainApp effect)', () => {
  it('a /queue paste whose content starts with ! is not shell-executed on auto-drain', async () => {
    patchUiState({ busy: false, busyInputMode: 'queue', sid: 'session-1' })
    const ui = mount([bang])

    try {
      ui.submit(`/queue ${bang.label}`)
      ui.autoDrain()
      await settle()
      expect({ prompts: ui.prompts, shell: ui.shell }).toEqual({ prompts: [bang.text], shell: [] })
    } finally {
      ui.unmount()
    }
  })

  it('a busy queue-mode paste reaches the model expanded on auto-drain', async () => {
    patchUiState({ busy: true, busyInputMode: 'queue', sid: 'session-1' })
    const ui = mount([log])

    try {
      ui.submit(`review this: ${log.label}`)
      patchUiState({ busy: false })
      ui.autoDrain()
      await settle()
      expect({ prompts: ui.prompts, sys: ui.sysLines }).toEqual({ prompts: [`review this: ${log.text}`], sys: [] })
    } finally {
      ui.unmount()
    }
  })
})

describe('probe: double-Enter drain outcome (failure diff shows the observed state)', () => {
  it('a busy queue-mode paste drained by double-Enter is delivered expanded, not dropped', async () => {
    patchUiState({ busy: true, busyInputMode: 'queue', sid: 'session-1' })
    const ui = mount([log])

    try {
      ui.submit(`review this: ${log.label}`)
      const queuedBefore = ui.queueLength()
      patchUiState({ busy: false })
      ui.doubleEnterDrain()
      await settle()
      expect({ prompts: ui.prompts, queuedAfter: ui.queueLength(), queuedBefore, sys: ui.sysLines }).toEqual({
        prompts: [`review this: ${log.text}`],
        queuedAfter: 0,
        queuedBefore: 1,
        sys: []
      })
    } finally {
      ui.unmount()
    }
  })
})

describe('probe: queue-edit submit (cycleQueue then Enter)', () => {
  it.each([
    { name: '/queue item', queueIt: (ui: ReturnType<typeof mount>) => ui.submit(`/queue review this: ${log.label}`), state: { busy: false } },
    { name: 'busy queue-mode item', queueIt: (ui: ReturnType<typeof mount>) => ui.submit(`review this: ${log.label}`), state: { busy: true } }
  ])('an edited-and-resubmitted queued collapsed paste is delivered expanded ($name)', async ({ queueIt, state }) => {
    patchUiState({ busyInputMode: 'queue', sid: 'session-1', ...state })
    const ui = mount([log])

    try {
      queueIt(ui)
      patchUiState({ busy: false })
      ui.editAndSubmitQueued(0)
      await settle()
      expect({ prompts: ui.prompts, queuedAfter: ui.queueLength(), sys: ui.sysLines.filter(l => !l.startsWith('queued:')) }).toEqual({
        prompts: [`review this: ${log.text}`],
        queuedAfter: 0,
        sys: []
      })
    } finally {
      ui.unmount()
    }
  })
})
