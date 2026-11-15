import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import { createElement } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { InputHandlerContext } from '../app/interfaces.js'
import { getOverlayState, patchOverlayState, resetOverlayState } from '../app/overlayStore.js'
import { rememberServerRequest, resetServerRequestsForTests } from '../app/serverRequestStore.js'
import { patchUiState, resetUiState } from '../app/uiStore.js'
import {
  applyVoiceRecordResponse,
  composerHasDraft,
  dismissSensitivePrompt,
  handleIdleHotkeyExit,
  isPlainCtrlC,
  resolveCtrlCComposerAction,
  resolveDoubleEscAction,
  shouldDetachEditedHistoryInput,
  shouldFallThroughForScroll,
  useInputHandlers
} from '../app/useInputHandlers.js'
import { GatewayClient } from '../gatewayClient.js'
import { DEFAULT_VOICE_RECORD_KEY } from '../lib/platform.js'

describe('Ctrl+C terminal input dispatch', () => {
  let unmount = () => {}

  beforeEach(() => {
    resetUiState()
    resetOverlayState()
    resetServerRequestsForTests()
    patchUiState({ busy: false, sid: 'owner' })
  })

  afterEach(() => {
    unmount()
    resetUiState()
    resetOverlayState()
    resetServerRequestsForTests()
  })

  function mount(input = '') {
    const stdin = Object.assign(new PassThrough(), {
      isRaw: false,
      isTTY: true,
      ref: vi.fn(),
      setRawMode: vi.fn(),
      unref: vi.fn()
    })

    const stdout = Object.assign(new PassThrough(), { columns: 80, isTTY: false, rows: 24 })

    const ctx: InputHandlerContext = {
      actions: {
        appendMessage: vi.fn(),
        cancelClarify: vi.fn(),
        countPrompts: () => 0,
        die: vi.fn(),
        dispatchSubmission: vi.fn(),
        guardBusySessionSwitch: () => false,
        newSession: vi.fn(),
        openBacktrack: vi.fn(),
        sys: vi.fn()
      },
      composer: {
        actions: {
          appendPaste: vi.fn(async () => {}),
          appendText: vi.fn(),
          attachClipboardImage: vi.fn(),
          attachImagePath: vi.fn(),
          attachImagePaths: vi.fn(async () => {}),
          clearIn: vi.fn(() => {
            ctx.composer.state.input = ''
          }),
          collapsePaste: () => '',
          dequeue: () => undefined,
          enqueue: vi.fn(),
          handleTextPaste: () => null,
          openEditor: vi.fn(async () => {}),
          prependQueue: vi.fn(),
          pushHistory: vi.fn(),
          queueDraft: () => '',
          removeQueue: vi.fn(),
          restoreDraft: () => false,
          setCompIdx: vi.fn(),
          setComposerTokens: vi.fn(),
          setHistoryIdx: vi.fn(),
          setInput: vi.fn(),
          setInputBuf: vi.fn(),
          setQueueEdit: vi.fn(),
          syncTokens: vi.fn(),
          takeQueue: () => undefined,
          togglePaste: () => false
        },
        refs: {
          historyDraftRef: { current: '' },
          historyRef: { current: [] },
          queueEditRef: { current: null },
          queueRef: { current: [] },
          submitRef: { current: vi.fn() },
          tokensRef: { current: [] }
        },
        state: {
          compIdx: 0,
          compReplace: 0,
          completions: [],
          historyIdx: null,
          input,
          inputBuf: [],
          pasteExpanded: false,
          queueEditIdx: null,
          queuedDisplay: [],
          tokens: []
        }
      },
      gateway: { gw: new GatewayClient(), rpc: async () => null },
      terminal: {
        hasSelection: false,
        scrollRef: { current: null },
        scrollWithSelection: vi.fn(),
        selection: {
          captureScrolledRows: vi.fn(),
          clearSelection: vi.fn(),
          copySelection: async () => '',
          copySelectionNoClear: async () => '',
          getState: () => null,
          shiftAnchor: vi.fn(),
          shiftSelection: vi.fn(),
          version: () => 0
        }
      },
      voice: {
        enabled: false,
        recording: false,
        recordKey: DEFAULT_VOICE_RECORD_KEY,
        setProcessing: vi.fn(),
        setRecording: vi.fn(),
        setVoiceEnabled: vi.fn(),
        setVoiceTts: vi.fn()
      },
      wheelStep: 3
    }

    function Harness() {
      useInputHandlers(ctx)

      return null
    }

    const instance = renderSync(createElement(Harness), {
      exitOnCtrlC: false,
      patchConsole: false,
      // Ink types require TTY streams; these in-memory streams implement the input/output contract.
      stdin: stdin as unknown as NodeJS.ReadStream,
      stdout: stdout as unknown as NodeJS.WriteStream
    })

    unmount = () => instance.unmount()

    const send = async (raw: string) => {
      await new Promise(resolve => setImmediate(resolve))
      stdin.write(raw)
      await new Promise(resolve => setTimeout(resolve, 70))
    }

    return { ctx, send }
  }

  describe.each([
    { name: 'Ctrl+C', plain: true, raw: '\x03' },
    { name: 'uppercase Ctrl+C', plain: true, raw: '\x1b[67;5u' },
    { name: 'Ctrl+Alt+C', plain: false, raw: '\x1b[99;7u' },
    { name: 'Ctrl+Shift+C', plain: false, raw: '\x1b[99;6u' },
    { name: 'Ctrl+Super+C', plain: false, raw: '\x1b[99;13u' }
  ])('$name', ({ plain, raw }) => {
    it('only clears an unsent draft for plain Ctrl+C', async () => {
      const { ctx, send } = mount('unsent draft')

      await send(raw)

      expect(ctx.composer.state.input).toBe(plain ? '' : 'unsent draft')
      expect(ctx.actions.die).not.toHaveBeenCalled()
    })

    it('only closes the session picker for plain Ctrl+C', async () => {
      patchOverlayState({ sessions: true })
      const { send } = mount()

      await send(raw)

      expect(getOverlayState().sessions).toBe(!plain)
    })

    it('only closes the pager for plain Ctrl+C', async () => {
      const pager = { lines: ['keep this visible'], offset: 0 }
      patchOverlayState({ pager })
      const { send } = mount()

      await send(raw)

      expect(getOverlayState().pager).toEqual(plain ? null : pager)
    })

    it('only denies an approval for plain Ctrl+C', async () => {
      const approval = { command: 'echo test', description: 'test approval', requestId: 'approval-ctrl-c' }
      const respond = vi.fn()
      rememberServerRequest({ fail: vi.fn(), id: approval.requestId, method: 'approval', params: {}, respond })
      patchOverlayState({ approval })
      const { send } = mount()

      await send(raw)

      expect(getOverlayState().approval).toEqual(plain ? null : approval)
      expect(respond).toHaveBeenCalledTimes(plain ? 1 : 0)

      if (plain) {
        expect(respond).toHaveBeenCalledWith({ choice: 'deny' })
      }
    })

    it('only dismisses a sensitive prompt for plain Ctrl+C', async () => {
      const sudo = { requestId: 'sudo-ctrl-c' }
      const respond = vi.fn()
      rememberServerRequest({ fail: vi.fn(), id: sudo.requestId, method: 'sudo', params: {}, respond })
      patchOverlayState({ sudo })
      const { send } = mount()

      await send(raw)

      expect(getOverlayState().sudo).toEqual(plain ? null : sudo)
      expect(respond).toHaveBeenCalledTimes(plain ? 1 : 0)

      if (plain) {
        expect(respond).toHaveBeenCalledWith({ value: '' })
      }
    })
  })
})

