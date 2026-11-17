// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { useModalBehavior } from "./useModalBehavior";

let container: HTMLDivElement;
let root: Root;

function Modal({ onClose }: { onClose: () => void }) {
  const ref = useModalBehavior({ open: true, onClose });
  return (
    <div ref={ref}>
      <input aria-label="Cron prompt" />
    </div>
  );
}

beforeEach(() => {
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => { root.unmount(); });
  container.remove();
});

it("keeps a modal open for composing Escape and keyCode 229, but closes on plain Escape", async () => {
  const onClose = vi.fn();
  await act(async () => { root.render(<Modal onClose={onClose} />); });
  const input = container.querySelector("input")!;

  async function escape({ isComposing = false, keyCode }: { isComposing?: boolean; keyCode?: number }) {
    const event = new KeyboardEvent("keydown", {
      key: "Escape",
      bubbles: true,
      cancelable: true,
      isComposing,
    });
    if (keyCode !== undefined) Object.defineProperty(event, "keyCode", { value: keyCode });
    await act(async () => { input.dispatchEvent(event); });
    return event;
  }

  const composing = await escape({ isComposing: true });
  expect(onClose).not.toHaveBeenCalled();
  expect(composing.defaultPrevented).toBe(false);

  const boundary = await escape({ keyCode: 229 });
  expect(onClose).not.toHaveBeenCalled();
  expect(boundary.defaultPrevented).toBe(false);

  const ordinary = await escape({});
  expect(onClose).toHaveBeenCalledTimes(1);
  expect(ordinary.defaultPrevented).toBe(true);
});
