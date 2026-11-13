---
name: openroad-hosted-numeric-attestation
description: "Use when auditing OpenROAD hosted numeric A/B receipts."
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [openroad, native-tests, provenance, code-review]
    related_skills: [upstream-contribution, github, requesting-code-review]
---

# OpenROAD hosted numeric attestation

## When to Use

Use for independent, read-only qualification of an existing OpenROAD numerical candidate using actual hosted A/B logs, especially when local native dependencies are absent.

## Procedure

- Pin fork workflow head, original owner head and owner target base separately. A QA patch stored in the repository is not an applied production fix; identify the actual overlay using original and patched Git blob hashes.
- Download the exact run artifact and job log. Verify the archive against its advertised SHA-256, then reconcile XML identities by `(classname, name)` with the actual source tests. Require executed/completed cases, no skips, exact expected baseline failures and zero candidate failures. Distinguish failed assertions from failed test cases.
- Trace the Bazel test dependency to production code. Preserve cache semantics accurately: `--nocache_test_results` prevents cached test verdicts but does not disable build caches.
- Do not invent a numeric baseline exit when the workflow only asserts nonzero. Record that limitation; a successful shell step is not a printed child status.
- Inspect commit check-runs by workflow path/run/job, not only `gh pr checks`: identically named jobs in separate workflows can hide a failure in the porcelain rollup.
- Read the pinned contribution guide's formatter version. A real formatting pass with another version is not contract compliance. Do not install a full compiler/toolchain merely to replace a bounded hosted attestation.
- Reuse a local native binary only with matching version/source/hash provenance. If absent, label fresh native execution NOT_RUN and retain the executed hosted receipt as independently audited evidence, not a fresh run.
- Distinguish native helper tests from real timing-driven design execution, especially when production callers prefilter nonfinite input. Keep invalid-data policy interpretation and multi-design/technology routed QoR as separate gates.
- Refresh current reviews and registry routing. Preserve original owner credit, pending registration and repository-local evidence carriers; historical factory fallback instructions do not override current routing policy. Prepare local human review notes without posting when repository policy requires human submission.
