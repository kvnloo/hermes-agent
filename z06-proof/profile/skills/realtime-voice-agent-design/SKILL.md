---
name: realtime-voice-agent-design
description: "Use when designing the owner's realtime voice agents."
version: 0.1.0
metadata:
  hermes:
    tags: [voice, realtime, z0live, agents, android, ux]
    related_skills: [lawnchair-z0live-delivery, z0live-voice-work-tools, phone-adb-tailnet-qualification, rendered-ui-qualification]
---

# Realtime voice agent design (z0live and app voice modes)

## When to Use
Any change to a voice assistant the owner talks to (z0live broker, Lawnchair/omalauncher/Dash clients, in-app voice modes): architecture, persona, tools, audio UX, screen understanding, or phone verification.

## Scope an in-app voice request first

1. Identify the requested client and interaction: continuous dictation into the active thread, spoken replies, or a separate realtime assistant. Inspect the named reference app's capture and send paths before treating “voice mode” as WebRTC conversation; continuous capture can use file-based utterances.
2. Reuse that client's recorder, transcription capability, authentication and submission pipeline. Do not introduce a paid realtime provider or a second assistant architecture merely to keep listening between utterances. Apply the architecture below to the dedicated assistant, not automatically to thread-scoped dictation.
3. Bind capture and asynchronous transcription results to the exact environment/thread/session. Stop and invalidate in-flight results on navigation, background, disconnect or permission loss so delayed speech cannot send into a different conversation. Preserve manual drafts and deduplicate final utterances before submission.
4. Keep capture mode separate from delivery policy. Route spoken turns through the same queue/steer capability checks as typed turns; listening continuously is not permission to interrupt every active run.
5. For this user's mobile composer, provide a direct alternate-send gesture rather than requiring queue → menu → steer: tap retains the primary action; hold arms the supported alternate with haptic and a release label; release sends once; slide away cancels. Suppress the ordinary tap after a hold and cancel stale gestures when destination or capability changes. Retain an accessible explicit alternate action.

## Configure and diagnose voice authentication

1. Identify the exact client's voice engine and the server profile serving that request before changing credentials. Read the installed voice status/session implementation and current official docs; account login, normal chat-model authorization, transcription/TTS and a full-duplex voice session can use different credential chains.
2. Explain the distinction briefly when the owner says he is already signed in. Verify whether this exact client and endpoint can reuse his subscription; a subscription-capable desktop plugin or another harness does not establish support in the mobile client's built-in mode. Do not turn an implementation-specific limitation into a permanent claim about all voice integrations.
3. Inspect the serving profile's configured credential names and available vault records without exposing values. Treat a record named `OPENAI_API_KEY` as a candidate, not proof of a valid platform key: inspect its shape in-process and test it against the intended provider endpoint. A JWT-shaped value may be an account bearer; neither the name nor the shape establishes API entitlement.
4. Validate authentication with a non-billable provider/model metadata request before copying a candidate into configuration or starting voice. Classify the actual response: a 401 invalid credential is distinct from a 403 entitlement failure or a missing model. Keep credentials, response tokens and personal claims out of output, and do not describe an unvalidated vault record as a working API key.
5. Disclose separate API billing, including session-time/idle charging when applicable, before starting a paid realtime session; check the current rate rather than preserving a price as a standing fact. Preserve the working chat setup if the available credential is rejected. Use an existing securely stored valid credential when authorized; request new secret entry only after establishing a private mechanism that can actually deliver it to the destination. A private card that returns only an unusable secret reference is not a completed provisioning path.
6. Use supported configuration commands for settings and profile-scoped secret storage for keys; never put a key in a config command's argv or print it in a readiness response. Verify resolved voice status after provisioning, then—with microphone/session authorization—exercise a real voice exchange and interruption. Report credential readiness, session creation, microphone capture and audible reply separately; a present key is not proof of working voice.

## Mobile subscription voice compatibility

