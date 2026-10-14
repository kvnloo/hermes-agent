// PR #111511: exercise timestamp continuity through the real event handler.
import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createGatewayEventHandler } from '../app/createGatewayEventHandler.js'
import type { GatewayEventHandlerContext, StateSetter } from '../app/interfaces.js'
import { resetOverlayState } from '../app/overlayStore.js'
import { turnController } from '../app/turnController.js'
import { getTurnState, resetTurnState } from '../app/turnStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import { fmtMsgTimestamp, MessageLine } from '../components/messageLine.js'
import { StreamingAssistant } from '../components/streamingAssistant.js'
import { appendTranscriptMessage, capTranscriptHistory } from '../lib/messages.js'
import { DEFAULT_THEME } from '../theme.js'
import type { Msg } from '../types.js'

const SID = 'handler-timestamp-fixture'
const renderers: (() => void)[] = []

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

  renderers.push(() => {
    instance.unmount()
    instance.cleanup()
    stdout.destroy()
    stdin.destroy()
    stderr.destroy()
  })

  return () => stripAnsi(output)
}

const lastLabel = (text: string) => Array.from(text.matchAll(/\[\d{2}:\d{2}\]/g)).at(-1)?.[0]

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

const createHarness = () => {
  let history: Msg[] = []
  // Apply the real handler-supplied updater, using the same append/cap helpers
  // as useMainApp. No replacement logic or timestamp is supplied by the test.
  const setHistoryItems = vi.fn<StateSetter<Msg[]>>(next => {
    history = capTranscriptHistory(typeof next === 'function' ? next(history) : next)
  })
  const appendMessage = vi.fn((msg: Msg) => setHistoryItems(prev => appendTranscriptMessage(prev, msg)))
  const sys = vi.fn((text: string) => appendMessage({ role: 'system', text }))
  const request = vi.fn(async <T,>(method: string, params?: Record<string, unknown>) => {
    expect(method).toBe('session.interrupt')
    expect(params).toEqual({ session_id: SID })

    return { status: 'interrupted' } as T
  })
  const rpc = vi.fn(async () => {
    throw new Error('Unexpected gateway RPC in timestamp fixture')
  })
  // Only the transport/context boundary is injected; production modules and
  // the actual event dispatch, controller, stores, append and renders are real.
  const ctx = {
    composer: { setInput: vi.fn() },
    gateway: { gw: { request }, rpc },
    session: {
      STARTUP_RESUME_ID: '',
      colsRef: { current: 80 },
      newSession: vi.fn(),
      resetSession: vi.fn(),
      resumeById: vi.fn(async () => undefined),
      setCatalog: vi.fn()
    },
    submission: { submitLiteralRef: { current: vi.fn() }, submitRef: { current: vi.fn() } },
    system: { bellOnComplete: false, sys },
    transcript: { appendMessage, panel: vi.fn(), setHistoryItems },
    voice: { setProcessing: vi.fn(), setRecording: vi.fn(), setVoiceEnabled: vi.fn(), setVoiceTts: vi.fn() }
  } as unknown as GatewayEventHandlerContext
  const onEvent = createGatewayEventHandler(ctx)

  const publish = async (text: string) => {
    onEvent({ payload: { text }, session_id: SID, type: 'message.delta' })
    await expect.poll(() => getTurnState().streaming, { timeout: 2000 }).toBe(text)
  }

  return { appendMessage, ctx, history: () => history, onEvent, publish, request, rpc, setHistoryItems }
}

beforeEach(() => {
  turnController.fullReset()
  resetTurnState()
  resetUiState()
  resetOverlayState()
  // Keep the controller's batch timer and native Ink scheduling real.
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date('2026-10-14T12:59:55.000Z'))
  patchUiState({ sid: SID, streaming: true })
})

afterEach(() => {
  while (renderers.length) renderers.pop()!()
  turnController.fullReset()
  turnController.persistSpawnTree = undefined
  resetTurnState()
  resetUiState()
  resetOverlayState()
  vi.useRealTimers()
})

