import { useStore } from '@nanostores/react'
import { useCallback, useEffect, useState } from 'react'

import { offerSuggestions } from '@/store/composer-suggestions'
import { $hudSession } from '@/store/hud'

import { type AgentTarget, neighbors, stepAgentTarget } from './hud-agent-strip'

/**
 * Horizontal app strip for HUD agent-mode (PER-582). Lives in HudShell — not a
 * second overlay window. Left/right (and click) pick the computer-use target;
 * pin reuses promoteHudOverlay on Hyprland.
 */
export function HudAgentStrip() {
  const sessionId = useStore($hudSession)
  const [windows, setWindows] = useState<AgentTarget[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [pinned, setPinned] = useState(false)

  const refresh = useCallback(async () => {
    const listed = await window.hermesDesktop?.hud?.listHyprlandWindows?.()

    if (!listed || listed.length === 0) {
      setWindows([])

      return
    }

    setWindows(listed)
    setSelectedId(current => (current && listed.some(window => window.id === current) ? current : listed[0].id))
  }, [])

  useEffect(() => {
    void refresh()
    const timer = setInterval(() => void refresh(), 1500)

    return () => clearInterval(timer)
  }, [refresh])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {
        return
      }

      event.preventDefault()
      setSelectedId(current => stepAgentTarget(windows, current, event.key === 'ArrowLeft' ? -1 : 1))
    }

    window.addEventListener('keydown', onKey)

    return () => window.removeEventListener('keydown', onKey)
  }, [windows])

  useEffect(() => {
    const selected = windows.find(window => window.id === selectedId)

    if (!selected) {
      offerSuggestions(sessionId, 'hud-agent-strip', [])

      return
    }

    offerSuggestions(sessionId, 'hud-agent-strip', [
      {
        id: String(selected.id),
        provider: 'hud-agent-strip',
        label: `Target ${selected.app}`,
        tip: selected.title || selected.app,
        icon: 'window',
        invoke: async () => undefined,
        workingLabel: `Targeting ${selected.app}…`,
        workingTip: selected.title || selected.app,
        doneLabel: `Target ${selected.app}`,
        doneTip: 'Computer-use / read_window_below aim this app'
      }
    ])

    return () => offerSuggestions(sessionId, 'hud-agent-strip', [])
  }, [selectedId, sessionId, windows])

  const shown = neighbors(windows, selectedId)

  const pin = async () => {
    const ok = await window.hermesDesktop?.hud?.pinOverlay?.()
    setPinned(Boolean(ok?.ok))
  }

  if (windows.length === 0) {
    return null
  }

  return (
    <div
      className="pointer-events-auto flex items-center justify-center gap-2 px-3 py-1"
      data-hud-agent-strip
      role="listbox"
      aria-label="HUD agent target apps"
    >
      {[shown.left, shown.center, shown.right].map((item, index) => {
        if (!item) {
          return null
        }

        const center = index === 1

        return (
          <button
            aria-selected={center}
            className={center ? 'px-2 text-sm font-medium opacity-100' : 'px-2 text-xs opacity-50'}
            key={`${item.id}-${index}`}
            onClick={() => setSelectedId(item.id)}
            role="option"
            type="button"
          >
            {item.app}
          </button>
        )
      })}
      <button aria-pressed={pinned} data-hud-pin type="button" onClick={() => void pin()}>
        {pinned ? 'Pinned' : 'Pin HUD'}
      </button>
    </div>
  )
}
