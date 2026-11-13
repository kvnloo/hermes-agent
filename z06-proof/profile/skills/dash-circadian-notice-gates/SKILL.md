---
name: dash-circadian-notice-gates
description: Use when changing Dash circadian notice routing gates.
---

# Dash circadian notice gates

- Read `shared/interaction-policy.ts`, `shared/human-posture.ts`, and `bridge/src/posture-http.ts` before editing adapters. Reuse `readPosture`, `route`, and `publicView`; do not clone policy logic.
- Gate bridge enforcement on a fresh circadiand source and the same snapshot's explicit `enforcement.enforcingNow === true`. Clock fallback is shadow-only. A producer-specified future `not_before` still holds.
- Serialize async ingress decisions before updating local budget counters; test concurrent submissions against the interrupt cap.
- Test queue mode, atomic persistence, restart, oldest-drop accounting, release timezone/day/08:00 boundary, not-before, and retry after publish-before-clear failure. Keep a stable in-flight digest batch or durable per-item delivery receipts across publish/clear retries: hashing the current ready items is not sufficient if new notices arrive between attempts. Commit per-item receipts atomically with digest history before broadcasting, retain them while their queue entries remain, and test after replay-history eviction so bounded history cannot erase deduplication evidence. Fault-inject the actual queue-clear failure, append a notice (and separately cross a not-before boundary), then retry; assert that already-published titles are not emitted again.
- Keep native scheduling at one call site after `route`. Preserve inbox writes independently of OS delivery and classify approvals as decisions.
- Scope posture caches to paired credentials, validate the public view at the network boundary, expire after five minutes, and fall back to clock-only on errors.
- Migrate immutable Android channels with a new LOW channel ID instead of changing an old DEFAULT channel. Test channel config and the PEAK-only focus sound invariant.
- Use lazy `require` with an explicit module type for optional Expo native modules. This repo's lint rejects dynamic `import()` in native Metro paths.
- Existing policy golden and Bend-table tests live in `shared/human-posture.test.ts`, not `shared/interaction-policy.test.ts`. Register the actual test file in mutation targets or mutation scores silently lose coverage.
- Isolate native-module mock suites in a fresh Bun process when earlier suites can mock only part of react-native. Bun 1.4.3 can link named imports against the first mock's export shape even after a later mock adds PermissionsAndroid; reproduce with a preceding AppState-only mock, not only the native suite alone.
- Run targeted tests serially. `scripts/mutate.ts --file` accepts registered targets only. Report selected-sample scores and survivors, not exhaustive mutation coverage. After adding a target, update the target-list test and preserve its minimum parser-branch assertions.
- On code-only assignments, do not run Metro, deploy, touch the installed bridge, or use phones. State the device/runtime evidence gap explicitly.
