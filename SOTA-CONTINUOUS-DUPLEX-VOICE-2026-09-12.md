# SOTA continuous duplex voice (refresh) and Grok Voice first-party trace

Cutoff: 2026-09-12. Read-only. No implementation, no vendor API calls, no GitHub writes.

This document **reuses** the 2026-08-27 primary-source matrix (`t_7848a838`) and the Grok-lineage report (`t_c09450fd`). It does not rewrite those artifacts. It records what changed in 16 days, re-traces Grok Voice against current first-party xAI pages, and extracts provider-neutral patterns for Hermes.

Evidence classes (do not mix):

- **First-party:** vendor docs, model cards, official announcements.
- **Paper:** arXiv / peer-reviewed work.
- **Observed product:** community/forum reports of live behavior; not API contracts.
- **Speculation:** unlabeled similarity, marketing leaderboards, unpublished internals.

## Bottom line (2026-09-12)

The load-bearing delta since 2026-08-27 is **OpenAI GPT-Live-1 in the API** (2026-09-10): a full-duplex voice *layer* that delegates reasoning/tools to a backend the application owns.[9][10][11] OpenAI now documents three voice architectures—GPT-Live, Realtime S2S, and chained STT–LLM–TTS—rather than one Realtime product.[15] That is the closest commercial analogue to the Codex/Hermes harness split (voice speaks; Hermes remains session/tool/approval/history authority). Hermes Desktop already opted into a GPT-Live path on main; Discord PCM duplex remains a different transport.

**xAI Grok Voice** is still a native speech-to-speech WebSocket (`wss://api.x.ai/v1/realtime`) with OpenAI Realtime *event compatibility*, in-house VAD/tokenizer/audio models (first-party claim, no paper), acoustic `server_vad` only, optional 30-minute resume, and minute billing.[1][2][4] No first-party technical report or cited research bibliography has appeared. Lineage remains **undisclosed**, not “Moshi-like.”

Hermes must not treat any provider as a second agent. No reviewed API documents a human-approval primitive that can authorize side effects. GPT-Live states this explicitly: the application owns permissions, confirmations, and durable task state; interrupting speech does **not** automatically cancel backend work.[10][11]

## What changed since 2026-08-27

| Item | 2026-08-27 baseline | 2026-09-12 |
|---|---|---|
| OpenAI duplex | Realtime `gpt-realtime-2.1` recommended first adapter | **GPT-Live-1** is a separate full-duplex product ($0.05/min voice layer + delegated backend). Realtime remains the turn-based S2S API.[9][12] |
| xAI billing pages | 2.0 $0.08/min; 1.0 $0.05/min | Confirmed on pricing (updated 2026-09-07). 1.0 marked deprecated. Marketing pages still say “starting $0.05/min.”[3][4][7] |
| xAI internals | API contract only | Still no technical report. Same first-party sentence: in-house VAD, tokenizer, audio models.[1] |
| Claude Voice | Mobile beta, no public audio API | Product voice now on mobile, desktop, and web; still **no public realtime audio API**; not in Claude Code/Cowork; Fable excluded.[24] |
| Safety literature | — | DuplexJail (2026-09-08 preprint): spoken interruption as a jailbreak vector on open full-duplex models.[30] |
| Local/open | Moshi / LFM2.5 / Ultravox as before | No new production-grade native-duplex local drop-in. Ultravox 0.7 still audio→text.[27][28][29] |

## 1. Grok Voice — first-party trace (do not invent internals)

### 1.1 Surfaces (keep them separate)

| Surface | What it is | First-party source |
|---|---|---|
| Consumer Grok Voice (apps / Tesla / Starlink support) | Product voice. API launch says the Voice Agent API is “the same stack.” No protocol docs for the car/app path. | [1][6] |
| Speech-to-Speech / Voice Agent API | `wss://api.x.ai/v1/realtime?model=…`. Native audio in/out, tools, VAD. | [2][3] |
| Voice Agent Builder (2026-07-01 beta) | No-code telephony + RAG + tools + guardrails **on** Grok Voice. A product orchestrator, not the model. | [7] |
| Standalone STT / TTS (2026-04-17) | REST + WS, “built on the same stack.” Not duplex. TTS speech tags (`[laugh]`, `<whisper>`). | [6] |
| Custom voices (2026-04-30) | Clone from ~1 minute; passphrase + embedding check; usable on TTS and Voice Agent. | [8] |
| Grok Build CLI voice | **Dictation only** (STT into prompt). Not S2S. | Observed in xAI grok-build source comments; not a Voice Agent API claim. |

