// Text input from keyboards that report every keystroke as keyCode 229
// without composition events (Android Gboard, IMEs typing punctuation).
//
// xterm 6 recovers that input in CompositionHelper._handleAnyTextareaChanges:
// it snapshots the textarea at each 229 keydown and on the next tick sends
// `newValue.replace(oldValue, "")`. That only holds for a pure append. Gboard
// applies a spelling correction or its double-space period as two 229
// keystrokes in one task (delete, then insert), so the first snapshot is no
// longer a substring and xterm sends the whole textarea ("helo" + "hello " +
// "lo "), the second sends the insert again, and the delete is never sent.
//
// This takes that input over: each beforeinput/input pair is translated into
// the exact edit at the end of the line — a DEL per removed character, then
// the inserted text — and xterm's 229 handler is skipped. Keys with a real
// keyCode and IME compositions stay on xterm's own paths.
//
// Some Android Gboard combinations instead emit beforeinput/input only,
// without keydown or composition events (#137986). The mobile-only opt-in
// handles those until any real keydown is observed on this textarea; unlike
// a timing heuristic, it will not steal a later hardware key sequence.

const DELETE = "\x7f";
const COMPOSITION_END_GRACE_MS = 80;

export function textareaEditToPtyData(before: string, after: string): string {
  const removed = Array.from(before);
  const added = Array.from(after);
  let common = 0;
  while (common < removed.length && common < added.length && removed[common] === added[common]) {
    common++;
  }
  return DELETE.repeat(removed.length - common) + added.slice(common).join("");
}

// Pastes and drops are routed through term.paste; compositions belong to
// xterm's CompositionHelper.
function isOwnInputType(inputType: string): boolean {
  return !/Composition|FromPaste|FromDrop/.test(inputType);
}

export function createImeTextInput(
  textarea: HTMLTextAreaElement,
  emit: (data: string) => void,
  allowBeforeInputOnly = false,
) {
  let lastKeydownWasIme = false;
  let sawKeydown = false;
  let composing = false;
  let lastCompositionEndAt: number | null = null;
  let before: string | null = null;

  const owns = (ev: InputEvent) => {
    const inputOnly =
      allowBeforeInputOnly &&
      !sawKeydown &&
      (lastCompositionEndAt === null ||
        Date.now() - lastCompositionEndAt > COMPOSITION_END_GRACE_MS);
    return (
      (lastKeydownWasIme || inputOnly) &&
      !composing &&
      !ev.isComposing &&
      isOwnInputType(ev.inputType)
    );
  };

  const onKeydown = (ev: KeyboardEvent) => {
    sawKeydown = true;
    lastKeydownWasIme = ev.keyCode === 229;
  };
  const onCompositionStart = () => {
    composing = true;
  };
  const onCompositionEnd = () => {
    composing = false;
    lastCompositionEndAt = Date.now();
  };
  const onBeforeInput = (ev: Event) => {
    before = owns(ev as InputEvent) ? textarea.value : null;
  };
  const onInput = (ev: Event) => {
    // Ownership was decided by beforeinput, never by a later key event.
    if (
      before === null ||
      composing ||
      (ev as InputEvent).isComposing ||
      !isOwnInputType((ev as InputEvent).inputType)
    ) {
      before = null;
      return;
    }
    const data = textareaEditToPtyData(before, textarea.value);
    before = null;
    if (data) emit(data);
  };

  const listeners: [string, EventListener][] = [
    ["keydown", onKeydown as EventListener],
    ["compositionstart", onCompositionStart],
    ["compositionend", onCompositionEnd],
    ["beforeinput", onBeforeInput],
    ["input", onInput],
  ];
  for (const [type, fn] of listeners) textarea.addEventListener(type, fn, true);

  return {
    // For term.attachCustomKeyEventHandler: false hands the keystroke to this
    // module so xterm's replace()-based recovery does not run alongside it.
    xtermShouldHandleKeydown: (ev: KeyboardEvent) =>
      !(ev.type === "keydown" && ev.keyCode === 229 && !composing),
    dispose: () => {
      for (const [type, fn] of listeners) textarea.removeEventListener(type, fn, true);
    },
  };
}
