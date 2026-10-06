import {
  TERN_UX_FIXTURE,
  TERN_UX_FIXTURE_VERSION,
  type ExperimentAttention,
  type ExperimentStep,
  type ExperimentViewportId
} from './fixture.js'

export type ExperimentRegion = 'chrome' | 'main' | 'dock' | 'layer' | 'aside'

export type GlanceRole = 'doing' | 'needs-user' | 'next' | 'input' | 'inspect'

export type ExperimentProgress =
  | { kind: 'indeterminate' }
  | {
      kind: 'determinate'
      value: number
      total: number
      denominatorKnown: boolean
    }

export type ExperimentElement = {
  id: string
  region: ExperimentRegion
  attention: ExperimentAttention
  visualPriority: 0 | 1 | 2 | 3
  persistent: boolean
  transientRows?: number
  visible?: boolean
  glance?: readonly GlanceRole[]
  progress?: ExperimentProgress
}

export type ExperimentHumanObservation = {
  timeToNeedsUserMs?: number
  glanceAnswers?: Partial<Record<GlanceRole, boolean>>
}

export type ExperimentFrame = {
  variant: string
  stepId: string
  viewport: ExperimentViewportId
  elements: readonly ExperimentElement[]
  focusedId?: string | null
  human?: ExperimentHumanObservation
}

export type ExperimentFrameMetrics = {
  stepId: string
  viewport: ExperimentViewportId
  visibleElements: number
  highSalienceElements: number
  persistentElements: number
  transientRows: number
  eyeTravel: number
  needsUserRank: number | null
  violations: string[]
}

export type ExperimentReceipt = {
  fixtureVersion: string
  variant: string
  frames: number
  averageHighSalienceElements: number
  maxHighSalienceElements: number
  averagePersistentElements: number
  totalTransientRows: number
  averageEyeTravel: number
  averageTimeToNeedsUserMs: number | null
  violations: string[]
}

const REGION_POINT: Record<ExperimentRegion, readonly [number, number]> = {
  chrome: [0.5, 0.05],
  main: [0.5, 0.45],
  dock: [0.5, 0.9],
  layer: [0.5, 0.55],
  aside: [0.85, 0.45]
}

const isVisible = (element: ExperimentElement): boolean => element.visible !== false

const hasGlanceRole = (element: ExperimentElement, role: GlanceRole): boolean =>
  element.glance?.includes(role) ?? false

const roleElement = (elements: readonly ExperimentElement[], role: GlanceRole): ExperimentElement | undefined =>
  elements.find(element => hasGlanceRole(element, role))

const distance = (left: ExperimentRegion, right: ExperimentRegion): number => {
  const [lx, ly] = REGION_POINT[left]
  const [rx, ry] = REGION_POINT[right]

  return Math.hypot(lx - rx, ly - ry)
}

function eyeTravel(elements: readonly ExperimentElement[], step: ExperimentStep): number {
  const doing = roleElement(elements, 'doing')
  const middle = roleElement(elements, step.needsUser ? 'needs-user' : 'next')
  const input = roleElement(elements, 'input')
  const path = [doing, middle, input].filter((item): item is ExperimentElement => Boolean(item))

  let total = 0

  for (let index = 1; index < path.length; index += 1) {
    total += distance(path[index - 1].region, path[index].region)
  }

  return total
}

