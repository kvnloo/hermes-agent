---
name: tiered-local-checks
description: Use when prototyping tiered local check runners.
---
# Tiered local checks without a framework

- Keep fast pure checks, resource-gated application smoke, and visual proof as explicit tiers; default to fast and report unrequested tiers as skipped, never passed.
- Inspect existing public CLIs and source-adjacent writes before selecting checks; AST parsing avoids importing scene-dependent modules, while a reviewed check-only branch can prove real command behavior cheaply.
- Exercise the runner through subprocess CLI tests with small generated fixtures, actual exit codes, malformed outputs, missing inputs, and real lock contention; do not substitute source-string assertions for orchestration behavior.
- Serialize lightweight suites with the shared nonblocking lock; give child fixture commands private locks only while the parent suite holds the shared lock, avoiding recursive deadlock without bypassing cohort serialization.
- Emit a parent-consumed smoke ticket rather than implementing a second scheduler; distinguish ticket_ready/not_submitted from accepted, running, and completed states.
- Stage scripts that write beside themselves with their relative dependencies in a fresh owned directory; pin source hashes and require a new receipt plus the real exit code and sentinel.
- Keep capacity observation separate from resource reservation; the parent must retain the scene lock while rechecking capacity and running the job.
- Treat manifest slots and image headers as structural evidence only; missing hash binding, decode, or review must remain explicit and cannot produce visual approval.
- Save real command outputs, including transient deferrals, and record successful retries separately instead of overwriting inconvenient evidence.
- Inventory every manifest entry's type before calling a manifest text-only; a vendored archive makes a strict text check fail even when all selected text hashes match. Keep partial text verification and deferred binary entries explicit without rewriting the source manifest to manufacture a pass.
- Audit remote default-tree metadata, installed workflows/runs, and Actions feature permissions separately; zero workflows does not mean Actions is disabled. A guard after normal checkout cannot prove private blobs were never ingested, so defer remote execution until the acquisition boundary is demonstrated.
- Preserve Git preimage bytes through JSON framing when terminal output may strip trailing newlines, then apply the exact generated patch in a tiny owned fixture and compare resulting bytes; textual resemblance is not patch-consumption evidence.
