---
name: tern-native-dictation-receipts
description: "Use when implementing or verifying native Tern dictation."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [tern, dictation, voice, stt, verification]
    related_skills: [tern-action-shortcut-receipts, hermes-agent]
---

# Native Tern dictation receipts

## When to Use

Use for native composer dictation, microphone lifecycle, STT hypotheses, or acceptance tests that must never open real audio devices.

## Rules

For subscription-backed duplex conversation via `hermes-talk`, Ctrl+L and the thinking orb, load `references/hermes-talk.md`. It is a different transport and lifecycle from review-only dictation.

- Reuse `tools.voice_mode.create_audio_recorder` and `transcribe_recording`; keep audio acquisition in the gateway and only review-only draft projection in TypeScript. Existing STT providers are batch APIs, so describe periodic snapshots as hypotheses, not provider-native token streaming.
- Treat recording as an explicit capture/session/transport lease. Never acquire audio on launch, focus, adoption, or a background ready event. Serialize competing voice/wake microphone starts against the dictation lease; close/discard on session teardown and transport disconnect.
- Use `spawn_context_thread` for profile-bound recorder/STT work, and explicitly call `.start()` on the returned unstarted thread. Scope RPCs that can read config or create recordings to the owning session profile.
- Give partial snapshots unique private filenames. Legacy final recordings use second-resolution timestamp names: sharing those names with a concurrent partial lets final stop overwrite audio and partial cleanup delete the final WAV.
- Close the recording device from the stop/cancel path even when partial STT is waiting on a provider. `AudioRecorder.stop()` preserves its input stream for legacy voice mode; call `shutdown()` to actually release it. Suppress cancelled and retired capture events and unlink every temporary WAV.
- Correlate frontend events with both session and capture identity, including events delivered before the start response. Serialize stop behind start acknowledgement because gateway long handlers run in a worker pool. A failed cancellation is not proof the microphone stopped: retain ownership and Send gating for an explicit retry.
- Commit only final text at the current caret in one undo step. Partials remain presentation-only; neither partials nor finals invoke prompt submission. Gate keyboard, alternate send, native Send, and stale click handlers while capture is active.
- Keep chords in `actions.ts` and run the exhaustive modifier/context collision suite. Give capture cancellation priority over completion while preserving modal/approval key ownership.
- Probe the installed SDK decoder before enabling hold-to-talk. Tern SDK 0.1.0 erases CSI-u press/repeat/release identity and negotiates kitty flag 1 only; a generic CSI-u claim, feature-name guess, `focus` click event or repeat timeout is not a release contract. On such hosts expose the unsupported reason and retain Mic/Alt+V, not a hypothetical hold controller proven only with invented events.
- Reserve legacy speaker pipelines synchronously before acknowledging their RPC; registering inside a newly scheduled thread leaves a window where live voice can acquire the same devices. Keep live capture, playback and provider work pinned to its exact session/transport lease; retire late STT/TTS work before it can submit or acquire playback.
- Make full-duplex endpoint capture cancellable as well as its initial listening loop. Retain an explicit input-stream handle for immediate abort/close on mute, stop and teardown, surface permission/provider errors instead of swallowing them, and wait for owned workers to release before declaring the lease idle.
- Qualify with a connected Tern SDK Session handshake and emitted View tree plus fake gateway events. Python uses a fake recorder and fake STT under temporary `HERMES_HOME`; snapshot WAV tests can use synthetic PCM without importing sounddevice. Never exercise a real microphone or provider in automated acceptance tests.
- The shared (canonical) gateway serves no `voice.record`/`voice.toggle` (not in CANONICAL_RPC_METHODS). In plugin frontends that attach to it (alt-glitch/hermes-tern), run capture in a helper executed with HERMES_PYTHON beside the pane (widget_author.py pattern) that calls `hermes_cli.voice.start_continuous(auto_restart=False)`/`stop_continuous`; stdin EOF must cancel.
- Tern's native editor consumes Ctrl+B (bold on Linux) before the app sees it, and `config.get full` always returns the default `voice.record_key: ctrl+b`; map ctrl+b to an app-reachable chord (Alt+V) and verify keys in `tern serve`, not only unit tests.
- For headless real runs: isolated HERMES_HOME must live outside ~/.hermes (a path under profiles/<name>/ is treated as that profile and collides with the host gateway), use its own minimal .env (a shared .env enables api_server on a taken port), set `_config_version` and telemetry/onboarding off, and unset this agent's HERMES_* env before `tern serve`. Don't move a home after first launch: PM generations hold absolute paths. Type into panes with `tern ctl type '"text"'`.
- Run typecheck, complete Vitest, ESLint, bundle, canonical Python voice/contract tests, generator `--check`, and a sabotage run with the toggle action disabled. Run isolated `tern-e2e.sh` smoke at the committed head; report tern-serve success separately from native-window signed-out/account blockers. Native SDK fixture coverage is not real microphone certification.
