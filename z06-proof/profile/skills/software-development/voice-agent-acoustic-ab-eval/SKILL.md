---
name: voice-agent-acoustic-ab-eval
description: "Use when A/B-testing voice agents on output audio."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [voice, eval, webrtc, omp, z0live, latency, barge-in]
    related_skills: [realtime-voice-assistant-ux, z0live-voice-work-tools]
---

# Voice agent acoustic A/B eval

Headless A/B of realtime voice agents (OMP /live, z0live realtime/bidi): scripted TTS mic, RMS timing on output audio, pre-registered gates. Reference implementation: kvnloo/z0evals `studies/voice-omp-parity-v0` (PR #101). Reuse it; do not rebuild.

## Rules

1. Time on OUTPUT AUDIO (50 ms RMS windows, threshold 0.015 = OMP OUTPUT_ACTIVE_LEVEL), never transcript text. Transcripts only for content checks.
2. Commit metric definitions + gates before any scored run; a pilot may only debug the harness and is excluded. Record post-hoc readings separately from verdicts.
3. One shared timeline runner for all arms; waits are acoustic plus an arm `workPending()` signal. `await_result` must wait for speech AFTER work settles.
4. Never use the owner's mic/speaker or phone broker: scripted PCM in, muted meter out, isolated broker.

## OMP /live arm (Bun, installed package, unchanged controller)

- Bun runtime plugin `build.module("@oh-my-pi/pi-natives", ...)` re-exporting the real module with a scripted `AudioCapture` (16 kHz, 20 ms frames) keeps OMP's echo gate in path; wrap `LiveWebRtcPeer` to timestamp its 50 ms output-level callback.
- Native speaker: `ALSA_CONFIG_PATH` to a MINIMAL file `pcm.!default { type null }`. Including `/usr/share/alsa/alsa.conf` lets PipeWire's default win (audible).
- `createAgentSession({sessionManager: SessionManager.inMemory(cwd), disableExtensionDiscovery, enableLsp:false, enableMCP:false, skipPythonPreflight:true})`: LSP/MCP startup stalls the JS loop for seconds and level timestamps are JS-stamped. Log loop lag >50 ms and exclude overlapping latencies; also report a stall-inclusive sensitivity row.
- Codex events arrive on BOTH data channel and sideband: dedupe delegations by item id.
- Sideband `session.output_audio.delta` (200 ms, 24 kHz int16, server start_ms/end_ms) leads RTP audibility by ~400 ms; it is generation time, not audible time.

## z0live arms (Node + Playwright + system Chromium)

- AudioWorklet `addModule` bypasses `page.route`: fetch the routed source and load via Blob URL.
- Remote WebRTC track needs a muted `<audio>` sink before WebAudio receives it. Launch with `--disable-audio-output --mute-audio`. Map worklet ctx time to perf time with a min-filtered offset (robust to main-thread stalls).
- Isolated broker: detached worktree, `Z0LIVE_PORT=18791`, private `Z0LIVE_DATA` with a copied `.hermes-api-key`, `Z0LIVE_IDLE_SECONDS`/`Z0LIVE_SUMMARY_SECONDS` huge and no `/end` (avoids Hermes summary jobs). Port the Lawnchair loop: speech_started -> response.cancel + output_audio_buffer.clear; ignore `response_cancel_not_active`.
- Bidi path (`feat/frameless-bidi`): mint with `transports:["bidi","realtime"]`, POST offer to `/v1/live/calls`, poll `/v1/live/trace` marks.final for work done; assistant `turn.done` is often missing on the client data channel, so import transcripts read-only from the broker DB after a 4 s drain.

## Host

- Live sessions are IO-bound: do not hold the shared heavy.lock per session (other agents hold it for long); keep nice + MemAvailable >= 4 GiB gate. Record loadavg per run.
- Offline TTS: kokoro-js 1.2.1 + Kokoro-82M q8 cached in `~/.cache/omp/cache/tts-runtime/kokoro-1.2.1` (allowRemoteModels=false). Normalize speech to -20 dBFS active RMS; synthesize noise procedurally (no licenses).
- z0evals PRs need a ```yaml receipt (issue, base_revision, head_revision = exact PR head, tests.red/green) in the body.

## Round-2 lessons (z0live client parity)

- The z0live arm must mirror the CURRENT APK loop (`--client apk`, default): semantic_vad high, speech gate, barge probe, early reply, system-item inbox, silent acceptance without continuation, bidi duck before the meter. `--client legacy` = the 6db52cb baseline. Re-port whenever the APK turn logic changes, or the eval measures a client nobody runs.
- A result being spoken is not pending work: counting the in-flight inbox item in `workPending()` moves await_result's anchor past its own speech and every delegation run idles to timeout.
- Silent async acceptance (`speech:"silent"`) is scored as the "synchronous tool result" work-complete signal, so `EOS -> result audible` reads the ack (~3 s). Report time to the spoken inbox answer separately.
- gpt-realtime WebRTC emitted `output_audio_buffer.cleared` at real-speech `speech_started` even with `interrupt_response:false`, but not on the noise clip; barge-to-silence then measures that, not the client gate.
- A scratch worktree broker needs `Z0LIVE_DEPLOYED_DATA=/mnt/zer0models/workspace/zer0/data/z0live` for `live_isolated_broker.py` to find the Hermes key; set `Z0LIVE_DELEGATE_SESSION` to a throwaway title.
- Score a new block against the unchanged OMP control by symlinking only `omp-live__*` run dirs (+run.json) into a scratch dir and passing it plus the new block to `analyze.py --runs a,b`; never mix same-named arms from two blocks.

## Pitfalls seen

- A 700 ms noise-gap rule is near natural `sol` sentence pauses: require transcript truncation or VAD evidence too.
- Silent inbox items (`say:""`) are data, not pending work.
- Absolute gates can fail the control; report control absolutes.
