# Hermes continuous duplex voice — architecture and first remaining slice

Status: BINDING for `t_178d1369` / `t_fad21e7f` (supersedes `t_c992ea57` ADR where they conflict)
Date: 2026-09-12
Evidence: `HERMES-VOICE-ISSUE-PR-DONOR-AUDIT.md`, `SOTA-CONTINUOUS-DUPLEX-VOICE-2026-09-12.md`, live `origin/main` `1c671beab29164d8931c5d01c5739502267089d8`
Publication / merge / maintainer ping: **not authorized**

This note does not re-research SOTA or re-audit PRs. It maps those artifacts onto current main.

---

## 0. Binding decisions (read first)

| Question | Decision |
|---|---|
| Improve GitHub PR **#95147 in place**? | **No.** CONFLICTING, Windows-file contamination, RFC author nominates #101808. |
| Open a competing ABC / Discord / Desktop / GPT-Live PR? | **No.** |
| First Desktop duplex slice? | **Already shipped on main** (Teknium `f923faa0b88` + `20816c13cdd`). Reuse; do not reimplement. |
| Remaining vertical slice? | **Discord VC PCM duplex**, opt-in, current in-tree plugin. |
| #95147 role? | **Selective reuse** of the waist (contracts, heard-boundary, exactly-once, fake two-provider tests). Cherry-pick/`-x` onto a **local** branch from **current** main. Preserve kvnloo authorship. |
| First Discord provider binding? | OpenAI Realtime **`gpt-realtime-2.1`** server WebSocket. GPT-Live WebRTC is not a bot-VC transport. |
| Agent / tools / approvals / history? | **Hermes only.** Voice models speak and propose. They never execute. |
| Default user behavior? | Unchanged. `voice.voice_chat_mode: chained`. Discord STT→Hermes→TTS stays the live path unless a **separate** Discord duplex flag is on. |
| This stale worktree `continuous-voice/t_c3c960f4` @ `fdb5ea295e5`? | **Evidence / salvage tests only.** Not the branch to push. Rebase from live main. |

Critical-path sentence:

Reuse landed GPT-Live (Desktop, opt-in) and current Discord/Hermes authority; cherry-pick only #95147’s heard-boundary / event identity / exactly-once / fake two-provider tests onto current main as a **local** coordinator waist; bind one OpenAI Realtime WebSocket adapter behind that waist into the **current** Discord plugin; prove duplex only in an authorized private VC. Do not merge, ping, or open a GitHub PR.

---

## 1. What already exists vs the gap

```text
MAIN TODAY
  Desktop chained STT→Hermes→TTS          default
  Desktop GPT-Live-1 WebRTC + client       opt-in voice.voice_chat_mode: gpt-live
    delegation (prompt.submit surface=
    voice-live; HUD note; key server-side)
  Discord VC                               half-duplex: VoiceReceiver pauses
                                           during play_in_voice_channel;
                                           PCM→WAV→STT→Hermes→TTS→VoiceMixer

GAP (this program’s only new slice)
  Discord capture stays live while mixing
  Local-first barge-in + heard-boundary
  Provider-neutral coordinator
  OpenAI Realtime WS as first adapter
  Exactly-once Hermes tools/approvals
  Durable transcript projection
  Metrics + legacy fallback
```

Do not treat GPT-Live Desktop as “the Discord slice.” Transport, interrupt clock, and heard-boundary are different. Do not treat S25 as the first proof surface: Discord already has gateway identity, VoiceReceiver, VoiceMixer, session/approval, and fallback.

---

## 2. Authority split (Codex / Hermes harness)

GPT-Live-1’s **client delegation** is the commercial analogue: the voice layer listens and speaks; the application owns tools, permissions, confirmations, and durable task state; interrupting speech does **not** cancel backend work.

Map:

| Concern | Owner | Never |
|---|---|---|
| Mic / speaker / PCM / mixer | Surface (Desktop renderer or Discord plugin) | Provider SDK inside core |
| Turn detection / audio gen | Provider adapter (capability-flagged) | Hermes inventing VAD |
| Tool schema / dispatch / approval | Hermes `handle_function_call` + existing `approvals.*` | Provider-native web/MCP/file tools |
| Session identity, history, prompt cache | Hermes SessionDB + conversation loop | Vendor `conversation_id` / Live session id |
| Reconnect identity | Hermes `session_id` + Discord user/guild | Provider resume token |

