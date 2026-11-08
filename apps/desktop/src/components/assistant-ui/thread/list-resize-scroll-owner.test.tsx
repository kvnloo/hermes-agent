import { AssistantRuntimeProvider, type ThreadMessage, useExternalStoreRuntime } from '@assistant-ui/react'
import { act, render } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'

import { rescopeConnectionScopedStores } from '@/lib/connection-scoped'
import { setActiveProfile } from '@/store/profile'
import { saveThreadScrollPosition } from '@/store/thread-scroll'

import { stubThreadEnvironment, stubThreadViewportSize } from '../test-utils'
import { Thread } from '.'

stubThreadEnvironment()
stubThreadViewportSize()

const CLIENT_H = 600
let scrollHeight = 5000

Object.defineProperty(HTMLElement.prototype, 'scrollHeight', {
  configurable: true,
  get() { return scrollHeight }
})
Object.defineProperty(HTMLElement.prototype, 'clientHeight', {
  configurable: true,
  get() { return CLIENT_H }
})

beforeEach(() => {
  scrollHeight = 5000
  window.localStorage.clear()
  setActiveProfile('default')
  rescopeConnectionScopedStores(null)
})

function Harness({ sessionKey, isRunning = true }: { sessionKey: string; isRunning?: boolean }) {
  const createdAt = new Date('2026-08-01T00:00:00.000Z')
  const messages = [
    {
      id: 'u-' + sessionKey, role: 'user',
      content: [{ type: 'text', text: 'inspect config' }], attachments: [], createdAt,
      metadata: { custom: {} }
    } as ThreadMessage,
    {
      id: 'a-' + sessionKey, role: 'assistant',
      content: [{ type: 'text', text: 'checking config' }],
      status: { type: 'complete', reason: 'stop' }, createdAt,
      metadata: { unstable_state: null, unstable_annotations: [], unstable_data: [], steps: [], custom: {} }
    } as ThreadMessage
  ]
  const runtime = useExternalStoreRuntime<ThreadMessage>({ isRunning, messages, onNew: async () => {} })
  return <AssistantRuntimeProvider runtime={runtime}><Thread clampToComposer={false} sessionKey={sessionKey} /></AssistantRuntimeProvider>
}

function viewport(container: HTMLElement): HTMLElement {
  const result = container.querySelector<HTMLElement>('[data-slot="aui_thread-viewport"]')
  expect(result).toBeTruthy()
  return result!
}

async function settle(ticks = 10) {
  await act(async () => {
    for (let i = 0; i < ticks; i += 1) {
      await new Promise<void>(resolve => window.setTimeout(resolve, 0))
    }
  })
}

function contentResizes() {
  const previous = globalThis.ResizeObserver
  const observers = new Set<{ callback: ResizeObserverCallback; targets: Set<Element> }>()
  vi.stubGlobal('ResizeObserver', class {
    targets = new Set<Element>()
    constructor(public callback: ResizeObserverCallback) { observers.add(this) }
    observe(target: Element) { this.targets.add(target) }
    unobserve(target: Element) { this.targets.delete(target) }
    disconnect() { this.targets.clear(); observers.delete(this) }
  })

  return {
    fire: () => {
      for (const observer of observers) {
        const targets = [...observer.targets].filter(el => el.getAttribute('data-slot') === 'aui_thread-content')
        if (targets.length) {
          observer.callback(
            targets.map(target => ({ target, contentRect: { height: scrollHeight } })) as ResizeObserverEntry[],
            observer as unknown as ResizeObserver
          )
        }
      }
    },
    restore: () => vi.stubGlobal('ResizeObserver', previous)
  }
}

it('follows streamed growth when a late scroll arrives before the resize observer (#128468)', async () => {
  const resize = contentResizes()
  const { container, unmount } = render(<Harness sessionKey="stream" />)
  try {
    const el = viewport(container)
    await settle()
    expect(el.scrollTop).toBe(scrollHeight - CLIENT_H)
    const raf = vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation(() => 0)
    try {
      act(() => {
        scrollHeight += 120
        // A scroll queued by the prior pin must not consume the growth baseline.
        el.dispatchEvent(new Event('scroll'))
        resize.fire()
      })
      expect(el.scrollTop).toBe(scrollHeight - CLIENT_H)
    } finally {
      raf.mockRestore()
    }
  } finally {
    unmount()
    resize.restore()
  }
})

it('does not interpret a switched session restored offset as streaming growth (#128468)', async () => {
  saveThreadScrollPosition('b', { fromBottom: 800, kind: 'offset' })
  const resize = contentResizes()
  const { container, rerender, unmount } = render(<Harness sessionKey="a" isRunning={false} />)
  try {
    await settle()
    scrollHeight = 6200
    rerender(<Harness sessionKey="b" isRunning={false} />)
    await settle()
    const el = viewport(container)
    const readingTop = scrollHeight - CLIENT_H - 800
    expect(el.scrollTop).toBe(readingTop)
    rerender(<Harness sessionKey="b" isRunning />)
    await settle(2)
    act(() => {
      // A queued scroll may run after the new transcript commits.
      el.dispatchEvent(new Event('scroll'))
      resize.fire()
    })
    expect(el.scrollTop).toBe(readingTop)
  } finally {
    unmount()
    resize.restore()
  }
})
