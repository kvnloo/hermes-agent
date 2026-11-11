# Device proof — t_fad21e7f (blocked, not accepted)

Observed: 2026-09-12T20:15:41Z. Surface required by architecture: **Discord private VC**, not S25.
No merge, no GitHub PR, no maintainer ping, no duplicate graph.

This card does **not** claim duplex. Synthetic/unit tests are not acceptance
(`HERMES-CONTINUOUS-VOICE-ARCHITECTURE.md` §14).

## Setup (what exists)

| Item | Result |
|---|---|
| Slice branch | `continuous-voice/t_178d1369` @ `3cdd1e9489f119b29af7d3dde76613b5dbd3a3fc` |
| Worktree | `/mnt/zer0models/workspaces/hermes-kanban/t_c3c960f4/impl-from-main` (ahead 1 of origin/main; not pushed) |
| Adapter files | `plugins/platforms/discord/realtime_openai.py`, `realtime_consumer.py` present |
| Opt-in default in slice | `voice.discord_duplex.enabled: false` (config_defaults) |
| Intake process env | `OPENAI_API_KEY` unset, `DISCORD_BOT_TOKEN` unset |
| Intake `.env` Discord/OpenAI/Voice keys | none |
| Default `~/.hermes/.env` Discord/OpenAI/Voice keys | none |
| Chiefstaff `.env` | `DISCORD_BOT_TOKEN` present, `DISCORD_ALLOWED_USERS` present; **no** `OPENAI_API_KEY` / `VOICE_TOOLS_OPENAI_KEY` / `REALTIME*` |
| Live Discord gateway | `hermes-gateway-chiefstaff.service` active/enabled, PID 3956093, NRestarts=0 |
| Live Discord identity | connected `groot#9037` (`gateway_state.json` platforms.discord.state=connected) |
| Live chiefstaff `config.yaml` | no `voice.discord_duplex` key (production tree, not the slice); `stt.provider: local`, `tts.provider: xai` |
| S25 | `adb devices` empty — no physical device |
| Secrets printed | no |

Live Discord is the **production** chiefstaff gateway on the installed tree, not the slice worktree.
Token lock forbids a second gateway on the same bot token. This run did not swap production code,
did not set `voice.discord_duplex.enabled`, and did not join a voice channel.

## Requirement matrix vs architecture §14

| Requirement | Target | This run | Verdict |
|---|---|---|---|
| Real audio transport E2E | Discord VC PCM in/out on the slice | Not run (slice not loaded on live bot; no OpenAI Realtime key) | FAIL / not observed |
| Continuous listening | Capture live while mixing | Not run | FAIL / not observed |
| Streamed playback | VoiceMixer cursor / voice FX | Not run | FAIL / not observed |
| Local-first barge-in | Interrupt → local silence p95 ≤150 ms, max ≤250 ms | Not run | FAIL / not observed |
| Heard-boundary | Mixer `played_through_ms`; stale audio p95 ≤100 ms | Not run | FAIL / not observed |
| Exactly-once tools/approvals | `call_id` once; deny executes zero times | Not run live (unit-only on parent card) | FAIL / not observed |
| Durable transcript | One finalized user turn per exchange; before/after correction | Not run | FAIL / not observed |
| Metrics | Stage timestamps; no PCM/transcript/keys | Not run live | FAIL / not observed |
| Warm EOT → first audible | p50 ≤700 ms, p95 ≤1500 ms | No samples | FAIL / not observed |
| Reconnect | Recover or fallback ≤5 s p95; no duplicate turn | Not run | FAIL / not observed |
| Privacy | Zero keys/PCM/raw provider errors in Discord text or default metrics | No duplex session to inspect | N/A this run |
| Default/legacy with opt-in off | Pause-during-TTS half-duplex still the live path | Live chiefstaff has **no** duplex flag and is still STT→Hermes→TTS config; this run did **not** exercise a VC pause-during-TTS session | PARTIAL config-only; not a voice proof |
| Unauthorized-speaker / approval-deny | 100% on fixtures | Live unauthorized RTP not exercised | FAIL / not observed |

Parent `t_178d1369` reported 36/36 credential-free tests. Those are **not** copied here as device evidence.

## Privacy notes (what would leave the device if the slice ran)

Intended path: Discord RTP PCM → gateway process → OpenAI Realtime WebSocket (`gpt-realtime-2.1`).
Audio and transcripts would leave the host toward OpenAI. Discord bot token stays on chiefstaff.
This run sent **no** PCM and made **no** Realtime call.

## Residual gaps (do not widen into a second slice)

1. Scoped `OPENAI_API_KEY` (Realtime `gpt-realtime-2.1`) on a proof profile — missing everywhere checked.
2. Human authorization to run the **slice worktree** as Discord without clobbering production chiefstaff (or a dedicated test-bot token).
3. One authorized speaker in a private VC (`/voice join`) while capture/metrics are recorded.
4. Mixer/voice FX installed for streamed playback (else legacy FFmpeg one-shot).
5. S25 is out of slice unless a human re-scopes this card.

## Closeout this run

- No merge, no push, no GitHub PR, no maintainer ping.
- Production chiefstaff Discord left running (PID 3956093).
- Intake left Telegram-only.
- Proof **not** accepted.
