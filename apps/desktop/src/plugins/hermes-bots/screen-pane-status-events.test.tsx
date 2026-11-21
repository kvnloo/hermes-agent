/**
 * The pane paints a cache of backend truth. A start or stop made outside this
 * window (CLI, gateway auto-start, another Desktop) reaches the renderer only
 * as a pushed `display.status` event — a stopped pane with no sibling portal
 * or hero mounted must pick it up itself or it stays "Stopped" forever.
 */

import { act, fireEvent, render, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { DisplayStatus } from './screen-connection'
import type * as ScreenConnection from './screen-connection'
import type { RosterRow } from './types'

vi.mock('@hermes/plugin-sdk', async () => {
  const { useStore } = await import('@nanostores/react')
  const { onGatewayEvent } = await import('../../contrib/events')

  return {
    Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
      <button {...props}>{children}</button>
    ),
    Codicon: () => null,
    GlyphSpinner: () => null,
    Tip: ({ children }: { children: ReactNode }) => <>{children}</>,
    EmptyState: () => null,
    useValue: useStore,
    host: { onEvent: onGatewayEvent }
  }
})
vi.mock('./routing', () => {
  const route = { connectionId: 'host-a', mode: 'remote', profile: 'ops', targetProfile: 'ops' }

  return { botConnectionRoute: () => route, resolveBotConnectionRoute: () => ({ status: 'resolved', route }) }
})
vi.mock('./data', () => ({ botSelectionKey: (bot: RosterRow) => bot.name }))
vi.mock('./i18n', () => ({
  useBots: () => ({
    screen: {
      title: 'Screen',
      unavailableTitle: 'Screen unavailable',
      notInstalledTitle: 'Screen packages missing',
      stoppedTitle: 'Stopped',
      stoppedBody: 'Body',
      start: 'Start',
      agentControls: 'Bot controls',
      takeOver: 'Take over',
      reconnect: 'Reconnect',
      streamLost: 'Stream lost'
    }
  })
}))
vi.mock('./screen-connection', async importActual => ({
  // Real predicate (`isEventForBotScreen`): the event must come from the bot's host.
  ...(await importActual<typeof ScreenConnection>()),
  displayRequest: vi.fn(),
  resolveScreenWsUrl: vi.fn(async () => 'ws://localhost/api/display/ws')
}))
vi.mock('@novnc/novnc', () => ({
  default: class {
    addEventListener() {}
    disconnect() {}
    focus() {}
  }
}))

// eslint-disable-next-line no-restricted-imports
import { emitGatewayEvent } from '../../contrib/events'

import { displayRequest } from './screen-connection'
import { BotScreenPane } from './screen-pane'
import { $screenState, setScreenStatus } from './screen-state'

const bot: RosterRow = { name: 'ops', sourceScoped: true, connectionId: 'host-a', connectionKind: 'remote' }

const stopped: DisplayStatus = {
  profile: 'ops',
  profile_key: '/home/hermes/.hermes',
  supported: true,
  installed: true,
  missing: [],
  running: false,
  pid: null,
  display: null,
  socket: null,
  geometry: '1440x900',
  install_command: null,
  lease: { holder: 'agent', viewer_id: null, viewer_hash: null, since: 1, reason: '', epoch: 0 }
}

const running: DisplayStatus = { ...stopped, running: true, pid: 42, display: ':20' }

beforeEach(() => {
  $screenState.set({})
  vi.mocked(displayRequest)
    .mockReset()
    .mockImplementation(async (_bot, method) =>
      method === 'display.observe' ? { ...running, ticket: 't', viewer_id: 'v1' } : stopped
    )
  vi.stubGlobal(
    'WebSocket',
    class {
      binaryType = ''
      addEventListener() {}
      close() {}
    }
  )
})

afterEach(() => vi.unstubAllGlobals())

it('a stopped pane learns of an external start from the pushed display.status event and attaches', async () => {
  const view = render(<BotScreenPane bot={bot} />)
  await waitFor(() => expect(view.getByText('Stopped')).toBeTruthy())

  // Another host's event about the same profile path is not ours.
  act(() => emitGatewayEvent({ type: 'display.status', connectionId: 'host-b', profile: 'ops', payload: running }))
  expect(view.getByText('Stopped')).toBeTruthy()

  act(() => emitGatewayEvent({ type: 'display.status', connectionId: 'host-a', profile: 'ops', payload: running }))
  await waitFor(() => expect(vi.mocked(displayRequest)).toHaveBeenCalledWith(bot, 'display.observe', expect.anything()))
  expect(view.queryByText('Stopped')).toBeNull()
  view.unmount()
})

it('shows the failed status RPC instead of stale package instructions and recovers on retry', async () => {
  // A cached status cannot overrule a failed fresh read of the gateway's truth.
  setScreenStatus(bot, { ...stopped, installed: false, missing: ['Xvnc'] })
  vi.mocked(displayRequest).mockRejectedValueOnce(new TypeError('host.requestProfile is not a function'))

  const view = render(<BotScreenPane bot={bot} />)
  await waitFor(() => expect(view.getByText('host.requestProfile is not a function')).toBeTruthy())
  expect(view.queryByText('Screen packages missing')).toBeNull()

  fireEvent.click(view.getByRole('button', { name: 'Reconnect' }))
  await waitFor(() => expect(view.getByText('Stopped')).toBeTruthy())
  expect(view.queryByText('host.requestProfile is not a function')).toBeNull()
  view.unmount()
})