Prompt-cache invariant: do not swap toolsets or rebuild the system prompt mid-voice-session. Discord must not inject synthetic user turns that break role alternation. Follow GPT-Live: a **per-turn note** on model input (HUD-note seam), byte-stable system prompt.

DuplexJail (arXiv 2609.09420): spoken interruption is a **safety** surface. Do not weaken tool/approval because the user talked over a refusal.

---

## 3. Components and data flow

### 3.1 Components

```text
┌─────────────────────────────────────────────────────────────────┐
│ Surfaces (session-scoped, not process-env gated)                │
│  Desktop GPT-Live (main, out of this slice)                     │
│  Discord plugin: VoiceReceiver, VoiceMixer, auth, RESUME        │
└──────────────┬──────────────────────────────────▲───────────────┘
               │ PCM / playback receipts          │ PCM / cancel
┌──────────────▼──────────────────────────────────┴───────────────┐
│ RealtimeVoiceCoordinator  (Hermes waist, cherry-pick #95147)    │
│  epochs, event-id dedupe, transcript replace/finalize,          │
│  heard-boundary, bounded queues, grouped exactly-once tools     │
└──────────────┬──────────────────────────────────▲───────────────┘
               │ RealtimeSession                  │ RealtimeEvent
┌──────────────▼──────────────────────────────────┴───────────────┐
│ RealtimeVoiceProvider plugins (registry, profile-scoped)        │
│  openai-realtime (slice) │ grok-s2s │ gemini-live │ fake-*      │
└─────────────────────────────────────────────────────────────────┘
               │
               ▼
        existing AIAgent / handle_function_call / SessionDB
```

Footprint: **no new core model tool.** Coordinator is agent runtime, not a schema on every API call. Providers register via existing `PluginContext.register_realtime_voice_provider` (already in this worktree’s `hermes_cli/plugins.py`; port that method, do not invent a second hook).

Do **not** add in-tree `plugins/realtime_voice/openai/` — that is #101808’s vocabulary. The first adapter lives next to the Discord consumer (`plugins/platforms/discord/realtime_openai.py` or a sibling module) and is constructed by the Discord plugin when the opt-in flag is on. Later challengers are **standalone** plugins against the ABC.

### 3.2 Discord slice data flow

```text
authorized speaker RTP
  → VoiceReceiver (capture NEVER paused for duplex)
  → acoustic admission (echo / other-talker / backchannel / takeover)
  → bounded ingress queue (≤2.0 s)
  → coordinator.send_audio(pcm)
  → OpenAI Realtime WS (pcm16, server_vad or semantic_vad if advertised)
  → normalized RealtimeEvent
  → coordinator:
       transcript replace → one SessionDB user turn per turn_id
       TOOL_CALL → background Hermes dispatch (exactly-once)
       AUDIO → bounded VoiceMixer play_speech / streaming child
  → mixer consumption timestamps = heard clock
  → report_audio_heard(event, audio_end_ms)
  → barge-in: stop mixer → receipt → epoch++ → truncate → cancel
```

Half-duplex bug to remove **only when duplex is on**: `play_in_voice_channel` currently `receiver.pause()` then `resume()`. Duplex keeps the receiver running and relies on admission, not pause.

### 3.3 Desktop GPT-Live (existing; do not duplicate)

```text
renderer WebRTC  → POST /v1/live/sessions (tools/voice_live.py, key server-side)
                 → session.delegation.created
                 → prompt.submit(surface=voice-live) + voice_live_turn_note
                 → session.commentary.append → spoken paraphrase
```

Interrupt does not cancel Hermes tools. That policy is **the default for Discord too**.

---

## 4. Interrupt and endpointing model

### 4.1 Local-first barge-in (binding order)

Copied from SOTA §4.1 and ADR §4.5. Provider `interrupted` is telemetry, not the silence gate.

1. Capture stays on while playing (true duplex). Echo admission so TTS does not false-trigger.
2. On **local** speech-start classified as takeover: **stop VoiceMixer speech immediately** (`stop_speech` / drain current child). Do not wait for RTT.
3. Emit the final playback receipt for the old epoch (`HeardAudioBoundary`).
4. Coordinator increments `cancellation_epoch` and rejects stale audio/transcript/continuation.
5. `truncate_response(boundary)` when the adapter supports it (OpenAI `conversation.item.truncate` with **heard** ms, not generated ms).
6. `cancel_response()` (`response.cancel` or equivalent).
7. Capture remains active; a new `turn_id` is assigned only after authorized endpoint/finalization.

