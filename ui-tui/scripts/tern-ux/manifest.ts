import {
  EXPERIMENT_VIEWPORTS,
  TERN_UX_FIXTURE,
  TERN_UX_FIXTURE_VERSION
} from '../../src/tern/experiments/fixture.js'
import { ACTIVE_TERN_UX_VARIANT } from '../../src/tern/experiments/activeVariant.js'

const receipt = {
  fixtureVersion: TERN_UX_FIXTURE_VERSION,
  variant: ACTIVE_TERN_UX_VARIANT,
  viewports: EXPERIMENT_VIEWPORTS,
  steps: TERN_UX_FIXTURE.map(step => ({
    id: step.id,
    attention: step.attention,
    needsUser: step.needsUser
  }))
}

process.stdout.write(JSON.stringify(receipt, null, 2) + '\n')
