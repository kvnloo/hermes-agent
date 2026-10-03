import type { PtyConnectionState } from "@/lib/pty-reconnect";

/**
 * Hard cap so a wedged resume (never gets PTY payload) cannot leave the
 * wait notice up forever.
 */
export const PTY_RESUME_LOADING_MAX_MS = 30000;

export const PTY_RESUME_LOADING_MESSAGE =
  "Please wait while the conversation loads…";

export interface ResumeLoadingOverlayInput {
  ptyState: PtyConnectionState;
  hydrating: boolean;
}

/**
 * Show a wait notice only while a resumed chat is still blank. Once the
 * first real PTY payload arrives the terminal has something to show, so
 * the notice hides and history can stream in underneath.
 *
 * `hydrating` alone encodes "a resume replay is in progress": it is set
 * only when a real resume target exists — either the `?resume=` URL param
 * (set before the socket opens) or the server's implicit active-session
 * control frame `{type:"resume", id:...}` (arrives after open, with no URL
 * param; see `beginResumeReplay` in ChatPage.tsx and `pty_ws` in
 * web_server.py). Gating on `hydrating` (not the URL param) keeps the
 * overlay on the implicit-fallback path, whose fresh `--resume` PTY boot
 * has the same blank window the explicit path does (#93518).
 *
 * Reconnect / ended / closed states keep their own overlays and must not
 * stack this one on top.
 */
export function shouldShowResumeLoadingOverlay({
  ptyState,
  hydrating,
}: ResumeLoadingOverlayInput): boolean {
  if (!hydrating) {
    return false;
  }
  if (
    ptyState === "reconnecting" ||
    ptyState === "closed" ||
    ptyState === "ended"
  ) {
    return false;
  }
  return ptyState === "connecting" || ptyState === "open";
}

/** First non-empty PTY chunk means the blank window is over. */
export function shouldFinishResumeHydrationOnChunk(chunkText: string): boolean {
  return chunkText.length > 0;
}
