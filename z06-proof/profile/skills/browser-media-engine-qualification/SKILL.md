---
name: browser-media-engine-qualification
description: Use when qualifying browser video preview/export engines.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [webcodecs, media, performance, qualification]
    related_skills: [spike, focus-safe-desktop-automation]
---

# Browser media engine qualification

## When to Use

Use for measured selection of browser media engines, frame-accurate seeking, timeline export, temporal accumulation, or native/browser performance comparisons.

## Procedure

1. Isolate a standalone spike and pin packages. Run installed Chromium headlessly in an owned profile; record CDP GPU/codec capabilities and exact flags. A hardware canvas renderer does not imply hardware video encoding.
2. Probe exact encoder and decoder configurations independently, including audio. Propagate the selected codec-capable browser channel/executable into every nested media harness; a child that launches a different Chromium build can fail media gates while the parent passes. Verify exported streams: an engine may silently replace unsupported AAC with Opus while still producing an MP4.
3. Freeze a random seek tape. Decode reference frames independently with FFmpeg and compare full-frame pixels, not just returned timestamps. A correct timestamp can label the wrong decoded pixels. Avoid sparse pixel sampling for nearest-frame identification in repetitive imagery; it can pick distant false matches.
4. Require seek promises to mean decoded and painted. Inspect asynchronous completion when screenshots show old frames. An arbitrary settling sleep is a diagnostic, not a production fix. For tap-to-play players using `preload="none"`, assert initial paused/muted/no-autoplay state before activation, then assert metadata and decoded playback after explicit Play; requiring metadata before the tap contradicts an allowed browser loading policy.
5. Measure distinct source-frame timestamps actually drawn to the output canvas. Propagate timestamps through intermediate cache canvases with WeakMaps; distinguish draw calls, repeated frames, missing frame budget and physical-display presentation. Start instrumentation after warm-up and stop before teardown.
6. Use real multi-clip media for composition gates and a labeled generated high-rate fixture for resolution/temporal stress. Do not infer 60 fps source coverage from 30 fps proxies. Preserve hashes and never publish private fixture pixels implicitly.
7. Verify exact frame counts, rational rates and durations after every export. Rounded microsecond time steps can add an extra terminal frame. Use the decoded frame count, not the requested count, when reporting throughput.
8. Add known audio impulses and black-backed visual flashes away from watermarks. Compare decoded audio against the source by correlation at beginning/middle/end; equal stream durations alone do not prove sync. Calculate frame offsets in integer frame coordinates to avoid floating-point boundary failures.
9. Run a real bounded scrub interval and record owned browser-process RSS plus heap. Distinguish submitted seeks from completed frames and attach errors. RSS includes shared mappings; a falling five-minute trace is not a lifetime leak proof.
10. Compare temporal accumulation before delivery encoding with a high-FPS intermediate plus FFmpeg tmix. Mix contiguous groups before decimation, document shutter phase and gamma/linear-light behavior, and verify output count. Repeated source frames are not invented optical-flow frames.
11. Benchmark native paths with the supplied project's actual export script. Preserve required input timestamp normalization. Separate process wall time from internal render timing, master render from final encoding, and different scenes from comparable workloads. Test an available hardware encoder rather than assuming its presence implies a speed win.
12. Retain numerical receipts, source/output hashes, capability probes and independent validation. Label shared-host contention and unfinished gates. A no-go backed by failed measurements is a completed qualification, not permission to fabricate a passing replacement.

## Audible preview seek-feedback diagnosis

- Compare the same preloaded source range with alternating muted/unmuted trials. Record `seeking`, `waiting`, and `requestVideoFrameCallback` separately; different scenes or source ranges confound the comparison. Test correction-write suppression as a single-variable diagnostic before blaming decode cost or networking.
- Let forward media-backed previews follow media time during startup/buffering rather than seeking repeatedly to an independent rAF clock. Retain explicit scrub/source-remapping seeks and a wall-clock fallback for reverse/still-only previews. Include playback-rate changes in preview invalidation so a stationary media clock cannot prevent Play/Pause from reaching the element.
- Simulate a frozen media-time getter for deterministic browser buffering regressions. Explicitly pausing the video is not equivalent to buffering: a legitimate playback updater may resume the paused element, invalidating that test premise. Keep real-media before/after measurements alongside the synthetic regression.

## Saved-document export boundary

1. Normalize saved documents through the canonical migration and validator before planning media work; an unchanged legacy project can still be old-schema on disk even when the editor shows a migrated document. Test immediate export without first editing or saving.
2. Reject nonfinite/nonpositive rates before constructing time-stretch filters; iterative factor decomposition can loop forever on zero, negative or infinite input and block the bridge synchronously. Exercise malformed saved documents at the renderer boundary, not only through browser controls.
3. Enumerate attached audio as well as primary clip media before admitting export. Mix supported layers with their documented offsets/durations, or fail explicitly before rendering; a valid silent MP4 is not a successful export of a soundtrack-bearing project. Keep embedded-audio and separate-soundtrack tests distinct.
4. Bound probing and encoding separately, restrict media protocols/demuxers, validate project/output containment, and remove only owned partial output on timeout. Explicitly trusted absolute local media is a separate contract from relative-path containment; do not describe either as a complete sandbox against concurrent local writers.
5. Probe actual short exports for decoded frame count and non-silent audio, and verify that refused inputs produce no output or subprocess work. Preserve the saved document's bytes when normalization is in-memory only.

## Adapter recommendations

Keep rational-time document snapshots, asset leases, capabilities, decoded-and-painted seeks, cancellation, bounded queues and verified export receipts outside vendor object graphs. Give active decode to one engine; use separate media-I/O jobs for probing/thumbnails/proxies. Put final codec selection and verification under a bridge/job boundary without claiming native rendering is inherently faster.
