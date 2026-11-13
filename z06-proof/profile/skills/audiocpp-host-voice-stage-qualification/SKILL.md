---
name: audiocpp-host-voice-stage-qualification
description: "Use when qualifying audio.cpp voice stages on host."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [audio.cpp, voice, benchmark, host]
    related_skills: [benchmark-checklist, oss-checkout-install]
---

# audio.cpp host voice-stage qualification

## When to Use

Use before adding on-device voice-stage benchmark lanes from host CLI recipes.

## Scope

Qualify VAD, turn, ASR and possible text-LLM routes without contacting a phone. Pin source commit, executable build/version, model package revisions/hashes and the benchmark's immutable starting commit. A concurrently advancing base branch is not an unchanged-referee reference.

## Procedure

1. Read the fixed benchmark and pinned ASR/model docs, model specs, and `audiocpp_cli --list-loaders --json`. Run loader discovery from the source checkout: advertising every loader may fail outside it when contracts are not deployment-embedded. `--help` can omit supported `turn`; verify execution rather than assuming the enumeration is exhaustive.
2. Query model-manager `sizes <shortlist> --jobs 3 --json` before installing. Enforce a byte budget, keep install commands/exit codes, and reuse bundled Earshot, Silero and MarbleNet assets. Use explicit `HF_HOME`, sanitized venv Python, `nice -n 10`, `--threads 4` and BLAS/OpenMP thread limits when modest CPU work is requested. Record ancestor cgroup quotas, not only visible CPU affinity.
3. Generate fixed PCM16 16 kHz mono English WAVs with hashes, source text, voice, duration and expected turn labels. For exact inserted pauses, synthesize clauses separately and insert zero samples; flag synthetic prosody as a limitation. Do not relabel incomplete clips to make a turn detector pass.
4. Execute one actual CLI per item. Capture monotonic line-receipt timestamps, exact argv/cwd/env, stdout/stderr, return code and typed output artifacts. `runtime.load.phase loaded` requires `--load-progress 1`; weight-upload progress can be lazy and is not an equivalent load boundary.
5. Distinguish `partial_text=` deltas from `partial_text_snapshot=` replacements; final transcript is `text_output=` plus the text artifact. Streaming file feed is unpaced and cannot establish live microphone-to-partial latency. Validate nonempty final outputs and corpus-normalized WER, not merely zero exit status.
6. Never assume the last `session.wall_ms` is whole-clip time. Some VAD paths emit it per chunk, ASR auto chunking can include helper VAD/subrequest markers, and some streaming paths emit none. Retain marker counts and raw native timing values. Explicitly define cross-recipe smoke RTF, such as `(FINAL receipt - LOADED receipt) / input duration`; retain process-including-load RTF separately. Do not sum nested timing scopes as exclusive work.
7. Read canonical streaming code when behavior contradicts names/docs. At audio.cpp a01aed4, Moonshine accepts chunks but buffers all waveform until finalize and emits no partials; Kroko is stateful streaming with a 660 ms finalization tail; Parakeet/Qwen3/SenseVoice have buffered alternatives. These are pinned findings, not promises about later versions.
8. Check standalone LLM support before downloading text checkpoints. At a01aed4 Qwen3 means ASR/TTS/aligner, not Qwen3 chat; LFM2/LFM3 audio expose ASR/TTS/S2S, not a text-to-text CLI. Preserve negative probes and report TTFT/tokens/s unavailable. An output cap of 40 is not a verified 40-token input prompt. Spoken-chat generation is not isolated text-LLM timing.
9. Preserve failures. Silero streaming at a01aed4 rejects a final file chunk shorter than exactly 512 samples; an offline fallback does not prove arbitrary-chunk streaming. Require explicit framing/padding and original-length accounting before qualifying that live path.
10. Build acceptance checks comparing every argv template with actual receipts, asserting corpus/model counts and hashes, independently recomputing WER/RTF, distinguishing alternate two-clip smoke runs from full-set results, and verifying fixed files against the starting SHA. Propose a new benchmark epoch without editing the referee when forbidden.

## Reporting

Publish machine-readable recipes/results plus concise recommendations. Name host quota/cache/noise limitations, synthetic quality limits, absent LLM support and failed turn labels. Host qualification does not prove Android packaging or phone real-time performance. Keep phone discovery, adb, mic/speaker and UI calls out when prohibited.
