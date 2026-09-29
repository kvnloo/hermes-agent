export interface ToolRowBudgetCandidate {
  fixedRows?: number
  index: number
  key: string
}

export const visibleRowSpan = (
  rowTop: number,
  rowBottom: number,
  viewportTop: number,
  viewportBottom: number
): number => Math.max(0, Math.min(rowBottom, viewportBottom) - Math.max(rowTop, viewportTop))

export const allocateToolRowBudgets = ({
  candidates,
  maxRowsPerTool = 3,
  occupiedRows,
  viewportHeight
}: {
  candidates: readonly ToolRowBudgetCandidate[]
  maxRowsPerTool?: number
  occupiedRows: number
  viewportHeight: number
}): Map<string, number> => {
  const budgets = new Map<string, number>()
  const maxRows = Math.max(1, Math.trunc(maxRowsPerTool))
  let committedRows = Math.max(0, Math.ceil(occupiedRows))

  for (const candidate of candidates) {
    budgets.set(candidate.key, 1)
    committedRows += 1 + Math.max(0, Math.ceil(candidate.fixedRows ?? 0))
  }

  let surplus = Math.max(0, Math.floor(viewportHeight) - committedRows)

  // Newer tools receive spare attention first. Every visible candidate already
  // owns one truthful row, so surplus only upgrades 1 → 2 → 3+.
  const newestFirst = [...candidates].sort((a, b) => b.index - a.index)

  for (const candidate of newestFirst) {
    if (surplus <= 0) {
      break
    }

    const current = budgets.get(candidate.key) ?? 1
    const extra = Math.min(Math.max(0, maxRows - current), surplus)

    budgets.set(candidate.key, current + extra)
    surplus -= extra
  }

  return budgets
}
