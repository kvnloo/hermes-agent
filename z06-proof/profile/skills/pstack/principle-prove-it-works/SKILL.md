---
name: principle-prove-it-works
description: "Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'"
disable-model-invocation: true
---

# principle-prove-it-works

Use when checking a completed task's real output before declaring it done.

## Rules

1. Check the real artifact directly before reporting completion; exercise the feature, inspect the diff or read the actual value as appropriate.
2. Verify process liveness from the process itself rather than inferring it from derived state.
3. Read current authoritative values instead of cached or derived representations; treat timestamps, screenshots and agent self-reports as insufficient substitutes.
4. When verification fails, check whether the observation method is wrong before diagnosing a system failure.
5. Prefer a deterministic rerunnable comparison script over a one-time visual inspection when scripting is practical.
6. Run the check and retain its output as a visible reviewer artifact; compilation alone is insufficient proof of feature behavior.
7. Commit proof artifacts only for large or complex work that needs a lasting audit trail, within the task's Git authorization.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
