// Regression for PR #111511: the same displayed burst keeps its time at settle.
import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { turnController } from '../app/turnController.js'
import { getTurnState, resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { fmtMsgTimestamp, MessageLine } from '../components/messageLine.js'
import { StreamingAssistant } from '../components/streamingAssistant.js'
import { appendTranscriptMessage } from '../lib/messages.js'
import { DEFAULT_THEME } from '../theme.js'
import type { Msg } from '../types.js'

const renderText = (node: React.ReactNode) => {
  const stdout = new PassThrough()
  const stdin = new PassThrough()
  const stderr = new PassThrough()
  let output = ''

  Object.assign(stdout, { columns: 80, isTTY: false, rows: 24 })
  Object.assign(stdin, { isTTY: false })
  Object.assign(stderr, { isTTY: false })
  stdout.on('data', chunk => {
    output += chunk.toString()
  })

  const instance = renderSync(node, {
    patchConsole: false,
    stderr: stderr as NodeJS.WriteStream,
    stdin: stdin as NodeJS.ReadStream,
    stdout: stdout as NodeJS.WriteStream
  })

  return {
    close: () => {
      instance.unmount()
      instance.cleanup()
      stdout.destroy()
      stdin.destroy()
      stderr.destroy()
    },
    text: () => stripAnsi(output)
  }
}

const lastLabel = (text: string) => Array.from(text.matchAll(/\[\d{2}:\d{2}\]/g)).at(-1)?.[0]

beforeEach(() => {
  turnController.fullReset()
  resetTurnState()
  resetUiState()
  // Only the wall clock is fake; real controller/Ink scheduling still executes.
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-10-14T12:59:55.000Z'))
  patchUiState({ streaming: true })
})

afterEach(() => {
  turnController.fullReset()
  resetTurnState()
  resetUiState()
  vi.useRealTimers()
})

describe('streaming-to-settled timestamp continuity', () => {
  it.each([
    { end: '2026-10-14T12:59:59.000Z', name: 'same-minute control' },
    { end: '2026-10-14T13:00:01.000Z', name: 'minute-boundary regression' }
  ])('preserves the rendered label: $name', async ({ end }) => {
    const initialTime = Date.now() / 1000
    turnController.startMessage()
    turnController.recordMessageDelta({ text: 'Hello' })
    await expect.poll(() => getTurnState().streaming, { timeout: 2000 }).toBe('Hello')

    const live = renderText(
      <StreamingAssistant
        cols={80}
        detailsMode="collapsed"
        detailsModeCommandOverride={false}
        progress={{ showProgressArea: false }}
        timestamps
      />
    )

    let settled: ReturnType<typeof renderText> | undefined

    try {
      await expect.poll(live.text, { timeout: 2000 }).toContain('Hello')
      const initialLabel = lastLabel(live.text())
      expect(initialLabel).toBe(fmtMsgTimestamp(initialTime))

      vi.setSystemTime(new Date(end))
      turnController.recordMessageDelta({ text: ' complete' })
      await expect.poll(() => getTurnState().streaming, { timeout: 2000 }).toBe('Hello complete')
      await expect.poll(live.text, { timeout: 2000 }).toContain('Hello complete')
      expect(lastLabel(live.text())).toBe(initialLabel)

      const { finalMessages } = turnController.recordMessageComplete({ text: 'Hello complete' })
      const transcript = finalMessages.reduce<Msg[]>(appendTranscriptMessage, [])
      expect(transcript).toHaveLength(1)
      expect(transcript[0]?.text).toBe('Hello complete')
      expect(getTurnState().streaming).toBe('')

      settled = renderText(<MessageLine cols={80} msg={transcript[0]!} t={DEFAULT_THEME} timestamps />)
      await expect.poll(settled.text, { timeout: 2000 }).toContain('Hello complete')
      console.info(JSON.stringify({ end, live: initialLabel, settled: lastLabel(settled.text()) }))
      expect(lastLabel(settled.text())).toBe(initialLabel)
    } finally {
      settled?.close()
      live.close()
    }
  })
})

const stream = async (text: string) => {
  turnController.recordMessageDelta({ text })
  await expect.poll(() => getTurnState().streaming, { timeout: 2000 }).toBe(text)
}

const mountLive = () =>
  renderText(
    <StreamingAssistant
      cols={80}
      detailsMode="collapsed"
      detailsModeCommandOverride={false}
      progress={{ showProgressArea: false }}
      timestamps
    />
  )

describe('displayed burst timestamp lifecycle', () => {
  it.each(['flush', 'tool', 'interim'] as const)(
    'preserves separate burst times through %s boundaries',
    async boundary => {
      turnController.startMessage()
      const firstTime = Date.now() / 1000
      await stream('First burst')
      vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))

      if (boundary === 'tool') {
        turnController.recordToolStart('tool-1', 'terminal', 'echo example')
        turnController.recordToolComplete('tool-1', 'terminal', 'example', 0)
      } else if (boundary === 'interim') {
        turnController.recordInterimMessage('First burst')
      } else {
        turnController.flushStreamingSegment()
      }

      expect(getTurnState().streamSegments.find(msg => msg.text === 'First burst')?.createdAt).toBe(firstTime)

      const secondTime = Date.now() / 1000
      await stream('Second burst')
      vi.setSystemTime(new Date('2026-10-14T13:01:01Z'))
      const { finalMessages } = turnController.recordMessageComplete({ text: 'Second burst' })
      const replies = finalMessages.reduce<Msg[]>(appendTranscriptMessage, []).filter(msg => msg.role === 'assistant')
      expect(replies.map(msg => msg.text)).toEqual(['First burst', 'Second burst'])
      expect(replies.map(msg => msg.createdAt)).toEqual([firstTime, secondTime])
    }
  )

  it('preserves an interrupted tail and already sealed segment', async () => {
    turnController.startMessage()
    const firstTime = Date.now() / 1000
    await stream('First burst')
    turnController.flushStreamingSegment()
    vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))
    const secondTime = Date.now() / 1000
    await stream('Unfinished tail')
    vi.setSystemTime(new Date('2026-10-14T13:01:01Z'))
    let transcript: Msg[] = []
    const calls: string[] = []
    // In-memory transport boundary only; no gateway/provider is executed.
    turnController.interruptTurn({
      appendMessage: msg => {
        transcript = appendTranscriptMessage(transcript, msg)
      },
      gw: {
        request: async <T,>(method: string) => {
          calls.push(method)

          return {} as T
        }
      },
      sid: 'timestamp-fixture',
      sys: text => {
        transcript = appendTranscriptMessage(transcript, { role: 'system', text })
      }
    })
    expect(calls).toEqual(['session.interrupt'])
    expect(transcript.map(msg => msg.createdAt)).toEqual([firstTime, secondTime])
    expect(transcript[1]?.text).toBe('Unfinished tail\n\n*[interrupted]*')
    // A late persisted extension must update text without replacing the sealed row's time.
    expect(
      turnController.recordMessageComplete({ status: 'interrupted', text: 'Unfinished tail extended' }).interruptedReply
    ).toEqual({ from: 'Unfinished tail\n\n*[interrupted]*', to: 'Unfinished tail extended\n\n*[interrupted]*' })
  })

  it('keeps the active label across remounts and resets it across turns with one mount', async () => {
    turnController.startMessage()
    await stream('First reply')
    const first = mountLive()
    let live: ReturnType<typeof mountLive> | undefined

    try {
      await expect.poll(first.text, { timeout: 2000 }).toContain('First reply')
      const firstLabel = lastLabel(first.text())
      first.close()
      vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))
      live = mountLive()
      await expect.poll(live.text, { timeout: 2000 }).toContain('First reply')
      expect(lastLabel(live.text())).toBe(firstLabel)
      turnController.recordMessageComplete({ text: 'First reply' })
      turnController.startMessage()
      await stream('Second reply')
      await expect.poll(live.text, { timeout: 2000 }).toContain('Second reply')
      const secondLabel = lastLabel(live.text())
      expect(secondLabel).not.toBe(firstLabel)
      vi.setSystemTime(new Date('2026-10-14T13:01:01Z'))
      const { finalMessages } = turnController.recordMessageComplete({ text: 'Second reply' })
      const settled = renderText(<MessageLine cols={80} msg={finalMessages[0]!} t={DEFAULT_THEME} timestamps />)

      try {
        await expect.poll(settled.text, { timeout: 2000 }).toContain('Second reply')
        expect(lastLabel(settled.text())).toBe(secondLabel)
      } finally {
        settled.close()
      }
    } finally {
      live?.close()

      if (!live) {
        first.close()
      }
    }
  })

  it.each(['no delta', 'streaming disabled', 'unpublished delta'] as const)(
    'retains append-time fallback for %s',
    mode => {
      turnController.startMessage()

      if (mode === 'streaming disabled') {
        patchUiState({ streaming: false })
      }

      if (mode !== 'no delta') {
        turnController.recordMessageDelta({ text: 'Reply' })
      }
      vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))
      const { finalMessages } = turnController.recordMessageComplete({ text: 'Reply' })
      expect(finalMessages[0]?.createdAt).toBeUndefined()
      expect(finalMessages.reduce<Msg[]>(appendTranscriptMessage, [])[0]?.createdAt).toBe(Date.now() / 1000)
    }
  )

  it.each(['error', 'reset', 'full reset', 'idle'] as const)(
    'does not inherit a discarded clock after %s',
    async boundary => {
      turnController.startMessage()
      await stream('Discarded')

      if (boundary === 'error') {
        turnController.recordError()
      } else if (boundary === 'reset') {
        turnController.reset()
      } else if (boundary === 'full reset') {
        turnController.fullReset()
      } else {
        turnController.idle()
      }

      // Check the cleanup boundary itself, before startMessage can clear it.
      expect(getTurnState().streaming).toBe('')
      expect(getTurnState().streamingCreatedAt).toBeUndefined()
      vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))
      turnController.startMessage()
      const { finalMessages } = turnController.recordMessageComplete({ text: 'Never streamed' })
      expect(finalMessages[0]?.createdAt).toBeUndefined()
      expect(finalMessages.reduce<Msg[]>(appendTranscriptMessage, [])[0]?.createdAt).toBe(Date.now() / 1000)
    }
  )

  it('retains hydrated visible burst time and ignores reasoning-only prefixes', async () => {
    turnController.startMessage()
    turnController.hydrateStreamingText('<think>Private reasoning')
    expect(getTurnState().streaming).toBe('')
    vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))
    const visibleTime = Date.now() / 1000
    turnController.hydrateStreamingText('<think>Private reasoning</think>Visible answer')
    const live = mountLive()

    try {
      await expect.poll(live.text, { timeout: 2000 }).toContain('Visible answer')
      const label = lastLabel(live.text())
      vi.setSystemTime(new Date('2026-10-14T13:01:01Z'))
      turnController.hydrateStreamingText('<think>Private reasoning</think>Visible answer extended')
      await expect.poll(live.text, { timeout: 2000 }).toContain('Visible answer extended')
      expect(lastLabel(live.text())).toBe(label)
      const { finalMessages } = turnController.recordMessageComplete({ text: 'Visible answer extended' })
      expect(finalMessages.find(msg => msg.role === 'assistant')?.createdAt).toBe(visibleTime)
    } finally {
      live.close()
    }
  })

  it('does not lend a flushed tail timestamp to distinct unstreamed final text', async () => {
    turnController.startMessage()
    const firstTime = Date.now() / 1000
    await stream('Streamed aside')
    vi.setSystemTime(new Date('2026-10-14T13:00:01Z'))
    const { finalMessages } = turnController.recordMessageComplete({ text: 'Different final answer' })
    const replies = finalMessages.reduce<Msg[]>(appendTranscriptMessage, []).filter(msg => msg.role === 'assistant')
    expect(replies.map(msg => msg.createdAt)).toEqual([firstTime, Date.now() / 1000])
  })
})
