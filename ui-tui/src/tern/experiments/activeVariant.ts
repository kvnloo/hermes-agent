import { defineTernUxVariant } from './variant.js'

export const ACTIVE_TERN_UX_VARIANT = defineTernUxVariant({
  id: 'hermes-baseline',
  label: 'B — Hermes design-language baseline',
  hypothesis:
    'Hermes can retain its recognizable hierarchy and interaction language inside Tern without recreating Desktop chrome.',
  primaryReference:
    'https://github.com/NousResearch/hermes-agent/blob/main/apps/desktop/DESIGN.md',
  invariants: [
    'Chat remains the home surface.',
    'Flat over boxed; whitespace and hairlines over nested cards.',
    'Intent before automation: tools do not steal focus or open working context on their own.',
    'Hermes approval, queue and disclosure semantics remain recognizable.',
    'Tern owns outer pane, split, tab, window and host chrome.'
  ],
  forbidden: [
    'Cloning the Desktop sidebar or titlebar into the Tern pane.',
    'Nested card chrome that violates the Desktop flatness contract.',
    'Ad-hoc colors or terminal ornamentation standing in for Hermes identity.'
  ]
})
