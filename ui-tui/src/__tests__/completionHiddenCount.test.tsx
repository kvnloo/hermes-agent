import { PassThrough } from 'node:stream'

import { Box, forceRedraw, renderSync, Text } from '@hermes/ink'
import { stripAnsi } from '@hermes/shared/ansi'
import React from 'react'
import { describe, expect, it, vi } from 'vitest'

import { GatewayProvider } from '../app/gatewayContext.js'
import type { CompletionItem, GatewayServices } from '../app/interfaces.js'
import { resetOverlayState } from '../app/overlayStore.js'
import { resetUiState } from '../app/uiStore.js'
import { CompletionMenuPanel, FloatingOverlays } from '../components/appOverlays.js'
import { DEFAULT_THEME } from '../theme.js'

const completion = (i: number): CompletionItem => ({
  display: `/cmd${i.toString().padStart(2, '0')}`,
  meta: `description ${i}`,
  text: `/cmd${i}`
})

const renderPanel = async (completions: CompletionItem[], compIdx = 0) => {
  const stdout = new PassThrough()
  Object.assign(stdout, { columns: 80, isTTY: false, rows: 30 })
  let output = ''
  stdout.on('data', chunk => {
    output += String(chunk)
  })

  const instance = renderSync(
    <CompletionMenuPanel cols={80} compIdx={compIdx} completions={completions} t={DEFAULT_THEME} />,
    {
      patchConsole: false,
      stdin: new PassThrough() as unknown as NodeJS.ReadStream,
      stdout: stdout as unknown as NodeJS.WriteStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream
    }
  )

  // Ink throttles the first paint; give the frame a turn to land before
  // reading the captured output.
  await new Promise(resolve => setTimeout(resolve, 100))
  instance.unmount()

  return stripAnsi(output)
}

describe('completion menu hidden-count footer', () => {
  it('shows how many completions the window truncated', async () => {
    const output = await renderPanel(Array.from({ length: 20 }, (_, i) => completion(i)))

    expect(output).toContain('/cmd00')
    expect(output).toContain('…and 4 more')
  })

  it('counts hidden items above the viewport too, not just the tail', async () => {
    // compIdx deep in the list scrolls the window; items hidden above the
    // window still count toward the footer total.
    const output = await renderPanel(
      Array.from({ length: 20 }, (_, i) => completion(i)),
      15
    )

    expect(output).toContain('…and 4 more')
  })

  it('shows no footer when the list fits inside the window', async () => {
    const output = await renderPanel(Array.from({ length: 16 }, (_, i) => completion(i)))

    expect(output).toContain('/cmd15')
    expect(output).not.toContain('…and')
  })

  it('shows no footer for a short list', async () => {
    const output = await renderPanel(Array.from({ length: 5 }, (_, i) => completion(i)))

    expect(output).toContain('/cmd04')
    expect(output).not.toContain('…and')
  })
})

it.each([false, true])(
  'keeps the live completion footer paired with only the visible rows (nativeMode=%s)',
  async nativeMode => {
    resetOverlayState()
    resetUiState()
    const stdout = Object.assign(new PassThrough(), { columns: 80, isTTY: true, rows: 40 })
    const stdin = Object.assign(new PassThrough(), { isTTY: false })
    let output = ''
    stdout.on('data', chunk => {
      output += String(chunk)
    })

    const request = vi.fn(() => {
      throw new Error('Completion rendering must not call the gateway')
    })

    const gateway = { gw: { request }, rpc: {} } as unknown as GatewayServices
    const control = vi.fn()

    const renderOverlay = (items: CompletionItem[], compIdx: number) => (
      <GatewayProvider value={gateway}>
        <Box flexDirection="column" height={30} justifyContent="flex-end">
          <Box flexDirection="column" position="relative">
            <FloatingOverlays
              cols={80}
              compIdx={compIdx}
              completions={items}
              nativeMode={nativeMode}
              onActiveSessionClose={async () => null}
              onActiveSessionSelect={control}
              onModelSelect={control}
              onNewLiveSession={control}
              onNewPromptSession={control}
              onResumeSelect={control}
              pagerPageSize={16}
            />
            <Text>COMPOSER_CONTROL</Text>
          </Box>
        </Box>
      </GatewayProvider>
    )

    const instance = renderSync(renderOverlay([], 0), {
      patchConsole: false,
      stdin: stdin as unknown as NodeJS.ReadStream,
      stdout: stdout as unknown as NodeJS.WriteStream,
      stderr: new PassThrough() as unknown as NodeJS.WriteStream
    })

    try {
      for (const [length, selected, firstVisible] of [
        [20, 0, 0],
        [20, 15, 4],
        [16, 15, 0],
        [5, 4, 0],
        [0, 0, 0],
        [21, 20, 5]
      ]) {
        const items = Array.from({ length }, (_, i) => completion(i))
        const visible = items.slice(firstVisible, firstVisible + 16).map(item => item.display)
        instance.rerender(renderOverlay(items, selected))
        await vi.waitFor(() => {
          // Ask the existing renderer for a fresh full frame so old terminal
          // writes cannot satisfy an assertion after the list shrinks.
          output = ''
          expect(forceRedraw(stdout as unknown as NodeJS.WriteStream)).toBe(true)
          const frame = stripAnsi(output)
          expect(frame.match(/COMPOSER_CONTROL/g)).toHaveLength(1)
          expect(frame.match(/\/cmd\d{2}/g) ?? []).toEqual(visible)
          const omitted = items.length - visible.length
          // TTY spaces may be cursor-advance escapes, which stripAnsi removes.
          const footerCounts = [...frame.matchAll(/…and\s*(\d+)\s*more/g)].map(match => match[1])
          expect(footerCounts).toEqual(omitted ? [String(omitted)] : [])

          if (items.length) {
            expect(visible).toContain(items[selected].display)
          }
        })
      }

      expect(request).not.toHaveBeenCalled()
      expect(control).not.toHaveBeenCalled()
    } finally {
      instance.unmount()
      instance.cleanup()
      resetOverlayState()
      resetUiState()
    }
  }
)
