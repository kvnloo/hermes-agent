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

// The real useSubmission + useQueue, with a fake gateway. `clearIn` drops the
// live tokens exactly like the composer does on submit, so anything that still
// needs them after that point has to carry its own copy.
function mount(tokens: ComposerToken[]) {
  const tokensRef = { current: tokens }
  // Text that reaches the model: prompt.submit, or session.steer into a live turn.
  const prompts: string[] = []
  const shell: string[] = []
  const transcript: string[] = []
  let api!: ReturnType<typeof useSubmission>

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
    const queue = useQueue()

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
      sys: () => {}
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
    // Double Enter on an empty composer sends the head of the queue.
    drainOne: () => {
      api.submit('')
      api.submit('')
    },
    prompts,
    shell,
    submit: (value: string) => api.submit(value),
    transcript,
    unmount: () => instance.unmount()
  }
}

afterEach(resetUiState)

describe('a collapsed paste that cannot be sent straight away', () => {
  const log = paste('line one\nline two\nline three\nline four\nline five')

  it.each([
    { name: 'busy, interrupt mode', queued: false, state: { busy: true, busyInputMode: 'interrupt' as const } },
    { name: 'busy, steer mode', queued: false, state: { busy: true, busyInputMode: 'steer' as const }, steer: true },
    { name: 'busy, queue mode', queued: true, state: { busy: true, busyInputMode: 'queue' as const } },
    { name: 'no session yet', queued: true, state: { busy: false, sid: null } }
  ])('reaches the model expanded ($name)', async ({ queued, state, steer }) => {
    patchUiState({ sid: 'session-1', ...state })
    const ui = mount([log])

    try {
      ui.submit(`review this: ${log.label}`)

      if (queued) {
        expect(ui.prompts).toEqual([])
        patchUiState({ busy: false, sid: 'session-1' })
        ui.drainOne()
      }

      await settle()

      expect(ui.prompts).toEqual([`review this: ${log.text}`])
      // A steer joins the live turn without a user bubble of its own.
      expect(ui.transcript).toEqual(steer ? [] : [`review this: ${log.label}`])
    } finally {
      ui.unmount()
    }
  })
})

describe('draining a queued collapsed paste', () => {
  // Interpolation and `!` belong to what the user typed, never to pasted bytes.
  const hidden = paste(`first line of the log\n${'x\n'.repeat(4)}untrusted {!touch /tmp/pwned}\n${'y\n'.repeat(14)}end`)
  const bang = paste(`!echo pwned\n${'z\n'.repeat(5)}end`)

  it.each([
    {
      expected: { prompt: `show Fri for ${hidden.text}`, shell: ['date'], transcript: `show Fri for ${hidden.label}` },
      name: 'runs only the visible {!...}, not one carried by the paste',
      queue: () => patchUiState({ busy: true }),
      token: hidden,
      typed: `show {!date} for ${hidden.label}`
    },
    {
      expected: { prompt: bang.text, shell: [], transcript: bang.label },
      name: 'does not shell-execute a /queue paste whose content starts with !',
      queue: () => {},
      token: bang,
      typed: `/queue ${bang.label}`
    }
  ])('$name', async ({ expected, queue, token, typed }) => {
    patchUiState({ busy: false, busyInputMode: 'queue', sid: 'session-1' })
    const ui = mount([token])

    try {
      queue()
      ui.submit(typed)
      patchUiState({ busy: false })
      ui.drainOne()
      await settle()

      expect(ui.shell).toEqual(expected.shell)
      expect(ui.prompts).toEqual([expected.prompt])
      expect(ui.transcript.at(-1)).toBe(expected.transcript)
    } finally {
      ui.unmount()
    }
  })
})
