import { defineTernUxVariant } from './variant.js'

export const ACTIVE_TERN_UX_VARIANT = defineTernUxVariant({
  id: 'attention-minimal',
  label: 'C — Attention-minimal hybrid',
  hypothesis:
    'A surface where only unresolved state earns salience will beat both baselines on glance speed and persistent visual load.',
  primaryReference: 'https://github.com/kvnloo/hermes-agent/issues/436',
  invariants: [
    'Only the highest-priority unresolved state may become the singular visual peak.',
    'Ambient and completed state recede.',
    'Idle persistent UI is minimized.',
    'The user can always answer what Hermes is doing, whether it needs them, what happens next and where to type.',
    'Tern owns environmental chrome while Hermes owns task semantics.'
  ],
  forbidden: [
    'Ambient animation whose only message is that the agent is alive.',
    'Duplicate model/context/path/status readouts.',
    'Fake determinate progress without a real denominator.',
    'Persistent diagnostic rails that consume attention while idle.'
  ]
})
