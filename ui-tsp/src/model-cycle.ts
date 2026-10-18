import type { ModelOptionsResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { modelId } from './model-recents.js'

/** Serialize relative navigation so rapid key repeats use the last accepted model. */
export function cycleModel(app: App, direction: -1 | 1): void {
  const sid = app.sid
  void app.modelRecents.enqueue(async () => {
    if (!sid || app.sid !== sid) {
      return
    }

    try {
      const options = await app.gw.request<ModelOptionsResult>('model.options', { safe_inventory: true, session_id: sid })

      if (app.sid !== sid) {
        return
      }

      const activeProvider = options.providers.find(row => row.is_current)?.slug ?? options.provider ?? app.info?.provider ?? ''
      const provider = options.pending_model ? options.pending_provider || activeProvider : activeProvider
      // Gateway-owned pending intent, not optimistic app.info: rapid cycles must advance while a turn streams.
      const current = { model: options.pending_model || options.model || app.info?.model || '', provider }

      const available = options.providers.filter(p => p.authenticated !== false).flatMap(p => (p.models ?? [])
        .filter(model => !p.unavailable_models?.includes(model))
        .map(model => ({ model, provider: p.slug })))

      const recent = app.modelRecents.list(sid).filter(row => available.some(item => modelId(item) === modelId(row)))
      // The picker's configured inventory already includes provider fallback catalogs.
      const rows = recent.length ? [...recent] : available

      if (!rows.some(row => modelId(row) === modelId(current))) {
        rows.unshift(current)
      }

      if (rows.length < 2) {
        app.transcript.notice('Only one model is available to cycle. Use /model to choose another.')
        app.changed()

        return
      }

      const at = rows.findIndex(row => modelId(row) === modelId(current))
      const next = rows[(at + direction + rows.length) % rows.length]!
      // /model owns the exact switchModel + confirm-required path.
      await app.slash(`/model ${next.model} --provider ${next.provider} --session`)
    } catch (error) {
      if (app.sid === sid) {
        app.transcript.notice(error instanceof Error ? error.message : String(error), 'error')
        app.changed()
      }
    }
  })
}
