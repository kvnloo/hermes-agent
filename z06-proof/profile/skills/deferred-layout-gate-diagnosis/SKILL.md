---
name: deferred-layout-gate-diagnosis
description: Use when browser gates race deferred layout callbacks.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [browser, debugging, regression, evidence]
    related_skills: [systematic-debugging, gev-ci-reliability-receipts]
---

# Deferred-layout gate diagnosis

## When to Use

Use for flaky browser assertions around ownership, accessibility markers, animation or deferred layout restoration.

## Procedure

Keep diagnosis separate from production or gate repair until causality is established.

1. Pin main, production-only and final integration heads; compare runtime blobs separately from colocated tests. Match manifests, browser/runtime, timezone, viewport and fresh server/profile settings.
2. Run the original full gate and extract its exact failing block without weakening console, HTTP or page-error checks. Store script hashes, per-run receipts and raw logs. Never infer nested test success from the runner exit code.
3. Observe classes, disclosure ARIA, exclusivity ARIA, geometry, animations, preferred-owner flags, reconsider flags and pending animation-frame IDs before/after scheduler and layout callbacks. Instrumentation is a separate cohort, not a natural frequency sample.
4. Check whether direct synchronous layout calls bypass scheduler preludes. Restoring auto-collapsed siblings may happen only inside a queued frame callback. A renderer may compute ARIA before changing collapsed classes and require a retry to reconcile them.
5. Compare wall-time waits with bounded frame/observable-contract completion. Stable rectangles alone do not prove marker or deferred-queue completion; do not recommend longer sleeps from a single pass.
6. Use a separately labeled scheduler fault as the negative control; restore by opening a fresh browser. Never represent scheduler suppression or synthetic DOM state as real user input.
7. Exercise native controls independently. Record unreachable controls as setup failures. If reaching the state requires theme or viewport intermediates, disclose that it is not an equivalent minimal path.
8. Keep inherited environment failures red. Passing the two target assertions is not a full gate pass.
9. Aggregate complete retained receipts in code; retain natural, instrumented, negative and modified-observation frequencies separately. Avoid repeat-count CLIs overwriting prior receipt slots.
10. End with exact mechanism versus unresolved attribution clearly separated, clean-tree/hash receipts, owned-process cleanup and a bindable-port check. Do not promote on timing evidence alone.