`voice.barge_in` already exists for Desktop chained TTS. Discord duplex uses the same **policy name** but a different clock (mixer frames, not renderer RMS). Do not overload Desktop grace/threshold constants onto Discord VC.

Classify overlap when possible: takeover vs backchannel vs echo vs other-talker. Acoustic-only VAD will false-cut (xAI, Nova, Gemini SIP). First slice: conservative takeover (energy + not-in-echo-window); backchannel (“mm-hm”, <300 ms) must **not** cancel.

### 4.2 Endpointing

Two-stage, capability-flagged on the adapter:

| Flag | Meaning | First Discord adapter |
|---|---|---|
| `server_vad` | Acoustic gate | OpenAI default; xAI **only** option |
| `semantic_vad` | OpenAI-only eagerness | Optional on OpenAI; **never send to xAI** |
| `manual` / PTT | Noisy VC fallback | Compose existing Discord half-duplex commit |
| `pause_sensitivity` | Nova-style | **Do not** adopt 1.5–2.0 s as Hermes default |

Do not copy Gemini “interrupt discards pending function calls” as Hermes policy.

### 4.3 Streaming playback

- Bounded playout (target ≤1.0 s queued). Backpressure fail-closed; never drop mid-item sequenced audio — cancel + degrade instead.
- Sequence + epoch on every audio delta; stale epoch discarded.
- Mixer consumption timestamps are the heard clock. `heard_through_ms == played_through_ms` is labeled **playback_receipt**, not biological hearing.

---

## 5. Heard-boundary and transcript reconciliation

### 5.1 HeardAudioBoundary

Already in this worktree (`agent/realtime_voice.py`):

```text
HeardAudioBoundary(item_id, audio_end_ms, response_id, cancellation_epoch)
```

Receipts: no foreign item, no regression, no future-of-generated, no stale epoch. `report_audio_heard` must identity-match the **emitted event object** (worktree hardening `fdb5ea295e`: retain emitted event identity; do not re-wrap).

Four cursors per `(response_id, item_id)` (ADR §4.4): generated / accepted_by_surface / played / heard. Discord slice approximates heard = played.

Durable assistant history = **heard** text, not planned/generated. Unplayed tail is an interruption marker, not SessionDB assistant content.

### 5.2 Transcript

User text is **replacement-capable** (`revision`, `final`, never append-only). Normalize:

- OpenAI input deltas (may revise; key by `item_id`)
- xAI cumulative `updated` then `completed` (later adapter)
- Nova SPECULATIVE vs FINAL (not in slice)

Rules:

1. Partial replaces prior unstable hypothesis.
2. Duplicate `event_id` is idempotent.
3. Older revision cannot overwrite newer.
4. Only input **final** creates a Hermes user turn.
5. Exactly one final per `turn_id`; conflicting later final is a reconciliation fault, not a second turn.
6. Provider finalization does not bypass Discord speaker allow-list.

---

## 6. Exactly-once tool / approval path

Provider `TOOL_CALL` events are **proposals**.

1. `call_id` required; payload SHA-256 of canonical JSON.
2. Cache terminal outcome `(call_id → (payload_hash, output))`. Replay returns the cache. Collision (same id, different hash) → fail closed, no execute.
3. Dispatch through existing Hermes callback (`handle_function_call` / approval policy). **Not inline** on the audio iterator (Enough1122 review). Bounded background tasks (`max_pending_tools`, default 8).
4. Grouped settlement: collect a response’s calls; submit results together; **one** continuation per `(response_id, tool_group_id, epoch)`.
5. Approval deny/timeout is a spoken coordinator state, not a silent hang. Zero side effects on deny.
6. Voice interrupt ≠ tool cancel. Finish already-authorized work in Hermes; do not resume stale provider speech. Bind work to epoch / `delegation_id`.
7. Disable provider-native search/MCP/file tools on the session (`tools` sent to the provider = Hermes function schemas only, or empty + host-side intercept). GPT-Live Desktop sends **no** tools to the voice model; Discord Realtime must intercept because the Realtime API expects function events — still Hermes-executed.