### 1.2 Disclosed architecture (first-party only)

xAI’s 2025-12-17 API launch is still the strongest internals statement:

> “We built the entire voice stack in-house, training our own voice activity detection (VAD), tokenizer, and audio models from scratch.”[1]

Also first-party:

- Bidirectional WebSocket; OpenAI Realtime **compatible**, with documented extensions (`force_message`, `resumption`, pronunciation `replace`).[2]
- Models: `grok-voice-think-fast-2.0` (flagship), alias `grok-voice-latest`; `grok-voice-think-fast-1.0` deprecated.[2][31]
- Region: `us-east-1`.[3][31]
- Session: max 120 minutes; default 10 concurrent sessions/team.[3]
- Turn detection: `server_vad` or `null` (manual). Parameters: threshold default 0.85, `silence_duration_ms`, `prefix_padding_ms` default 333, optional `idle_timeout_ms`. **No `semantic_vad` / Smart Turn on `/v1/realtime`.**[2]
- Interruption: VAD barge-in automatic in `server_vad`; `response.cancel` for manual; truncate unplayed tail.[2]
- Audio: PCM / PCMU / PCMA / Opus; PCM rates 8–48 kHz; JSON (base64) or binary frames.[2]
- Output speed 0.7–1.5. Reasoning effort `high` (default) or `none`.[2]
- Tools: `file_search`, `web_search`, `x_search`, `mcp`, custom `function`. Parallel custom calls documented in the prior SOTA; still no approval primitive.[2][3]
- Resume: opt-in `resumption.enabled`; cache keyed by `conversation_id`; 30 minutes inactivity; replays transcripts + tool calls + `function_call_output`. Not durable truth. Unavailable under ZDR.[2][5]
- Auth: API key (server) or ephemeral client secret (`xai-client-secret.` subprotocol) for browsers.[2]
- Privacy: default API logs 30 days, no training without permission; ZDR team-wide and **voice agent conversation history is not persisted** under ZDR.[5]
- Pricing conflict: Voice 2.0 is **$0.08/min audio + $0.004/text input**; 1.0 **$0.05/min** deprecated. Model card and Agent Builder still say “starting at $0.05/min.” Treat $0.08 as the live 2.0 meter.[3][4][7]

Self-reported (not independent, not a leaderboard): “#1 on Big Bench Audio”, “average time-to-first-audio of less than 1 second”, “nearly 5 times faster than the closest competitor”, blind preference vs OpenAI Realtime on pronunciation/accent/prosody, τ-voice Bench scores on the Agent Builder post.[1][7][32] Do not rank these against OpenAI Full Duplex Bench or Gemini “low latency.”

### 1.3 Unknowns (must stay unknown)

- No technical report, training data, parameter count, codec paper, or cited academic lineage on current Voice Overview / S2S / model pages (same finding as `t_c09450fd`).
- Whether consumer Tesla/app Voice is bit-identical to `grok-voice-think-fast-2.0`.
- Semantic endpointing: **not documented** for S2S. Do not send OpenAI `semantic_vad`.
- Generated-vs-heard: xAI documents cancel/truncate; it does **not** document a playback-receipt field. Hermes must own heard-boundary.
- Approval / human-in-the-loop: none.
- Independent p50/p95 barge-in-to-silence, false-cutoff, echo robustness.

**Speculation to refuse:** “Grok is Moshi,” “Grok uses SyncLLM,” “Grok has semantic VAD internally.” Feature overlap is not provenance.[1][2]

## 2. Comparison matrix (evaluation axes)

Legend: **FP** first-party, **Obs** observed, **Paper**, **Unk** not established in reviewed sources.

