import { EXPERIMENT_VIEWPORTS, TERN_UX_FIXTURE_VERSION, type ExperimentViewportId } from './fixture.js'

export type TernCaptureMode = 'live-hermes' | 'fixture-replay'

export interface TernCaptureEvidence {
  bytes: number
  path: string
  sha256: string
}

export interface TernCaptureGlance {
  timeToNeedsUserMs?: number
  answers?: {
    doing?: boolean
    needsUser?: boolean
    next?: boolean
    type?: boolean
    inspect?: boolean
  }
}

export interface TernCaptureInput {
  commit: string
  evidence: TernCaptureEvidence
  mode: TernCaptureMode
  ternVersion: string
  viewport: ExperimentViewportId
  glance?: TernCaptureGlance
}

export function buildTernCaptureReceipt(input: TernCaptureInput) {
  const viewport = EXPERIMENT_VIEWPORTS.find(item => item.id === input.viewport)

  if (!viewport) {
    throw new Error(`Unknown viewport: ${input.viewport}`)
  }

  if (!/^[0-9a-f]{7,40}$/i.test(input.commit)) {
    throw new Error('Capture receipt requires an exact git commit SHA')
  }

  if (!input.ternVersion.trim()) {
    throw new Error('Capture receipt requires the observed Tern version')
  }

  if (input.evidence.bytes <= 0 || !/^[0-9a-f]{64}$/i.test(input.evidence.sha256)) {
    throw new Error('Capture receipt requires a non-empty hashed evidence file')
  }

  const answers = input.glance?.answers
  const answered = answers ? Object.values(answers).filter(value => value !== undefined).length : 0
  const attentionMeasured =
    typeof input.glance?.timeToNeedsUserMs === 'number' || answered > 0

  return {
    fixtureVersion: TERN_UX_FIXTURE_VERSION,
    variant: 'omp-baseline',
    commit: input.commit,
    mode: input.mode,
    ternVersion: input.ternVersion.trim(),
    viewport,
    evidence: input.evidence,
    liveTernVerified: input.mode === 'live-hermes',
    attentionMeasured,
    ...(input.glance ? { glance: input.glance } : {})
  }
}
