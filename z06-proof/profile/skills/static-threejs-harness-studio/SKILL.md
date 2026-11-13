---
name: static-threejs-harness-studio
description: Use when building static Three.js image-harness studios.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [threejs, blender, comfyui, static-export, verification]
    related_skills: [test-driven-development, threejs-real-gpu-receipts]
---
# Static Three.js harness studio

## When to Use
Use for a static browser editor combining locked Blender-derived geometry, user textures and direct local image-harness connections.

## Preserve source and isolate work
- Create only the authorized worktree/branch. Read installed framework docs before adding a client-only static-export route.
- Export a web derivative from a locked Blender file without saving the blend. Hash the source before/after; bound textures and GLB size; ship a local decoder and its license.
- Label standard PBR conversions as approximations when procedural shading, light linking or optical shaders are not baked.

## Camera and texture correctness
- Pass an explicit Three.js PerspectiveCamera instance to R3F when preserving a Blender quaternion. R3F's default camera construction can call lookAt(0,0,0) when rotation is absent even if quaternion was provided.
- Preserve named UV maps explicitly in export shaders. A material can use Creation or RegisteredPosterUV while UVMap is the active layer; replacing its shader with an unbound image texture silently produces stripes or wrong projection.
- Preserve the original texture channel when applying replacement textures. Clone mutable materials and replacement maps; dispose owned resources without mutating the shared GLTF loader cache.
- Inspect actual exported hero PNGs. Passing WebGL initialization and nonblank-pixel tests does not prove camera framing or artwork registration.

## Harness behavior and proof
- Probe targeted ComfyUI node schemas first, not the full object_info inventory. Large installations can return multiple megabytes and time out during software-rendered browser tests. Fall back to the inventory only when the preferred node is absent.
- Upload references, submit a job once, poll bounded history, handle execution errors and read back the output. Never automatically retry generation or silently switch providers after submission: subscriptions can be charged twice.
- Bind connection results to a settings revision so a late detection response cannot reconnect a URL the user changed.
- Require explicit transfer consent; do not scan localhost automatically. Explain CORS, Local Network Access, mixed content and the distinction between stopping a client wait and cancelling a server job.
- Keep one durable attempt guard before an authorized paid generation. Record prompt, reference hash, adapter hash, prompt ID, output hash/path and seconds. Preserve exact executed-source lineage if later edits only optimize detection; do not relabel old receipts as exact-head proof.
- Use mocked HTTP or a clearly labeled recorded-result replay for repeatable UI tests without spending another generation. Keep the real generation receipt separate from the emulated/replayed browser evidence.
- Own the ephemeral static server and headless browser and clean both up. Label SwiftShader as EMULATION. Exercise every material slot with pixel changes, JSON/localStorage round trips, exports, stale-connection races and the complete restyle UI cycle.
