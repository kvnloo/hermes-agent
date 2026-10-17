import type { ScrollTo } from '@stencil-hq/tern'

import { matchesAction, REPORT_ACTIONS } from '../actions.js'
import type { Overlay, OverlayHost } from '../overlay.js'
import type { Report } from '../reports.js'

interface ReportHost extends OverlayHost {
  copy(text: string): void
  scroll(overlay: Overlay, to: ScrollTo): void
}

/** Native overlays own their scroll container; main's ids and scroll stay untouched. */
export function openReportSheet(host: ReportHost, report: Report) {
  let message = ''

  const sheet: Overlay = {
    key: 'report',
    modal: true,
    node: id => (
      <overlay anchor="center" head={report.title} key={id.slice('layer.'.length)} modal role="omp.overlay.report" size="lg">
        <col gap="md" key="body">
          <md key="markdown" role="omp.report.body">{report.text}</md>
          {message ? <text key="notice" role="omp.report.notice" text={message} wrap="word" /> : null}
          <row align="center" gap="sm" key="actions" role="omp.actions">
            <row
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
            </row>
            <spacer grow={1} key="fill" />
            <row key="close" onClick={() => host.close(sheet)} role="omp.btn" title="Close  escape">
              <text key="label" text="Close" />
              <kbd key="keys" keys={REPORT_ACTIONS[0]!.keys} />
            </row>
          </row>
        </col>
      </overlay>
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
}
