// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { bindDesktopPtyImeInput } from "./pty-desktop-ime";

describe("bindDesktopPtyImeInput (#106487)", () => {
  afterEach(() => vi.useRealTimers());

  function harness() {
    const textarea = document.createElement("textarea");
    const send = vi.fn<(data: string) => void>();
    const cleanup = bindDesktopPtyImeInput(textarea, send);
    return { textarea, send, cleanup };
  }

  function bareCommit(textarea: HTMLTextAreaElement, data: string) {
    const ev = new InputEvent("input", {
      inputType: "insertText", data, bubbles: true, cancelable: true,
    });
    textarea.dispatchEvent(ev);
    return ev;
  }

  it("preserves a distinct CJK commit inside the composition echo window", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-16T12:00:00Z"));
    const { textarea, send, cleanup } = harness();
    textarea.dispatchEvent(new CompositionEvent("compositionend", { data: "你" }));
    vi.advanceTimersByTime(40);
    const echo = bareCommit(textarea, "你");
    const next = bareCommit(textarea, "好");

    expect(echo.defaultPrevented).toBe(true);
    expect(next.defaultPrevented).toBe(true);
    expect(send.mock.calls.map(([text]) => text)).toEqual(["你", "好"]);
    cleanup();
  });

  it("does not forward pre-commit insertText before compositionend", () => {
    const { textarea, send, cleanup } = harness();
    textarea.dispatchEvent(new CompositionEvent("compositionstart"));
    // Some browsers set isComposing=false on their final input.
    bareCommit(textarea, "中文");
    textarea.dispatchEvent(new CompositionEvent("compositionend", { data: "中文" }));

    expect(send).toHaveBeenCalledExactlyOnceWith("中文");
    cleanup();
  });

  it("forwards bare CJK after cancelled composition", () => {
    const { textarea, send, cleanup } = harness();
    textarea.dispatchEvent(new CompositionEvent("compositionend", { data: "" }));
    bareCommit(textarea, "文字");
    expect(send).toHaveBeenCalledExactlyOnceWith("文字");
    cleanup();
  });
});