| System | Duplex / interrupt | Endpointing | Latency (as stated) | Turn-taking | Prosody | Transcript correction | Tools / approval | Reconnect | Privacy | Authority fit for Hermes |
|---|---|---|---|---|---|---|---|---|---|---|
| **OpenAI GPT-Live-1** | Native full duplex; one model listens+speaks; local playback still must stop on barge-in.[9][10] | Native turn detection even though not turn-based.[9] | Self-reported Full Duplex Bench turn-taking 0.798s vs 1.41s for realtime-2.1. Not an SLA.[9] | Designed for overlap, backchannels, thinking pauses (Speak: ~80% fewer interruptions vs turn-based — vendor eval).[9] | Prompt-steered tone/pace/style; more voices.[9] | Native ASR transcripts + response text; replacement contract not fully specified in getting-started extract.[9] | **Delegates** tools/reasoning to Responses or **client** backend. App owns permissions/confirmations. Interrupt does **not** cancel backend.[10][11] | Session close collects usage; no reviewed durable resume token in getting-started extract.[10] | Key stays on server; ephemeral client path implied by WebRTC quickstart.[10] | **Best commercial match** to Hermes: voice layer vs harness. Client delegation is the mapping. |
| **OpenAI Realtime `gpt-realtime-2.1`** | Bidirectional S2S; VAD cancel; WS must `conversation.item.truncate` with heard ms.[12][14] | `server_vad` or `semantic_vad` (eagerness).[13] | No public p50/p95 SLA. Session ≤60 min.[14] | Semantic VAD waits on “ummm…”; still acoustic-gated.[13] | Built-in voices; voice locks after first audio.[14] | Input deltas may revise; reconcile by `item_id`.[14] | Function tools + MCP; no approval primitive. `response.create` after results.[12] | No documented resume token.[14] | Client secrets; API data not for training (prior SOTA O7). | Strong protocol. Tools still fire inside the voice model unless Hermes intercepts. |
| **xAI Grok S2S 2.0** | Bidirectional; server VAD barge-in; cancel/truncate.[2] | Acoustic `server_vad` only.[2] | Self-reported <1s first audio.[1] | Idle re-engage timer optional.[2] | Speech tags on TTS path; S2S speed 0.7–1.5; no emotion scalar on S2S docs.[2][6] | Cumulative input `updated` then `completed` (Aug 27 SOTA, still the contract to implement against).[2] | Provider web/X/file/MCP **plus** functions. Disable provider tools. No approval.[2] | Opt-in 30 min cache.[2] | 30d logs or ZDR (drops voice history).[5] | Good second adapter. Resume is a cache. Do not enable xAI-native tools. |
| **Gemini Live** | Continuous input; `interrupted` flushes client buffer; pending function calls discarded.[16][17][18] | Automatic acoustic VAD; Proactive Audio; no named semantic VAD.[16] | “Low latency”; 20–40ms client chunks recommended (prior). | Barge-in first-class.[16] | Affective Dialog; 70 languages claimed.[16] | Optional in/out transcripts; correction contract Unk.[16] | Function + Search; non-blocking scheduling on some models (prior). No approval. Interrupt **cancels pending calls**.[17] | GoAway; resume handle (Developer 2h / Vertex 24h, prior). Audio-only ~15 min baseline (prior). | Free-tier may train; paid/Vertex differ (prior). | Useful challenger. Do not copy 15 min cap or interrupt-cancels-tools as Hermes policy. |
| **Amazon Nova 2 Sonic** | Concurrent I/O; barge-in marker.[19][20] | `endpointingSensitivity` HIGH/MED/LOW = **1.5 / 1.75 / ~2.0 s** pauses.[19] | Unk p50. Bidirectional Bedrock stream.[20] | Very patient vs semantic VAD. | Expressive multilingual (prior). | Assistant text SPECULATIVE vs FINAL (prior). | Async tools; **not** auto-cancelled if user changes request (prior). No approval. | ≤8 min connection; client replay (prior). | Bedrock retention settings (prior). | Do **not** copy 1.5s endpoint as Hermes default. Keep async-tool non-cancel as a hazard. |
| **Hume EVI 3 / 4-mini** | Always interruptible; tone-aware end-of-turn (product claim).[21] | Prosody-based EOT; exact semantic contract Unk.[21] | “Low latency” Unk SLA.[21] | Expression-aware.[21] | Core differentiator: prosody in and out.[21] | Transcripts + expression measures; replacement Unk.[21] | Tools; parallel/approval Unk.[21] | Chat config/resume Unk detail.[21] | API key; retention Unk. | Prosody donor, not first slice. Hybrid if supplemental LLM enabled (4-mini requires it).[21] |
| **ElevenAgents** | Interruptions + proprietary turn-taking.[22] | Proprietary model; not native S2S.[22] | Config-dependent (ASR+LLM+TTS hops).[22] | Claimed product strength.[22] | 5k+ voices / many languages.[22] | Conversation events; replacement Unk.[22] | Tools in the **agent product**. Parallel/approval Unk.[22] | Unk as a single contract. | Plan/residency mutable. | **Do not copy the agent.** Cascade + second control plane. Speech transport only if authority stripped. |
| **Azure GPT Realtime** | Tracks OpenAI Realtime family.[23] | server/semantic VAD per deployed version. | WS higher latency than WebRTC (prior). | Version-pinned. | Azure TTS voices optional on Voice Live.[23] | Version-pinned. | Tools; approval app-owned.[23] | Unk universal resume. | Azure/Entra, data zone SKUs.[23] | Pin version; same Hermes intercept as OpenAI. |
| **Azure Voice Live** | Unified API; **native or cascaded** depending on model (realtime vs GPT-5.x+STT/TTS).[23] | Semantic/multilingual VAD, AEC, noise (product). | Model-dependent. | Model-dependent. | 600+ voices / 150+ locales claimed.[23] | Pipeline-dependent. | Tools/MCP/Foundry; approval remains app.[23] | Unk one contract. | Foundry/Speech resource. | Do not treat as one model. Capability negotiation required. |
| **Anthropic Claude Voice** | Product two-way voice; interrupt by speaking; PTT option.[24] | Hands-free “natural pauses”; noisy rooms → PTT.[24] | Unk. | Product only. | Preset voices; **no cloning** (safety).[24] | Transcripts saved as chat history.[24] | Connected product tools; not a developer protocol.[24] | Same chat; text↔voice switch keeps context.[24] | Plan limits; transcripts stored.[24] | **Non-goal as an adapter.** No public audio API. Not in Claude Code/Cowork. Dictation ≠ duplex.[24][35] |
| **Moshi v0.1** | Native full duplex, two audio streams + inner text.[25][26] | No explicit turn segmentation; continuous.[25] | 160ms theoretical / ~200ms on L4.[25][26] | Joint user/assistant streams.[25] | Direct audio, overlap retained.[25] | Inner monologue text, not a revision API. | Not a Hermes tool protocol. | N/A (self-host). | Local. MIT/Apache code, CC-BY-4.0 weights.[25] | Protocol/local **reference**, not first cloud slice. 24GB PyTorch. |
| **LFM2.5-Audio 1.5B** | Interleaved audio/text generation for “real-time S2S chat”; **not documented as barge-in duplex**.[27] | Unk. | Designed for low latency; no official barge-in metric.[27] | Interleaved vs sequential modes.[27] | English only in card.[27] | Unk revision API. | Not a realtime tool protocol. | N/A. | LFM Open License v1.0 (commercial cap in prior SOTA).[27] | Local experiment only. |
| **Ultravox 0.7** | Audio **in** → streaming **text** out. External TTS for voice.[28][29] | N/A duplex. | Historical ~200ms text TTFT (prior). | N/A. | N/A. | Text generation. | Text tools if wrapped. | N/A. | MIT projector + backbone licenses.[28] | Exclude from native-S2S shortlist. |