export function validateExperimentFrame(frame: ExperimentFrame, step: ExperimentStep): string[] {
  const elements = frame.elements.filter(isVisible)
  const violations: string[] = []
  const requiredRoles: GlanceRole[] = ['doing', 'next', 'input', 'inspect']

  if (step.needsUser) {
    requiredRoles.push('needs-user')
  }

  for (const role of requiredRoles) {
    if (!roleElement(elements, role)) {
      violations.push(`missing-glance-role:${role}`)
    }
  }

  const needsUserElements = elements.filter(element => element.attention === 'needs-user')

  if (step.needsUser && needsUserElements.length !== 1) {
    violations.push(`needs-user-count:${needsUserElements.length}`)
  }

  if (!step.needsUser && needsUserElements.length > 0) {
    violations.push(`unexpected-needs-user:${needsUserElements.length}`)
  }

  const needsUserTarget = roleElement(elements, 'needs-user')

  if (needsUserTarget) {
    const maxPriority = Math.max(...elements.map(element => element.visualPriority), 0)

    if (needsUserTarget.visualPriority !== maxPriority) {
      violations.push('needs-user-not-highest-priority')
    }

    if (elements.filter(element => element.visualPriority === maxPriority).length !== 1) {
      violations.push('needs-user-not-singular-peak')
    }
  }

  for (const element of elements) {
    if (element.attention === 'ambient' && element.visualPriority > 1) {
      violations.push(`ambient-too-loud:${element.id}`)
    }

    if (element.attention === 'completed' && element.visualPriority > 1) {
      violations.push(`completed-too-loud:${element.id}`)
    }

    if (
      element.progress?.kind === 'determinate' &&
      (!element.progress.denominatorKnown ||
        element.progress.total <= 0 ||
        element.progress.value < 0 ||
        element.progress.value > element.progress.total)
    ) {
      violations.push(`untruthful-progress:${element.id}`)
    }
  }

  return violations
}

export function scoreExperimentFrame(frame: ExperimentFrame, step: ExperimentStep): ExperimentFrameMetrics {
  const elements = frame.elements.filter(isVisible)
  const needsUserTarget = roleElement(elements, 'needs-user')
  const orderedByPriority = [...elements].sort((left, right) => right.visualPriority - left.visualPriority)
  const needsUserRank = needsUserTarget ? orderedByPriority.findIndex(element => element.id === needsUserTarget.id) + 1 : null

  return {
    stepId: frame.stepId,
    viewport: frame.viewport,
    visibleElements: elements.length,
    highSalienceElements: elements.filter(element => element.visualPriority >= 2).length,
    persistentElements: elements.filter(element => element.persistent).length,
    transientRows: elements.reduce((sum, element) => sum + Math.max(0, element.transientRows ?? 0), 0),
    eyeTravel: eyeTravel(elements, step),
    needsUserRank,
    violations: validateExperimentFrame(frame, step)
  }
}

const average = (values: readonly number[]): number =>
  values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length

export function buildExperimentReceipt(frames: readonly ExperimentFrame[]): ExperimentReceipt {
  const stepById = new Map(TERN_UX_FIXTURE.map(step => [step.id, step]))
  const metrics: ExperimentFrameMetrics[] = []
  const violations: string[] = []
  const timesToNeedsUser: number[] = []

  for (const frame of frames) {
    const step = stepById.get(frame.stepId)

    if (!step) {
      violations.push(`${frame.stepId}/${frame.viewport}:unknown-step`)
      continue
    }

    const scored = scoreExperimentFrame(frame, step)
    metrics.push(scored)
    violations.push(
      ...scored.violations.map(violation => `${frame.stepId}/${frame.viewport}:${violation}`)
    )

    if (typeof frame.human?.timeToNeedsUserMs === 'number') {
      timesToNeedsUser.push(frame.human.timeToNeedsUserMs)
    }
  }

  const variants = new Set(frames.map(frame => frame.variant))
  const variant = variants.size === 1 ? frames[0]?.variant ?? 'unknown' : 'mixed'

  return {
    fixtureVersion: TERN_UX_FIXTURE_VERSION,
    variant,
    frames: metrics.length,
    averageHighSalienceElements: average(metrics.map(metric => metric.highSalienceElements)),
    maxHighSalienceElements: Math.max(0, ...metrics.map(metric => metric.highSalienceElements)),
    averagePersistentElements: average(metrics.map(metric => metric.persistentElements)),
    totalTransientRows: metrics.reduce((sum, metric) => sum + metric.transientRows, 0),
    averageEyeTravel: average(metrics.map(metric => metric.eyeTravel)),
    averageTimeToNeedsUserMs: timesToNeedsUser.length > 0 ? average(timesToNeedsUser) : null,
    violations
  }
}
