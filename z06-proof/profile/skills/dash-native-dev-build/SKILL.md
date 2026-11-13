---
name: dash-native-dev-build
description: Use when building Dash's native Android dev APK.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dash, android, expo, fleet, development-build]
    related_skills: [dash-turbo-live-preview, dash-phone-service-switch]
---

# dash-native-dev-build

Use when building, integrating, installing or qualifying Dash native Android development APKs, native notifications or share receivers, or their compatible turbo Metro runtime.

## Rules

1. Read the owned worktree's AGENTS.md and docs/native-android.md. Keep native features optional in Expo Go and web. Work in an unserved tree based on current turbo, preserving z0live, QA, voice, annotation and queue/context behavior; compare actual native manifests and dependencies before composition.
2. Route installs, tests, typechecks, lock generation, Expo prebuild/export and Gradle through `/home/kvn/.local/bin/fleet-build --node mbp`. Use two CPUs for the first native build. Honor exit 75, queue Hold, thermal cordons and DiskPressure; wait for normal admission instead of falling back to groot or stopping another worker.
3. On O15 branches, follow AGENTS.md, TESTING.md and `.claude/skills/verify-dash/SKILL.md`. Obtain a complete green CI tester-army receipt for the exact SHA before `scripts/build-native-android.sh`. Preserve matching base-plus-spec and implementation failures as an O15 blocker; older unit/mutation recipes cannot replace that branch contract.
4. Build through `fleet-build --node mbp --android --cpus 2 --wait 1800 --timeout 3600 --fetch .native-receipts --out <receipts> -- bash scripts/fleet-native-android.sh`. Diagnose a missing existing native module as a build-path problem before editing it. Compose every required native module into one APK and inspect actual module inclusion, permissions and signer metadata.
5. Use SDK-compatible expo-dev-client and `bun x expo install <packages>` from app/ on the worker. Transfer pinned private dependencies as a Git bundle with a job-scoped URL rewrite, keeping credentials off the worker. Create an ephemeral Git inventory only inside the transferred snapshot when inventory tests need it.
6. Read SDK 57 module publication metadata rather than assuming Gradle subprojects. Use an owned writable SDK overlay with individually linked version directories and verify generated NDK, CMake, platform and build-tools requirements. Check Skia's arm64 libskia.a before CMake; run its inspected install-libs.js on MBP if missing. Keep incremental source in an owned locked cache.
7. Fetch the APK and inspect its signature and merged manifest, including SEND/SEND_MULTIPLE, package, POST_NOTIFICATIONS, singleTask, debuggability and dev-client schemes. Invoke an existing BusyBox-hosted signer as `bash "$signer" verify ...` when needed. Parse actual signer labels and compare certificate digests with the pulled installed base; preserve the app and data on mismatch.
8. Prepare a private local app/node_modules overlay, linking compatible unchanged packages and copying missing packages recursively with `rsync -ar`. Verify actual JS entry files and package manifests. Keep served dependency trees and other workers' caches unchanged. Exercise external symlink resolution through a real MBP Metro export before handing off a clean runtime-ready path.
9. Bind exact source archives and native inputs to receipts. Validate and hash baseline archives before submission and verify the hash remotely. Reuse an APK for JS-only revisions only after an explicit empty native-input diff; bind both APK input SHA and final JS SHA and rerun composed JS/runtime gates. Label any reused unchanged-JS receipts accurately.
10. Observe an existing fleet job after a tool timeout using its JSON job ID and `fleet-build --attach JOB`. Classify exit 137 from pod reason/events, preserving evictions and missing artifacts as infrastructure or unknown acceptance. Avoid concurrent terminal attachment with the persistent launcher. Resolve fetch paths relative to the retained stage and recover the same job instead of resubmitting for retrieval failures.
11. Keep each gate timeout below the fleet deadline and confirm runner scripts survive staging excludes. Report full-suite inherited failures separately from targeted passes. Reuse exact-revision exports for missing renderer proof with a checked hash manifest; label read-only host snapshot replay separately from live bridge, real-model and native proof. Record unavailable Jev as a limitation.
12. Respect separate rollout, service and phone-UI clearance. Under the app's device-install lock, reread `pm path app.dash.mobile`, metadata and installed base.apk SHA-256. Skip reinstall when it already matches; otherwise compare signers, use `adb -s <device> install -r <apk>`, and read back the installed hash. Preserve data and unrelated foreground apps.
13. Start compatible Metro from the integrated app/ with its private environment, `CI=false`, `EXPO_PUBLIC_DASH_TURBO=1`, `REACT_NATIVE_PACKAGER_HOSTNAME=<groot-tailnet-IP>` and `bun x expo start --dev-client --host lan --port 8098`, using an owned free port when needed. Require `/status` and the Android dev-client manifest before launching the merged-manifest scheme `exp+dash://expo-development-client/?url=<encoded-http-Metro-URL>` in app.dash.mobile.
14. Observe loaded JS and expected screen content through a bounded loop after launch; correlate bundle/runtime logs and foreground package before interpreting early black frames. Retry stored enrollment credentials after pair.claim, keep native SecureStore imports static, and inspect token metadata only. Verify bridge introspection, real model/mic flow and Fast Refresh separately; receiver queries establish registration only, and killed-app push needs a configured FCM path.
15. Animate a real native View around the SVG eye layer on Fabric, preserving transform origin, reduced-motion, geometry and animated-gaze proofs. Inspect Reanimated warnings and populated native frame behavior. Qualify production performance with embedded minified JS/Hermes and __DEV__ false while retaining the dev-preview lane. Report source gates, APK availability, installation and usability as separate milestones with exact job and blocker.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