### Observed (not first-party contracts)

- OpenAI forum: `interrupt_response: false` still cleared `output_audio_buffer` on `speech_started` for `gpt-realtime-2.1` WebRTC (2025-12 report). Treat local playback stop + truncate as mandatory even when flags say otherwise.[33]
- Gemini Live SIP: carrier echo of model audio retriggers VAD/`interrupted` (2026-05). AEC is a **client/telephony** problem; prefix padding is not enough.[34]

### Paper (safety)

DuplexJail (2026-09-08): fixed spoken interruptions raised attack success on PersonaPlex / PersonaPlex-RL (AdvBench whole-response ASR up to 40–49%). Full-duplex interruption is a safety surface, not only a UX feature.[30]

## 3. Codex / Hermes harness implications

| Pattern | Copy into Hermes? | Why |
|---|---|---|
| GPT-Live **client delegation** (voice continues; app runs tools/approvals; results return as commentary) | **Yes, as the authority split** | Matches “Hermes sole tool/approval/history owner.” Already the Desktop GPT-Live idea.[10][11] |
| GPT-Live “interrupt does not cancel backend” | **Yes, with epochs** | Approvals and terminal jobs must not die because the user said “wait.” Bind work to `delegation_id` / cancellation epoch; don’t silently drop.[11] |
| OpenAI `semantic_vad` | Optional on OpenAI Realtime adapter only | Not portable to xAI S2S.[2][13] |
| OpenAI WS `conversation.item.truncate(audio_end_ms)` | **Yes (heard-boundary)** | Generated ≠ heard.[14] |
| Local-first barge-in (stop speakers before RTT) | **Yes** | Google Cloud Tech / Gemini client docs; OpenAI WS guide.[14][18] |
| xAI `conversation_id` resume | Optimization only | 30 min; gone under ZDR; Hermes SessionDB is truth.[2][5] |
| xAI/Gemini/OpenAI provider-native web/MCP tools | **No** | Second agent. Expose only Hermes function schemas. |
| ElevenAgents / xAI Voice Agent Builder as the runtime | **No** | They *are* the orchestrator (telephony, RAG, guardrails, tickets).[7][22] |
| Nova 1.5s HIGH endpoint | **No as default** | Feels laggy vs semantic VAD.[19] |
| Gemini discard-pending-tools on interrupt | **No as Hermes policy** | Conflicts with exactly-once grouped tools. Record cancel; do not equate VAD start with tool abort unless the user intent is abort.[17] |
| Claude product voice UX (PTT in noise, limited voices, transcript-as-chat) | UX hints only | No API to implement.[24] |
| Moshi dual-stream | Local research / mental model | Hardware + no Hermes tool contract.[25] |
| Cascaded STT→Hermes→TTS | **Keep as fallback** | Current Discord/main default. Unchanged when realtime off. |

