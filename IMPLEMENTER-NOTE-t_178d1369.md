# Implementer note — t_178d1369 Discord PCM duplex slice

Status: code-complete on local branch `continuous-voice/t_178d1369` from origin/main `1c671beab29`. No GitHub PR. No merge. No maintainer ping. Not real duplex — device proof is `t_fad21e7f`.

## How to run

Worktree: `/mnt/zer0models/workspaces/hermes-kanban/t_c3c960f4/impl-from-main`

```bash
cd /mnt/zer0models/workspaces/hermes-kanban/t_c3c960f4/impl-from-main
scripts/run_tests.sh tests/agent/test_realtime_voice.py \
  tests/hermes_cli/test_plugins_realtime_voice_registration.py \
  tests/gateway/test_discord_realtime_openai.py \
  tests/gateway/test_discord_duplex_consumer.py \
  tests/gateway/test_discord_voice_mixer.py -q
```

Opt-in (config.yaml only; default remains half-duplex STT→Hermes→TTS):

```yaml
voice:
  voice_chat_mode: chained   # Desktop; do not add a third value
  discord_duplex:
    enabled: true
    provider: openai
    model: gpt-realtime-2.1
    vad: server_vad
```

Needs `OPENAI_API_KEY` (or `voice.discord_duplex.api_key`) and an authorized Discord VC. Missing key logs `DEGRADED_LEGACY` and keeps the current pause-during-TTS path.

## Reused vs new

Reused
- #95147 waist names and contracts: `agent/realtime_voice.py`, coordinator, registry, fake two-provider tests (kvnloo). Hardening from worktree `fdb5ea295e5` (event identity, epochs, payload-hash dedupe).
- PluginContext scoped registrar table (no bespoke PluginContext method).
- Current Discord `VoiceReceiver` + `VoiceMixer` (PCM in/out, `stop_speech`).
- Desktop GPT-Live / `voice.voice_chat_mode` — untouched.
- Hermes `handle_function_call` for tools/approvals.

New
- `voice.discord_duplex` defaults (`enabled: false`).
- `plugins/platforms/discord/realtime_openai.py` — OpenAI Realtime WS, DI websocket factory, 48k stereo ↔ 24k mono.
- `plugins/platforms/discord/realtime_consumer.py` — admission, local-first barge-in, fallback, transcript replace/finalize.
- Mixer `played_through_ms` heard clock; receiver `take_live_pcm`; adapter skips `pause()` when duplex is on.

## Tests (credential-free)

- Barge-in: mixer stop before provider cancel.
- Heard-boundary / stale epoch / identity.
- Exactly-once tools: collision fail-closed, grouped settlement, approval deny returns error without a second execute.
- Transcript: one final per turn_id; conflicting later final is not a second turn.
- Fallback: flag off; overflow → `DEGRADED_LEGACY`; unauthorized RTP is not a turn.
- Metrics: stage timestamps + counters (no PCM/transcript/keys).
- Two fake providers + OpenAI protocol DI (no network).

## Remaining gaps for device proof (`t_fad21e7f`)

- Live OpenAI Realtime WS + private Discord VC, one authorized speaker.
- Warm EOT→audible and interrupt→local silence vs architecture targets.
- Reconnect ≤5s p95 / visible fallback; no duplicate finalized turn.
- Mixer must be installed (voice FX enabled) for streamed playback; otherwise legacy FFmpeg one-shot.
- Echo admission is energy + echo-window only; no learned AEC.
- No live credential in this worker; do not claim duplex from these unit tests.

## Human-gated (do not do from this program)

Merge-order vs #101808, any GitHub PR, maintainer ping, closing #77111/#94462/#95147.
