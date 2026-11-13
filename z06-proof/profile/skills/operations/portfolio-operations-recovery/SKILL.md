---
name: portfolio-operations-recovery
description: Use when recovering portfolio work after interruption.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [portfolio, recovery, kanban, crash, evidence, messaging]
    related_skills: [coding-session-continuity, messaging-gateway-operations]
---

# Portfolio Operations Recovery

## Trigger

Use when a host, gateway, dispatcher, or agent session restarts while several products or Kanban lanes are active; when the user says “continue after the crash”; or when they ask to see and receive the complete recovered portfolio view.

For retrospective requests spanning messages, harnesses, Git and completed cards, use `references/comprehensive-cross-instance-census.md`. Recover the full requested window before ranking priorities: keep user-locked priorities, but do not preselect the remaining winners from familiar projects. Read message bodies rather than treating a session index as a transcript audit. Keep the exhaustive evidence on disk and return the small product-level tracker Kevin requested; output brevity must not shrink investigation coverage.

## Core rule

Recover from durable task graphs, repositories, revisions, and artifacts—not from the last chat summary. Operational continuation is not visual approval, merge approval, publication approval, or acceptance of an unreviewed artifact.

## Workflow

### 1. Persist the recovery request

When the operating contract requires intake receipts, create one stable recovery request before routing work. Reuse existing product cards and dependency graphs; the receipt is an executive audit record, not a duplicate implementation root.

### 2. Reconcile live execution

Before dispatching anything, validate the execution envelope as data: the assignee is spawn-capable, `workspace_kind=worktree` has either an exact repository/workspace path or a valid board default, directory workspaces exist at the intended revision, and the task body cannot mistake an intake census for authorization to rebase or implement. A malformed legacy card can consume its retry budget through deterministic spawn failures; do not retry it unchanged. Preserve it as a tombstone, create one idempotent replacement bound to the verified workspace, and rewire downstream dependencies through the replacement's independent reviewer.

For each named lane, inspect the native task record and latest run. Separate:

- `done`: inspect the completion handoff and artifact/revision;
- `running`: require a current run/heartbeat, not a stale PID;
- `ready/todo`: queued, not active;
- `blocked`: preserve unless the dependency is resolved or an explicit decision supersedes it;
- `crashed/reclaimed`: inspect the later run before deciding whether work still needs dispatch.

A task can complete after the chat still calls it blocked. A crash can also reclaim and respawn the same task under a new run ID. Never replay a lane from prose alone.

### 3. Reconcile repositories

For every active workspace, record branch, HEAD, status, and relevant artifacts. Classify dirt as expected in-flight output, pre-existing user work, or unexplained. Do not reset, clean, stash, or create a replacement worktree merely to make the portfolio appear clean.

### 3b. Repair stale portfolio cards from current product evidence

When a project/feature card materially disagrees with the active repository, treat the card as a stale projection rather than editing its old narrative incrementally:

1. Identify the active implementation lane from worktrees, branch history, current dirty paths, and session lineage; distinguish it from a dirty canonical checkout or unrelated worktree.
2. Read the current product contract, runnable scripts, private/public boundary rules, and evidence manifests. Do not infer product identity from the legacy card title.
3. Run the documented structural gates and the actual user-visible path. Start required local services before browser tests; a connection failure without the service is an observation-envelope failure, not a product verdict.
4. Inspect representative visual artifacts directly. Report functional maturity and visual maturity separately because passing browser/mesh tests cannot establish art-quality acceptance.
5. Classify every dirty path before preservation. Commit only the coherent product slice on its existing branch, leave private binary inputs/evidence off Git, and verify the exact branch is clean after the commit. Never clean an unrelated checkout just because the project has another dirty worktree.
6. Rewrite the card around current outcome, active owner/workspace, implemented behavior, revision-bound evidence, honest maturity, privacy/publication boundary, and one next decision. Remove superseded blockers and completion claims rather than retaining contradictory history in the active description.
7. Read back the external card after the update, then write the same corrected summary into the durable portfolio state. Keep old leaf relationships only when they still describe executable work; a relation is not evidence that its stale status remains valid.

### 4. Audit downstream auto-promotion before closing parents

A repair or reviewer completion can immediately promote and spawn a descendant activation, publisher, migration, deployer, or merge card. Before completing, approving, linking, or unblocking any parent:

1. Enumerate its descendants and classify every side effect.
2. If a descendant crosses a human gate, place a durable `needs_input` block on that descendant before the last dependency can complete.
3. Complete the reversible parent only after the block is read back.
4. After parent completion, inspect the descendant again and verify no run was claimed during the transition.
5. Read back the real external state, such as timer/service status, deployment revision, or publication target.

Do not rely on a descendant task body's prose gate. Dispatcher dependency resolution is mechanical and can race ahead of a foreground operator. See `references/gated-descendant-auto-promotion.md`.

### 5. Preserve gates and ownership

Reuse roots, persistent Second Mate cards, review children, and hotspot ownership. Unblock only with a concrete rationale. “Continue” after interruption resumes execution but does not silently approve:

- visual direction or pixel quality;
- external publication;
- destructive changes;
- credentials or spending;
- development-branch merge;
- deployment, state migration, live canary dispatch, or scheduler/service activation.