No new core tool. No second converse loop (#103279 rejected).

---

## 7. Reconnect

Two layers, never collapsed:

| Layer | Owner | Identity |
|---|---|---|
| Discord voice RESUME | current plugin / #87300 compose | `surface_connection_id` |
| Provider WS | adapter | `provider_session_id` (cache only) |

Host `session_id`, `turn_id`, `call_id`, epochs survive both. xAI `conversation_id` / Gemini handle = optional acceleration, gone under ZDR — Hermes SessionDB is truth.

After 2 s log `reconnecting`; by 5 s p95 recover or visible legacy fallback. Fallback must not re-submit the active finalized user turn. Stale `surface_connection_id` cannot submit receipts.

---

## 8. Metrics (redacted)

Labels only: surface, provider, model, network class, stage, outcome, config hash. **No PCM, no transcript, no keys, no Discord message text.** IDs are trace fields with retention limits, not metric labels.

Stage timestamps (monotonic ns):

```text
capture_open, speech_first_frame, vad_speech_start, last_voiced_frame,
endpoint_decision, transcript_partial_first, transcript_final,
agent_submit, approval_requested, approval_resolved,
tool_group_start, tool_group_terminal, response_created,
first_audio_received, first_audio_queued, playback_first_sample,
interruption_detected, local_playback_silent, provider_cancel_ack,
playback_end, reconnect_start, reconnect_ready,
fallback_start, fallback_ready, turn_complete
```

Also: queue high-water bytes/ms, coalesced revisions, deduped events, stale-epoch drops, generated-vs-played divergence, failures by stage.

---

## 9. Opt-in surface and fallback

### 9.1 Do not extend `voice.voice_chat_mode`

On main that key is a **Desktop** engine switch, allow-list `chained | gpt-live` (`tui_gateway/methods_config_set.py`). A third value would break the composer menu. Discord duplex is a **different surface**.

### 9.2 New keys (config.yaml only; no `HERMES_*` behavioral env)

Add under existing `voice:` in `hermes_cli/config_defaults.py` (deep-merge; **no** `_config_version` bump):

```yaml
voice:
  voice_chat_mode: chained          # UNCHANGED default (Desktop)
  gpt_live: { ... }                 # UNCHANGED
  discord_duplex:
    enabled: false                  # default: current half-duplex STT→TTS
    provider: openai                # adapter name in the registry
    model: gpt-realtime-2.1
    vad: server_vad                 # server_vad | semantic_vad | manual
    max_ingress_seconds: 2.0
    max_playback_seconds: 1.0
    max_pending_tools: 8
    reconnect_deadline_seconds: 5.0
```

Secrets stay in `.env` (`OPENAI_API_KEY` / existing OpenAI audio chain). Optional override `voice.discord_duplex.api_key` only if we already allow `voice.gpt_live.api_key` (config-held secret exception already used for GPT-Live — do not invent a new env).

Gateway/Discord: when `enabled: false` or adapter unavailable, **bit-identical** current path (`VoiceReceiver.check_silence` → WAV → `transcribe_audio` → Hermes → TTS → `play_in_voice_channel` with pause).

Fallback triggers: flag off; missing key; adapter open failure; overflow; reconnect deadline; provider error class retryable-exhausted. Visible/logged `DEGRADED_LEGACY`. One legacy turn in the same Hermes session; no duplicate prompt.

---

## 10. Privacy and authority rules

| Rule | Detail |
|---|---|
| What is stored | SessionDB: finalized user transcript, Hermes tool/approval records, heard-aligned assistant text, interruption markers. Not PCM. Not generated-unplayed audio. Metrics: timestamps only. |
| Logs | No raw provider errors to Discord text. No keys. Default logs: no transcript. |
| Who approves tools | Existing Hermes `approvals.mode` for that session/profile. Voice is not an approval bypass. Discord allow-list / mention gates unchanged. |
| Reconnect identity | Hermes profile + session_id + Discord user snowflake. Not OpenAI session id, not GPT-Live session id, not xAI conversation_id. |
| Credentials | Long-lived keys stay on the gateway process. Desktop GPT-Live already mints WebRTC via `POST /v1/live/sessions`. Discord slice is server-WS — no ephemeral client secret needed. |
| Speaker auth | Current `VoiceReceiver(allowed_user_ids)`. Unauthorized RTP is not a turn. |
| Safety | Interrupt does not skip a pending approval. DuplexJail: do not treat barge-in as jailbreak-success / tool-abort. |

---

## 11. Provider-neutral interfaces (slice may bind one)

Keep the worktree / #95147 names so cherry-picks apply. Do **not** rename to #101808’s `realtime_voice_provider.py` / `orchestrator.py` in this program.

```text
REALTIME_VOICE_INTERFACE_VERSION = "hermes.realtime_voice.v1"

RealtimeVoiceProvider
  name, is_available(), get_setup_schema()
  open_session(instructions, tools, voice) -> RealtimeSession
  advertised_capabilities: frozenset
    {truncate, semantic_vad, server_vad, provider_resume,
     transcript_replace, parallel_proposals, binary_frames}

RealtimeSession
  send_audio(pcm)
  events() -> AsyncIterator[RealtimeEvent]
  submit_tool_result(call_id, output)
  truncate_response(HeardAudioBoundary)   # default no-op
  cancel_response()
  close()

HeardAudioBoundary
RealtimeEvent  (explicit event_id, epoch, sequence; never id(event))
```

Coordinator correctness **must not** depend on truncate/resume/semantic_vad. Local stale rejection always works.

First concrete transport: OpenAI Realtime WebSocket (documented events: input audio append, `speech_started`, item truncate, function call, output audio delta). Two **deterministic fake** adapters in tests (already the #95147 pattern): one with truncate, one legacy cancel-only.

Later plugs (not this slice): xAI `wss://api.x.ai/v1/realtime` (server_vad only; disable native tools; resume is cache); Gemini Live (do not copy pending-tool-cancel); Moshi local reference.

---

## 12. Smallest vertical-slice scope

**Proof surface: Discord private VC** (one authorized speaker). S25 / Desktop GPT-Live are **not** this slice’s acceptance; Desktop is already on main; S25 remains a later gate (`t_fad21e7f` may only claim Discord unless a human re-scopes).

### In slice

- Real PCM in/out on **current** `plugins/platforms/discord` (VoiceReceiver + VoiceMixer). Not a stub. Not #21504’s tree.
- Capture remains active during playback.
- Streamed playback through VoiceMixer (extend with a cursor; do not replace the mixer).
- Local-first barge-in + echo-safe admission (fresh-port ideas from #75325 / #92762 / #80996; do not merge those branches).
- Heard-boundary + epoch stale rejection.
- Exactly-once Hermes tools/approvals (grouped, non-inline).
- Durable transcript replace/finalize into existing SessionDB.
- Redacted metrics.
- Opt-in `voice.discord_duplex.enabled` default false; legacy path unchanged.
- OpenAI Realtime `gpt-realtime-2.1` adapter behind DI (live calls only in `t_fad21e7f`).
- Focused tests: barge-in, heard-boundary, exactly-once, transcript durability, fallback, two fake providers.
- Contributor credit in commit bodies.

### Out of slice

- Any GitHub PR, force-push, merge, maintainer ping, catalog/docs publication.
- Improving #95147’s GitHub head; competing with #101808 / #101034 / #103279 / hermes-talk / hermes-live-voice.
- Desktop GPT-Live / `voice.voice_chat_mode` changes; #95180; TUI visualizer.
- S25 / Android companion / WebUI bridge (#95191).
- xAI / Gemini / Moshi adapters; Voice Agent Builder; ElevenAgents.
- Multi-speaker VC, ambient bed as a feature, cloned voices, Meet/SIP/WhatsApp.
- New core tool, new `HERMES_*` behavioral env, second session store.
- Nova 1.5 s endpoint as default; Gemini interrupt-cancels-tools.

---

## 13. Implementation plan against current main + #95147

### Non-duplication statement

This program **does not** open a parallel competing PR. It **does not** push to `feat/realtime-voice-provider`. It **does not** merge Windows-contaminated commits `239501833569` / `e426eb62`. It **does not** vendor hermes-talk or reimplement GPT-Live.

Local branch from **live** `origin/main` (`1c671beab29` or newer). Cherry-pick/`-x` **realtime-only** commits from #95147 and salvage tests from worktree `fdb5ea295e5`. If a human later publishes, it is a **follow-on** from current main, not an update to #95147, and only after merge-order vs #101808 is decided out of band.

Do not duplicate: #95147, #101808, #101034, #97325, #108568, #106640, #103279, #21504, #27650, #27040, #31604, #75325.

### File / API map

| Path | Action |
|---|---|
| `agent/realtime_voice.py` | Cherry-pick ABC + `HeardAudioBoundary` + `RealtimeEvent` (explicit ids). Absent on main. |
| `agent/realtime_voice_coordinator.py` | Cherry-pick + worktree hardening (event identity, epochs, hash dedupe, non-inline dispatch, bounded ingress/playback). |
| `agent/realtime_voice_registry.py` | Cherry-pick profile-scoped registry. |
| `hermes_cli/plugins.py` | Port `register_realtime_voice_provider` only (already in this worktree). Do not grow PluginContext otherwise. |
| `tests/agent/test_realtime_voice.py` | Cherry-pick + expand tracer bullets (two fakes). |
| `tests/hermes_cli/test_plugins_realtime_voice_registration.py` | Cherry-pick. |
| `hermes_cli/config_defaults.py` | Add `voice.discord_duplex` block; do not bump `_config_version`; do not touch `voice_chat_mode`. |
| `plugins/platforms/discord/adapter.py` | Duplex listen loop gated on flag: no `pause()` during play; admission; PCM pump into coordinator; compose RESUME. |
| `plugins/platforms/discord/voice_mixer.py` | Playback cursor / `played_through_ms` receipts; `stop_speech` already exists — use it as local silence. |
| `plugins/platforms/discord/realtime_openai.py` | **New**, Discord-plugin-local OpenAI WS adapter implementing `RealtimeSession`. DI; no live call in unit tests. |
| `plugins/platforms/discord/realtime_consumer.py` | **New**, wires coordinator ↔ receiver/mixer; fallback to `_process_voice_input`. |
| `tools/voice_live.py`, Desktop `voice-live.ts`, `use-voice-live-conversation.ts` | **Do not modify.** |
| `scripts/desktop-update/windows.ps1` | **Do not touch** (contamination). |

### Suggested RED→GREEN order (implementer)

Credential-free first. Live OpenAI/Discord only in `t_fad21e7f`.

1. Isolated worktree at live main. Do not continue `continuous-voice/t_c3c960f4`.
2. Cherry-pick realtime-only #95147 + identity/epoch tests. Stop if main has landed a competing ABC.
3. Coordinator amendments already in `fdb5ea295e` if missing from the GitHub cherry-picks.
4. Fake two-provider tests: truncate vs legacy cancel; collision; stale epoch; conflicting final.
5. OpenAI adapter against documented protocol, DI, no network in unit tests.
6. Discord consumer + mixer cursor + opt-in config + fallback.
7. Focused `scripts/run_tests.sh` on the new tests. No claim of real duplex.

### Donor credit (commit bodies)

TheSmokeDev #77111/#101808; kvnloo #95147/#94462; Teknium GPT-Live; RationallyPrime #21504 (PCM ideas); RichardHojunJang #75325; AustinKelsay #75014; Enough1122 review.

---

## 14. Success metrics (architecture targets for `t_fad21e7f`)

Deterministic tests must exist before device proof. Device proof is **not** this card.

| Requirement | Target |
|---|---|
| Default path | With flag off, Discord still pause-during-TTS half-duplex; Desktop `chained` unchanged |
| Warm EOT → first audible | p50 ≤700 ms, p95 ≤1500 ms (private VC, warm) |
| Interrupt → local silence | p95 ≤150 ms, max ≤250 ms |
| Stale audio after interrupt | p95 ≤100 ms, max ≤200 ms |
| Transcript | one finalized user turn per exchange |
| Tools | exactly-once by `call_id`; deny executes zero times |
| Reconnect | recover or fallback ≤5 s p95; no duplicate turn/side effect |
| Privacy | zero keys/PCM/raw provider errors in Discord text or default metrics |
| Safety | 100% on unauthorized-speaker and approval-deny fixtures |

Synthetic audio / unit tests are **not** `t_fad21e7f` acceptance.

---

## 15. Open questions — human-gated (out of band)

Do **not** resolve these by opening a PR, pinging teknium/TheSmokeDev, merging, or publishing.

1. **ABC merge-order:** #95147 waist vs #101808 orchestrator vs “no ABC, GPT-Live-style delegation only.” This program implements a **local** #95147-shaped waist. A maintainer may later ask to port heard-boundary onto #101808 instead.
2. **Whether any GitHub PR should exist** for the Discord slice. Default: **no**. `t_178d1369` must not open one. If a human later wants publication, it is a follow-on from current main after (1).
3. **Proof surface override:** this architecture picks Discord, not S25. Changing that is a human re-scope of `t_fad21e7f`.
4. **Discord credentials** for the canary (intake/chiefstaff currently lack `DISCORD_BOT_TOKEN` per `t_d0d6c90c`). Capability block belongs on the **prove** card, not on architecture.
5. **Closing #77111 / #94462 / #95147** — never from this program.

---

## 16. Handoff to `t_178d1369`

Follow this file. Do not redesign. Do not re-audit. Do not re-research SOTA.

Start from **current** `origin/main`, not this scratch worktree. Treat GPT-Live on main as already done. Treat #95147 as a cherry-pick donor, not a merge vehicle.

When implementation is code-complete without live credentials, do **not** claim duplex; leave real VC proof to `t_fad21e7f`.
