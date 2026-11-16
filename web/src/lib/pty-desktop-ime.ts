/**
 * Desktop IME input seam for xterm-backed dashboard Chat (#106487).
 *
 * xterm 6's old-offset textarea slice may be a line-tail fragment instead
 * of the committed word. Compositionend data is authoritative on desktop.
 * Some IMEs deliver only bare non-ASCII insertText without composition.
 */
export function bindDesktopPtyImeInput(
  textarea: HTMLTextAreaElement,
  send: (data: string) => void,
): () => void {
  const COMPOSITION_ECHO_MS = 300;
  // eslint-disable-next-line no-control-regex -- non-keyboard text
  const NON_ASCII_TEXT = /[^\x00-\x7f]/;
  let composing = false;
  let lastComposition: { data: string; at: number } | null = null;

  const forward = (ev: Event, data: string) => {
    ev.preventDefault();
    ev.stopImmediatePropagation(); // prevent xterm's stale-slice send
    textarea.value = "";
    try {
      textarea.setSelectionRange(0, 0);
    } catch {
      // Some browser textarea implementations can refuse selection changes.
    }
    send(data);
  };
  const onCompositionStart = () => {
    composing = true;
  };
  const onCompositionEnd = (ev: CompositionEvent) => {
    composing = false;
    // A cancellation sent nothing and must not silence a later bare commit.
    lastComposition = ev.data ? { data: ev.data, at: Date.now() } : null;
    if (ev.data) forward(ev, ev.data);
  };
  const onInput = (ev: Event) => {
    const input = ev as InputEvent;
    // A final insertText can have isComposing=false before compositionend.
    if (composing || input.isComposing || input.inputType !== "insertText") return;
    const data = input.data;
    if (!data || !NON_ASCII_TEXT.test(data)) return;
    // A time-only grace window drops a *different* prompt CJK commit.
    // Treat only the first identical post-composition input as an echo.
    const echo = lastComposition !== null &&
      lastComposition.data === data &&
      Date.now() - lastComposition.at <= COMPOSITION_ECHO_MS;
    lastComposition = null;
    if (echo) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      return;
    }
    forward(ev, data);
  };

  textarea.addEventListener("compositionstart", onCompositionStart, true);
  textarea.addEventListener("compositionend", onCompositionEnd, true);
  textarea.addEventListener("input", onInput, true);
  return () => {
    textarea.removeEventListener("compositionstart", onCompositionStart, true);
    textarea.removeEventListener("compositionend", onCompositionEnd, true);
    textarea.removeEventListener("input", onInput, true);
  };
}
