import { describe, expect, it } from 'vitest'

import { TERN_UX_FIXTURE, TERN_UX_FIXTURE_VERSION } from './fixture.js'
import {
  buildExperimentReceipt,
  scoreExperimentFrame,
  validateExperimentFrame,
  type ExperimentFrame
} from './attention.js'

const approvalStep = TERN_UX_FIXTURE.find(step => step.id === 'approval-required')!

const approvalFrame: ExperimentFrame = {
  variant: 'test',
  stepId: approvalStep.id,
  viewport: 'normal',
  elements: [
    {
      id: 'transcript',
      region: 'main',
      attention: 'ambient',
      visualPriority: 0,
      persistent: true,
      glance: ['doing']
    },
    {
      id: 'approval',
      region: 'layer',
      attention: 'needs-user',
      visualPriority: 3,
      persistent: false,
      transientRows: 4,
      glance: ['needs-user', 'next', 'inspect']
    },
    {
      id: 'composer',
      region: 'dock',
      attention: 'ambient',
      visualPriority: 1,
      persistent: true,
      glance: ['input']
    }
  ]
}

describe('Tern UX deterministic fixture', () => {
  it('keeps the issue #436 flow stable and ordered', () => {
    expect(TERN_UX_FIXTURE_VERSION).toBe('tern-ux-v1')
    expect(TERN_UX_FIXTURE.map(step => step.id)).toEqual([
      'fresh-session',
      'bounded-request',
      'thinking',
      'read-search',
      'write-edit',
      'subagent-start',
      'queued-follow-up',
      'approval-required',
      'tool-failure-recovery',
      'successful-completion',
      'model-picker',
      'inspect-background',
      'split-preview',
      'return-chat'
    ])
  })

  it('accepts one singular needs-user peak with the composer still discoverable', () => {
    expect(validateExperimentFrame(approvalFrame, approvalStep)).toEqual([])

    const metrics = scoreExperimentFrame(approvalFrame, approvalStep)

    expect(metrics.needsUserRank).toBe(1)
    expect(metrics.highSalienceElements).toBe(1)
    expect(metrics.persistentElements).toBe(2)
    expect(metrics.transientRows).toBe(4)
    expect(metrics.eyeTravel).toBeGreaterThan(0)
  })

  it('flags competing attention and fake determinate progress', () => {
    const badFrame: ExperimentFrame = {
      ...approvalFrame,
      elements: [
        ...approvalFrame.elements,
        {
          id: 'spinner',
          region: 'chrome',
          attention: 'active',
          visualPriority: 3,
          persistent: true,
          progress: {
            kind: 'determinate',
            value: 50,
            total: 100,
            denominatorKnown: false
          }
        }
      ]
    }

    expect(validateExperimentFrame(badFrame, approvalStep)).toEqual(
      expect.arrayContaining(['needs-user-not-singular-peak', 'untruthful-progress:spinner'])
    )
  })

  it('builds deterministic receipts without timestamps', () => {
    const receipt = buildExperimentReceipt([
      {
        ...approvalFrame,
        human: { timeToNeedsUserMs: 420 }
      }
    ])

    expect(receipt).toMatchObject({
      fixtureVersion: 'tern-ux-v1',
      variant: 'test',
      frames: 1,
      averageTimeToNeedsUserMs: 420,
      violations: []
    })
  })
})
