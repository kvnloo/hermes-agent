---
name: tern-secondary-native-ui
description: Use when adding a secondary Tern native UI to a web app.
version: 1.0.0
---

# Secondary Tern native UI qualification

Keep the web product independent. Put optional Luau launchers, Node TSP code, dependencies and tests in their own directory. Use a worktree and explicit branch; never change the user's settings.json.

- Fetch current SDK documentation from https://docs.stencil.so/tern/ and the source at https://github.com/stencil-hq/tern-sdk. The old docs-site tarball may return 404.
- Register palette commands in window.luau; launch an owned tab. Put PID/health checks, bridge startup, files and ACP in the process rather than the 50 ms Luau callback.
- Use the official @stencil-hq/tern SDK for handshake, flow control, blobs and cleanup. Basic editor keys remain program-owned even with `features: ['edit', 'send']`; implement ordinary key editing plus native edit/send events.
- Use `html.div({class: ...})` for custom CSS containers. `class` on semantic col nodes may not reach the real renderer.
- Never await an ACP prompt within a TSP event callback. Start an independently caught task so permission clicks can be processed while the turn is pending. Show explicit allow/deny choices and cancel pending permissions on close.
- Read the current bridge credential at runtime. Send credential-bearing Tern control commands via a private 0600 scenario file, suppress CLI output, then remove the file in finally. Node child stdio pipes are sockets on Linux; `ctl --file /dev/stdin` may fail even when the same Python pipe works.
- `TERN_PANE` identifies the program's pane on the tested build. Do not assume TERN_PANE_ID or TERN_WINDOW_KEY exists. CLI new/split can create a pane without revealing it; verify actual tab state before clicking.
- Use an ordinary signed-in Tern window on isolated Xvfb with its own config and daemon socket, not a replay or headless serve as native evidence. Let the keyring complete normally; never bypass the account gate.
- If isolated WPE crashes in egl-wayland dmabuf device setup, qualify process-local Mesa/software flags: LIBGL_ALWAYS_SOFTWARE=1, __EGL_VENDOR_LIBRARY_FILENAMES=/usr/share/glvnd/egl_vendor.d/50_mesa.json and WEBKIT_DISABLE_DMABUF_RENDERER=1. Do not install those into the user's config.
- `ctl shot` verifies native surfaces but may show a placeholder for the platform webview. Capture the actual isolated X display with PIL.ImageGrab for web pixels; inspect both. Verify video readiness/playback through the browser DOM too.
- Wait for the expected semantic state after native input; an immediate tree can race the TSP callback. Poll narrowly. A daemon plugin-list `ready` does not prove the window entry survived its 50 ms budget: invoke the command and inspect the real surface.
- Never print raw browser inventories: /open URLs can retain credentials until navigation finishes. Redact by URL pattern, not by comparing against the latest discovery token, which another process may have replaced. Capture screenshots only after redirect.
- Isolate test discovery files. Concurrent bridge tests may overwrite a global bridge.json with a dead fixture PID even while the actual bridge keeps serving. Preserve live unrelated processes and use an explicit alternate discovery file for owned qualification.
- Report missing render-scheduler APIs as unavailable, not as an empty live queue. Label imported-output inventories accurately.
- Keep screenshot paths, actual loaded version, view counts, real ACP completion and browser playback receipts in an evidence note; never include credentials.
