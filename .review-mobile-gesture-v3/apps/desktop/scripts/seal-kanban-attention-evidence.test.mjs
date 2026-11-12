import assert from 'node:assert/strict'
import test from 'node:test'

import { validateInteractionEvidence } from './kanban-attention-evidence-validation.mjs'

const widths = [320, 360, 390, 430, 1220]
const valid = () => ({ responsiveTrace: widths.map(width => ({ width, escapeFocusRestored: true, cancelFocusRestored: true, openGeometry: { controls: [{ width: 44, height: 44 }] } })) })

test('rejects evidence with omitted Cancel proof', () => {
  const trace = valid()
  delete trace.responsiveTrace[2].cancelFocusRestored
  assert.throws(() => validateInteractionEvidence(trace), /missing Cancel focus proof at 390px/)
})

test('rejects evidence with omitted open-state geometry', () => {
  const trace = valid()
  delete trace.responsiveTrace[0].openGeometry
  assert.throws(() => validateInteractionEvidence(trace), /missing open-state geometry at 320px/)
})