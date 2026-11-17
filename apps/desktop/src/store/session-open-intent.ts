// Bumped when the person opens a chat in this window (sidebar row, ⌘K, a
// notification, the session switcher: every door goes through openSession).
// Route effects that select a chat on their own (the cold-start route resume,
// runtime recovery) never bump it, so a background restore can tell a chat the
// user chose, which it must leave open, from one selected automatically.
// Explicit user selection, not passive route/session hydration. The sidebar
// provider consumes this to dismiss the *real* narrow layout-tree overlay.
export const USER_SESSION_OPEN_EVENT = 'hermes:user-session-open'

let userSessionOpenRevision = 0

/** The revision at window start. Module load precedes any input, so a launch
 *  restore compares against this rather than a value read once boot reaches
 *  the registry: the connecting overlay lifts at the socket open while config
 *  still loads, and a chat clicked in that gap would otherwise become the
 *  baseline and be closed by the restore. */
export const LAUNCH_USER_SESSION_OPEN = 0

export function currentUserSessionOpen(): number {
  return userSessionOpenRevision
}

export function noteUserSessionOpen(): void {
  userSessionOpenRevision += 1
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new Event(USER_SESSION_OPEN_EVENT))
  }
}

export function _resetUserSessionOpenForTests(): void {
  userSessionOpenRevision = LAUNCH_USER_SESSION_OPEN
}
