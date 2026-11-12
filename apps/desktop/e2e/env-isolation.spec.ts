import { buildAppEnv, type Sandbox } from './fixtures'
import { expect, test } from './test'

test('E2E app env rejects inherited canonical Kanban routing', () => {
  const prior = Object.fromEntries(
    Object.entries(process.env).filter(([key]) => key.startsWith('HERMES_KANBAN_')),
  )
  Object.assign(process.env, {
    HERMES_KANBAN_BOARD: 'canonical',
    HERMES_KANBAN_DB: '/canonical/kanban.db',
    HERMES_KANBAN_HOME: '/canonical',
    HERMES_KANBAN_TASK: 't_live',
    HERMES_KANBAN_WORKSPACES_ROOT: '/canonical/workspaces',
  })

  try {
    const sandbox = {
      root: '/tmp/hermes-e2e-test',
      hermesHome: '/tmp/hermes-e2e-test/hermes-home',
      userDataDir: '/tmp/hermes-e2e-test/user-data',
      cleanup: () => undefined,
    } satisfies Sandbox
    const env = buildAppEnv(sandbox)

    expect(env.HERMES_HOME).toBe(sandbox.hermesHome)
    expect(Object.keys(env).filter((key) => key.startsWith('HERMES_KANBAN_'))).toEqual([])
  } finally {
    for (const key of Object.keys(process.env)) {
      if (key.startsWith('HERMES_KANBAN_')) delete process.env[key]
    }
    Object.assign(process.env, prior)
  }
})