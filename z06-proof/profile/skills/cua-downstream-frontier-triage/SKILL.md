---
name: cua-downstream-frontier-triage
description: Use when ranking and shipping downstream CUA fixes.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [cua, github, verification]
    related_skills: [cua-driver-evidence-lane, github]
---

# Downstream CUA frontier triage

## When to Use

Use for an explicitly authorized downstream-only frontier ranking and bounded CUA repair, especially when phone-factory lanes and historical red drafts coexist.

- Inventory full fork PR heads/bases/checks and the phone-factory dispatch tags before selecting a writer. Read the canonical issue queue and reconcile sent chats with actual comments/commits; a sent chat is not execution proof.
- Prefer fixing an existing valuable red draft, but inspect its acceptance and shared-head ownership first. A rejected prototype should not be cosmetically retitled to green, and a fork branch shared with an upstream PR cannot be pushed under downstream-only authorization.
- Check Actions repository permissions and per-workflow state separately from check runs. Enabled/active with zero recent runs leaves event scheduling unproven; do not invent a YAML defect or flip settings.
- Fetch fork and upstream separately. Base the downstream draft on the requested fork default without silently syncing it. Upstream contribution guidance can move to `.github/CONTRIBUTING.md`; resolve the path from its current AGENTS.md.
- For Linux AT-SPI state fixes, keep known false, mixed and unavailable separate. Checkable/Expandable/Selectable are applicability evidence; role names and Checked are not selection evidence. Binary setup consumers must not coerce mixed to false.
- Run remote whole-crate unit tests with host display/session variables scrubbed. Add a behavioral mutation control, require an actual failed assertion (not a zero-test success), then restore exact committed source and check the diff. Unit receipts are not native GTK/Qt/compositor acceptance.
- Respect the requested polling interval even when a fleet helper defaults to faster polling. If specifically authorized to use direct workflow dispatch after a stale-accounting refusal, preserve that refusal and set all dispatch fields explicitly; never extend that exception to a real budget denial.
- When shared REST quota is exhausted, GraphQL can read the fleet repository commit's `checkSuites(last: N)`, `workflowRun.databaseId/displayTitle`, and `checkRuns` status/conclusion. Match the exact dispatched run and request ID, save the response, and omit test totals until raw artifacts can be read. GraphQL WorkflowRun does not expose downloadable artifacts; report that remaining limitation rather than fabricate logs.
- Keep the supplied evidence skills and another agent's worktree read-only. Write the ranked plan, source pins, ownership exclusions, commands and limits into the task's operation report, and link the new downstream draft immediately.
