---
name: webgpu-canvas-recovery
description: Use when a WebGPU canvas blanks after focus loss.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [webgpu, three, wayland, canvas]
    related_skills: []
---

# WebGPU canvas recovery

## When to Use

Use when a Three.js WebGPU page loses the canvas and CSS2D labels after a window, workspace, or focus change, and plain HTML text is still there. Also use when a previous resize-only recovery is already on the served branch and the blank still happens.

## Procedure

1. Confirm a resize-only path is not the fix. `setPixelRatio` plus `onResize` does not drop the cached context, and assigning `canvas.width` via `setSize` destroys the Wayland surface.
2. Arm recovery only after the document was focused and then hidden or blurred. The first focus after load must not call `unconfigure` or `setSize`. A refresh that paints and then goes black is the recovery killing a live swapchain.
3. On that return, once: `unconfigure()`, then `renderer.backend.updateSize()` so Three drops its cache, reattach a disconnected CSS2D element, then `animate`. Do not call `setSize`, `setPixelRatio`, `onResize`, or `configure()` yourself. `getContext('webgpu')` returns the same context; Three's next render configures it with `format`. `configure({ device })` without `format` throws and leaves the canvas black.
4. Clear the away flag when that burst starts. A poll that stays armed calls `unconfigure` every few hundred milliseconds, and the canvas stays black. One burst per leave, including a short retry, then stop.
5. If the CSS2D `domElement` is no longer in the document, append it again. Those labels live on the canvas layer; HTML text that stays is not evidence the renderer recovered.
6. If `renderer.backend.device` is missing, the device is lost. A resize cannot paint. Reload once. Do not loop the reload.
7. Skip the restore while `document.visibilityState` is `hidden` or the document does not have focus. Restoring an unfocused surface recreates the blank.
8. A log line that says painted means `animate` was called, not that pixels appeared. Read the recovery log before adding another restore. A burst of restores after one switch means the away flag never cleared.

## Pitfalls

- Give each renderer tier attempt (WebGPU, then WebGL2) a fresh canvas. `getContext('webgpu')` claims the canvas even when `requestAdapter()` then returns null, so a WebGL2 fallback on the same canvas gets `null` and the page silently stays on its CSS/static tier. This is common on Linux browsers that expose `navigator.gpu` without an adapter. Regression-test it in Playwright with `page.add_init_script("navigator.gpu && (navigator.gpu.requestAdapter = async () => null)")` and assert that auto mode reaches WebGL2.
- Do not nudge the drawing buffer. Assigning `canvas.width` drops the Wayland surface even when the logical size is unchanged.
- Do not schedule the restore only from `ResizeObserver`. Focus return without a size change is the common case.
- Verify the served file, not the branch tip. A live server can be running an older overlay than the commit you just found.
- A browser that cannot create a WebGPU device stops on an unsupported page. Script and marker presence there does not prove the canvas recovered. Say which layer you observed. To see pixels, use a separate headless Chrome that can create the device (`references/headless-webgpu-capture.md`: flags, canvas readback, full-page composite); never focus the user's window to check.
