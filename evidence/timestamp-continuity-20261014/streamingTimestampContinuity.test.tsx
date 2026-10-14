// Regression evidence for PR #111511: the same reply keeps its label at settle.
import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { turnController } from '../app/turnController.js'
import { getTurnState, resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { MessageLine } from '../components/messageLine.js'
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
      expect(initialLabel).toBe('[12:59]')

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