- Compare the installed mobile APK's actual data-channel event names with the subscription transport before substituting a signaling endpoint. The native GPT-Live client uses `session.delegation.created`, `session.*_transcript.delta`, `session.thinking.append`, and `session.commentary.append`; Codex Frameless Bidi uses `delegation.created`, `*_transcript.added`, `turn.done`, and `delegation.context.append`/`session.context.append`. A subscription-capable Desktop plugin alone does not translate the mobile wire protocol.
- When client source is unavailable, a backend compatibility adapter can bridge two WebRTC peers and translate the data channel; disclose that audio now relays through the owner's server rather than going directly from phone to provider. Keep the existing dashboard as bearer-auth authority, intercept only exact voice routes, preserve the selected chat's delegation ownership and approvals, reject foreign delegation IDs, separate silent progress from speakable results, and bound calls/buffers/lifecycle. Never bypass authentication merely because the adapter listens on loopback.
- Use the existing Codex subscription signaling contract and let the installed Codex app-server's `account/read` with `refreshToken:true` own refreshes; never hand-write or return account tokens, run a second agent for client-owned delegations, or silently fall back to paid API billing. Run blocking refresh outside the voice event loop and clean up only the helper process this adapter created.
- Buffer outbound context until the provider emits `session.started`, not merely until its data channel opens. Test both readiness orders, actual bidirectional audio, mute/close, authentication rejection, exact proxy routing and UTF-8 chunk limits before activating only the adapter/proxy, not the shared Hermes owner.
- Use an offline-synthesized generic spoken utterance for the live subscription oracle. Require real provider input transcript, client delegation, returned fixture result, expected output transcript and non-silent audio. Label scripted backend results as fixtures, not Hermes tool execution. A context-only append may legitimately produce silence before a user speaks, and received RTP frames can be silence; neither proves audible voice. Keep handset microphone/speaker, real-chat delegation and acoustic interruption unverified until exercised on the device.

## Subscription-backed in-app live voice

1. Honor an explicit GPT live/Codex-subscription requirement as a transport constraint: do not substitute Whisper, chained transcription/TTS, a paid API key, or a native Codex harness.
2. Discover the installed Hermes checkout and serving profile's actual auth resolver, then inspect the existing z0live transport before implementing an adapter. Keep OAuth on its owner host; bridge signaling and sideband over an authenticated control channel when the app runs elsewhere. Report auth capabilities as booleans, never credential values.
3. Bind client delegations to the app's existing assistant submission/session and return its actual result through the live sideband. Reusing transport does not authorize routing work into an unrelated persistent z0live session or applying proposals automatically.
4. Publish the same-origin SDP/events/context/end contract early so frontend work can proceed independently. Require both bridge authentication and a per-call capability for subsequent operations; make cursor gaps and unknown context delivery explicit, and never blindly resend an uncertain operation.
5. Verify mocked backend boundaries and real subscription WebRTC signaling/connection/context/end separately. A synthetic silent-track smoke proves transport, not microphone capture, audible speech, interruption, or delegation execution through the app.

See [Subscription live adapters](references/subscription-live-adapters.md) for the tested cross-host recipe and wire-boundary pitfalls.

## Dedicated realtime-assistant architecture
1. Realtime voice (ChatGPT Realtime over direct WebRTC from the phone) talks to the human only: quick acknowledgements, never heavy work.
2. A fast liaison (`smol` role: Haiku/Luna class) is the voice's single work counterpart. It only exchanges information: crisp brief, instant hot-cache answers, short progress lines, voice-sized condensation, clarifying questions.
3. A smart meta agent (the persistent Opus Hermes session) drives answers and actions, checks z0intelligence unified memory first, and fans bulk context gathering out to cheaper workers, the way the interactive Hermes session works.
4. Cheap workers (sol/Haiku/DeepSeek/Cerebras/Groq) gather context in parallel; Jev gates fast routing.
- Role->model bindings come from z0intelligence and are pinned per session; z0live runs no second router. Mirror role names from the owner's oh-my-pi `modelRoles` (smol, default, task, plan/slow, judge).
- Barge-in or "never mind" cancels the whole chain. Progress lines queue while the human holds the floor.
- Log a per-turn trace (layer, model, latency, cost) so Hermes can review usage.

