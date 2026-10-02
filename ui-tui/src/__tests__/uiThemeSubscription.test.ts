import { PassThrough } from 'node:stream'

import { Box, forceRedraw, renderSync, Text } from '@hermes/ink'
import React, { Profiler } from 'react'
import stripAnsi from 'strip-ansi'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { patchTurnState, resetTurnState } from '../app/turnStore.js'
import { $uiState, $uiTheme, getUiState, patchUiState, resetUiState } from '../app/uiStore.js'
import { LiveTodoPanel, StreamingAssistant } from '../components/streamingAssistant.js'

afterEach(resetUiState)

describe('ui theme subscription', () => {
  it('does not notify theme-only consumers for unrelated ui-state churn', () => {
    let fullStoreWakeups = 0
    let themeWakeups = 0

    const stopFull = $uiState.listen(() => {
      fullStoreWakeups += 1
    })

    const stopTheme = $uiTheme.listen(() => {
      themeWakeups += 1
    })

    try {
      const fullBaseline = fullStoreWakeups
      const themeBaseline = themeWakeups

      for (let i = 0; i < 20; i++) {
        patchUiState({ status: `streaming-${i}` })
      }

      expect(fullStoreWakeups - fullBaseline).toBe(20)
      expect(themeWakeups - themeBaseline).toBe(0)

      patchUiState({ theme: { ...getUiState().theme } })
      expect(themeWakeups - themeBaseline).toBe(1)
    } finally {
      stopTheme()
      stopFull()
    }
  })
})

it.each(['streaming', 'todo'] as const)('keeps the real %s consumer scoped to theme and turn content', async mode => {
  resetUiState()
  resetTurnState()

  const setContent = (text: string) => {
    if (mode === 'streaming') {
      patchTurnState({ streaming: text })
    } else {
      patchTurnState({ todos: text ? [{ id: 'fixture-todo', content: text, status: 'pending' }] : [] })
    }
  }

  setContent('fixturecontent')
  const stdout = Object.assign(new PassThrough(), { columns: 100, rows: 20, isTTY: true })
  const stdin = Object.assign(new PassThrough(), { isTTY: false })
  let output = ''
  stdout.on('data', chunk => {
    output += String(chunk)
  })
  const commits = vi.fn()

  const consumer =
    mode === 'streaming'
      ? React.createElement(StreamingAssistant, {
          cols: 90,
          detailsMode: 'collapsed',
          detailsModeCommandOverride: false,
          progress: { showProgressArea: false }
        })
      : React.createElement(LiveTodoPanel)

  const view = renderSync(
    React.createElement(
      Box,
      { flexDirection: 'column', height: 8 },
      React.createElement(Profiler, { id: mode, onRender: commits }, consumer),
      React.createElement(Text, null, 'TURN_CONTROL')
    ),
    {
      patchConsole: false,
      stdout: stdout as unknown as NodeJS.WriteStream,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream
    }
  )

  const settle = async () => {
    await new Promise<void>(resolve => setImmediate(resolve))
    await new Promise<void>(resolve => setImmediate(resolve))
  }

  const frame = async () => {
    await settle()
    output = ''
    expect(forceRedraw(stdout as unknown as NodeJS.WriteStream)).toBe(true)
    const text = stripAnsi(output)
    expect(text).toContain('TURN_CONTROL')

    return text
  }

  try {
    expect(await frame()).toContain('fixturecontent')
    expect(commits).toHaveBeenCalled()
    commits.mockClear()

    for (let i = 0; i < 20; i++) {
      patchUiState({ status: `streaming-${i}` })
    }

    await settle()
    expect(commits).not.toHaveBeenCalled()

    patchUiState({ theme: { ...getUiState().theme } })
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    expect(await frame()).toContain('fixturecontent')
    commits.mockClear()

    setContent('changedcontent')
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    const changed = await frame()
    expect(changed).toContain('changedcontent')
    expect(changed).not.toContain('fixturecontent')
    commits.mockClear()

    setContent('')
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    expect(await frame()).not.toContain('changedcontent')
    commits.mockClear()

    setContent('restoredcontent')
    await settle()
    expect(commits).toHaveBeenCalledTimes(1)
    expect(await frame()).toContain('restoredcontent')
  } finally {
    view.unmount()
    view.cleanup()
    resetTurnState()
    resetUiState()
  }
})
