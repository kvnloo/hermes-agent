// A session-local entry point to an existing OpenUI candidate. Tern's file
// route opens the separately installed Luau block; this sheet grants nothing.
import type { Overlay, OverlayHost } from '../overlay.js'
import { type PreparedVisual, readPreparedVisual, type VisualSession, visualScope } from '../visuals.js'

interface VisualHost extends OverlayHost, VisualSession {
  readonly overlays: readonly Overlay[]
}

type LoadVisual = (path: string, scope: string, signal: AbortSignal) => Promise<PreparedVisual>

/** Reuses App's instance-owned callbacks. Late reads never reopen a dismissed sheet. */
export async function openVisual(app: VisualHost, path: string, load: LoadVisual = readPreparedVisual): Promise<void> {
  const sid = app.sid
  const scope = visualScope(app)
  const controller = new AbortController()
  let candidate: PreparedVisual | undefined
  let error = ''
  let expired = false

  const current = () => {
    expired ||= app.sid !== sid || visualScope(app) !== scope
    return !expired && app.overlays.includes(overlay)
  }
  const close = () => {
    controller.abort()
    app.close(overlay)
  }
  const overlay: Overlay = {
    key: 'visual-preview',
    modal: true,
    node: id => {
      const valid = current()
      return (
        <overlay anchor="center" head="Visual preview" key={id.slice('layer.'.length)} modal size="lg">
          <col gap="md" key="body">
            {!valid ? (
              <text key="expired" text="Session or branch changed. Reopen the preview in its owning session." />
            ) : !scope ? (
              <text key="unavailable" text="Start a session before opening a visual preview." />
            ) : !path ? (
              <col key="usage" gap="sm">
                <text key="command" text="/visual /absolute/path/to/candidate.hvisual.json" />
                <text key="discovery" text="Or run the existing prepare CLI through the agent terminal with --json, then reopen /visual to select its reported file." />
                <text key="scope-label" text="Prepare the existing OpenUI bundle with this exact scope argument:" />
                <text key="scope" text={scope} />
                <text key="note" text="This command inspects prepared data; it does not generate, approve, publish or share it." />
              </col>
            ) : error ? (
              <text key="error" tone="error" text={error} />
            ) : candidate ? (
              <col key="candidate" gap="sm">
                <text key="title" text={candidate.title} />
                <text key="status" tone="warning" text="Preview only · not visually verified or published" />
                <kv key="metrics" items={candidate.metrics.map(metric => ({ k: metric.label, v: String(metric.value) }))} />
                <text key="mode" text={`Initial mode: ${candidate.mode}`} />
                <text key="identity" text={`Bundle: ${candidate.id}`} />
                <text key="file" spans={[{ t: 'Open candidate file in Tern', href: candidate.href, s: 'link' }]} />
                <text key="route" text="The enabled hermes-openui file route opens the Luau viewer. No plugin is installed by this command; opening reads the current file again." />
              </col>
            ) : (
              <text key="loading" text="Checking prepared visual…" />
            )}
            <row key="close" role="omp.btn" onClick={close} title="Close  escape">
              <text key="label" text="Close" /><kbd key="key" keys={['escape']} />
            </row>
          </col>
        </overlay>
      )
    },
    onKey: key => {
      if (!current() || key.name === 'escape' || key.name === 'q') close()
      return true
    }
  }
  app.open(overlay)
  if (!scope || !path) return
  try {
    const result = await load(path, scope, controller.signal)
    if (!current() || controller.signal.aborted) return
    candidate = result
  } catch (cause) {
    if (!current() || controller.signal.aborted) return
    error = cause instanceof Error ? cause.message : String(cause)
  }
  if (current()) app.changed()
}