### 6. Verify infrastructure separately

Check mounts, free space, timers/services, and gateway health as supporting evidence. Service/process presence proves infrastructure availability, not product completion.

### 7. Build the executive view

Report each material lane as:

- Priority / product
- Owner and exact task
- Current state
- Latest verified revision/artifact
- Evidence limit or blocker
- Next action/decision

Exclude synthetic E2E, benchmark, and fixture cards from company-work counts. Mark in-flight dirty work as not frozen.

### 8. Deliver evidence cross-channel

When the user asks for the packet on Telegram or another configured surface:

1. Send a concise text index first.
2. Attach the smallest useful set of representative evidence—normally one artifact per active visual lane, plus critical comparisons.
3. Resolve the gateway’s real `HERMES_HOME`, active profile, home channel, and configured delivery target before sending. A CLI scoped to a different profile may falsely report “platform not configured.”
4. Prefer the supported messaging command/tool; never print or expose bot tokens.
5. Verify the exact chat and retain returned message IDs before claiming delivery.

See `references/crash-recovery-and-telegram-delivery.md` for a compact field checklist and validated evidence-packet shape.
See `references/intake-only-recovery-receipts.md` for auto-dispatched recovery receipts, board-local parent constraints, final-status readback, and bounded cross-board resumption.
See `references/pre-dispatch-envelope-and-replacement.md` for validating workspaces/assignees before dispatch and repairing deterministic spawn failures without losing lineage.

## Pitfalls

- Recreating tasks because the chat summary looks stale.
- Calling an old session, PID, or null `ended_at` active.
- Treating a resumed worker as evidence that its artifact passed.
- Conflating operational “continue” with approval of a visual checkpoint.
- Listing hundreds of synthetic/bench cards as real portfolio work.
- Reporting a dirty active worktree as a frozen deliverable.
- Updating a stale portfolio card from its own description instead of reconstructing current product identity and maturity from the active repository, runtime path, and direct artifact inspection.
- Treating one dirty checkout as permission to clean every worktree for that repository; scope preservation and cleanup to the proven implementation lane.
- Calling structural, mesh, or browser checks visual acceptance; inspect representative images/motion and state the remaining quality gap separately.
- Sending only paths when the user explicitly requested Telegram delivery.
- Claiming delivery from command exit alone without exact chat/message evidence.
- Leaving an intake-only recovery receipt `running` after auto-dispatch; reclaim, constrain, census in the foreground, then close it.
- Treating reclaim as closure without a second status readback.
- Forcing a company-board parent onto a product-board card; Kanban parents are board-local.
- Replaying stale overnight factory, tournament, or activation graphs because the user said “resume the factory.”
- Letting an auto-dispatched executive intake receipt create advisory rebases or implementation branches; constrain or reclaim it before it can cross from census into product work.
- Re-dispatching a `worktree` task with no resolvable repository path until the circuit breaker trips; validate the envelope first and replace the malformed card once.
- Completing the final repair/reviewer parent before blocking a human-gated descendant; dispatcher promotion can claim the descendant immediately.
- Assuming a task body's written approval requirement prevents dispatcher execution. Encode the gate in task status and dependency topology.
- Treating the newest generic “audit” card as the user's intended continuation when the reply context names a product or capability. Use conversational anchors to constrain discovery, then confirm against durable task state.
- Accepting aggregate benchmark prose when raw receipts use different success definitions. Reconcile transport, nonempty output, exact-oracle output, aggregator success, and user-visible success separately before closing the card.

## Verification

- [ ] Recovery request is durable when required.
- [ ] Every named lane was read from the current task graph.
- [ ] Latest post-crash run inspected for reclaimed/crashed cards.
- [ ] Active workspaces reconciled against Git and artifacts.
- [ ] Any stale portfolio card was rebuilt from current product contracts, runtime evidence, and direct visual inspection; functional and visual maturity are separate.
- [ ] Cleanup/commit scope was limited to the proven implementation lane, and that exact branch was read back clean.
- [ ] Updated external cards were read back and mirrored into durable portfolio state without preserving contradictory active claims.
- [ ] No duplicate implementation graph created.
- [ ] Human gates remain explicit.
- [ ] Synthetic/benchmark fixtures excluded from portfolio totals.
- [ ] Cross-channel delivery verified with exact target and message IDs.
- [ ] Intake-only receipts were read back after reclaim and closed intentionally.
- [ ] Cross-board lineage uses supported board-local relationships; no duplicate graph was created to force parentage.
- [ ] “Resumed” names an actually running bounded task and its parent-gated reviewer, not merely a completed census.
- [ ] Every dispatched card has a spawn-capable assignee and resolvable workspace envelope.
- [ ] Intake-only workers were prevented from performing product rebases/implementation unless that exact mutation was separately authorized.
- [ ] A malformed legacy card was preserved as a tombstone; exactly one idempotent replacement and reviewer gate carry downstream lineage.
- [ ] Human-gated descendants were enumerated and blocked before the final parent completed.
- [ ] Descendant status and the real external runtime were read back after parent completion.
- [ ] Continuation discovery was constrained by the user's reply context, not only by newest-card chronology.
- [ ] Conflicting reports were reconciled from raw receipts with success dimensions named explicitly.
