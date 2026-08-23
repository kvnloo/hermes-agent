// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatVoiceControl } from "./ChatVoiceControl";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

interface FakeResult {
  0: { transcript: string };
  isFinal: boolean;
}

class FakeRecognition {
  static instances: FakeRecognition[] = [];
  continuous = false;
  interimResults = false;
  lang = "";
  onresult: ((event: { resultIndex: number; results: FakeResult[] }) => void) | null = null;
  onend: (() => void) | null = null;
  onerror: ((event: { error: string }) => void) | null = null;
  start = vi.fn();
  stop = vi.fn();
  abort = vi.fn();
  constructor() { FakeRecognition.instances.push(this); }
  result(...rows: Array<[string, boolean]>) {
    this.onresult?.({
      resultIndex: 0,
      results: rows.map(([transcript, isFinal]) => ({ 0: { transcript }, isFinal })),
    });
  }
}

describe("ChatVoiceControl Web Speech mode", () => {
  let host: HTMLDivElement;
  let root: ReturnType<typeof createRoot>;

  beforeEach(() => {
    vi.useFakeTimers();
    FakeRecognition.instances = [];
    vi.stubGlobal("SpeechRecognition", FakeRecognition);
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
  });

  afterEach(async () => {
    await act(async () => root.unmount());
    host.remove();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  async function render(submit = vi.fn()) {
    await act(async () => root.render(
      <ChatVoiceControl profile="chiefstaff" connected submit={submit} />,
    ));
    return {
      submit,
      surface: host.querySelector('[aria-label="Voice conversation surface"]') as HTMLButtonElement,
    };
  }

  it("shows interim and final speech without submitting partial results", async () => {
    const { submit, surface } = await render();
    await act(async () => surface.click());
    const recognition = FakeRecognition.instances[0];
    expect(recognition.continuous).toBe(true);
    expect(recognition.interimResults).toBe(true);
    expect(recognition.lang).toBe("en-US");

    await act(async () => recognition.result(["Call the ", true], ["crew", false]));
    expect(host.textContent).toContain("Call the crew");
    expect(submit).not.toHaveBeenCalled();
  });

  it("restarts after Android ends recognition without submitting twice", async () => {
    const { submit, surface } = await render();
    await act(async () => surface.click());
    const first = FakeRecognition.instances[0];
    await act(async () => first.result(["Keep going", true]));
    await act(async () => first.onend?.());
    expect(submit).not.toHaveBeenCalled();

    await act(async () => vi.advanceTimersByTime(250));
    expect(FakeRecognition.instances).toHaveLength(2);
    expect(FakeRecognition.instances[1].start).toHaveBeenCalledOnce();
    expect(host.textContent).toContain("Keep going");
  });

  it("commits the visible transcript once when the full surface is tapped", async () => {
    const { submit, surface } = await render();
    await act(async () => surface.click());
    await act(async () => FakeRecognition.instances[0].result(["Call the crew", true]));
    await act(async () => surface.click());

    expect(submit).toHaveBeenCalledTimes(1);
    expect(submit).toHaveBeenCalledWith("Call the crew");
    expect(FakeRecognition.instances[0].abort).toHaveBeenCalled();
    expect(host.textContent).toContain("SENT");
  });

  it("does not restart after a fatal permission error", async () => {
    const { surface } = await render();
    await act(async () => surface.click());
    const recognition = FakeRecognition.instances[0];
    await act(async () => recognition.onerror?.({ error: "not-allowed" }));
    await act(async () => recognition.onend?.());
    await act(async () => vi.runAllTimers());

    expect(FakeRecognition.instances).toHaveLength(1);
    expect(host.textContent).toContain("Microphone permission was denied");
  });

  it("does not submit an empty tap and keeps the session listening", async () => {
    const { submit, surface } = await render();
    await act(async () => surface.click());
    await act(async () => surface.click());

    expect(submit).not.toHaveBeenCalled();
    expect(host.textContent).toContain("No speech heard");
  });
});