describe('gateway handler timestamp continuity', () => {
  it('normal completion appends the live timestamp across a minute boundary', async () => {
    const h = createHarness()
    const firstTime = Date.now() / 1000
    h.onEvent({ payload: {}, session_id: SID, type: 'message.start' })
    await h.publish('Hello')
    const live = mountLive()
    await expect.poll(live, { timeout: 2000 }).toContain('Hello')
    const liveLabel = lastLabel(live())
    expect(liveLabel).toBe(fmtMsgTimestamp(firstTime))

    vi.setSystemTime(new Date('2026-10-14T13:00:01.000Z'))
    h.onEvent({ payload: { text: 'Hello complete' }, session_id: SID, type: 'message.complete' })

    expect(h.appendMessage).toHaveBeenCalledTimes(1)
    expect(h.setHistoryItems).toHaveBeenCalledTimes(1)
    expect(h.history()).toHaveLength(1)
    expect(h.history()[0]?.text).toBe('Hello complete')
    expect(getTurnState().streaming).toBe('')
    expect(h.request).not.toHaveBeenCalled()
    expect(h.rpc).not.toHaveBeenCalled()
    const row = h.history()[0]!
    const settled = renderText(<MessageLine cols={80} msg={row} t={DEFAULT_THEME} timestamps />)
    await expect.poll(settled, { timeout: 2000 }).toContain('Hello complete')
    console.info(JSON.stringify({ case: 'normal-handler-append', createdAt: row.createdAt, firstTime, live: liveLabel, settled: lastLabel(settled()) }))
    expect.soft(row.createdAt).toBe(firstTime)
    expect.soft(lastLabel(settled())).toBe(liveLabel)
  })

  it('late interrupted completion replaces the real row and retains both burst times', async () => {
    const h = createHarness()
    const firstTime = Date.now() / 1000
    h.onEvent({ payload: {}, session_id: SID, type: 'message.start' })
    await h.publish('First burst')
    h.onEvent({ payload: { text: 'First burst' }, session_id: SID, type: 'message.interim' })

    vi.setSystemTime(new Date('2026-10-14T13:00:01.000Z'))
    const tailTime = Date.now() / 1000
    await h.publish('Unfinished tail')
    const live = mountLive()
    await expect.poll(live, { timeout: 2000 }).toContain('Unfinished tail')
    const liveLabel = lastLabel(live())
    expect(liveLabel).toBe(fmtMsgTimestamp(tailTime))

    vi.setSystemTime(new Date('2026-10-14T13:01:01.000Z'))
    // Ctrl+C is a local input action, not a gateway event. Use its production
    // cancellation seam, then drive the late completion through the handler.
    turnController.interruptTurn({ appendMessage: h.appendMessage, gw: h.ctx.gateway.gw, sid: SID, sys: h.ctx.system.sys })
    expect(h.history().map(msg => msg.text)).toEqual(['First burst', 'Unfinished tail\n\n*[interrupted]*'])
    const firstRow = h.history()[0]!
    const sealedTail = h.history()[1]!
    const appendsBefore = h.appendMessage.mock.calls.length
    const updatesBefore = h.setHistoryItems.mock.calls.length

    vi.setSystemTime(new Date('2026-10-14T13:02:01.000Z'))
    h.onEvent({ payload: { text: ' late ignored delta' }, session_id: SID, type: 'message.delta' })
    h.onEvent({ payload: { status: 'interrupted', text: 'Unfinished tail extended' }, session_id: SID, type: 'message.complete' })

    // Prove actual handler application before timestamp checks: the updater
    // runs, existing text changes, and no extra assistant row is appended.
    expect(h.setHistoryItems).toHaveBeenCalledTimes(updatesBefore + 1)
    expect(typeof h.setHistoryItems.mock.calls.at(-1)?.[0]).toBe('function')
    expect(h.appendMessage).toHaveBeenCalledTimes(appendsBefore)
    expect(h.history()).toHaveLength(2)
    expect(h.history()[0]).toBe(firstRow)
    const updatedTail = h.history()[1]!
    expect(updatedTail).not.toBe(sealedTail)
    expect(updatedTail).toEqual({ ...sealedTail, text: 'Unfinished tail extended\n\n*[interrupted]*' })
    expect(getTurnState().streaming).toBe('')
    expect(h.request).toHaveBeenCalledExactlyOnceWith('session.interrupt', { session_id: SID })
    expect(h.rpc).not.toHaveBeenCalled()

    const settled = renderText(<MessageLine cols={80} msg={updatedTail} t={DEFAULT_THEME} timestamps />)
    await expect.poll(settled, { timeout: 2000 }).toContain('Unfinished tail extended')
    console.info(JSON.stringify({ case: 'late-handler-replacement', firstCreatedAt: firstRow.createdAt, firstTime, createdAt: updatedTail.createdAt, tailTime, live: liveLabel, settled: lastLabel(settled()), replacementApplied: true }))
    expect.soft(firstRow.createdAt).toBe(firstTime)
    expect.soft(updatedTail.createdAt).toBe(tailTime)
    expect.soft(lastLabel(settled())).toBe(liveLabel)
  })
})
