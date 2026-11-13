---
name: android-ui-replay-qualification
description: Use when comparing UI renderers on a real Android phone.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [android, rendering, replay, evidence]
    related_skills: [phone-harness-android-fast-tree, third-party-stack-research]
---
# Real Android renderer replay

## When to Use
Use for renderer comparison demos, split-screen streamed UI replays, and real-device installation/capture qualification.

## Procedure

For actual T3 React Native builds, private transcript snapshots, missing inline artifacts and native capture pitfalls, follow [T3 native replay](references/t3-native-replay.md). When the owner may be on the phone or on DeX, run the test app on the focus-safe display from `android-agent-virtual-display` instead of asking for an idle window: it never moves his keyboard focus. In particular, check foreground ownership before every input and reject clipped/occluded accessibility targets; a successful tap or a title in the sidebar does not establish the intended screen.

### Prepare the capture window first

- Obtain a scoped phone-idle window, verify the device is unlocked, and arrange an owner-approved temporary keep-awake lease before a multi-step recording; otherwise screen timeout can invalidate the capture while the app itself remains healthy. Release the lease when the window ends rather than changing persistent screen-timeout settings.
- Treat an unavailable foreground package as an unresolved observation, not proof that the owner switched apps. Pause input and check the lock gate and actual pixels; a locked phone needs the owner's unlock, never an entered PIN or a lock-screen bypass.
- Keep capture inputs and dwell times bounded inside the authorized window. Recheck readiness after long build or verification work instead of carrying an earlier unlocked-state assumption into recording.

### Report the actual stopping point

When user-requested work pauses at a device gate, return a concise status naming what is built, installed and visually verified, what acceptance is still missing, and the exact owner action needed. Do not leave an empty response after tool work or present a partial recording as completion. Correlate background build notices with their exact run IDs so a superseded failure does not replace a newer verified success.

- Separate live model generation, controlled stream replay, parser/renderer synchronous work, and observed frame readiness. A paced fixture cannot substantiate model-generation speedup. Name the actual baseline; plain HTML is not the product's production renderer.
- Use identical semantic content and arrival schedules only for a rendering-overhead experiment; compare text/data fidelity before considering timings. To examine token-efficient generation, measure actual format token counts and replay recorded provider timestamps, or explicitly label assumed token throughput as modeled. Do not impose equal per-row delays and then interpret a tied finish as a generation-speed result. Shared-thread, fixed-order lanes are a visual demonstrator, not isolated randomized microbenchmarks. Preserve raw per-run samples and aggregate in code.
- Pin stock runtime packages and disable unnecessary install lifecycle scripts. Isolate renderer spikes outside the product checkout and install them under a distinct package identity. For product dogfood, use an isolated worktree of the actual client and its message/artifact path; do not substitute another WebView shell merely because the spike was easier to package. Keep the owner's daily app and data intact in either case.
- Check configured remote build routes and toolchain availability separately. A scheduler hold does not prove a host is unreachable or has a JDK. Include the existing GitHub Actions lane in discovery before reporting a blocked build; inspect its workflow and use the approved source/signing path. Never upload private conversation traces or signing keys as public workflow inputs. Use a documented local Android fallback only when its actual prerequisite is established; never bypass paid-account or quota policy holds.
- Before implementing product integration, inspect live T3 threads and the Git worktree registry for an existing candidate. Reuse or extend verified work without overwriting another thread's dirty files. Distinguish branch source, passing focused tests, a built APK, installation, and real-device acceptance; none substitutes for the next.
- When the owner explicitly requests both actual-app recordings, treat a shortlist or implementation brief as intermediate progress, not the deliverable. Continue through integration, build, install and capture within the authorized scope. Report a genuine permission or unavailable-capability blocker only after checking supported alternatives.
- For tiny SDK-only Android wrappers, avoid Java lambdas when javac uses android.jar as its boot classpath: the platform stubs can omit LambdaMetafactory.metafactory. Use an anonymous listener or a supported desugaring toolchain.
- Apply native WindowInsets around the WebView when targeting Android 35+, then inspect an actual device screenshot; a passing build does not prove the header clears status bars.
- Handle onNewIntent by storing the incoming intent and reloading the owned test view. Correlate completion with an exact per-run ID available through the native bridge; never accept an old receipt after relaunch.
- Capture only the authorized test app. Verify foreground ownership before recording. Inspect both progressive frames and the last encoded frame: screenrecord can omit static completion updates. A short bounded visible clock after completion can guarantee a later draw without adding a perpetual animation.
- Pull the installed APK from the exact package-manager path and compare its digest with the built artifact. Preserve signer continuity; never uninstall or clear data on a signature mismatch.
- Retain the APK, source, exact-run receipts, screenshot, recording and interpretation together in the canonical experiment directory. Label WebView proof separately from native React Native proof. Avoid modifying the product repo merely to run a renderer spike.
