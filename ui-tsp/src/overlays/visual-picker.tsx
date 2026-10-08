// Reuse the current overlay owner and #464's validator. No watcher, global
// index, generated-code execution or automatic artifact opening is involved.
import { basename } from 'node:path'
import type { Entry } from '../model.js'
import type { Overlay, OverlayHost } from '../overlay.js'
import { recentVisualCandidates, type VisualCandidate } from '../visual-discovery.js'
import { readPreparedVisual, type PreparedVisual, type VisualSession, visualScope } from '../visuals.js'
import { openVisual } from './visual.js'

interface VisualPickerHost extends OverlayHost, VisualSession {
  readonly overlays: readonly Overlay[]
  readonly transcript: { entries: readonly Entry[] }
}
type LoadVisual = (path: string, scope: string, signal: AbortSignal) => Promise<PreparedVisual>

/** No path needed for machine-readable candidates emitted in this transcript. */
export async function openVisualPicker(app: VisualPickerHost, path: string, load: LoadVisual = readPreparedVisual): Promise<void> {
  const sid = app.sid, scope = visualScope(app), entries = app.transcript.entries
  const candidates = !path && scope ? recentVisualCandidates(entries, scope) : []
  if (path || !scope || !candidates.length) return openVisual(app, path, load)
  let selected = 0, expired = false
  const current = () => {
    expired ||= app.sid !== sid || visualScope(app) !== scope || app.transcript.entries !== entries
    return !expired && app.overlays.includes(overlay)
  }
  const close = () => app.close(overlay)
  const choose = async (candidate: VisualCandidate) => {
    if (!current() || app.overlays.at(-1) !== overlay) return
    close()
    await openVisual(app, candidate.path, async (file, owner, signal) => {
      const result = await load(file, owner, signal)
      if (app.transcript.entries !== entries) throw new Error('The transcript changed. Reopen /visual.')
      if (result.id !== candidate.id) throw new Error('The file no longer matches the reported bundle. Prepare it again.')
      return result
    })
  }
  const overlay: Overlay = {
    key: 'visual-candidates', modal: true,
    node: id => (
      <overlay anchor="center" head="Recent visual candidates" key={id.slice('layer.'.length)} modal size="lg">
        <col key="body" gap="sm">
          {!current() ? <text key="expired" text="Session, branch or transcript changed. Reopen /visual." /> : (
            <col key="choices" gap="sm">
              <text key="status" tone="warning" text="Reported files only · not validated, visually verified or published" />
              <text key="hint" text="Select a candidate to validate and preview. Up/Down, Enter; Escape closes." />
              {candidates.map((candidate, index) => (
                <row key={`candidate-${index}`} role="omp.btn" title={candidate.path} onClick={() => choose(candidate)}>
                  <text key="name" text={`${index === selected ? '› ' : ''}${basename(candidate.path)}`} />
                  <text key="identity" text={candidate.id.slice(0, 12)} />
                </row>
              ))}
              <text key="limits" text="Up to 12 candidates from bounded recent completed terminal results. Reopen to refresh; no file scan or live polling." />
              <text key="scope" text={scope} />
            </col>
          )}
          <row key="close" role="omp.btn" onClick={close} title="Close  escape">
            <text key="label" text="Close" /><kbd key="key" keys={['escape']} />
          </row>
        </col>
      </overlay>
    ),
    onKey: key => {
      if (!current()) { close(); return true }
      if (app.overlays.at(-1) !== overlay) return true
      if (key.name === 'escape' || key.name === 'q') close()
      else if (key.name === 'up' || key.name === 'down') {
        selected = (selected + (key.name === 'up' ? -1 : 1) + candidates.length) % candidates.length
        app.changed()
      } else if (key.name === 'enter' || key.name === 'return') void choose(candidates[selected]!)
      return true
    }
  }
  app.open(overlay)
}
