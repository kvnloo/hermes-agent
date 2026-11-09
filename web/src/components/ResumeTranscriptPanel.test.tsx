// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, expect, it, vi } from "vitest";

const apiMocks = vi.hoisted(() => ({ getSessionMessages: vi.fn() }));
vi.mock("@/lib/api", () => ({ api: apiMocks }));

import { useResumeTranscript } from "./ResumeTranscriptPanel";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function ResumeProbe() {
  const transcript = useResumeTranscript("sid", "worker");
  return <span>{transcript?.messages?.length ?? "loading"}</span>;
}

describe("useResumeTranscript", () => {
  it("fetches once when a stable resume target finishes hydrating", async () => {
    apiMocks.getSessionMessages.mockReset();
    apiMocks.getSessionMessages.mockResolvedValueOnce({
      messages: [{ role: "user", content: "hello" }],
    });
    // On the broken head, the second fetch must not resolve and recursively
    // trigger further effects; count the duplicate request instead.
    apiMocks.getSessionMessages.mockImplementation(
      () => new Promise(() => {}),
    );

    const container = document.createElement("div");
    document.body.append(container);
    const root = createRoot(container);
    try {
      await act(async () => {
        root.render(<ResumeProbe />);
      });

      expect(container.textContent).toBe("1");
      expect(apiMocks.getSessionMessages).toHaveBeenCalledTimes(1);
      expect(apiMocks.getSessionMessages).toHaveBeenCalledWith("sid", "worker");

      await act(async () => {
        root.render(<ResumeProbe />);
      });
      expect(apiMocks.getSessionMessages).toHaveBeenCalledTimes(1);
    } finally {
      await act(async () => root.unmount());
      container.remove();
    }
  });
});
