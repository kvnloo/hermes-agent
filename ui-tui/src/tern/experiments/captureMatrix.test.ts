import { describe, expect, it } from 'vitest'

import { verifyTernCaptureMatrix, type CaptureReceiptLike } from './captureMatrix.js'

const receipt = (id: 'narrow' | 'normal' | 'wide'): CaptureReceiptLike => ({
  commit: 'abcdef1234567890',
  liveTernVerified: true,
  mode: 'live-hermes',
  ternVersion: '0.4.5',
  viewport:
    id === 'narrow'
      ? { id, columns: 80, rows: 28 }
      : id === 'normal'
        ? { id, columns: 120, rows: 36 }
        : { id, columns: 180, rows: 44 }
})

describe('real Tern capture matrix', () => {
  it('requires all three canonical live viewports on one build', () => {
    expect(verifyTernCaptureMatrix([receipt('narrow'), receipt('normal'), receipt('wide')])).toEqual({
      commit: 'abcdef1234567890',
      ternVersion: '0.4.5',
      viewports: ['narrow', 'normal', 'wide'],
      complete: true
    })
  })

  it('rejects replay receipts and mixed builds', () => {
    expect(() =>
      verifyTernCaptureMatrix([
        receipt('narrow'),
        { ...receipt('normal'), mode: 'fixture-replay', liveTernVerified: false },
        receipt('wide')
      ])
    ).toThrow(/3 live-Hermes/)

    expect(() =>
      verifyTernCaptureMatrix([
        receipt('narrow'),
        { ...receipt('normal'), commit: '1234567' },
        receipt('wide')
      ])
    ).toThrow(/one Variant A commit/)
  })
})
