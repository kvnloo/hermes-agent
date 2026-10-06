import { ACTIVE_TERN_UX_VARIANT } from './activeVariant.js'
import { EXPERIMENT_VIEWPORTS, TERN_UX_FIXTURE, TERN_UX_FIXTURE_VERSION, type ExperimentViewportId } from './fixture.js'
import { NativeFixtureSession } from './nativeSession.js'
import { fixtureRequiredKinds, NATIVE_FIXTURE_REVISION, NATIVE_FIXTURE_SURFACE } from './nativeView.js'

export interface NativeFixtureRecord {
  t: number
  dir: 'out'
  verb: 'o' | 'f' | 'x'
  params: Record<string, string>
  body: Record<string, unknown>
}

/** Salvages the offline patch's replay export onto the newer interactive viewer.
 * Reuse its actual session/reconciler, not a second authored task or renderer.
 * Can Bölük / Stencil Labs: OMP reference patterns and Tern replay vocabulary. */
export function recordNativePreview(viewport: ExperimentViewportId) {
  if (ACTIVE_TERN_UX_VARIANT.id !== 'omp-baseline') throw new Error('Run recording from the OMP baseline branch')
  const size = EXPERIMENT_VIEWPORTS.find(item => item.id === viewport)
  if (!size) throw new RangeError(`Unknown viewport: ${viewport}`)

  const records: NativeFixtureRecord[] = []
  let checkpoint = 0
  let sequence = 0
  const session = new NativeFixtureSession({
    r: 'hello', v: 1, term: 'synthetic-recorder', kinds: fixtureRequiredKinds(),
    features: ['dock'], credits: 1
  }, (verb, body) => {
    records.push({ t: checkpoint * 1000, dir: 'out', verb, params: {}, body: structuredClone(body) })
    if (verb === 'f') sequence = body.s as number
  })

  for (checkpoint = 0; checkpoint < TERN_UX_FIXTURE.length; checkpoint++) {
    if (checkpoint === 0) session.start()
    else session.dispatch('next')
    if (sequence !== checkpoint + 1) throw new Error(`Missing recording checkpoint ${checkpoint + 1}`)
    // Synthetic ACK permits the next scripted state; this is NOT a latency sample.
    session.event({ ev: 'ack', sf: NATIVE_FIXTURE_SURFACE, s: sequence })
  }

  // Leave the final view open for inspection in a disposable surface-play pane.
  return {
    records,
    manifest: {
      fixtureVersion: TERN_UX_FIXTURE_VERSION,
      presentationRevision: NATIVE_FIXTURE_REVISION,
      recordingRevision: 'native-a-replay-v2',
      variant: ACTIVE_TERN_UX_VARIANT.id,
      viewport: size,
      evidence: 'authored-native-fixture-not-runtime-capture',
      timestamps: 'virtual-ms-not-measured',
      liveTernVerified: false,
      attentionMeasured: false,
      interactivePlayback: false,
      checkpoints: TERN_UX_FIXTURE.map((step, index) => ({
        frame: index + 1, stepId: step.id,
        coverage: step.id === 'split-preview' ? 'in-surface-preview-not-host-split' : 'read-only-replay'
      }))
    }
  }
}
