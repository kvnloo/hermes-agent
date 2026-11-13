---
name: gev-deterministic-4k-capture
description: Use when capturing deterministic 4K GEV feature clips.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cesium, gev, capture, nvidia, video, evidence]
---
# Deterministic 4K God's Eye View capture

## When to Use
Use for source-grounded Cesium/GEV footage, deterministic offline camera clips, GPU shader finishing, and native-versus-upscaled quality comparisons.

## Contract
Use an owned headless Chromium, isolated worktree and loopback server. Preserve other servers, source worktrees and desktop focus. Load focus-safe-desktop-automation, threejs-real-gpu-receipts, api-key-secret-storage and the media skill first.

## Procedure
1. Pin the source SHA. Read current GEV source rather than assuming old globals. Recent upstream exposes `window.__godsEyeView` with viewer, styleManager, dataManager and tileset; this avoids permanent source changes.
2. Resolve optional Google credentials through bws without printing values. Scope them to a mode-0600 ignored worktree `.env.local`. A stored Google key may not authorize Maps 3D Tiles. On 401, use the genuine keyless imagery/terrain route and label photogrammetry unavailable. Shred the owned key file and restart the owned Vite server: a hot restart can retain injected environment values.
3. Launch installed Chromium headlessly with `--ignore-gpu-blocklist --enable-gpu --use-angle=vulkan --enable-features=Vulkan`. Prove NVIDIA in the initialized WebGL debug renderer string; flags alone prove nothing.
4. Verify canvas backing size is 3840x2160 with viewport 3840x2160, DPR1 and resolutionScale1. Avoid accidentally supersampling to 8K. Set useBrowserRecommendedResolution=false, MSAA up to the actual GL MAX_SAMPLES, FXAA off when preserving fine texture, globe SSE1 and a bounded tile cache. Tune a Google tileset only when one really exists.
5. Use explicit camera poses, smoothstep position/angles and logarithmic altitude. Pause the clock; explain that live feeds and built-in shader noise remain nondeterministic. For offline capture, disabling the default render loop and calling `viewer.resize(); viewer.render()` inside the tile-settle loop avoids wasting GPU work during PNG transfer and encoding; verify a real preview before adopting it. Warm endpoints and sampled path poses. Before every screenshot, require consecutive globe.tilesLoaded and tileset.tilesLoaded readiness after a minimum settle interval; retry boundedly and fail closed.
6. Preserve provider attribution by capturing the full page. Clean view is not the same as disabling the scope overlay. URL `sc=0` restoration can race initialization: set `setScopeMaskEnabled(false)` through the observed `/src/scopeMask.js` module at each deterministic camera step. This removes the global scope, not the authored NVG/FLIR shader optics. Disable duplicate built-in sharpening before applying a separate post pass.
7. Benchmark Playwright PNG against CDP `Page.captureScreenshot` with `format=png`, `captureBeyondViewport=false`, `optimizeForSpeed=true` on one frozen image. Compare decoded RGB hashes. Adopt the faster path only if pixels match; compressed-file hashes legitimately differ.
8. Use a real, compiled, warmed GPU shader object for postprocessing. An owned NVIDIA EGL/ModernGL pass is an honest ReShade-style alternative to an uninstalled Vulkan injector. Enable an isolated NVIDIA disk cache and retain source hashes and backend receipts. Binary cache files prove persistence, not a cross-run cache hit. Do not call a custom sharpen AMD CAS or claim vkBasalt injection without testing it.
9. Compare native 4K with an actual same-camera 1080p render. Real-ESRGAN ncnn-vulkan is a usable NVIDIA-backed offline alternative; x4plus can render 4x then downsample to the target 2x. Inspect native-pixel crops. Learned sharpening can smooth/reconstruct geography; do not promote it merely because it appears sharp. Report viewport LOD differences as a limitation of RMSE/PSNR comparisons.
10. Encode exact frame counts into ProRes HQ masters and 1080p H.264 proxies. If installed FFmpeg exposes `prores_ks_vulkan`, qualify it on the same real 4K input with `-init_hw_device vulkan=vk:0 -filter_hw_device vk -vf format=yuv422p10le,hwupload -c:v prores_ks_vulkan -profile:v 3`; compare full decoded output and error against CPU `prores_ks` before switching. This can remove CPU encoder backpressure without changing the delivery profile. A 10-bit ProRes container sourced from 8-bit screenshots is not HDR or newly recovered precision. Persist every completed clip and receipt incrementally; safely resume by explicit shot ID.
11. Separate scene preRender/postRender CPU submission, tile settling, screenshot wall time, post/readback, JS heap and whole-device VRAM. These are offline capture costs, not a real-time frame-rate benchmark. Shared-device VRAM is not exclusive process memory.
12. Verify every declared file with ffprobe dimensions/FPS/frame count/duration, a full ffmpeg decoder pass, SHA-256 and decoded early/middle/late contact sheets. Count manifest entries programmatically. Review real encoded pixels, not just pre-encode PNGs. Close owned browsers and server and verify the key file remains absent.

## Quackles transfer boundary
Apply source-grounded contracts: resolution is not authority, no partial publication, camera owns the budget, measure separate residency/refinement costs, and compare every representation with a known control. Distinguish Quackles RFC/north-star proposals from shipped behavior. Offline ready-frame gating does not prove improved GEV interactive streaming or phone/120Hz performance.
