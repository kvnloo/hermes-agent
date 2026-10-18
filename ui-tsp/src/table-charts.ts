import type { TableChartPlanResult, TableChartPolicy } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { TableCharts } from './view/table-charts.js'

export function appTableCharts(app: App): TableCharts {
  return new TableCharts({
    policy: async session_id => {
      const { mode } = await app.gw.request<TableChartPolicy>('table_chart.policy', { session_id })

      return mode === 'always' || mode === 'smart' ? mode : 'off'
    },
    plan: async (session_id, table) => {
      const { kind } = await app.gw.request<TableChartPlanResult>('table_chart.plan', { session_id, source: table.source })

      return kind === 'line' || kind === 'none' ? kind : 'bar'
    }
  }, () => app.changed())
}
