/**
 * Recovers plain `insertText` letters that xterm 6.0 silently swallows on
 * Android keyboards (#136179).
 *
 * Gboard's English layout delivers every letter as a `keydown` with
 * `key = "Unidentified"` / `keyCode = 229` and **no matching keyup**, followed
 * by a `beforeinput`/`input` pair with `inputType = "insertText"`. xterm's
 * `_inputEvent` drops that insertText because `_keyDownSeen` is still armed
 * (`!e.composed || !this._keyDownSeen`) and the 229 never resolves into real
 * composition events — so mobile chat becomes paste-only. The tracker below
 * recognises exactly that dangling-229 shape and routes the letter through
 * the composition commit forwarder, which already defers to xterm's onData
 * and de-duplicates echoes. Every other shape is left to xterm: a 229 keyup
 * before the input, plain desktop keydowns, and real composition commits
 * (whose trailing insertText lands right after compositionend).
 */

import { shouldTreatInputAsMobileReplacement } from "./pty-mobile-input";

// A real composition commit can emit a trailing `insertText` input event a
// few milliseconds after compositionend; that path already owns the text, so
// the fallback must not arm for it. Matches the forwarder's echo window.
const RECENT_COMPOSITION_END_MS = 80;

export function isImePlaceholderKey(
  ev: Pick<KeyboardEvent, "keyCode" | "key">,
): boolean {
  return ev.keyCode === 229 || ev.key === "Unidentified";
}

// A keydown and its browser beforeinput normally happen in the same short
// event sequence. After this window, a plain insertText without new key
// events is treated as the independent beforeinput-only path (#137986).
const KEYDOWN_PAIR_WINDOW_MS = 80;

export function createDanglingImeInsertTextTracker() {
  let danglingImeKeydown = false;
  let lastKeydownAt: number | null = null;
  let lastCompositionEndAt: number | null = null;
  let composing = false;

  const classifyFallback = (
    ev: Pick<InputEvent, "inputType" | "data">,
    now: number = Date.now(),
  ): "dangling" | "beforeinput-only" | null => {
    if (ev.inputType !== "insertText" || !ev.data || composing) return null;
    if (
      lastCompositionEndAt !== null &&
      now - lastCompositionEndAt <= RECENT_COMPOSITION_END_MS
    ) return null;

    if (lastKeydownAt === null || now - lastKeydownAt > KEYDOWN_PAIR_WINDOW_MS) {
      return "beforeinput-only";
    }
    return danglingImeKeydown ? "dangling" : null;
  };

  return {
    onKeydown(ev: Pick<KeyboardEvent, "keyCode" | "key">, at: number = Date.now()) {
      danglingImeKeydown = isImePlaceholderKey(ev);
      lastKeydownAt = at;
    },
    onKeyup(ev: Pick<KeyboardEvent, "keyCode" | "key">) {
      // A keyup for the placeholder key means the sequence is not dangling
      // and xterm will deliver the input itself.
      if (isImePlaceholderKey(ev)) {
        danglingImeKeydown = false;
      }
    },
    noteCompositionStart() {
      composing = true;
    },
    noteCompositionEnd(at: number = Date.now()) {
      composing = false;
      lastCompositionEndAt = at;
    },
    classifyFallback,
    shouldFallback(
      ev: Pick<InputEvent, "inputType" | "data">,
      now: number = Date.now(),
    ): boolean {
      return classifyFallback(ev, now) !== null;
    },
  };
}

export interface PtyTextareaInputGuardHooks {
  isMobileLike: boolean;
  markReplacementWindow(): void;
  /** compositionend commits — the composition forwarder's main channel. */
  onCompositionCommit(data: string | null): void;
  /** insertText letters xterm swallowed behind a dangling IME keydown. */
  onDanglingInsertText(data: string): void;
  /** Plain beforeinput on devices that emit no keydown/composition events. */
  onBeforeInputOnly(data: string): void;
}

/**
 * Installs the terminal textarea's mobile-input listeners (replacement
 * window marking, composition commits, and the dangling-229 insertText
 * fallback) and returns their cleanup.
 */
export function attachPtyTextareaInputGuards(
  textarea: HTMLTextAreaElement,
  hooks: PtyTextareaInputGuardHooks,
): () => void {
  const tracker = createDanglingImeInsertTextTracker();

  const onBeforeInput = (ev: Event) => {
    const input = ev as InputEvent;
    if (
      shouldTreatInputAsMobileReplacement(
        input.inputType,
        input.data,
        hooks.isMobileLike,
      )
    ) {
      hooks.markReplacementWindow();
    }
    const fallback = hooks.isMobileLike ? tracker.classifyFallback(input) : null;
    if (fallback === "dangling") {
      hooks.onDanglingInsertText(input.data ?? "");
    } else if (fallback === "beforeinput-only") {
      hooks.onBeforeInputOnly(input.data ?? "");
    }
  };
  const onCompositionStart = () => tracker.noteCompositionStart();
  const onCompositionEnd = (ev: CompositionEvent) => {
    hooks.markReplacementWindow();
    tracker.noteCompositionEnd();
    hooks.onCompositionCommit(ev.data);
  };
  const onKeydown = (ev: KeyboardEvent) => tracker.onKeydown(ev);
  const onKeyup = (ev: KeyboardEvent) => tracker.onKeyup(ev);

  textarea.addEventListener("beforeinput", onBeforeInput, true);
  textarea.addEventListener("compositionstart", onCompositionStart, true);
  textarea.addEventListener("compositionend", onCompositionEnd, true);
  textarea.addEventListener("keydown", onKeydown, true);
  textarea.addEventListener("keyup", onKeyup, true);
  // The dashboard's host-level IME guard (#52111) stops keyCode-229 keydowns
  // before they reach the textarea; observe at document capture — above the
  // guard — so the dangling-229 tracker can arm for Gboard's letters.
  const keyEventDoc = textarea.ownerDocument;
  // Document capture sees a key destined for this textarea even if the host
  // swallows propagation. Ignore keys targeting other dashboard controls.
  const onDocumentKeydown = (ev: KeyboardEvent) => {
    if (ev.target === textarea) onKeydown(ev);
  };
  const onDocumentKeyup = (ev: KeyboardEvent) => {
    if (ev.target === textarea) onKeyup(ev);
  };
  keyEventDoc.addEventListener("keydown", onDocumentKeydown, true);
  keyEventDoc.addEventListener("keyup", onDocumentKeyup, true);
  return () => {
    textarea.removeEventListener("beforeinput", onBeforeInput, true);
    textarea.removeEventListener("compositionstart", onCompositionStart, true);
    textarea.removeEventListener("compositionend", onCompositionEnd, true);
    textarea.removeEventListener("keydown", onKeydown, true);
    textarea.removeEventListener("keyup", onKeyup, true);
    keyEventDoc.removeEventListener("keydown", onDocumentKeydown, true);
    keyEventDoc.removeEventListener("keyup", onDocumentKeyup, true);
  };
}
