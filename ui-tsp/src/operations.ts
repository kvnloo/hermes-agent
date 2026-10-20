import type { OperationalReportResult } from '@hermes/shared/gateway-events'

import type { App } from './app.js'
import { displayText } from './display-text.js'
import { openReportSheet } from './overlays/report-sheet.js'
import { operationalView, type Report } from './reports.js'

type OperationalHost = Pick<App, 'sid' | 'gw' | 'overlays' | 'open' | 'close' | 'changed' | 'scrollOverlay'>

/** Display backend data as literal Markdown, not server-supplied links or headings. */
function literal(text: string): string {
  return displayText(text).replace(/[\t\r\n]+/g, ' ').replace(/([\\`*_{}[\]()#+.!|<>~-])/g, '\\$1')
}

export function operationalText(result: OperationalReportResult): string {
  const empty =
    result.view === 'ssh-list'
      ? 'No SSH hosts configured in this Hermes profile.'
      : result.view === 'mcp-catalog'
        ? 'No MCP catalog entries available.'
        : 'No MCP servers configured in this Hermes profile.'

  return [
    literal(result.message),
    ...result.rows.map(
      row => `## ${literal(row.name)}\n\n${row.details.map(detail => `- ${literal(detail)}`).join('\n')}`
    ),
    ...(result.state === 'ready' && !result.rows.length ? [empty] : [])
  ].join('\n\n')
}

/** No slash.exec inference and no mutations. A read is tied to this exact session and sheet. */
export async function openOperationalSheet(
  host: OperationalHost,
  name: string,
  arg: string,
  copy: (text: string) => void
) {
  const sid = host.sid

  if (!sid) {
    return
  }

  const view = operationalView(name, arg)
  const service = name.toLowerCase() === 'ssh' ? 'SSH' : 'MCP'

  const report: Report = view
    ? { title: `/${name}${arg ? ` ${arg}` : ''}`, text: `Reading Hermes ${service} inventory…`, status: 'loading' }
    : {
        title: `${service} management unavailable`,
        status: 'unsupported',
        text:
          `${service} management is unsupported in this native sheet. No command or mutation was sent.\n\n` +
          (service === 'SSH'
            ? 'Use /ssh list to inspect the current profile’s configured terminal target. SSH add/remove, reconnect and authentication require a canonical backend management API; none is exposed here.'
            : 'Use /mcp list, /mcp status, /mcp tools or /mcp catalog for read-only inventory. Add/remove, reconnect, reload and authentication are not exposed here without backend validation, exact scope and verified readback.')
      }

  const sheet = openReportSheet(
    {
      open: overlay => host.open(overlay),
      close: overlay => host.close(overlay),
      changed: () => host.changed(),
      scroll: (overlay, to) => host.scrollOverlay(overlay, 'body.markdown', to),
      copy
    },
    report
  )

  if (!view) {
    return
  }

  try {
    const result = await host.gw.request<OperationalReportResult>('operations.report', { session_id: sid, view })

    if (host.sid !== sid || !host.overlays.includes(sheet)) {
      return
    }

    report.status = result.state
    report.scope = result.scope
    report.text = operationalText(result)
  } catch {
    if (host.sid !== sid || !host.overlays.includes(sheet)) {
      return
    }

    // Auth/provider exceptions can carry credentials; use no raw error strings in this sheet.
    report.status = 'unavailable'
    report.text = 'Hermes inventory service is unavailable. No connection or mutation was attempted.'
  }

  host.changed()
}
