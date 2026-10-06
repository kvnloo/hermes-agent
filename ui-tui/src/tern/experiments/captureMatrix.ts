import { EXPERIMENT_VIEWPORTS } from './fixture.js'

export interface CaptureReceiptLike {
  commit: string
  liveTernVerified: boolean
  mode: string
  ternVersion: string
  viewport: { id: string; columns: number; rows: number }
}

export function verifyTernCaptureMatrix(receipts: readonly CaptureReceiptLike[]) {
  const live = receipts.filter(receipt => receipt.mode === 'live-hermes' && receipt.liveTernVerified)

  if (live.length !== EXPERIMENT_VIEWPORTS.length) {
    throw new Error(`Expected ${EXPERIMENT_VIEWPORTS.length} live-Hermes receipts, got ${live.length}`)
  }

  const byId = new Map(live.map(receipt => [receipt.viewport.id, receipt]))

  for (const viewport of EXPERIMENT_VIEWPORTS) {
    const receipt = byId.get(viewport.id)

    if (!receipt) {
      throw new Error(`Missing live capture for ${viewport.id}`)
    }

    if (receipt.viewport.columns !== viewport.columns || receipt.viewport.rows !== viewport.rows) {
      throw new Error(`Wrong dimensions for ${viewport.id}`)
    }
  }

  const commits = new Set(live.map(receipt => receipt.commit))
  const versions = new Set(live.map(receipt => receipt.ternVersion))

  if (commits.size !== 1) {
    throw new Error('Capture matrix must use one Variant A commit')
  }

  if (versions.size !== 1) {
    throw new Error('Capture matrix must use one Tern version')
  }

  return {
    commit: live[0]!.commit,
    ternVersion: live[0]!.ternVersion,
    viewports: EXPERIMENT_VIEWPORTS.map(viewport => viewport.id),
    complete: true
  }
}
