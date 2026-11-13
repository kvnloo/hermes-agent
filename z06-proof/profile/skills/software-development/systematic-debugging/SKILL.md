---
name: systematic-debugging
description: "4-phase root cause debugging: understand bugs before fixing."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [debugging, troubleshooting, problem-solving, root-cause, investigation]
    related_skills: [test-driven-development, subagent-driven-development]
---

# systematic-debugging

Use when investigating a test, production, performance, build or integration failure before attempting a repair.

## Rules

1. Establish a fast red-capable command for the user's exact symptom before theorizing or fixing. Improve flaky reproduction rates; gather evidence instead of guessing when reproduction is missing.
2. Complete investigation, pattern analysis, hypothesis testing and implementation in order. Read full errors, trace bad values upstream and instrument component boundaries to locate the cause.
3. Run the same oracle on alleged good and bad endpoints before bisection. Reject an unsupported regression premise when both classify alike; avoid manufacturing a first-bad commit.
4. Shrink a failing reproduction one element at a time. Compare complete working implementations and enumerate differences, dependencies and assumptions.
5. Rank 3-5 falsifiable hypotheses by likelihood and probe cost. Test one variable at a time; share the ranking when the user is present and proceed independently when absent.
6. Inspect durable state, bindings, timeline and continuation queue before retrying a failed orchestration handoff. Preserve partial success and existing continuations; verify the actual shell directory separately.
7. Trace the reported client's complete journey before repairing a nearby defect. Separate mailto composition from provider drafts, provider identity from transport labels, and UI transition failures from restart workarounds.
8. For async cancellation, establish ownership before awaits, test each setup/submission race, cancel only owned remote IDs and prove settlement plus cleanup. Use references/async-cancellation.md.
9. Add a failing regression case, implement one root-cause fix and run the project's real runner plus relevant broader gates. Keep extracted-function probes and unrun tests explicitly partial.
10. After a failed fix, return to investigation rather than stacking patches. After three failed fixes, stop for architectural discussion before a fourth attempt.
11. Continue authorized host-side tracing, tests and repairs when device verification is blocked. Report source-tested, built, installed and device-verified milestones separately; identify the remaining live gate.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
