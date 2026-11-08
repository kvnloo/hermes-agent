import type { BrowserWindow } from 'electron'
import { expect, test, vi } from 'vitest'

const handlers = vi.hoisted(
  () => new Map<string, (event: { sender: unknown }, pluginId?: string) => Promise<{ ok: boolean }>>()
)

vi.mock('electron', () => ({
  ipcMain: {
    handle: (channel: string, handler: (event: { sender: unknown }, pluginId?: string) => Promise<{ ok: boolean }>) => {
      handlers.set(channel, handler)
    },
    on: () => {}
  }
}))

import { registerPluginOverlayIpc } from './plugin-overlay-ipc'

test('a plugin-scoped close cannot dismiss another plugin\'s overlay', async () => {
  const mainSender = {}
  const overlaySender = {}
  const closeOverlay = vi.fn()

  registerPluginOverlayIpc({
    getMainWindow: () => ({ isDestroyed: () => false, webContents: mainSender }) as unknown as BrowserWindow,
    getOverlayWindow: () => ({ isDestroyed: () => false, webContents: overlaySender }) as unknown as BrowserWindow,
    getOverlayPluginId: () => 'owner-plugin',
    getOverlayMode: () => 'card',
    openOverlay: () => null,
    closeOverlay,
    setOverlayMode: () => {},
    snapBounds: bounds => bounds,
    setShape: () => {},
    persistBounds: () => {},
    readBounds: () => null
  })

  const close = handlers.get('hermes:plugin-overlay:close')
  expect(close).toBeDefined()
  if (!close) throw new Error('plugin overlay close handler not registered')

  await expect(close({ sender: mainSender }, 'other-plugin')).resolves.toEqual({ ok: false })
  await expect(close({ sender: mainSender })).resolves.toEqual({ ok: false })
  expect(closeOverlay).not.toHaveBeenCalled()

  await expect(close({ sender: mainSender }, 'owner-plugin')).resolves.toEqual({ ok: true })
  await expect(close({ sender: overlaySender })).resolves.toEqual({ ok: true })
  expect(closeOverlay).toHaveBeenCalledTimes(2)
})
