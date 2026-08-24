// Stream-aware background throttling for chat windows.
//
// Each visible chat window must keep painting while blurred. Hidden windows are
// unthrottled only while their own renderer reports active work, then for a
// short trailing interval so the final coalesced flush can land. State is
// intentionally per-window: one profile's stream must not wake its siblings.

const RETHROTTLE_DELAY_MS = 5_000

export interface ThrottleWindowLike {
  isDestroyed(): boolean
  isMinimized?(): boolean
  isVisible?(): boolean
  webContents?: {
    isDestroyed(): boolean
    setBackgroundThrottling(allowed: boolean): void
  } | null
}

interface TimersLike {
  clearTimeout(handle: unknown): void
  setTimeout(fn: () => void, ms: number): unknown
}

export interface StreamThrottle {
  /** True while this window (or any window when omitted) is stream-unthrottled. */
  isUnthrottled(win?: ThrottleWindowLike): boolean
  register(win: ThrottleWindowLike & { on?: (event: string, fn: () => void) => void }): void
  update(win: ThrottleWindowLike, busy: boolean): void
}

interface WindowThrottleState {
  trailing: unknown | null
  unthrottled: boolean
}

export function createStreamThrottle(
  timers: TimersLike = { clearTimeout: handle => clearTimeout(handle as never), setTimeout },
  delayMs: number = RETHROTTLE_DELAY_MS
): StreamThrottle {
  const windows = new Map<ThrottleWindowLike, WindowThrottleState>()

  function remove(win: ThrottleWindowLike) {
    const state = windows.get(win)
    if (state?.trailing !== null && state?.trailing !== undefined) {
      timers.clearTimeout(state.trailing)
    }
    windows.delete(win)
  }

  /** Missing or throwing probes fail closed: only positively on-screen windows
   * bypass Chromium throttling while idle. */
  function isOnScreen(win: ThrottleWindowLike): boolean {
    try {
      return win.isVisible?.() === true && win.isMinimized?.() !== true
    } catch {
      return false
    }
  }

  function apply(win: ThrottleWindowLike, state: WindowThrottleState) {
    if (win.isDestroyed()) {
      remove(win)
      return
    }
    const contents = win.webContents
    if (!contents || contents.isDestroyed()) {
      remove(win)
      return
    }
    try {
      contents.setBackgroundThrottling(!state.unthrottled && !isOnScreen(win))
    } catch {
      // A window mid-teardown can throw; its close event removes it.
    }
  }

  return {
    isUnthrottled: win =>
      win ? (windows.get(win)?.unthrottled ?? false) : [...windows.values()].some(state => state.unthrottled),

    register(win) {
      if (windows.has(win)) return
      const state: WindowThrottleState = { trailing: null, unthrottled: false }
      windows.set(win, state)
      win.on?.('closed', () => remove(win))
      for (const event of ['minimize', 'restore', 'show', 'hide']) {
        win.on?.(event, () => {
          const current = windows.get(win)
          if (current) apply(win, current)
        })
      }
      apply(win, state)
    },

    update(win, busy) {
      const state = windows.get(win)
      if (!state) return
      if (busy) {
        if (state.trailing !== null) {
          timers.clearTimeout(state.trailing)
          state.trailing = null
        }
        if (!state.unthrottled) {
          state.unthrottled = true
          apply(win, state)
        }
        return
      }
      if (!state.unthrottled || state.trailing !== null) return
      state.trailing = timers.setTimeout(() => {
        state.trailing = null
        state.unthrottled = false
        apply(win, state)
      }, delayMs)
    }
  }
}
