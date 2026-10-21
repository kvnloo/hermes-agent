import { matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { Overlay } from '../overlay.js'
import type { Report } from '../reports.js'
import { ActionButton } from '../view/action-button.js'

import { Sheet, type SheetHost } from './sheet.js'

interface ReportHost extends SheetHost {
  copy(text: string): void
}

/** Native overlays own their scroll container; main's ids and scroll stay untouched. */
export function openReportSheet(host: ReportHost, report: Report) {
  let message = ''

  const sheet: Overlay = {
    key: 'report',
    modal: true,
    node: id => (
      <Sheet id={id} role="omp.overlay.report" title={report.title}>
        {report.status ? (
          <text
            key="state"
            role="omp.report.state"
            text={report.status}
            tone={report.status === 'unavailable' ? 'error' : undefined}
          />
        ) : null}
        {report.scope ? (
          <text key="scope" role="omp.report.scope" text={`Hermes profile: ${report.scope} · Read only`} wrap="word" />
        ) : null}
        {report.format === 'plain' ? (
          <text key="markdown" role="omp.report.body" spans={[{ s: 'mono', t: report.text }]} wrap="none" />
        ) : (
          <md key="markdown" role="omp.report.body">{report.text}</md>
        )}
        {message ? <text key="notice" role="omp.report.notice" text={message} wrap="word" /> : null}
        <row align="center" gap="sm" key="actions" role="omp.actions">
          <ActionButton
            key="copy"
            onClick={() => {
              try {
                host.copy(report.text)
                message = 'Report sent to the terminal clipboard (OSC 52).'
              } catch {
                message = 'Could not copy the report to the clipboard.'
              }

              host.changed()
            }}
            role="omp.btn"
            title="Copy report"
          >
            <text key="label" text="Copy" />
          </ActionButton>
          <spacer grow={1} key="fill" />
          <ActionButton key="close" onClick={() => host.close(sheet)} role="omp.btn" title="Close  escape">
            <text key="label" text="Close" />
            <kbd key="keys" keys={REPORT_ACTIONS[0]!.keys} />
          </ActionButton>
        </row>
      </Sheet>
    ),
    onKey: key => {
      const action = REPORT_ACTIONS.find(action => matchesAction(action, key))

      if (action?.intent.kind === 'close') {
        host.close(sheet)
      } else if (action?.intent.kind === 'scroll') {
        host.scroll(sheet, action.intent.to)
      }

      return true
    }
  }

  host.open(sheet)

  return sheet
}
