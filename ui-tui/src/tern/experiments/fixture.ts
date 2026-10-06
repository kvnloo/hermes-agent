export const TERN_UX_FIXTURE_VERSION = 'tern-ux-v1'

export const EXPERIMENT_VIEWPORTS = [
  { id: 'narrow', columns: 80, rows: 28 },
  { id: 'normal', columns: 120, rows: 36 },
  { id: 'wide', columns: 180, rows: 44 }
] as const

export type ExperimentViewportId = (typeof EXPERIMENT_VIEWPORTS)[number]['id']

export type ExperimentAttention = 'ambient' | 'active' | 'needs-user' | 'completed'

export type ExperimentStep = {
  id: string
  title: string
  attention: ExperimentAttention
  needsUser: boolean
  expectedDoing: string
  expectedNext: string
}

export const TERN_UX_FIXTURE = [
  {
    id: 'fresh-session',
    title: 'Fresh session',
    attention: 'ambient',
    needsUser: false,
    expectedDoing: 'Idle and ready',
    expectedNext: 'Accept a prompt'
  },
  {
    id: 'bounded-request',
    title: 'Bounded code-change request',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Understand the requested change',
    expectedNext: 'Inspect the relevant code'
  },
  {
    id: 'thinking',
    title: 'Assistant thinking',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Reason about the change',
    expectedNext: 'Choose the first concrete action'
  },
  {
    id: 'read-search',
    title: 'Read/search tool',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Inspect repository context',
    expectedNext: 'Apply the smallest change'
  },
  {
    id: 'write-edit',
    title: 'Write/edit tool',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Apply the code change',
    expectedNext: 'Verify the result'
  },
  {
    id: 'subagent-start',
    title: 'Subagent starts',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Run delegated work in parallel',
    expectedNext: 'Continue the main task while the child works'
  },
  {
    id: 'queued-follow-up',
    title: 'Queued user follow-up',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Finish the current boundary',
    expectedNext: 'Apply the queued user follow-up'
  },
  {
    id: 'approval-required',
    title: 'Approval-required command',
    attention: 'needs-user',
    needsUser: true,
    expectedDoing: 'Wait for command approval',
    expectedNext: 'Run or deny the requested command'
  },
  {
    id: 'tool-failure-recovery',
    title: 'Tool failure and recovery',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Recover from a tool failure',
    expectedNext: 'Retry or choose a safe alternative'
  },
  {
    id: 'successful-completion',
    title: 'Successful completion',
    attention: 'completed',
    needsUser: false,
    expectedDoing: 'Present the completed result',
    expectedNext: 'Accept the next user action'
  },
  {
    id: 'model-picker',
    title: 'Open model picker',
    attention: 'needs-user',
    needsUser: true,
    expectedDoing: 'Choose a model',
    expectedNext: 'Apply the selected model'
  },
  {
    id: 'inspect-background',
    title: 'Inspect background/agent state',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Inspect live background work',
    expectedNext: 'Return to the main task or intervene'
  },
  {
    id: 'split-preview',
    title: 'Open split preview',
    attention: 'active',
    needsUser: false,
    expectedDoing: 'Inspect a task-attached preview',
    expectedNext: 'Keep or dismiss the working context'
  },
  {
    id: 'return-chat',
    title: 'Return to chat',
    attention: 'ambient',
    needsUser: false,
    expectedDoing: 'Resume the conversation in place',
    expectedNext: 'Continue from the preserved composer/transcript state'
  }
] as const satisfies readonly ExperimentStep[]

export type ExperimentStepId = (typeof TERN_UX_FIXTURE)[number]['id']

export function getExperimentStep(id: string): ExperimentStep | undefined {
  return TERN_UX_FIXTURE.find(step => step.id === id)
}