const baseKey = {
  downArrow: false,
  pageDown: false,
  pageUp: false,
  shift: false,
  upArrow: false,
  wheelDown: false,
  wheelUp: false
}

describe('shouldFallThroughForScroll — keep transcript scrolling alive during prompt overlays', () => {
  it('falls through for wheel scrolls', () => {
    expect(shouldFallThroughForScroll({ ...baseKey, wheelUp: true })).toBe(true)
    expect(shouldFallThroughForScroll({ ...baseKey, wheelDown: true })).toBe(true)
  })

  it('falls through for PageUp / PageDown', () => {
    expect(shouldFallThroughForScroll({ ...baseKey, pageUp: true })).toBe(true)
    expect(shouldFallThroughForScroll({ ...baseKey, pageDown: true })).toBe(true)
  })

  it('falls through for Shift+ArrowUp / Shift+ArrowDown', () => {
    expect(shouldFallThroughForScroll({ ...baseKey, shift: true, upArrow: true })).toBe(true)
    expect(shouldFallThroughForScroll({ ...baseKey, shift: true, downArrow: true })).toBe(true)
  })

  it('does NOT fall through for plain arrows — those drive in-prompt selection', () => {
    expect(shouldFallThroughForScroll({ ...baseKey, upArrow: true })).toBe(false)
    expect(shouldFallThroughForScroll({ ...baseKey, downArrow: true })).toBe(false)
  })

  it('does NOT fall through for plain Shift — without an arrow it is a no-op', () => {
    expect(shouldFallThroughForScroll({ ...baseKey, shift: true })).toBe(false)
  })

  it('does NOT fall through for unrelated state (no scroll keys held)', () => {
    expect(shouldFallThroughForScroll(baseKey)).toBe(false)
  })
})

