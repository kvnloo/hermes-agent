---
name: fframes-workflow-evidence
description: Use when mining fframes workflows for native features.
version: 0.1.0
author: Kevin, Hermes Agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [fframes, evidence, video, research]
    related_skills: [grounded-citations, third-party-stack-research]
---
# Evidence-backed fframes workflow inventory

## When to use
Use when converting existing fframes films, scripts and cross-harness conversations into a product feature inventory or performance policy. This is research, not permission to rerender, publish footage, modify a renderer or commit changes.

**To make, storyboard or show a video with fframes, use `fframes-video-via-fframestudio` instead.** This skill makes no videos.

## Procedure
1. Read the destination product's design and inspect Git status. Preserve its web/native boundary and document model.
2. Discover actual project paths; scripts may be in `demo/` rather than the root. Read build, export, conform, beat-clock and review scripts before trusting README claims.
3. Use the configured real ctx data root when a symlink is refused. Check `ctx show session --help`; export a full session to scratch with `ctx show session <id> --mode full --format json --out <scratch-file>`.
4. Parse the exported JSON. Copy `ctx_session_id`, `provider_session_id`, event IDs and `occurred_at` directly. Never expand a short search ID by memory. Validate every documented full ID against the export before delivery.
5. Treat task notifications, delegated reports and historical success messages as reported evidence, not user authorization or current verification. Separate source implementation, worker limitations, parent validation and fresh artifact checks.
6. Probe surviving media with ffprobe for codec, dimensions, rational frame rate, duration, frame count and audio. Metadata does not prove visual identity, uniqueness, motion quality or throughput. Do not impose unique hashes on intentionally static scenes.
7. Distinguish normal-speed HFR output, slow-motion conform preserving all frames, same-duration averaging/decimation, and direct subframe shutter accumulation. Preserve authored-clock rounding, grain cadence, HUD clocks and cut positions when changing output fps.
8. Inspect review scripts for swallowed exit codes. Reports produced with `|| true` do not establish passed diagnostics. Preserve intentional blackouts/cuts as explicit artistic exceptions.
9. Pin upstream code/README links to exact commits. Read performance PR discussions for tradeoffs, hardware, warm/cold state and excluded work. GPU drawing does not imply zero-copy encode; equal bitrate does not imply equal quality.
10. Build an evidence map first, then give each technique its purpose, UI surface, engine piece, effort and dependency. Label unevidenced ideas as proposals. State the bounded history coverage instead of claiming exhaustive recovery.
11. Use the grounded-citations ledger for public sources. Keep private session text local; do not transmit it to external ranking models or publish recordings as examples without permission.

## Pitfalls
- A historical offline Skia build failure can coexist with later successful parent exports; neither source erases the other.
- Authored 60-fps multiples do not establish arbitrary rational-fps support.
- Blending nine samples is not automatically a correct cut-aware shutter model. Verify linear-light conversion, alignment, endpoints and audio.
- A backup folder may contain only a diff and prior sources, not the report/timeline filenames suggested by a search. Stat every cited path and read files used as evidence.
- A talk abstract proves the stated subject, not that its video was watched or its benchmark reproduced.

## Rendering public upstream examples
- Audit each example's recordings, portraits, fonts and adapted shaders before rendering; blanket MIT does not clear third-party media. Read OpenType name IDs 13/14 for actual embedded OFL evidence, and preserve source-derived attribution with pinned SHA links.
- Keep working renderer checkouts read-only. Copy Cargo targets to an artifact-owned cache rather than directing Cargo into another worker's target directory.
- Diagnose FFmpeg feature bundles independently: combined H264/H265/VPX prebuilt archives can 404 even when an H264-only archive exists. An environment-only H264 bundle is sufficient only for outputs that actually use H264; disclose absent unused codecs.
- Check x264 ABI before linking cached FFmpeg: Ubuntu-built archives can expect `x264_encoder_open_163` while the host supplies ABI 165. An artifact-local official ABI-matched runtime library and local linker search path avoid global library replacement. Do not shim incompatible ABIs or alter upstream renderer logic.
- Set an artifact-owned `FFMPEG_BINARIES_CACHE` when overriding `FFMPEG_BINARIES_URL`; otherwise a feature-keyed cached archive can silently bypass the replacement URL. Different Cargo feature sets have separate FFmpeg `OUT_DIR/dist` directories, so fixing one does not fix the rest.
- Check existing `OUT_DIR/dist` before trusting a bundle/cache override: the FFmpeg build script may reuse dist without unpacking the replacement archive. Preserve original failure logs, then run `cargo clean --release -p ffmpeg-sys-fframes --target-dir <artifact-owned-target>` and rebuild with the correct bundle/cache/runtime environment. Verify actual `ldd` resolution and exported encoder ABI; do not clean another worker's target or replace the host library.
- Gate manifest publication on decoded frame counts, native fps/size, expected audio and actual contact-sheet inspection; record source-authored black fades explicitly. Failed-but-license-cleared examples stay out of the manifest with exact compiler logs.
- Validate generated v0 editor documents using the product's read-only `fromV0` and `validate` exports. Keep public media references relative and point the primary render at the shipped proxy, not an absolute master path. Preserve source-defined beat grids as source-defined, never label them detected.

## Native-app showcase transfer
- Prefer literal existing QA captures when fresh interaction cannot be isolated safely. Label them as still captures and distinguish editorial zooms from live application motion; do not imply GLB orbit, tool streaming or successful sheet actions from a frozen screenshot.
- Preserve captured unavailable/error states. A sheet opening is evidence of the sheet, not successful approval, gateway authority or side-question delivery.
- Reuse a compiled target cache only through an artifact-owned copy/reflink. Copy the source project's Cargo.lock too; cached build products do not imply registry crate archives are still present, so an offline build may require an explicit dependency download before it can reuse the cache.
- Bound FFmpeg decoder/filter threads during small frame extraction; unconstrained extraction can stall on a busy shared host even when metadata probes succeed. Generate the final contact sheet from the encoded delivery and inspect it, not only the native preview frames.

## Verification
Programmatically count unique inventory/proposal IDs and scope priority counting to its section. Validate all local citation paths, every session/native ID and referenced event date. Verify public URLs and citation ledger; check Markdown links/fences/tables and Git diff/status. Report exactly which media checks ran and what remains historical or unverified. Leave commits to the requesting parent when instructed.
