---
name: platform-delivery-evidence
description: Use when testing platform-aware video delivery exports.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [ffmpeg, video, encoding, vmaf, qualification]
    related_skills: [browser-media-engine-qualification, test-driven-development]
---

# Platform delivery evidence

Qualify export recipes with real encodes and traceable frame scores. Treat a local transcode model as a hypothesis, never as a service replica.

## When to Use

Use for platform-aware export recipes, re-encode survival tests, temporal conform comparisons, or evidence audits of claimed social-video quality gains.

## Answering "can we deliver X fps / sharper?"

- Before telling the owner a platform limit blocks something, check the embed and self-hosted paths too (Player Cards, own site, direct file), because a native-upload cap is not a ceiling on what viewers can see. Lead with the path that works and its trade-offs (reach, bandwidth, client support), not with "no".
- Sharp-text recipes, high-fps masters, X Player Card embeds and refresh-adaptive serving: `references/high-fps-and-sharp-delivery.md`.

## Establish the experiment

- Separate official ingest requirements from observed playback behavior, because upload dimensions do not prove a viewer-resolution cap.
- Date every platform assumption and mark unsupported codec-allocation, HDR, bitrate, and loudness claims UNVERIFIED.
- Apply the same simulator settings to every treatment arm, because an invented higher-resolution codec bonus manufactures a win.
- Freeze the naive recipe independently of selected profiles, because promoting a filter must not silently add that filter to the control.
- Include a matched-encoder-quality scaling control, because CRF23 versus CQ14 confounds preprocessing with first-generation encoding loss.
- Preserve losses and counterexamples, because an aggregate VMAF improvement can coexist with worse banding or worse text on individual clips.

## Protect color and temporal meaning

- Probe the actual matrix and range of each source, because full-range JPEG commonly reports BT.601-family `bt470bg`, not BT.709.
- Convert the matrix and range rather than only setting tags, because mislabeled red JPEG pixels can acquire a visible green component.
- Reject unsupported HDR conversion explicitly, because assigning BT.709 tags is not tone mapping.
- Label 8-bit canonical references as 8-bit, because Main10 encoding cannot demonstrate preservation of precision absent from the source.
- Add a separately labeled native-10-bit ramp when testing banding, because codec and bit-depth changes otherwise remain untested or confounded.
- Align sparse interpolation samples to the exact instantaneous reference, because independent FPS filters can choose different sampling phases.
- Verify the first sparse frame with a decoded hash, because matching timestamps and frame counts alone do not prove matching picture phase.
- Score temporal outputs against both instant and box-exposure targets, because a blend's match to its own blur intent is not proof of perceptual superiority.
- Label full-period signal-domain averaging honestly, because it is neither a 180-degree shutter nor physically accurate linear-light exposure.
- Separate a temporal-derivative error proxy from perceptual flicker assessment, because still filmstrips cannot establish real-time viewing quality.

## Exercise the encoders

- Initialize an encoder with a real frame before claiming hardware support, because an FFmpeg encoder listing does not prove that the installed GPU supports it.
- Disable NVENC scene cuts with `-no-scenecut 1` when fixed cadence is required, because `-g` alone can still permit extra keyframes.
- Verify decoded keyframe indices, because rate-control flags are not proof of GOP behavior.
- Use zero target bitrate for SVT-AV1 CRF mode, because a nonzero target bitrate can make SVT reject the configuration.
- Measure actual output bitrate separately from nominal rate-control arguments, because short constrained-quality files can exceed the nominal average substantially.
- Remove a stale success receipt before overwriting an export, because a later encoder or upload-limit failure must not retain earlier success evidence.
- Map the same audio track during loudness analysis and export, because default-track selection can otherwise measure a different stream.

## Preserve auditable results

- Score every aligned frame and reject unequal geometry, frame rate, or frame count, because automatic padding can hide missing frames.
- Pool frame values before computing a platform p5, because the average of clip p5 values is not the pooled fifth percentile.
- Keep frame scores, exact command receipts, source hashes, and media hashes, because summary numbers alone cannot establish provenance.
- Version and hash-check prepared references, because changed color conversion or duration invalidates cached inputs.
- Put a recipe signature in output filenames, because rerunning a variant with different settings must not overwrite artifacts cited by older rows.
- Reject duplicate or incomplete comparison cohorts, because selecting a convenient subset silently biases the reported result.
- Replay shipped profiles through the public CLI and compare decoded hashes with measured uploads, because a report recipe can diverge from the actual defaults.
- Generate crops from identical frames and coordinates, because empty or mismatched crops do not demonstrate quality.
- Inspect the sheets and record modest or invisible differences plainly, because metric gains are not a substitute for visible evidence.

## Report speed without overclaiming

- Measure actual minute-long exports separately from short-clip extrapolations, because startup costs can dominate a three-second encode.
- Include startup, probing, audio policy, source preparation, and thread limits in the timing definition, because seconds-per-minute numbers are otherwise ambiguous.
- Report repeated-trial ranges and shared-host load caveats, because GPU contention can reverse an apparent hardware/software ranking.
- Compare quality before selecting the faster encoder, because CQ and CRF values are not interchangeable quality scales.
- Require authorized live upload/download calibration before service-specific marketing claims, because a configurable simulator cannot prove proprietary platform behavior.
