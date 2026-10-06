import { describe, expect, it } from 'vitest'

import { buildTernCaptureReceipt } from './captureReceipt.js'

const evidence = {
  bytes: 120_000,
  path: '/tmp/normal.png',
  sha256: 'a'.repeat(64)
}

describe('real Tern capture receipts', () => {
  it('marks only actual live-Hermes evidence as live verified', () => {
    const live = buildTernCaptureReceipt({
      commit: 'abcdef1234567890',
      evidence,
      mode: 'live-hermes',
      ternVersion: '0.4.5',
      viewport: 'normal'
    })
    const replay = buildTernCaptureReceipt({
      commit: 'abcdef1234567890',
      evidence,
      mode: 'fixture-replay',
      ternVersion: '0.4.5',
      viewport: 'normal'
    })

    expect(live.liveTernVerified).toBe(true)
    expect(replay.liveTernVerified).toBe(false)
    expect(live.viewport).toEqual({ id: 'normal', columns: 120, rows: 36 })
  })

  it('marks attention measured only when actual glance observations are supplied', () => {
    const plain = buildTernCaptureReceipt({
      commit: 'abcdef1234567890',
      evidence,
      mode: 'live-hermes',
      ternVersion: '0.4.5',
      viewport: 'narrow'
    })
    const measured = buildTernCaptureReceipt({
      commit: 'abcdef1234567890',
      evidence,
      mode: 'live-hermes',
      ternVersion: '0.4.5',
      viewport: 'narrow',
      glance: {
        timeToNeedsUserMs: 410,
        answers: { doing: true, needsUser: true, next: true, type: true, inspect: false }
      }
    })

    expect(plain.attentionMeasured).toBe(false)
    expect(measured.attentionMeasured).toBe(true)
  })

  it('rejects untraceable evidence and unknown dimensions', () => {
    expect(() => buildTernCaptureReceipt({
      commit: 'not-a-sha',
      evidence,
      mode: 'live-hermes',
      ternVersion: '0.4.5',
      viewport: 'normal'
    })).toThrow(/commit SHA/)

    expect(() => buildTernCaptureReceipt({
      commit: 'abcdef1',
      evidence: { ...evidence, bytes: 0 },
      mode: 'live-hermes',
      ternVersion: '0.4.5',
      viewport: 'normal'
    })).toThrow(/evidence/)

    expect(() => buildTernCaptureReceipt({
      commit: 'abcdef1',
      evidence,
      mode: 'live-hermes',
      ternVersion: '0.4.5',
      viewport: 'tablet' as never
    })).toThrow(/Unknown viewport/)
  })
})
