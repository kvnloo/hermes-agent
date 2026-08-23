import { Mic, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@nous-research/ui/ui/components/button";

const RESTART_DELAY_MS = 250;
const MAX_RESTARTS = 6;

type VoiceState = "idle" | "listening" | "sent" | "error";

interface SpeechRecognitionResultLike {
  readonly isFinal: boolean;
  readonly 0: { readonly transcript: string };
}

interface SpeechRecognitionEventLike {
  readonly resultIndex: number;
  readonly results: ArrayLike<SpeechRecognitionResultLike>;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onend: (() => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

interface ChatVoiceControlProps {
  connected: boolean;
  profile: string;
  submit: (transcript: string) => void;
}

function recognitionConstructor(): SpeechRecognitionConstructor | undefined {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

export function ChatVoiceControl({ connected, submit }: ChatVoiceControlProps) {
  const [state, setState] = useState<VoiceState>("idle");
  const [finalTranscript, setFinalTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const listeningRef = useRef(false);
  const fatalRef = useRef(false);
  const restartCountRef = useRef(0);
  const restartTimerRef = useRef<number | null>(null);
  const finalRef = useRef("");
  const interimRef = useRef("");

  const clearRestart = () => {
    if (restartTimerRef.current !== null) window.clearTimeout(restartTimerRef.current);
    restartTimerRef.current = null;
  };

  const updateFinal = (value: string) => {
    finalRef.current = value;
    setFinalTranscript(value);
  };

  const updateInterim = (value: string) => {
    interimRef.current = value;
    setInterimTranscript(value);
  };

  const startRecognition = () => {
    const Constructor = recognitionConstructor();
    if (!Constructor) {
      listeningRef.current = false;
      setError("Chrome speech recognition is unavailable. Use Gboard below.");
      setState("error");
      return;
    }

    const recognition = new Constructor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onresult = (event) => {
      let appendedFinal = "";
      let nextInterim = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index];
        const text = result?.[0]?.transcript ?? "";
        if (result?.isFinal) appendedFinal += text;
        else nextInterim += text;
      }
      if (appendedFinal) updateFinal(`${finalRef.current}${appendedFinal}`);
      updateInterim(nextInterim);
      setError("");
    };
    recognition.onerror = (event) => {
      const fatal = event.error === "not-allowed" || event.error === "service-not-allowed";
      if (fatal) {
        fatalRef.current = true;
        listeningRef.current = false;
        setError(event.error === "not-allowed"
          ? "Microphone permission was denied. Allow mic access in Chrome, then tap again."
          : "Chrome speech recognition is not allowed on this device.");
        setState("error");
      } else {
        setError(`Speech recognition error: ${event.error}. Retrying…`);
      }
    };
    recognition.onend = () => {
      if (!listeningRef.current || fatalRef.current) return;
      if (restartCountRef.current >= MAX_RESTARTS) {
        listeningRef.current = false;
        setError("Speech recognition kept stopping. Tap to resume or use Gboard below.");
        setState("error");
        return;
      }
      const delay = RESTART_DELAY_MS * 2 ** Math.min(restartCountRef.current, 3);
      restartCountRef.current += 1;
      restartTimerRef.current = window.setTimeout(startRecognition, delay);
    };
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch {
      listeningRef.current = false;
      setError("Could not start Chrome speech recognition. Tap to try again.");
      setState("error");
    }
  };

  const begin = () => {
    if (!connected) {
      setError("Chat is not connected yet.");
      setState("error");
      return;
    }
    clearRestart();
    fatalRef.current = false;
    restartCountRef.current = 0;
    listeningRef.current = true;
    setError("");
    setState("listening");
    startRecognition();
  };

  const commit = () => {
    const transcript = `${finalRef.current} ${interimRef.current}`.replace(/\s+/g, " ").trim();
    if (!transcript) {
      setError("No speech heard yet — keep talking, then tap anywhere to send.");
      return;
    }
    listeningRef.current = false;
    clearRestart();
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    submit(transcript);
    updateFinal("");
    updateInterim("");
    setError("");
    setState("sent");
  };

  const end = () => {
    listeningRef.current = false;
    clearRestart();
    recognitionRef.current?.abort();
    recognitionRef.current = null;
    updateFinal("");
    updateInterim("");
    setError("");
    setState("idle");
  };

  useEffect(() => () => {
    listeningRef.current = false;
    clearRestart();
    recognitionRef.current?.abort();
  }, []);

  const transcript = `${finalTranscript}${interimTranscript}`.trim();
  const headline = state === "listening"
    ? (transcript || "LISTENING…")
    : state === "sent"
      ? "SENT"
      : "TAP TO TALK";

  return (
    <div className="relative flex min-h-[42dvh] shrink-0 flex-col border border-current/25 bg-black/30 pb-[env(safe-area-inset-bottom)] text-white lg:min-h-44">
      <button
        type="button"
        aria-label="Voice conversation surface"
        onClick={state === "listening" ? commit : begin}
        className="flex min-h-[42dvh] w-full touch-manipulation flex-1 flex-col items-center justify-center gap-5 px-5 py-8 text-center active:bg-white/10 lg:min-h-44"
      >
        <Mic className={state === "listening" ? "h-12 w-12 animate-pulse text-red-400" : "h-12 w-12"} />
        <span className="max-h-[45dvh] w-full overflow-y-auto whitespace-pre-wrap break-words text-2xl font-semibold leading-tight sm:text-3xl">
          {headline}
        </span>
        <span className="text-sm tracking-wide text-white/70">
          {state === "listening" ? "TAP ANYWHERE TO SEND" : "Chrome live speech • Gboard remains below"}
        </span>
      </button>
      {error && <div role="alert" className="px-4 pb-3 text-center text-sm text-red-300">{error}</div>}
      <Button
        ghost
        aria-label="End or cancel voice conversation"
        onClick={end}
        className="absolute right-2 top-2 min-h-11 min-w-11 touch-manipulation px-2"
        prefix={<X className="h-5 w-5" />}
      >
        End
      </Button>
    </div>
  );
}
