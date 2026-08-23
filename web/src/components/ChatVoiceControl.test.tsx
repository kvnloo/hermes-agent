// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatVoiceControl } from "./ChatVoiceControl";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

class FakeRecorder {
  static isTypeSupported = () => true;
  state = "inactive";
  mimeType = "audio/webm";
  ondataavailable: ((event: { data: Blob }) => void) | null = null;
  onstop: (() => void) | null = null;
  constructor(_stream: MediaStream, _options?: MediaRecorderOptions) {}
  start() { this.state = "recording"; }
  stop() {
    this.state = "inactive";
    this.ondataavailable?.({ data: new Blob(["voice"], { type: this.mimeType }) });
    this.onstop?.();
  }
}

const flush = async () => act(async () => { await Promise.resolve(); await Promise.resolve(); });

describe("ChatVoiceControl", () => {
  let host: HTMLDivElement;
  let root: ReturnType<typeof createRoot>;

  afterEach(async () => {
    await act(async () => root?.unmount());
    host?.remove();
    vi.unstubAllGlobals();
  });

  it("records, transcribes, and submits a bounded clip through the active PTY", async () => {
    const submit = vi.fn();
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ transcript: "Call the crew" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("MediaRecorder", FakeRecorder);
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn(async () => ({ getTracks: () => [{ stop: vi.fn() }] })) },
    });

    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    await act(async () => root.render(<ChatVoiceControl profile="chiefstaff" connected submit={submit} />));

    const start = host.querySelector('[aria-label="Start voice input"]') as HTMLButtonElement;
    expect(start.getBoundingClientRect).toBeDefined();
    await act(async () => start.click());
    expect(host.textContent).toContain("Listening");

    const stop = host.querySelector('[aria-label="Stop and send voice input"]') as HTMLButtonElement;
    await act(async () => stop.click());
    await flush();
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalled());

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/audio/transcribe?profile=chiefstaff"),
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(submit).toHaveBeenCalledWith("Call the crew");
    expect(host.textContent).toContain("Sent");
  });

  it("ends without submitting and exposes an explicit error", async () => {
    vi.stubGlobal("MediaRecorder", FakeRecorder);
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    await act(async () => root.render(<ChatVoiceControl profile="chiefstaff" connected submit={vi.fn()} />));
    await act(async () => (host.querySelector('[aria-label="Start voice input"]') as HTMLButtonElement).click());
    expect(host.firstElementChild?.getAttribute("data-voice-state")).toBe("error");
    expect(host.textContent).toContain("Microphone recording is unavailable");
  });
});