describe('composerHasDraft — Ctrl+D exits only from an empty composer (#116443)', () => {
  it('is false for an empty composer and true for text, multi-line buffer or attachments', () => {
    expect(composerHasDraft({ input: '', inputBuf: [], tokens: [] })).toBe(false)
    expect(composerHasDraft({ input: 'hi', inputBuf: [], tokens: [] })).toBe(true)
    expect(composerHasDraft({ input: '', inputBuf: ['line 1'], tokens: [] })).toBe(true)
    expect(composerHasDraft({ input: '', inputBuf: [], tokens: [{ kind: 'image' }] })).toBe(true)
  })
})

describe('shouldDetachEditedHistoryInput', () => {
  const history = ['older message', 'line one\nline two']

  it('detaches a recalled entry as soon as the user edits it', () => {
    expect(shouldDetachEditedHistoryInput(1, history, 'line one edited\nline two')).toBe(true)
  })

  it('keeps unchanged recalled entries in history navigation', () => {
    expect(shouldDetachEditedHistoryInput(1, history, 'line one\nline two')).toBe(false)
  })

  it('does not detach an ordinary current draft', () => {
    expect(shouldDetachEditedHistoryInput(null, history, 'new draft')).toBe(false)
  })
})

describe('resolveCtrlCComposerAction — draft wins over interrupt', () => {
  it('clears a non-empty composer even while the agent is streaming', () => {
    expect(resolveCtrlCComposerAction({ busy: true, hasDraft: true, hasSession: true })).toBe('clear')
  })

  it('interrupts a running turn when the composer is empty', () => {
    expect(resolveCtrlCComposerAction({ busy: true, hasDraft: false, hasSession: true })).toBe('interrupt')
  })

  it('clears an idle composer instead of exiting', () => {
    expect(resolveCtrlCComposerAction({ busy: false, hasDraft: true, hasSession: true })).toBe('clear')
  })

  it('exits when idle with an empty composer', () => {
    expect(resolveCtrlCComposerAction({ busy: false, hasDraft: false, hasSession: true })).toBe('exit')
  })

  it('does not interrupt a busy session that has no sid yet', () => {
    expect(resolveCtrlCComposerAction({ busy: true, hasDraft: false, hasSession: false })).toBe('exit')
  })
})

describe('plain Ctrl+C — modified chords leave drafts and overlays intact', () => {
  const controlOnly = { ctrl: true, meta: false, shift: false, super: false }

  it('matches plain Ctrl+C regardless of letter case, not unrelated keys', () => {
    expect(isPlainCtrlC(controlOnly, 'c')).toBe(true)
    expect(isPlainCtrlC(controlOnly, 'C')).toBe(true)
    expect(isPlainCtrlC(controlOnly, 'x')).toBe(false)
    expect(isPlainCtrlC({ ...controlOnly, ctrl: false }, 'c')).toBe(false)
  })

  it.each([
    { name: 'Ctrl+Alt+C', modifiers: { meta: true } },
    { name: 'Ctrl+Shift+C', modifiers: { shift: true } },
    { name: 'Ctrl+Super+C', modifiers: { super: true } }
  ])('$name is not the TUI cancel/clear/interrupt command', ({ modifiers }) => {
    expect(isPlainCtrlC({ ...controlOnly, ...modifiers }, 'c')).toBe(false)
    expect(isPlainCtrlC({ ...controlOnly, ...modifiers }, 'C')).toBe(false)
  })
})

describe('resolveDoubleEscAction — double-Esc interrupts only a busy, draft-free turn (#62478)', () => {
  it('interrupts the running turn when the composer is empty', () => {
    expect(resolveDoubleEscAction({ busy: true, hasDraft: false, hasSession: true })).toBe('interrupt')
  })

  it('clears a draft instead of interrupting, even mid-stream', () => {
    expect(resolveDoubleEscAction({ busy: true, hasDraft: true, hasSession: true })).toBe('clear')
  })

  it('does nothing while idle with an empty composer (single-Esc conventions unchanged)', () => {
    expect(resolveDoubleEscAction({ busy: false, hasDraft: false, hasSession: true })).toBe('none')
  })

  it('does not interrupt a busy session that has no sid yet', () => {
    expect(resolveDoubleEscAction({ busy: true, hasDraft: false, hasSession: false })).toBe('none')
  })

  it('keeps clearing an idle draft (existing discard convention)', () => {
    expect(resolveDoubleEscAction({ busy: false, hasDraft: true, hasSession: true })).toBe('clear')
  })
})

