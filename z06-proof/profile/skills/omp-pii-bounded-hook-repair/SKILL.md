---
name: omp-pii-bounded-hook-repair
description: "Use when repairing OMP PII hook timeout regressions."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [omp, privacy, cancellation, testing]
    related_skills: [upstream-contribution, test-driven-development]
---

# OMP PII hook qualification

## When to Use

Use for local repair and qualification of OMP PII structured-leaf, timeout, shared-helper and persisted-details review findings.

## Procedure

- Read the exact `ExtensionContext`, `createHandlerContext`, handler timeout race and `ExtensionAPI.exec` implementation before wiring cancellation. Some OMP revisions keep the runner signal internal and expose it only to UI operations; never invent `ctx.signal`. `pi.exec` can still accept an explicitly owned AbortSignal.
- Return the privacy replacement before the runner's timeout, because that runner discards timed-out handler replacements and retains its original payload. A subprocess-only timeout does not bound a sequential transcript walk.
- Derive fallback changes from the actual review: distinguish ordinary spawn/nonzero-exit regex fallback from budget exhaustion. Regex does not detect NER-only names, so treating cancelled/unprocessed text as regex-clean fails closed-budget requirements. Document any whole-text withholding explicitly and retain human review as a separate gate.
- Share one operation budget across all text and persisted details in a hook; clear its timer in finally, pass the signal into actual exec, and prevent further detector work after cancellation. Do not solve latency by unbounded process fan-out.
- Preserve the original WeakMap clone-before-recursion behavior through async traversal. Exercise configured NER on cycles/shared aliases as well as identity and bytes of typed arrays and opaque native values.
- Apply preservation assertions at the correct carrier boundary: `emitContext` first structured-clones messages, so compare non-text block values/order there rather than identity against caller-owned objects. Provider and tool-result payloads can still require native-value identity. Preserve an incorrect independent fixture and its failure log before correcting it; do not call that failure a production regression.
- Challenge configured detection with representative system, tool-schema, tool-call, thinking/provider-extension leaves and persisted Ask-shaped `customInput`/`note`, not only a top-level system field. Keep synthetic executable detector and mock-provider evidence explicitly separate from real model inference and interactive UI qualification.
- When review requests one async-capable text-block helper, retain every original block-order assertion, make it fail with an async detector first, and route live context and tool hooks through that helper. Mutation-disable each live caller and the shared transform; helper-only tests do not establish production coverage.
- Keep independent probes byte-frozen. Run their real 30-second timeout control on the accepted pre-repair head and the repaired head; record calls at return and after a further wait. A short-timer or fake-clock probe supplements but does not replace this receipt.
- Separately mutation-remove `pi.exec` signal forwarding and use a real executable detector plus a short explicit AbortController to prove prompt cancellation and child reaping. A whole-operation deadline test can stay green without actual signal forwarding if the active process finishes just inside the runner's budget.
- Re-run real ExtensionRunner and wrapper → Agent loop → AgentSession → SessionManager JSONL readback with synthetic Ask-shaped details. Disclose the mock provider and synthetic detector; this is not real NER inference or interactive Ask UI evidence.
- Keep two-CPU lightweight Bun tests separate from memory-heavy package checks. Serialize heavy checks under the shared build lock; waiting for the lock is not test execution. Preserve exact exits, source hashes, mutable-overlay provenance and cleaned process-group evidence.
- Deliver an incremental Git bundle with its exact prerequisite, restore it into a fresh repository, compare all tracked file hashes and rerun behavioral gates. Retain source-owner worktrees, donor ancestry and every remotely unresolved thread. Local correctness does not clear concurrent-owner, current-main conflict, human-review or publication gates.
