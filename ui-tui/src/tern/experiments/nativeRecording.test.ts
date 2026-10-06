import assert from 'node:assert/strict'
import { describe, it } from 'vitest'

import { EXPERIMENT_VIEWPORTS, TERN_UX_FIXTURE } from './fixture.js'
import { recordNativePreview } from './nativeRecording.js'
import { diffFixtureViews } from './nativeSession.js'
import { INITIAL_NATIVE_FIXTURE, NATIVE_FIXTURE_SURFACE, renderNativeFixture, type FixtureView } from './nativeView.js'

describe('offline replay of the current native viewer', () => {
  for (const viewport of EXPERIMENT_VIEWPORTS) {
    it(`records every current-viewer checkpoint without changing it: ${viewport.id}`, () => {
      const { records, manifest } = recordNativePreview(viewport.id)
      assert.deepEqual(records.filter(record => record.verb === 'o').map(record => record.body.id), [NATIVE_FIXTURE_SURFACE])
      assert.equal(records.filter(record => record.verb === 'x').length, 0)
      const frames = records.filter(record => record.verb === 'f')
      assert.equal(frames.length, TERN_UX_FIXTURE.length)
      let previous: FixtureView | null = null
      for (const [index, frame] of frames.entries()) {
        const next = renderNativeFixture({ ...INITIAL_NATIVE_FIXTURE, step: index })
        assert.deepEqual(frame.body, { sf: NATIVE_FIXTURE_SURFACE, s: index + 1, ops: diffFixtureViews(previous, next) })
        assert.equal(frame.t, index * 1000)
        previous = next
      }
      assert.deepEqual(manifest.viewport, viewport)
      assert.deepEqual(manifest.checkpoints.map(item => item.stepId), TERN_UX_FIXTURE.map(item => item.id))
      assert.equal(manifest.liveTernVerified, false)
      assert.equal(manifest.attentionMeasured, false)
      assert.equal(manifest.interactivePlayback, false)
    })
  }

  it('is deterministic and labels virtual time and absent host-split coverage', () => {
    assert.deepEqual(recordNativePreview('normal'), recordNativePreview('normal'))
    const { manifest } = recordNativePreview('normal')
    assert.equal(manifest.timestamps, 'virtual-ms-not-measured')
    assert.equal(manifest.recordingRevision, 'native-a-replay-v2')
    assert.equal(manifest.checkpoints.find(item => item.stepId === 'split-preview')?.coverage, 'in-surface-preview-not-host-split')
  })

  it('rejects invalid dimensions rather than silently selecting another viewport', () => {
    assert.throws(() => recordNativePreview('unknown' as 'normal'), /Unknown viewport/)
  })
})
