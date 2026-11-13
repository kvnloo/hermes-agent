---
name: quackles-plate-editor-evidence
description: Use when editing the rendered Quackles home plate.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [quackles, blender, image-editing, verification]
    related_skills: [blender-locked-scene-continuation, design-taste-frontend, test-driven-development]
---
# Rendered home editor

## When to Use
Use for masked customization of the existing Quackles home and its evidence pipeline.

- Preserve the authored Blender plate and existing inspection camera. Mount editing as an opt-in layer on Landing; do not replace the page with a WebGL approximation.
- Read poster chrome and globals before styling. Reuse live paper/ink tokens, mono typography, square controls and restrained motion; put a narrow panel in the desktop gutter and a scrollable sheet on mobile.
- Derive selectable IDs from a locked-scene CPU Object Index render, never hand-authored rectangles. Open with sanitized HOME/PATH, background/factory startup, and exit without saving; hash donors before and after.
- In Blender 5.2 set image media_type to MULTI_LAYER_IMAGE before choosing OPEN_EXR_MULTILAYER. OpenImageIO may expose the index subimage as `Object Index.X`, not `IndexOB`; inspect every subimage and accept either spelling.
- Export an indexed PNG whose palette maps ID N to RGB(N,N,N), plus source hashes, camera parameters, visible pixel counts and actual mask-derived bounds. Keep zero-visibility groups in metadata, omit them from selection.
- Match mask dimensions to the shipped base plate. Record the exact plate URL and hash; an identical camera does not make changed geometry pixel-identical across scene generations. Document that boundary instead of silently repainting or replacing the beauty.
- Invert inspectionCrop for bbox framing: normalized focus is crop travel fraction, not image centre. Disable hover-follow and competing theme drags while the editor owns selection, and restore normal camera behavior on close/Escape.
- Expand generation crops to a supported output aspect ratio, rather than stretching returned geometry. Send source crop and real mask; add texture guidance explicitly.
- Use an inward-only feather, with zero coverage outside the selected ID including internal holes. Verify the saved generated PNG's alpha against the rendered ID mask, not just the composite helper's unit test.
- Commit theme JSON and patch blobs atomically in IndexedDB. Make a new blob durable before publishing its theme reference to the painting effect; otherwise the paint can race the write. Serialize rapid slider saves and read back committed records.
- Invalidate connection state whenever the endpoint changes, and generation-gate asynchronous detection responses. A successful old endpoint probe must not authorize transfer after the URL changes.
- Retain a generation attempt guard; never automatically retry or switch providers after submission. Capture the actual UI request, Comfy history, uploaded source/mask, raw result and saved masked patch. Cancellation stops client waiting, not an already queued job.
- Run a separately built pinned baseline and candidate in owned loopback servers with isolated headless Chromium. Label screenshots EMULATION. Compare normal-home pixels excluding only the authorized Edit control; keep real detail asset routing distinct from mocked image responses.
- Save the real live run separately from subsequent no-spend regression runs. Bind final source SHA and relevant source hashes to both receipts; a later connection-only fix does not justify pretending the earlier live run used the final bytes.
