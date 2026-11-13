---
name: realtime-voice-assistant-ux
description: "Use when building or testing realtime voice clients."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [voice, realtime, webrtc, android, z0live, ux]
    related_skills: [lawnchair-z0live-delivery, z0live-voice-work-tools, phone-adb-tailnet-qualification]
---

# Realtime voice assistant UX

## When to Use

Use when building, changing or testing a realtime voice assistant, continuous dictation client, or voice broker. Distinguish foreground thread-scoped dictation from a duplex assistant before choosing an architecture; spoken replies and background listening are not implied by hands-free dictation.

## Continuous dictation implementation

1. Trace the complete existing capture-to-submission path before writing controls: recorder, platform-specific transcriber implementation, transport contract, authentication, and final message dispatch. Check the Android-resolved file rather than assuming an iOS implementation or a shared interface establishes Android support. If a required capability is absent, surface that scope decision before substantial implementation; an unavailable control is not a working dictation feature. Never invent an endpoint or silently select a paid transcriber.
2. Reuse the recorder/controller and the authoritative message-submission policy. Keep transcripts separate from manual draft text, attachments, and context; do not temporarily replace a draft to drive its send button. Reuse or extract the existing dispatch operation instead of copying queue/steer mapping into a voice component, because approval handling, setup states, permissions, and future policy changes must remain aligned.
3. Bind each user-started session to the exact environment and thread. Invalidate its token on stop, mute, navigation, background, disconnect, or permission loss; check validity after every await and immediately before submission. Do not let cleanup from a retired owner cancel a replacement owner's recorder. Treat a submission already admitted to the outbox separately from a late transcript that must be discarded.
4. Serialize file-based capture, finish, transcription, submission, and restart. Wait for recorder/controller cleanup before beginning the next segment. Ignore overlapping metering ticks while finishing; rotate long silent captures without transcribing noise. Allow a bounded startup grace for absent native metering, then fail visibly if metering or capture remains unavailable.
5. Test lifecycle races with deferred milestones: late preparation, late transcription, stop during submission, overlapping ticks, and cleanup before restart. Await entry into the operation being cancelled instead of assuming one microtask reaches it. Exercise the real shared controller in at least one focused lifecycle test; mocked orchestration alone cannot prove resource release. Report native microphone acceptance separately from unit tests, including metering, pause thresholds, interruptions, permission changes, and stop/restart gaps. Never present an unexecuted suite as verification.

## Duplex assistant procedure

1. Persona: inject the live tool list and a truthful self-description at session mint (what model/voice, what broker, who sees transcripts, what it can and cannot do). An assistant that answers "I can't see your screen for privacy reasons" or doesn't know its own model is a missing tool/persona, not a policy.
2. One voice: speak everything through the realtime model's own voice. Never fall back to platform TTS (Android TextToSpeech, speechSynthesis) for assistant output; a second, lower-quality voice mid-session is a top owner complaint.
3. Inbox delivery:
   - Persist the inbox cursor per device across sessions; on first connect start at the latest id. An in-memory cursor replays the whole backlog each session.
   - Inject items into the live session only at a safe turn (response done, user silent, no pending tool) and only during a session the owner started, about work he asked for. Otherwise post a silent notification or batch to the messaging gateway.
   - Session summaries and notes-to-Hermes are for the agent, never spoken: skip inbox delivery for summary jobs and do not summarize status-only sessions (connected, nothing said).
4. Opening: no unprompted summary at session start; greet briefly or wait for the owner.
5. Barge-in on words, never on sound. Voice activity alone fires on footsteps, doors and room noise. It cuts the model off mid-sentence and then gets answered as empty or garbled turns.
   - Use semantic turn detection with far-field noise reduction, and turn off the server's own `interrupt_response` and `create_response`.
   - Interrupt (cancel the response and clear the output buffer) only when the live transcript holds real words.
   - Create the reply only for a real final transcript, and delete noise-only turns from the conversation.
   - Echo-gate mic frames against the current output level before sending them; OMP `/live` drops mic frames below a multiple of the output level.
   - Propagate cancel to background work on "never mind".
   - Treat mute as a turn-state transition: clear pending input.

   The Lawnchair implementation and its tests are in lawnchair-z0live-delivery.
6. Background results are context the voice interprets, never a script it reads.
   - Inject a finished lookup or run as a system-role item framed by its kind (lookup, run, progress).
   - Ask for 1–3 spoken sentences in the voice's own words that answer what the user asked.
   - Never put a response-level `instructions` override on that reply. It replaces the session persona and context, and "relay faithfully" wording produces verbatim read-aloud that sounds like TTS.
   - Progress is silent commentary. Only the final result is speakable.
   - Never narrate waiting ("no update yet, something may come soon").
6a. Reference architecture to match or beat: OMP `/live` (`packages/coding-agent/src/live/` in can1357/oh-my-pi).
   - It runs on a duplex voice model with native client delegation (`gpt-live-1-codex`, Codex "quicksilver" signaling plus a sideband WebSocket). The model emits a delegation, and the client runs it in the agent.
   - The client streams back `commentary` (silent progress) and one final speakable message, which the voice presents as its own.
   - Persona: "you and the agent are one assistant". Delegate all tool work. Never claim results before they arrive.
   - Before adding more function tools or another inbox to a `gpt-realtime` voice, compare against this design. A long tool list and a separately named agent ("Hermes says") produce capability confusion and chatter.
