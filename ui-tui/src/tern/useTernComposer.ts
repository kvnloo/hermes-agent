import { useEffect } from 'react'

import type { ComposerActions, ComposerRefs } from '../app/interfaces.js'
import { $isBlocked } from '../app/overlayStore.js'
import { $uiState } from '../app/uiStore.js'

import type { TernComposer } from './composer.js'

export function useTernComposer(
  tern: TernComposer | undefined,
  refs: ComposerRefs,
  actions: ComposerActions,
  submit: (full: string) => void
) {
  const draftRevision = tern ? refs.readDraft().revision : 0

  useEffect(() => {
    if (!tern) {
      return
    }

    tern.bind({
      edit: text => {
        actions.syncTokens(text)
        actions.setInputBuf([])
        actions.setInput(text)
      },
      read: () => {
        const ui = $uiState.get()

        return {
          ...refs.readDraft(),
          busy: ui.busy,
          modal: $isBlocked.get(),
          owner: JSON.stringify([ui.sid, ui.info?.stored_session_id, ui.info?.profile_name,
            ui.info?.execution_epoch, ui.info?.execution_generation]),
          ready: Boolean(ui.sid && ui.gatewayConnected === true)
        }
      },
      submit // Existing dispatchSubmission: history, command routing, durable admission and RPC authority.
    })
    const stopUi = $uiState.subscribe(() => tern.refresh())
    const stopModal = $isBlocked.subscribe(() => tern.refresh())

    return () => {
      stopUi()
      stopModal()
      tern.unbind()
    }
  }, [actions, draftRevision, refs, submit, tern])
}
