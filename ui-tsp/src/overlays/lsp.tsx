import type { LspQueryParams, LspQueryResult } from '@hermes/shared/gateway-events'

import { matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { App } from '../app.js'
import type { Overlay } from '../overlay.js'
import { ActionButton } from '../view/action-button.js'
import { lspResult } from '../view/lsp-diagnostics.js'

export const LSP_COMMANDS: [string, string][] = [
  ['/lsp', 'Inspect references, symbols or hover: /lsp <operation> <path> [line column]']
]

/** One explicit user query; no model tool, transcript mutation, timers or background polling. */
export async function openLsp(app: App, arg: string) {
  const match = /^(references|hover|symbols)\s+(.*?)(?:\s+([1-9]\d*)\s+([1-9]\d*))?$/.exec(arg)
  const operation = match?.[1]
  const path = match?.[2]

  if (!path || (operation !== 'references' && operation !== 'hover' && operation !== 'symbols') ||
      (operation !== 'symbols' && !match?.[3])) {
    app.transcript.notice('Usage: /lsp symbols <path> or /lsp references|hover <path> <line> <UTF-16 column>', 'warning')
    app.changed()

    return
  }

  const sid = app.sid

  if (!sid) { return }
  const params: LspQueryParams = { session_id: sid, operation, path, line: Number(match?.[3] ?? 1), col: Number(match?.[4] ?? 1) }
  let response: LspQueryResult | undefined
  let error = ''
  let closed = false

  const sheet: Overlay = {
    key: 'lsp', modal: true,
    onClose: () => { closed = true },
    node: id => (
      <overlay anchor="center" head={`LSP · ${operation}`} key={id.slice('layer.'.length)} modal role="omp.overlay.lsp" size="lg">
        <col gap="md" key="body">
          {app.sid !== sid ? <text key="stale" text="This inspection belongs to a different session." wrap="word" />
            : error ? <text key="error" role="omp.tool.lsp.error" text={error} tone="error" wrap="word" />
            : response ? lspResult(response.lsp_result, app.info?.cwd ?? '', !app.gw.attached && app.info?.terminal_backend === 'local') ??
              <text key="invalid" text="Unsupported LSP result; no semantic view available." wrap="word" />
              : <text key="loading" role="omp.tool.context" text="Waiting for language server…" wrap="word" />}
          <ActionButton key="close" onClick={() => { closed = true; app.close(sheet) }} role="omp.btn" text="Close  escape" />
        </col>
      </overlay>
    ),
    onKey: key => {
      const action = REPORT_ACTIONS.find(action => matchesAction(action, key))

      if (action?.intent.kind === 'close') { closed = true; app.close(sheet) }
      else if (action?.intent.kind === 'scroll') { app.scrollOverlay(sheet, 'body', action.intent.to) }

      return true
    }
  }

  app.open(sheet)

  try { response = await app.gw.request<LspQueryResult>('lsp.query', { ...params }) }
  catch (cause) { error = cause instanceof Error ? cause.message : String(cause) }

  if (!closed && app.sid === sid) { app.changed() }
}