- Frameless Bidi (`gpt-live-1-codex`, OMP `/live`) replaces the router-style realtime voice: one assistant persona, native client delegations into the intended Hermes session (the app's existing session for an in-app integration), silent `commentary` progress, one speakable `"Agent Final Message"`. Measured on the same acoustic script it removed plumbing/capability-confusion turns (0 vs 6/42) and cut words per turn 16 to 5, with faster first audio; its barge-in stop is slower (~1.5 s vs ~0.33 s).

## On-phone local voice candidates (2026-11 state)
- Use audio.cpp (`0xShug0/audio.cpp`, Apache-2.0, ggml) as the single phone-side engine. It covers Phonon, Pocket, Qwen3-TTS, Kitten, Kokoro, LFM3-Audio S2S, Moonshine, Parakeet, Silero VAD and Smart Turn.
  - Android arm64 CPU build: NDK toolchain, `-DGGML_CPU_ARM_ARCH=armv8.2-a+dotprod+fp16+i8mm`, OpenMP off, `AUDIOCPP_BUILD_NATIVE_MODEL_MANAGER=OFF`, and `-DCMAKE_EXE_LINKER_FLAGS=-llog`. Without liblog the link fails on `__android_log_write`. Strip the result to ~28 MB.
  - Fetch models with `tools/model_manager_v2.py install <pkg> --models-root DIR`.
  - The LFM3 GGUF needs `--model-spec-override model_specs/lfm3_audio.json`.
  - Pocket needs `--voice-id alba`.
  - Kitten and Kokoro need eSpeak-ng (GPL) at runtime; avoid them on the phone.
  - Artifacts: `/mnt/zer0models/models/zlv-tts/` (`phone-bundle/tts_probe.sh` and models).
- ~0.6B "very natural" TTS models (Qwen3-TTS 0.6B, Lure 0.6B/Turbo) set the naturalness ceiling, not the live phone voice. On groot's 3080 Ti, first audio p50 is 555–900 ms. On CPU, RTF is ~5–6, and the vendor-measured Galaxy S26 LiteRT RTF is 2.6. Phonon 31M and Pocket are real-time on CPU.
- Measured on the S25 (CPU, 4 unpinned threads, audio.cpp from /data/local/tmp): Phonon 31M ~80 ms load->first chunk (bench median) at RTF ~0.5, Pocket ~150 ms at RTF ~0.5, LFM3-Audio-2B Q4 S2S 8.6 s wall for a 5 s answer with correct content. A CLI probe launched with `adb shell` never touches display focus, so it needs no virtual display; still check `mTopFocusedDisplayId` before and after.
- S25 hardware (probed): SM8750, cpus 0-5 Oryon perf 3.53 GHz (taskset `3f`), cpus 6-7 prime 4.47 GHz (`c0`), WALT governor; i8mm/bf16/dotprod, no SVE/SME; Adreno 830 (OpenCL + Vulkan); Hexagon HTP **v79** (not v75). Full profile: autokernel `mobile/hw/s25.json`.
- Pipeline stages (host-qualified; recipes in autokernel `mobile/stages.json` / `STAGES.md`):
  - ASR: Moonshine-tiny (~4% WER at 0.016 RTF) is the speed pick; SenseVoice and Moonshine-small reach ~1% WER. Kroko is the one that streams partials.
  - VAD: Earshot (~1.5 ms per clip).
  - Turn detection: don't trust Smart Turn v3 alone, because it scored a trailing-off incomplete clip as complete (0.92).
  - LLM: audio.cpp has no text-LLM route. Use llama.cpp's official Android Snapdragon build, which includes Adreno OpenCL and Hexagon HTP v79 backends (Qwen3-0.6B / LFM2-1.2B Q4_0).
- Optimize the on-phone stack through the council autoresearch loop (`council-autoresearch-loops`); its referee is autokernel `mobile/bench_s25.py`. Phone-bench mechanics (owner-idle gate, telemetry, storage, timing): `references/s25-on-device-bench.md`.
- Phone runs follow the owner's tiered consent: read-only inventory, then isolated inference (adb push to /data/local/tmp), then mic/speaker. Each tier needs a separate yes, and a silent or timed-out ask means no.
- Run lure-tts CUDA with `transformers==5.15.1`; 5.22 breaks with `property 'upsample' ... has no setter`. Unset the Hermes `PYTHONPATH` (`env -u PYTHONPATH`) for every external venv, or numpy fails to import.

## Persona and tools
- The persona knows what it is (name, realtime voice provider/model, desktop broker minting sessions, Hermes seeing transcripts) and lists its real tools generated from the minted catalog, so new tools appear without persona edits.
- Say a missing capability is "not wired yet", never a privacy refusal: the owner reads a false refusal as the product being broken.
- Clients consume the minted tool list; a hardcoded allowlist in an APK silently drops new tools.
- Phone actions use public Android APIs; anything that sends (calls, texts) is prefilled and confirmed by the human. Each tool returns a structured result so the voice confirms honestly.
- In-app control (tap by exact text/view ID, `ACTION_SET_TEXT`, scroll, back/home) goes through an isolated AccessibilityService the owner enables manually in Settings plus per-session consent; never try to bypass Android's enablement. Refuse password fields and blocklisted sensitive apps, re-check the window before acting (ambiguous or stale target -> ask), and report `dispatched, verified:false` until the effect is confirmed on screen.
- The voice-to-Hermes path is the broker's existing native API bridge to `hermes -p clean`; when the owner names a bridge component that does not exist as a separate project, map it to that bridge rather than inventing a second protocol.

- Hermes Talk sessions run only a curated set of read-only host tools themselves and delegate everything else to full-toolset agents, with spoken approvals. Answer permission questions, and "use `/talk core join`" claims, from the installed plugin source and the host's real modules. [Hermes Talk permissions](references/hermes-talk-permissions.md) has the model, the reason, the core-lane gates and the real settings.

## Audio UX
- No unprompted summary at session start; open short and let the human lead.
- Waiting is silent. One short acknowledgement when work is dispatched, then speak only on a real state change, the result, or when asked. Never inject periodic "no update yet / something coming soon" turns and drop status injections that carry no new information; repeated filler makes the voice feel worse than the ChatGPT app on the same API, which the owner uses as the bar for natural conversation.
- Speak everything through the realtime model's voice. Reading inbox backlog or Hermes replies via Android TextToSpeech makes the owner hear robotic TTS, then a voice switch.
- Enable server/semantic VAD with interrupt_response and truncate assistant audio on speech start; test interruption explicitly.

## Screen understanding (privacy-first)
Accessibility UI tree as text first; on-device small VLM for pixels; desktop VLM over the tailnet only as fallback. Only text leaves the phone; per-session capture consent plus an app blocklist. Choose the model from a measured on-device benchmark on the owner's own screens (latency, RAM, thermals, accuracy), recorded on the z0intelligence model-portfolio issue.

## Packaging
The intelligence (voice session, screen reader, models, Hermes link, permissions) belongs in one separate z0 app; launchers and Dash are thin clients. Launchers can't host it reliably: only the default launcher stays alive on Samsung, models are GBs, permissions bind to one app, and upstream won't accept it. Lawnchair-side code follows Lawnchair's Compose/Material 3 design language exactly and stays in an isolated package so it can merge upstream.

## Verification
- Drive real GPT turns with text injected on the realtime data channel (debug-only hook) using natural owner phrasing; assert effects on the device, not the model's claims.
- Run phone checks as one scripted ADB batch (intents, wait-for-condition loops, evidence screencaps downscaled to <=720 px). Per-tap agent turns cost ~10 s each; raw ADB taps take ~0.06 s.
- Fire deep links only with the phone unlocked on the home screen and confirm focus; launched behind another app, confirm screens stay hidden and single-use credentials expire.
- Report what was not verified on the handset (mic, audio quality, background survival).
