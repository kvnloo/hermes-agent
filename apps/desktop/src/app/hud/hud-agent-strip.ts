/** Cover-flow-lite index math for the HUD app strip. No Hyprland calls. */

export type AgentTarget = { app: string; id: number; title: string }

export function stepAgentTarget(windows: AgentTarget[], selectedId: number | null, delta: -1 | 1): number | null {
  if (windows.length === 0) {
    return null
  }

  const current = windows.findIndex(window => window.id === selectedId)
  const index = current < 0 ? 0 : (current + delta + windows.length) % windows.length

  return windows[index]?.id ?? null
}

export function neighbors(windows: AgentTarget[], selectedId: number | null): {
  center: AgentTarget | null
  left: AgentTarget | null
  right: AgentTarget | null
} {
  if (windows.length === 0) {
    return { center: null, left: null, right: null }
  }

  const current = Math.max(0, windows.findIndex(window => window.id === selectedId))
  const last = windows.length - 1

  return {
    center: windows[current] ?? null,
    left: windows[current === 0 ? last : current - 1] ?? null,
    right: windows[current === last ? 0 : current + 1] ?? null
  }
}
