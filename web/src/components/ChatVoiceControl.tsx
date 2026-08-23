import { Mic, Send, Square, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@nous-research/ui/ui/components/button";
import { authedFetch } from "@/lib/api";

const MAX_RECORDING_MS = 30_000;
const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"];

type VoiceState = "idle" | "listening" | "transcribing" | "sent" | "error";

interface ChatVoiceControlProps {
  connected: boolean;
  profile: string;
  submit: (transcript: string) => void;
}

function blobDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the recording"));
    reader.onload = () => resolve(String(reader.result));
    reader.readAsDataURL(blob);
  });
}

export function ChatVoiceControl({ connected, profile, submit }: ChatVoiceControlProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [error, setError] = useState("");
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const cleanup = () => {
    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    timerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    recorderRef.current = null;
  };

  useEffect(() => () => cleanup(), []);

  const fail = (message: string) => {
    cleanup();
    setError(message);
    setState("error");
  };

  const transcribe = async (blob: Blob) => {
    setState("transcribing");
    try {
      const dataUrl = await blobDataUrl(blob);
      const suffix = profile ? `?profile=${encodeURIComponent(profile)}` : "";
      const response = await authedFetch(`/api/audio/transcribe${suffix}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data_url: dataUrl, mime_type: blob.type || "audio/webm" }),
      });
      if (!response.ok) throw new Error((await response.text()) || `Transcription failed (${response.status})`);
      const result = (await response.json()) as { transcript?: string };
      const transcript = result.transcript?.trim();
      if (!transcript) throw new Error("No speech detected. Tap Start and try again.");
      submit(transcript);
      setState("sent");
    } catch (cause) {
      fail(cause instanceof Error ? cause.message : "Voice input failed");
    }
  };

  const stop = () => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    recorder.stop();
  };

  const start = async () => {
    setError("");
    if (!connected) return fail("Chat is not connected yet.");
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      return fail("Microphone recording is unavailable in this browser.");
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
      const mimeType = MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      streamRef.current = stream;
      recorderRef.current = recorder;
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => fail("Microphone recording failed.");
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || mimeType || "audio/webm" });
        chunksRef.current = [];
        cleanup();
        if (blob.size) void transcribe(blob);
        else fail("The recording was empty.");
      };
      recorder.start();
      setState("listening");
      timerRef.current = window.setTimeout(stop, MAX_RECORDING_MS);
    } catch (cause) {
      const denied = cause instanceof DOMException && ["NotAllowedError", "SecurityError"].includes(cause.name);
      fail(denied ? "Microphone permission was denied." : "Could not start the microphone.");
    }
  };

  const end = () => {
    const recorder = recorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.ondataavailable = null;
      recorder.onstop = null;
      recorder.stop();
    }
    cleanup();
    chunksRef.current = [];
    setError("");
    setState("idle");
  };

  const label = state === "listening" ? "Listening (30s max)" : state === "transcribing" ? "Transcribing…" : state === "sent" ? "Sent — reply appears below" : state === "error" ? error : "Voice input ready";

  return (
    <div data-voice-state={state} className="flex min-h-11 shrink-0 items-center gap-2 border border-current/20 bg-black/20 px-2 py-1 text-xs text-white/85" role="status" aria-live="polite">
      {state === "listening" ? (
        <Button aria-label="Stop and send voice input" onClick={stop} className="min-h-11 min-w-11 px-3" prefix={<Send className="h-4 w-4" />}>Send</Button>
      ) : (
        <Button aria-label="Start voice input" onClick={() => void start()} disabled={state === "transcribing"} className="min-h-11 min-w-11 px-3" prefix={<Mic className="h-4 w-4" />}>Start</Button>
      )}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      <Button ghost aria-label="End voice input" onClick={end} className="min-h-11 min-w-11 px-2" prefix={state === "listening" ? <Square className="h-4 w-4" /> : <X className="h-4 w-4" />}>End</Button>
    </div>
  );
}
