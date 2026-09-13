import { describe, expect, it } from "vitest";

import { PtyResumeSanitizer } from "./pty-resume-sanitizer";
import {
  PTY_RESUME_LOADING_MAX_MS,
  shouldFinishResumeHydrationOnChunk,
  shouldShowResumeLoadingOverlay,
} from "./pty-resume-loading";

describe("shouldFinishResumeHydrationOnChunk", () => {
  it("finishes on the first non-empty chunk", () => {
    expect(shouldFinishResumeHydrationOnChunk("")).toBe(false);
    expect(shouldFinishResumeHydrationOnChunk("hello")).toBe(true);
  });

  it("keeps a positive hard-cap timeout for wedged resumes", () => {
    expect(PTY_RESUME_LOADING_MAX_MS).toBeGreaterThan(0);
  });
});

describe("resume hydration gate over the real sanitizer", () => {
  // Regression: the gate must key off the payload actually written to xterm,
  // not the raw frame. The sanitizer collapses an erase-only / all-newline /
  // partial-CSI resume frame to "", so a nonempty raw first frame would
  // otherwise clear the wait notice while the terminal is still blank.
  const ESC = String.fromCharCode(27);
  const CRLF = String.fromCharCode(13, 10);
  const VISIBLE = `Hello world${CRLF}`;

  const controlOnlyFirstFrames: Array<[string, string]> = [
    ["erase-only", `${ESC}[2K`],
    ["all-newline", `${CRLF}${CRLF}`],
    ["partial-CSI", `${ESC}[`],
  ];

  it.each(controlOnlyFirstFrames)(
    "keeps hydrating on a %s first frame, then finishes on visible replay",
    (_label, firstFrame) => {
      const sanitizer = new PtyResumeSanitizer();

      // Raw first frame is nonempty, but nothing is written to xterm...
      expect(firstFrame.length).toBeGreaterThan(0);
      const firstRendered = sanitizer.next(firstFrame);
      expect(firstRendered).toBe("");
      expect(shouldFinishResumeHydrationOnChunk(firstRendered)).toBe(false);

      // ...so the notice only clears once real replay output arrives.
      const secondRendered = sanitizer.next(VISIBLE);
      expect(secondRendered.length).toBeGreaterThan(0);
      expect(shouldFinishResumeHydrationOnChunk(secondRendered)).toBe(true);
    },
  );
});

describe("shouldShowResumeLoadingOverlay", () => {
  // The overlay keys on `hydrating` alone (not the URL `?resume=` param):
  // `resumeHydrating` is set both for explicit `?resume=` chats (at the top
  // of the connect effect) and for an implicit server-announced resume
  // (`beginResumeReplay` after the active-session control frame arrives,
  // with no `?resume=` on the URL — see `pty_ws` in web_server.py, #93518).
  // Both paths spawn a fresh `--resume` PTY with the same blank boot window,
  // so both must show the overlay for `hydrating && (connecting|open)`.
  // Regression: the old helper took `hasResumeTarget: Boolean(resumeParam)`,
  // which suppressed the overlay on the implicit path.
  it("shows while connecting or open and still hydrating (explicit or implicit resume)", () => {
    expect(
      shouldShowResumeLoadingOverlay({
        ptyState: "connecting",
        hydrating: true,
      }),
    ).toBe(true);
    expect(
      shouldShowResumeLoadingOverlay({
        ptyState: "open",
        hydrating: true,
      }),
    ).toBe(true);
  });

  it("hides once hydration finishes", () => {
    expect(
      shouldShowResumeLoadingOverlay({
        ptyState: "open",
        hydrating: false,
      }),
    ).toBe(false);
  });

  it("defers to reconnect / closed / ended overlays", () => {
    for (const ptyState of ["reconnecting", "closed", "ended"] as const) {
      expect(
        shouldShowResumeLoadingOverlay({
          ptyState,
          hydrating: true,
        }),
      ).toBe(false);
    }
  });
});
