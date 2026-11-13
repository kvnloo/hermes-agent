// @vitest-environment jsdom
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { atom } from 'nanostores'
import { expect, it, vi } from 'vitest'

import { useHermesConfigRecord } from '@/app/hooks/use-config-record'

import { TileChat } from './session-tile'
import type { SessionView } from './session-view'

vi.mock('@/app/hooks/use-config-record', () => ({
  useHermesConfigRecord: vi.fn(() => ({ data: { voice: { max_recording_seconds: 600 } } }))
}))

vi.mock('@/app/gateway/hooks/use-gateway-request', () => ({
  useGatewayRequest: () => ({ gateway: null, requestGateway: vi.fn() })
}))

vi.mock('@/app/session/hooks/use-model-controls', () => ({
  useModelControls: () => ({ selectModel: vi.fn() })
}))

vi.mock('./session-tile-owner', () => ({
  tileOwnerRoute: () => ({ connectionId: 'tile-connection', profile: 'desktop-profile', targetProfile: 'recording-profile' })
}))

vi.mock('./session-tile-actions', () => ({
  useSessionTileActions: () => ({})
}))

vi.mock('./hooks/use-composer-actions', () => ({
  useComposerActions: () => ({
    addContextRefAttachment: vi.fn(),
    attachDroppedItems: vi.fn(),
    attachImageBlob: vi.fn(),
    attachPastedText: vi.fn(),
    pasteClipboardImage: vi.fn(),
    pickContextPaths: vi.fn(),
    pickImages: vi.fn(),
    removeAttachment: vi.fn()
  })
}))

vi.mock('.', () => ({
  ChatView: ({ maxVoiceRecordingSeconds }: { maxVoiceRecordingSeconds?: number }) => (
    <output data-testid="tile-recording-limit">{maxVoiceRecordingSeconds}</output>
  )
}))

it('uses the owning profile\'s configured 600-second dictation cap in a session tile', () => {
  const view = { $cwd: atom(''), $messages: atom([]) } as unknown as SessionView
  const queryClient = new QueryClient()

  render(
    <QueryClientProvider client={queryClient}>
      <TileChat runtimeId="runtime-1" storedSessionId="session-1" view={view} />
    </QueryClientProvider>
  )

  expect(useHermesConfigRecord).toHaveBeenCalledWith({
    connectionId: 'tile-connection',
    profile: 'recording-profile'
  })
  expect(screen.getByTestId('tile-recording-limit').textContent).toBe('600')
})