Prompt-cache invariant: do not swap toolsets or rebuild system prompt mid-voice-session. GPT-Live already uses a HUD-note seam on Desktop; Discord slice must not inject synthetic user turns that break alternation.

## 4. Extracted best patterns (provider-neutral)

These are implementation *contracts* for the architecture child (`t_30b59355`), not code.

### 4.1 Barge-in

1. Capture stays on while playing (true duplex), with echo admission so TTS does not false-trigger.
2. On local speech-start: **stop playback immediately** (clear device/mixer queue). Do not wait for provider `interrupted`.
3. Then send provider cancel (`response.cancel` / equivalent).
4. Truncate assistant history to **heard ms**, not generated ms.
5. Classify overlap when possible: takeover vs backchannel vs echo vs other-talker. Acoustic-only VAD will false-cut (xAI, Nova, Gemini SIP).

### 4.2 Endpointing

1. Two-stage: cheap acoustic gate + (when the adapter has it) semantic/prosodic completion.
2. Adapter capability flag: `semantic_vad | server_vad | pause_sensitivity | manual | none`.
3. Manual / PTT remains a first-class fallback (Claude product, OpenAI push-to-talk, noisy Discord VC).[14][24]
4. Do not globally adopt Nova’s 1.5–2.0s pause table.

### 4.3 Streaming playback

1. Bounded playout queue (bytes + time). Backpressure fail-closed.
2. Sequence + epoch on every audio delta; stale epoch discarded.
3. Mixer consumption timestamps are the heard clock (Discord VoiceMixer / Desktop audio).

