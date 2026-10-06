import { defineTernUxVariant } from './variant.js'

export const ACTIVE_TERN_UX_VARIANT = defineTernUxVariant({
  id: 'omp-baseline',
  label: 'A — OMP/Tern-native baseline',
  hypothesis:
    'The proven native OMP/Tern presentation grammar provides the lowest-friction baseline for a coding-agent pane.',
  primaryReference: 'https://stencil.so/tern#graphics',
  invariants: [
    'Use the actual native OMP-in-Tern interaction hierarchy as the baseline, not OMP rendered as ANSI.',
    'Tern owns pane, tab, split, window and host chrome.',
    'Hermes runtime, session, tool, model and approval state remain authoritative.',
    'Prefer Tern-native semantic nodes and transient sheets over permanent application chrome.'
  ],
  forbidden: [
    'Copying OMP runtime architecture into Hermes.',
    'Using normal-terminal OMP screenshots as native-Tern evidence.',
    'Adding Hermes Desktop sidebar/window chrome merely for familiarity.'
  ]
})