describe('handleIdleHotkeyExit', () => {
  it('exits in normal terminals', () => {
    const actions = { die: vi.fn(), sys: vi.fn() }

    handleIdleHotkeyExit(actions, false)

    expect(actions.die).toHaveBeenCalledTimes(1)
    expect(actions.sys).not.toHaveBeenCalled()
  })

  it('asks the dashboard for a fresh chat instead of leaving a ghost session', () => {
    const actions = { die: vi.fn(), sys: vi.fn() }
    const requestDashboardNewSession = vi.fn()

    handleIdleHotkeyExit(actions, true, requestDashboardNewSession)

    expect(actions.die).not.toHaveBeenCalled()
    expect(requestDashboardNewSession).toHaveBeenCalledTimes(1)
    expect(actions.sys).toHaveBeenCalled()
  })
})

describe('applyVoiceRecordResponse', () => {
  it('reverts optimistic REC state when the gateway reports voice busy', () => {
    const setProcessing = vi.fn()
    const setRecording = vi.fn()
    const sys = vi.fn()

    applyVoiceRecordResponse({ status: 'busy' }, true, { setProcessing, setRecording }, sys)

    expect(setRecording).toHaveBeenCalledWith(false)
    expect(setProcessing).toHaveBeenCalledWith(true)
    expect(sys).toHaveBeenCalled()
  })

  it('keeps optimistic REC state for successful recording starts', () => {
    const setProcessing = vi.fn()
    const setRecording = vi.fn()

    applyVoiceRecordResponse({ status: 'recording' }, true, { setProcessing, setRecording }, vi.fn())

    expect(setRecording).not.toHaveBeenCalled()
    expect(setProcessing).not.toHaveBeenCalled()
  })

  it('reverts optimistic REC state when the gateway returns null', () => {
    const setProcessing = vi.fn()
    const setRecording = vi.fn()

    applyVoiceRecordResponse(null, true, { setProcessing, setRecording }, vi.fn())

    expect(setRecording).toHaveBeenCalledWith(false)
    expect(setProcessing).toHaveBeenCalledWith(false)
  })
})

describe('dismissSensitivePrompt', () => {
  const openRequest = (id: string, method: string) => {
    const respond = vi.fn()

    rememberServerRequest({ fail: vi.fn(), id, method, params: {}, respond })

    return respond
  }

  it('clears a sudo overlay and answers the server request with an empty value', () => {
    resetOverlayState()
    resetServerRequestsForTests()
    patchOverlayState({ sudo: { requestId: 'srq-sudo' } })
    const respond = openRequest('srq-sudo', 'sudo')
    const sys = vi.fn()

    dismissSensitivePrompt(getOverlayState(), vi.fn(), sys)

    expect(getOverlayState().sudo).toBeNull()
    expect(sys).toHaveBeenCalled()
    expect(respond).toHaveBeenCalledWith({ value: '' })
  })

  it('clears a secret overlay even when its request already expired (nothing left to answer)', () => {
    resetOverlayState()
    resetServerRequestsForTests()
    patchOverlayState({ secret: { envVar: 'API_KEY', prompt: 'Enter API key', requestId: 'srq-gone' } })
    const sys = vi.fn()

    dismissSensitivePrompt(getOverlayState(), vi.fn(), sys)

    expect(getOverlayState().secret).toBeNull()
    expect(sys).toHaveBeenCalled()
  })

  it('declines a vault save-login overlay with an empty value so the blocked wait resolves', () => {
    resetOverlayState()
    resetServerRequestsForTests()
    patchOverlayState({ vaultSaveLogin: { origin: 'https://example.com', requestId: 'save-1', site: 'example.com' } })
    const respond = openRequest('save-1', 'vault.save_login')
    const sys = vi.fn()

    dismissSensitivePrompt(getOverlayState(), vi.fn(), sys)

    expect(getOverlayState().vaultSaveLogin).toBeNull()
    expect(sys).toHaveBeenCalledWith('login for example.com not saved')
    expect(respond).toHaveBeenCalledWith({ value: '' })
  })

  it('skips a vault verification-code overlay with an empty value', () => {
    resetOverlayState()
    resetServerRequestsForTests()
    patchOverlayState({ vaultCode: { hint: '', requestId: 'code-1', site: 'github.com' } })
    const respond = openRequest('code-1', 'vault.code')
    const sys = vi.fn()

    dismissSensitivePrompt(getOverlayState(), vi.fn(), sys)

    expect(getOverlayState().vaultCode).toBeNull()
    expect(sys).toHaveBeenCalledWith('verification code for github.com skipped')
    expect(respond).toHaveBeenCalledWith({ value: '' })
  })
})
