import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { $activeGatewayProfile } from '@/store/profile'
import {
  $currentModel,
  $currentProvider,
  markComposerSelectionManual,
  setConnection,
  setCurrentModel,
  setCurrentModelSource,
  setCurrentProvider
} from '@/store/session'

import { desktopSessionCreateParams } from './session-create-request'
import { applyRuntimeInfo } from './utils'

vi.mock('@/store/profile', async original => ({
  ...(await original<Record<string, unknown>>()),
  ensureGatewayAgent: vi.fn(async () => undefined),
  ensureGatewayProfile: vi.fn(async () => undefined)
}))

beforeEach(() => {
  window.localStorage.clear()
  $activeGatewayProfile.set('default')
  setConnection({
    baseUrl: 'http://localhost:7070',
    isFullscreen: false,
    logs: [],
    mode: 'local',
    nativeOverlayWidth: 0,
    token: '',
    windowButtonPosition: null,
    wsUrl: 'ws://localhost:7070'
  })
  setCurrentModel('recommended')
  setCurrentProvider('custom:litellm-local')
  markComposerSelectionManual()
})

afterEach(() => {
  setCurrentModel('')
  setCurrentProvider('')
  setCurrentModelSource('')
  setConnection(null)
  window.localStorage.clear()
})

describe('named custom route survives a resolved runtime echo', () => {
  it('launches the next manual chat with the saved route, not the billing class or fallback model', async () => {
    // Real foreground runtime publisher: PR #148274 fixes persistence, but it
    // still repaints the same live atoms the old session.create consumer reads.
    applyRuntimeInfo({ model: 'fallback-model', provider: 'custom' })
    expect($currentModel.get()).toBe('fallback-model')
    expect($currentProvider.get()).toBe('custom')
    expect(window.localStorage.getItem('hermes.desktop.composer.model')).toBe('recommended')
    expect(window.localStorage.getItem('hermes.desktop.composer.provider')).toBe('custom:litellm-local')

    // The named entry is the only routable identity for this saved manual pick.
    await expect(desktopSessionCreateParams('')).resolves.toMatchObject({
      model: 'recommended',
      provider: 'custom:litellm-local'
    })
  })
})
