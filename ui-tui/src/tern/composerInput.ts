export interface NativeSendState {
  draft: string
  blocked: boolean
  busy: boolean
  completions: number
  bufferedLines: number
  sendEnabled: boolean
}

export interface NativeSendOwner {
  read: () => NativeSendState
  clearDraft: () => void
  submit: (text: string) => void
}

/** Called by the live surface's send event, never by fixture controls.
 * Read current application readiness; do not capture it at surface mount.
 * Buffered-line and completion semantics remain on the existing input path. */
export function dispatchNativeSend(text: string, owner: NativeSendOwner): boolean {
  const state = owner.read()
  if (
    state.blocked || state.busy || !state.sendEnabled ||
    state.completions > 0 || state.bufferedLines > 0 ||
    !text.trim() || text !== state.draft
  ) return false

  // The owner clears its synchronous bridge snapshot before dispatch. A second
  // event, even reentrant from submit, cannot replay the previous draft.
  owner.clearDraft()
  owner.submit(text)
  return true
}