7. Layering for latency: realtime voice -> fast liaison model (smol role) for instant/cached answers and spoken progress -> smart meta agent that uses unified memory first and fans out to cheaper workers. Role->model bindings come from the model-selection plane, pinned per session.
8. Hands-free triggers (ring tap, hotword, hardware button): Android blocks starting a mic foreground service cold from the background, but that is a design constraint, not a no. Lead with the paths that work: an opt-in Standby mic FGS the owner starts once while visible (idle, no capture) that later gestures toggle; default-assistant (ROLE_ASSISTANT) background-start exemptions; shell-initiated `adb shell am start ... --ez autostart true` over tailnet ADB as fallback. Route the gesture through the broker with an authenticated nonce and pick the target device from recent activity.

## Emergency voice containment and lifecycle

1. Treat an owner reporting overlapping conversations or asking to end calls as an immediate stop request, not a debugging discussion. Silence the identified voice outputs and microphone inputs first; keep the progress report to the result and any remaining blocker.
2. On PulseAudio/PipeWire, enumerate `pactl -f json list sink-inputs` and `pactl -f json list source-outputs`. Match `properties["application.process.id"]` and the stream's target/name to the actual voice owner; leave unrelated audio and DSP nodes alone. Apply `pactl set-sink-input-mute INDEX 1` and `pactl set-source-output-mute INDEX 1`, then re-enumerate and verify `mute: true`. This is containment only: muting does not disconnect the provider or stop billing.
3. Resolve calls to their owning processes before killing anything. Multiple playback/capture pairs can belong to threads in one shared gateway; do not describe them as separate processes or kill a shared agent owner based on stream count. An instruction to kill voice processes authorizes stopping those calls, not silently terminating unrelated chats. If broader termination is the only verified path, state the exact shared-owner impact and obtain that scope decision.
4. Use the installed voice surface's supported stop/cancel control and read back call state plus audio streams. If no stop path has been verified, report “muted, calls still running,” not “stopped.” Do not turn speculative debugger injection, guessed audio-server commands, or untested thread cancellation into a recovery recipe.
5. Do not recommend or start a replacement call while old calls remain live. A frontend timeout can stop waiting without cancelling its backend handler, so retrying a long-running voice command can create concurrent microphone sessions. Verify the old call ended before retrying; never infer call failure from an expired UI wait.
6. For voice implementations, enforce one active call lease per microphone/owner, return an explicit already-active receipt on repeated starts, and expose idempotent stop-all scoped to that owner. Keep stop available outside the blocking start command so frontend abandonment cannot orphan an uncontrollable call. Test duplicate starts, frontend timeouts, stop during startup, and restart after confirmed teardown.

## Diagnosing a voice complaint

- For a feature-availability question, inspect the active profile's installed voice plugins before concluding the host only supports STT → agent → TTS. In Hermes, consult the installed `hermes-talk` README and command handler; subscription-backed OpenAI Realtime and the separately selected GPT-Live lane are distinct from built-in `/voice`. Inspect an owner-named Tern tab read-only with `tern ls --json` and `tern capture BLOCK --surfaces` rather than asking them to repeat visible context or stealing focus. Follow the `hermes-agent` configuration reference for Hermes-specific entry points.
- Read the recorded sessions before touching code. On z0live they live in `data/z0live/sessions/*.jsonl` and `broker.db` (see lawnchair-z0live-delivery for the fields).
  - Empty user transcripts between assistant lines mean noise turns.
  - A model denying a capability usually means the installed client lacks the tool.
  - Repeated filler means status messages are being made speakable.
- Confirm which client build the phone actually runs before attributing behaviour to new code.
- Measure quality as the owner feels it: end of user speech to first audible output (output RMS, not first transcript text), as p50/p95 over repeated runs; false interruptions from non-speech noise; repeated, stale or filler speech. Pre-register thresholds before looking at results, and use OMP `/live` as the control arm.

## Testing on the owner's phone

- Write device checks as ONE scripted batch (intents, resource-id lookups, condition waits, asserts), inspect only final evidence frames downscaled <=720 px. Per-tap agent turns cost ~10 s/step; raw ADB over the tailnet is ~0.06 s/tap.
- Prefer a debug-only text-turn injection hook and headless Chromium WebRTC for real model turns; use the handset only for final qualification.
- Check `dumpsys window mCurrentFocus` first; never loop checks that start voice sessions while the owner is in another app. Run once with his OK; stop all device actions at the first interference report, then clean up side effects (inbox rows, summaries) after backing up the store.
- Feedback-loop smell: automated sessions -> agent commentary -> spoken on the phone -> more sessions. Break it at the broker (no spoken summaries) and the client (cursor persistence), not just by stopping the test.
- Stop only helper PIDs captured when spawning them; process-name or path matching can select the agent or another active session.
