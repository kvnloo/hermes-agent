# Opt-in native live voice

Live voice is separate from **Mic / Alt+V** (review-only dictation). Activate
**Live voice… / Alt+Shift+V**, read the consent text, then choose **Allow
microphone + automatic spoken turns**. No microphone, speaker, provider call,
or background loop starts before that confirmation. Consent is per session and
connection, never persisted. Switching sessions requires fresh consent.

This mode captures on the **gateway machine**, not the Tern client machine.
Its existing Hermes full-duplex detector endpoints speech and rejects speaker
bleed; configured Hermes STT transcribes each utterance, the normal session
prompt pipeline runs it, and configured Hermes TTS speaks the completed reply.
There is no new paid provider or realtime-model fallback. Tool activity,
approvals and the assistant transcript remain in the regular conversation.

- **Mute** immediately closes input and cancels pending speech; **Unmute**
  explicitly reacquires input. Muting never changes the draft.
- **Barge in / silence reply** cuts playback and interrupts only this session.
  Detected speech does the same during generation or playback.
- **Stop**, Escape, Ctrl+C, session switch, session teardown and transport
  disconnect retire the lease and close input/playback. Late STT/TTS results
  cannot send or acquire playback. A provider request already in flight can
  finish in the background; its lease remains reserved until cleanup completes.
- All draft Send paths are disabled while consent or a live lease is active;
  live speech never submits, replaces or clears the composer draft.
- Device permission, STT, assistant and TTS failures stay visible. Fix the
  configured backend/device and explicitly activate again; no automatic retry.

Automated acceptance uses a connected Tern SDK Session and fake gateway
transport, plus Python fake audio/STT/TTS. It never opens real devices or calls
a paid provider. Actual OS microphone/speaker permission prompts, acoustic echo
rejection and physical full-duplex latency still need an opt-in hardware trial.
