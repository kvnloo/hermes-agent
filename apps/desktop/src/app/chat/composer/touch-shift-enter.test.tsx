// @vitest-environment jsdom
import { AssistantRuntimeProvider, useExternalStoreRuntime } from '@assistant-ui/react'
import type { ThreadMessageLike } from '@assistant-ui/react'
import { act, cleanup, fireEvent, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'
import { $touchPointer } from '@/lib/touch-interaction'
import { mainComposerScope } from '@/store/composer'

import { ChatBar } from './index'
import { composerPlainText, RICH_INPUT_SLOT } from './rich-editor'
import { placeCaretAtEnd } from './test-utils'
import type { ChatBarState } from './types'

const state: ChatBarState = {
  model: { canSwitch: false, model: '', provider: '' },
  tools: { enabled: false, label: '' },
  voice: { enabled: false, active: false }
}

function Harness({ onSubmit }: { onSubmit: (text: string) => Promise<boolean> }) {
  const runtime = useExternalStoreRuntime({
    convertMessage: (message: ThreadMessageLike) => message,
    isRunning: false,
    messages: [] as ThreadMessageLike[],
    onNew: async () => {}
  })

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <MemoryRouter>
        <I18nProvider configClient={null} initialLocale="en">
          <ChatBar busy={false} disabled={false} gateway={null} onCancel={vi.fn()} onSubmit={onSubmit} state={state} />
        </I18nProvider>
      </MemoryRouter>
    </AssistantRuntimeProvider>
  )
}

afterEach(() => {
  cleanup()
  mainComposerScope.clear()
  $touchPointer.set(false)
  delete document.documentElement.dataset.hermesDesktopHost
  window.getSelection()?.removeAllRanges()
  vi.unstubAllGlobals()
})

it('touch Shift+Return inserts a draft newline instead of submitting (#156562)', async () => {
  document.documentElement.dataset.hermesDesktopHost = 'browser'
  $touchPointer.set(true)
  vi.stubGlobal('requestAnimationFrame', () => 0)
  const onSubmit = vi.fn(async (_text: string) => true)
  const { container } = render(<Harness onSubmit={onSubmit} />)
  const editor = container.querySelector<HTMLElement>(`[data-slot="${RICH_INPUT_SLOT}"]`)!

  // jsdom does not make contenteditable focusable like WebKit/Chromium do.
  editor.tabIndex = 0
  let keydown: KeyboardEvent | undefined

  await act(async () => {
    editor.focus()
    editor.textContent = 'first line'
    fireEvent.input(editor)
    placeCaretAtEnd(editor)
    editor.addEventListener('keydown', event => { keydown = event }, { capture: true, once: true })
    fireEvent.keyDown(editor, { key: 'Enter', shiftKey: true })
  })

  expect(keydown?.defaultPrevented).toBe(true)
  expect(composerPlainText(editor)).toBe('first line\n')
  expect(onSubmit).not.toHaveBeenCalled()
})
