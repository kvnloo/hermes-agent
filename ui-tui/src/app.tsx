import { useStore } from '@nanostores/react'

import { GatewayProvider } from './app/gatewayContext.js'
import { $uiState } from './app/uiStore.js'
import { useMainApp } from './app/useMainApp.js'
import { AppLayout } from './components/appLayout.js'
import type { GatewayClient } from './gatewayClient.js'
import type { TernComposer } from './tern/composer.js'

export function App({ gw, tern }: { gw: GatewayClient; tern?: TernComposer }) {
  const { appActions, appComposer, appProgress, appStatus, appTranscript, gateway } = useMainApp(gw, tern)
  const { mouseTracking } = useStore($uiState)

  return (
    <GatewayProvider value={gateway}>
      <AppLayout
        actions={appActions}
        composer={appComposer}
        mouseTracking={mouseTracking}
        progress={appProgress}
        status={appStatus}
        transcript={appTranscript}
      />
    </GatewayProvider>
  )
}
