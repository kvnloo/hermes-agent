// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { createImeTextInput, textareaEditToPtyData } from "./pty-ime-text-input";

const DEL = "\x7f";

describe("textareaEditToPtyData", () => {
  it("sends only the appended text", () => {
    expect(textareaEditToPtyData("h", "he")).toBe("e");
  });

  it("sends a DEL per removed character", () => {
    expect(textareaEditToPtyData("helo", "hel")).toBe(DEL);
  });

  it("rewrites a replaced tail as DELs plus the new tail", () => {
    expect(textareaEditToPtyData("hello wrold", "hello world ")).toBe(`${DEL.repeat(4)}orld `);
  });

  it("counts an emoji as one character", () => {
    expect(textareaEditToPtyData("hi 👋", "hi ")).toBe(DEL);
  });
});

// Event sequences recorded from Android Chrome + Gboard on the dashboard chat:
// every keystroke is keydown(229) → beforeinput → input, with no composition events.
function mountTextarea(allowBeforeInputOnly = false) {
  const textarea = document.createElement("textarea");
  document.body.appendChild(textarea);
  const sent: string[] = [];
  const ime = createImeTextInput(textarea, (data) => sent.push(data), allowBeforeInputOnly);

  const keydown = (keyCode: number, key = "Unidentified") => {
    const ev = new KeyboardEvent("keydown", { key, keyCode, bubbles: true });
    textarea.dispatchEvent(ev);
    return ev;
  };
  const edit = (inputType: string, data: string | null, after: string, isComposing = false) => {
    textarea.dispatchEvent(new InputEvent("beforeinput", { inputType, data, isComposing, bubbles: true }));
    textarea.value = after;
    textarea.dispatchEvent(new InputEvent("input", { inputType, data, isComposing, bubbles: true }));
  };
  return { textarea, sent, ime, keydown, edit };
}

describe("createImeTextInput", () => {
  let dispose: (() => void) | null = null;
  afterEach(() => {
    dispose?.();
    dispose = null;
    document.body.innerHTML = "";
  });

  it("recovers no-keydown mobile Gboard taps, including rapid identical letters", () => {
    const t = mountTextarea(true);
    dispose = t.ime.dispose;

    // Two Android #137986 beforeinput/input pairs. No keydown or composition.
    t.edit("insertText", "l", "l");
    t.edit("insertText", "l", "ll");

    expect(t.sent).toEqual(["l", "l"]);
  });

  it("recovers corrections and double-space edits without any keydown", () => {
    const t = mountTextarea(true);
    dispose = t.ime.dispose;
    t.textarea.value = "helo";

    t.edit("deleteContentBackward", null, "hel");
    t.edit("insertText", "lo ", "hello ");
    t.edit("deleteContentBackward", null, "hello");
    t.edit("insertText", ". ", "hello. ");

    expect(t.sent.join("")).toBe(`${DEL}lo ${DEL}. `);
  });

  it("leaves input-only events alone without the mobile opt-in", () => {
    const t = mountTextarea();
    dispose = t.ime.dispose;

    t.edit("insertText", "a", "a");
    expect(t.sent).toEqual([]);
  });

  it("does not steal a hardware key or later keyless input after one hardware key", () => {
    const t = mountTextarea(true);
    dispose = t.ime.dispose;

    const ev = t.keydown(65, "a");
    t.edit("insertText", "a", "a");
    t.edit("insertText", "b", "ab");

    expect(t.ime.xtermShouldHandleKeydown(ev)).toBe(true);
    expect(t.sent).toEqual([]);
  });

  it("protects an open composition and its trailing insertText, then resumes", () => {
    vi.useFakeTimers();
    try {
      vi.setSystemTime(new Date("2026-10-13T12:00:00Z"));
      const t = mountTextarea(true);
      dispose = t.ime.dispose;

      t.textarea.dispatchEvent(new CompositionEvent("compositionstart"));
      t.edit("insertCompositionText", "中", "中", true);
      expect(t.sent).toEqual([]);

      t.textarea.dispatchEvent(new CompositionEvent("compositionend", { data: "中" }));
      t.edit("insertText", "中", "中");
      expect(t.sent).toEqual([]);

      vi.advanceTimersByTime(81);
      t.edit("insertText", "x", "中x");
      expect(t.sent).toEqual(["x"]);
    } finally {
      vi.useRealTimers();
    }
  });

  it("removes the no-keydown listeners on disposal", () => {
    const t = mountTextarea(true);
    t.ime.dispose();
    dispose = null;
    t.edit("insertText", "x", "x");
    expect(t.sent).toEqual([]);
  });

  it("turns a Gboard spelling correction into DEL + the corrected tail", () => {
    const t = mountTextarea();
    dispose = t.ime.dispose;
    t.textarea.value = "helo";

    t.keydown(229);
    t.edit("deleteContentBackward", null, "hel");
    t.keydown(229);
    t.edit("insertText", "lo ", "hello ");

    expect(t.sent.join("")).toBe(`${DEL}lo `);
  });

  it("turns Gboard's double-space period into DEL + '. '", () => {
    const t = mountTextarea();
    dispose = t.ime.dispose;
    t.textarea.value = "hello world ";

    t.keydown(229);
    t.edit("deleteContentBackward", null, "hello world");
    t.keydown(229);
    t.edit("insertText", ". ", "hello world. ");

    expect(t.sent.join("")).toBe(`${DEL}. `);
  });

  it("leaves keys with a real keyCode to xterm", () => {
    const t = mountTextarea();
    dispose = t.ime.dispose;

    const ev = t.keydown(65, "a");
    t.edit("insertText", "a", "a");

    expect(t.sent).toEqual([]);
    expect(t.ime.xtermShouldHandleKeydown(ev)).toBe(true);
  });

  it("takes keyCode-229 keydowns away from xterm outside a composition", () => {
    const t = mountTextarea();
    dispose = t.ime.dispose;

    expect(t.ime.xtermShouldHandleKeydown(t.keydown(229))).toBe(false);
  });

  it("leaves IME compositions to xterm's composition handling", () => {
    const t = mountTextarea();
    dispose = t.ime.dispose;

    t.textarea.dispatchEvent(new CompositionEvent("compositionstart", { data: "" }));
    const ev = t.keydown(229);
    t.edit("insertCompositionText", "ni", "ni", true);

    expect(t.sent).toEqual([]);
    expect(t.ime.xtermShouldHandleKeydown(ev)).toBe(true);
  });
});