### 4.4 Transcript reconciliation

1. User text is **replacement-capable** (revision, `is_final`, `supersedes`), never append-only. Normalize OpenAI deltas, xAI cumulative updates, Nova SPECULATIVE/FINAL.
2. Assistant durable history = **heard** text, not planned/generated.
3. One final user turn per Hermes `turn_id`.

### 4.5 Tool / approval

1. Provider tool events are **proposals**. Hermes `handle_function_call` is the only executor.
2. `call_id` exactly-once; payload-hash collision reject.
3. Grouped settlement: all results, then one continuation.
4. Approval deny/timeout is a spoken coordinator state, not a silent hang.
5. Voice interrupt ≠ tool cancel unless the user (or policy) says abort. GPT-Live’s rule is the default.[11]
6. Disable provider-native search/MCP on xAI/OpenAI/Gemini sessions.

### 4.6 Reconnect

1. Hermes ledger replay is canonical.
2. Provider resume (xAI `conversation_id`, Gemini handle) is optional acceleration.
3. Discord voice RESUME and provider WS reconnect are **two layers** (see sibling audit).
4. Dedup replayed tool calls.

### 4.7 Privacy / authority

1. Long-lived provider keys never reach clients; ephemeral tokens where the adapter has them (OpenAI client secrets, xAI `xai-client-secret`).[2][12]
2. Metrics: stage timestamps only; no PCM, no raw transcript in default logs.
3. ZDR / enterprise retention is adapter-specific; reconnect-by-provider-cache must degrade if ZDR is on.[5]
4. Duplex interruption is a **safety** surface (DuplexJail); do not weaken tool/approval because the user talked over a refusal.[30]
5. Identity on reconnect is Hermes session/profile, not a vendor call id.

## 5. Explicit non-goals and constraints (do not copy blindly)

1. **Claude Voice** is a consumer UI: no developer realtime endpoint, no Cowork/Code, no voice cloning, transcripts stored as chats, Fable excluded. Do not design Hermes around those limits or assume an Anthropic audio API.[24][35]
2. **ElevenAgents / xAI Voice Agent Builder / Azure Voice Live (cascaded SKUs)** are managed *agents*. Copying them duplicates Hermes.
3. **GPT-Live WebRTC** is not a Discord bot VC transport. Desktop may keep GPT-Live; Discord still needs PCM on the current plugin.
4. **xAI `semantic_vad` / Smart Turn** are not S2S features. Sending them is a protocol error.[2]
5. **Gemini ~15 min audio-only / 2 min A/V** baseline is a vendor quota, not a Hermes session model.
6. **Nova HIGH 1.5s endpoint** is too slow for “continuous conversation” UX.
7. **Vendor leaderboards** (Big Bench Audio, τ-voice, Full Duplex Bench, Tau3) are not comparable across houses; do not pick a provider by them.[1][7][9]
8. **OpenAI `interrupt_response` flag** is not a substitute for local barge-in.[33]
9. **Ultravox** is not speech-to-speech.[28][29]
10. **Do not invent Grok architecture** beyond the in-house VAD/tokenizer/audio-models sentence.[1]
11. **Do not open a competing PR** (sibling audit): selective reuse of #95147; GPT-Live-on-main is the Desktop slice; Discord remains the gap.
12. **No merge, no maintainer ping, no publication.**

## 6. Shortlist for the architecture child (not a re-decision of Discord vs Desktop)

Protocol completeness vs harness fit, **not** voice-quality ranking:

1. **GPT-Live-1 + client delegation** — authority split. Already on Desktop main as opt-in. Not Discord PCM.
2. **OpenAI Realtime `gpt-realtime-2.1`** — still the richest *event* protocol (semantic VAD, truncate, ephemeral secrets) for a Discord WebSocket adapter.
3. **xAI Grok S2S 2.0** — first challenger adapter (resume, codecs, minute price, cumulative transcripts). Acoustic VAD only.
4. **Gemini Live** — second challenger (affect, proactive silence, resume). Watch interrupt-cancels-tools and session caps.
5. **Moshi** — local duplex reference only.

