import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, expect, it } from 'vitest'

import type { HermesConnection } from '@/global'
import { $activeGatewayProfile } from '@/store/profile'
import { $connection } from '@/store/session'

import { ThemeProvider, useTheme } from './context'

let theme: ReturnType<typeof useTheme>

function Probe() {
  theme = useTheme()

  return null
}

function connect(connectionId: string) {
  const connection: HermesConnection = {
    connectionId,
    profile: 'default',
    mode: connectionId === 'local' ? 'local' : 'remote',
    baseUrl: 'http://127.0.0.1:10001',
    wsUrl: 'ws://127.0.0.1:10001/ws',
    token: '',
    logs: [],
    isFullscreen: false,
    nativeOverlayWidth: 0,
    windowButtonPosition: null
  }

  act(() => {
    $activeGatewayProfile.set('default')
    $connection.set(connection)
  })
}

beforeEach(() => {
  window.localStorage.clear()
  $connection.set(null)
  $activeGatewayProfile.set('default')
})

afterEach(() => {
  cleanup()
  $connection.set(null)
  $activeGatewayProfile.set('default')
})

it('keeps independent appearance for the same default profile on two gateways', () => {
  connect('local')
  render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>
  )

  act(() => {
    theme.setTheme('catppuccin')
    theme.setMode('dark')
  })

  connect('remote-a')
  act(() => {
    theme.setTheme('ember')
    theme.setMode('light')
  })

  connect('local')
  expect([theme.themeName, theme.mode]).toEqual(['catppuccin', 'dark'])

  connect('remote-a')
  expect([theme.themeName, theme.mode]).toEqual(['ember', 'light'])
})
