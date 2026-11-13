---
name: garden-room-replay-watch
description: "Use when watching Garden Room use or replay complaints."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [garden-room, replay, rrweb, debugging, privacy]
    related_skills: [garden-room-voice-realtime, rendered-ui-qualification, threejs-real-gpu-receipts]
---
# Garden Room private replay

## When to Use
Use to inspect Garden Room owner sessions, debug complaint-time replays, or maintain the private recorder/viewer and Hermes evidence bridge.

## Procedure

- Read project `docs/REPLAY.md` and `docs/HERMES_LINK.md` before using or changing the replay lane. Keep capture in replay.js/replay.css, replay route/helpers, viewer, tests and docs; preserve parallel app/server/voice edits.
- Use `tools/replay_tail.py --seconds 30` and `tools/replay_snapshot.py --output data/replay/current.png` to inspect actual recorded owner use, then open the PNG with vision. Pass `--at` and optionally `--session` to inspect a complaint. Never substitute a screenshot of a freshly launched app for owner-session evidence.
- Check lifecycle recording state and batch timestamps before requesting historical frames. A paused recorder can leave a valid pre-complaint session but no scan/review frames. Compare the returned `frame_ts` with the requested time: the snapshot CLI can exit zero yet return the same stale last-known frame for every later request. Timeout or stale pixels are missing interval evidence, not permission to relabel a reconstructed screen as the owner's recording. Use voice timestamps and saved scan artifacts with that boundary stated.
- For a real-phone verification, perform navigation, condition waits, captures and restoration in one scripted ADB run, not an LLM round-trip per tap. Downscale captures to a maximum 720 px before vision. Recent Samsung dumpsys uses `topResumedActivity=` as well as `mResumedActivity:`. Direct page WebSocket CDP can work when Playwright `connectOverCDP` hangs on Android Browser/Target domains; use an ADB-forwarded Chrome socket, touch only the exact app tab, intercept owner state writes during previews, restore app state and leave Home. Give screencap subprocesses an explicit buffer above 1 MB.
- Read the complaint's `replay_context.sidecar` first. Pending/unavailable snapshots are explicit states; paths in a delivered message are not proof that files exist. Legacy inbox IDs are deterministic content hashes shared by watcher and worker.
- Keep rrweb locally pinned/licensed. Avoid WebGL command recording on the phone: use bounded asynchronous JPEG samples plus DOM events, and preserve app-key redaction on both sides. Do not capture network headers/bodies, browser storage, camera or audio.
- Use regular fetch for continuous batches, consume response bodies, and reserve keepalive for a small final unload attempt. Repeated keepalive image batches can exhaust Chromium's small outstanding-body quota and silently freeze live viewing; assert sustained frame-age samples and online status, not just initial attachment.
- Overlay the actual stored JPEG in replay DOM. Freeze replay CSS entrance animations at final state; otherwise a paused animation can make an existing sheet transparent. Compare live and replay PNGs through vision, including numeric fields and the bottom dock.
- Run `node tests/replay_storage.mjs`, `REPLAY_GPU=1 node tests/replay.mjs`, `python3 tests/hermes_link.py`, and `node tests/phone.mjs`. Use a separate viewer browser process so viewing does not hide the simulated phone. Uniquely identify injected test complaints because voice transport deduplicates identical text for a short window.
- Prove CDP/WebGL hardware renderer identity before reporting overhead. Headless ANGLE GL on this host supports NVIDIA hardware; SwiftShader under concurrent jobs is correctness-only evidence. Report OFF/ON frame distributions and synchronous-copy versus asynchronous encode latency separately; desktop hardware is not an S25 Ultra benchmark.
- Preserve owner state in tests by intercepting room/layout, Zen progress, drive and relevant voice action endpoints. Use `[test]` connectivity complaints, check automatic PNG/timeline/errors artifacts and actual worker receipts, and do not ask the worker to repair synthetic test errors.
- Commit only owned source/vendor/license files; replay/voice recordings, screenshots and keys remain private/gitignored. Rerun the full phone gate after concurrent integration and report a failing unrelated gate rather than modifying someone else's files to hide it.
