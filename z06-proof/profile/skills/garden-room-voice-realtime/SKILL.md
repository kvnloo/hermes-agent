---
name: garden-room-voice-realtime
description: Use when building garden-room browser voice control.
version: 1.0.0
author: Nous Research
license: MIT
metadata:
  hermes:
    tags: [voice, webrtc, jev, garden-room]
    related_skills: [rendered-ui-qualification, api-key-secret-storage]
---
# Garden-room voice qualification

## When to Use

Use when implementing, maintaining or verifying garden-room Speech API commands, Realtime WebRTC, voice feedback storage or Hermes drive integration.

## Procedure

- Keep client voice work in `public/modules/voice.js` + `voice.css` and stdlib server work in `routes/voice.py`; do not modify app.js/server.py during parallel module work.
- Build a full closed action table from current items, then shortlist named/selected items before submitting to Jev: the direct `/v1/systemone` API rejects choice dictionaries above 255 entries with HTTP 422. Include `reobserve` and `abstain`; enforce 0.65 on server and client.
- Keep parameters separate from action selection. Call Cerebras directly from the browser, using authenticated no-store config, and validate units, dimensions, room containment and locked state before GR execution. Never store provider keys in localStorage.
- Mint OpenAI GA client secrets using `{session:{type:'realtime',model:'gpt-realtime',instructions,audio,tools}}`; the response has top-level `value` and `expires_at`. For the owner-authorized OAuth path, read host Codex auth lazily and derive ChatGPT-Account-ID from the token claim. Never print tokens.
- Exchange browser SDP at `/v1/realtime/calls` with ephemeral bearer auth and `Content-Type: application/sdp`. A 201 SDP plus connected peer/open data channel proves transport; minting a secret alone does not.
- Prime the same remote audio element with silent WAV playback synchronously inside the user tap, before permission/token awaits. Qualify with strict `--autoplay-policy=user-gesture-required`, a live remote track, `paused === false`, unmuted volume 1, and nonzero inbound RTP audio energy. Test playback rejection and same-orb resume; headless playback cannot prove the physical phone speaker route.
- Default the one voice entry to conversation, and announce automatic backup. Backup abstain utterances need a real short conversational response plus speechSynthesis, not a caption telling the owner to discover another mode.
- Classify feedback with a binary feedback-versus-none question alongside action selection. Splitting bug and complaint can divide probability mass below the threshold and silently drop obvious feedback. Lexical final-transcript fallback and atomic persisted utterance-ID/text dedup protect delivery independently of GPT tool use.
- Move the existing orb/caption/audio into the AR dom-overlay rather than cloning controls or restarting media. Use viewport positioning to avoid placing captions over the AR bottom form; assert rendered overlay geometry. A glass/backdrop-filter ancestor still contains fixed descendants: lift the requested host into the XR overlay root rather than trusting position:fixed alone. Resolve status() as well as getState()/state for optional module context.
- Wait for the specific tool turn’s assistant completion before injecting another real response request. A startup greeting means any-transcript assertions and transient created/done count equality can falsely finish the previous turn while its tool continuation is just starting.
- Test actual GPT tool use by adding a normal user message requesting the tool, then `response.create`; a text-only forced-function response can return literal argument JSON as text instead of a function call. Capture real `response.function_call_arguments.done` before claiming tools work.
- Queue tool-continuation `response.create` until the prior response is done, so function arguments arriving before response.done do not race an active response. Handle async tool outputs and provider errors explicitly.
- Stop SpeechRecognition during local speechSynthesis and remote assistant playback to prevent voice-command echo. Mute the WebRTC input track during local confirmations; re-enable it afterward. On Speech API mic errors or repeated termination in Talk, use Realtime completed transcripts through the same Jev path.
- Arbitrate Speech API and Realtime transcripts per VAD turn to avoid executing the same utterance twice. Stop pending actions with a generation counter when voice is turned off.
- Resolve optional module APIs at call time. Older garden-room history modules expose a per-item History action, not GR.history; older AR modules expose their existing panel and `[data-tool=ruler]`, not GR.ar. Verify actual UI targets before confirming success.
- Isolate `/api/state`, `/api/zen/progress`, feedback, drive queue and private history in browser tests. Merely intercepting room-state PUT does not protect the owner's Zen journal from module onboarding writes.
- Use a scratch-directory silent WAV with Chromium `--use-fake-device-for-media-stream`, `--use-fake-ui-for-media-stream`, and `--use-file-for-fake-audio-capture=...` for real WebRTC transport tests without recording the host microphone.
- Run `python tests/voice_api.py`, `node tests/voice.mjs`, `node tests/voice_webrtc.mjs`, and finally `node tests/phone.mjs`. Inspect phone/narrow/wide/Talk screenshots. Parallel software-rendered scenes can delay camera matrix refresh past fixed smoke-test waits; diagnose with camera matrix/RAF evidence rather than masking failures.
- Never commit `data/voice/` logs or provider credentials. Commit only owned module, route, tests and documentation files when other builders share the checkout.