Chained STT→Hermes→TTS remains the **default fallback**. Realtime stays opt-in (`voice.*` / existing `voice.voice_chat_mode`).

## 7. Evidence limits

- No live provider calls, microphones, Discord canaries, or S25 runs.
- Aug 27 matrices for Nova async-tools, Gemini resume TTLs, OpenAI pricing tokens, Hume/Eleven procurement remain valid unless contradicted above.
- GPT-Live getting-started/delegation pages were extracted 2026-09-12; some session-duration and transcript-revision details may live on unfetched subpages (`live-conversations`). Flag those as Unk rather than guessed.
- xAI “audio never stored” vs 30-day API log vs ZDR: use the Security FAQ as the retention source of truth.[5]

## Sources

[1] https://x.ai/news/grok-voice-agent-api — Grok Voice Agent API
[2] https://docs.x.ai/developers/model-capabilities/audio/speech-to-speech — xAI Speech to Speech
[3] https://docs.x.ai/developers/models/voice-agent-api — xAI Voice Agent API model page
[4] https://docs.x.ai/developers/pricing — xAI API Pricing
[5] https://docs.x.ai/developers/faq/security — xAI FAQ Security
[6] https://x.ai/news/grok-stt-and-tts-apis — Grok STT and TTS APIs
[7] https://x.ai/news/grok-voice-agent-builder — Voice Agent Builder
[8] https://x.ai/news/grok-custom-voices — Custom Voices
[9] https://openai.com/index/introducing-gpt-live-1-in-the-api — GPT-Live-1 in the API
[10] https://developers.openai.com/api/docs/guides/live — Getting started with GPT-Live
[11] https://developers.openai.com/api/docs/guides/live-delegation — GPT-Live delegation and tools
[12] https://developers.openai.com/api/docs/guides/realtime — OpenAI Realtime API
[13] https://developers.openai.com/api/docs/guides/realtime-vad — OpenAI Realtime VAD
[14] https://developers.openai.com/api/docs/guides/realtime-conversations — OpenAI Realtime conversations
[15] https://developers.openai.com/api/docs/guides/voice-agents — OpenAI voice agents
[16] https://ai.google.dev/gemini-api/docs/live-api — Gemini Live API overview
[17] https://ai.google.dev/gemini-api/docs/live-api/capabilities — Gemini Live capabilities
[18] https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/live-api/send-audio-video-streams — Gemini Live send audio/video
[19] https://docs.aws.amazon.com/nova/latest/nova2-userguide/sonic-turn-taking.html — Nova 2 Sonic turn-taking
[20] https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-2-sonic.html — Nova 2 Sonic model card
[21] https://dev.hume.ai/docs/speech-to-speech-evi/overview — Hume EVI overview
[22] https://elevenlabs.io/docs/eleven-agents/overview — ElevenAgents overview
[23] https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live — Azure Voice Live
[24] https://support.claude.com/en/articles/11101966-use-voice-mode — Claude voice mode
[25] https://github.com/kyutai-labs/moshi — Moshi GitHub
[26] https://arxiv.org/abs/2410.00037 — Moshi paper
[27] https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B — LFM2.5-Audio-1.5B
[28] https://huggingface.co/fixie-ai/ultravox-v0_7-glm-4_6 — Ultravox v0.7 GLM-4.6
[29] https://github.com/fixie-ai/ultravox — Ultravox GitHub
[30] https://arxiv.org/abs/2609.09420 — DuplexJail
[31] https://docs.x.ai/developers/models/grok-voice-think-fast-2.0 — grok-voice-think-fast-2.0
[32] https://x.ai/api/voice — Grok Voice product page
[33] https://community.openai.com/t/issues-with-realtime-turn-taking/1369161 — OpenAI community interrupt_response
[34] https://discuss.ai.google.dev/t/gemini-live-api-acoustic-echo-cancellation-needed-for-sip-telephony-deployments/144332 — Gemini Live SIP AEC thread
[35] https://code.claude.com/docs/en/voice-dictation — Claude Code voice dictation
