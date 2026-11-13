---
name: session-recovery
description: "Use when asked to recover session or continue work."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [session, recovery, state-db, delegation]
    related_skills: [hermes-agent, github]
---

# session-recovery

Use when recovering or continuing work after a reset, crash, closed terminal, failed app thread, or interrupted delegation.

## Rules

1. Recover the original human request and acceptance criteria from disk instead of asking the owner to repeat them. Separate human asks from worker deliveries, runtime notices and injected instruction envelopes.
2. Read a supplied app thread through its app-owned reader first; record host/environment coverage and search sibling/scratch projects before claiming absence. Use read-only native databases or bounded transcript fallback, not assumed local app state.
3. Identify unnamed failures from recent unfiltered thread candidates and actual error records, not longest timelines. Read bounded tails and saved spillover; request a thread identifier after targeted evidence cannot distinguish candidates.
4. Inspect previous user turns and substantive final answers. Relay an already-completed owed artifact rather than rerunning it; treat restated unmet criteria as a reason to resume discovery, not defend the old answer.
5. Search cross-profile/harness history, parent sessions, repo plans and prior offline evaluations for known projects. Preserve source dates and distinguish owner decisions from assistant suggestions; scope not-found claims to inspected surfaces.
6. Prove the previous execution owner is dead before relaunching. Check recent native rows, run identities, processes and unexpected file/ref changes; a cancelled T3 run or shared session ID can conceal an active ghost writer. Preserve its ownership and shared host processes.
7. Reconcile worktree HEAD, dirty/untracked files, checkpoints and canonical execution cards before writing. Rescue scratch-only briefs and evidence into durable operations storage and resume the earliest authorized missing gate rather than repeat implementation.
8. Read async delegation result_json and full report/transcript files even when delivered or no worker is listed. Bind proof to exact artifact bytes. Resume GPT workers through fx/pi under the owner's 2026-11-04 harness rule, with transcript, head, checkpoint and ownership context.
9. Diagnose provider-session, model-switch, context-limit and OOM failures before retrying. Use a capable fresh thread when retries cannot work; preserve checkpoints and exact launch commands for restart-safe long jobs.
10. Preserve approval, privacy, branch and publication boundaries during recovery. Coordinate live sibling work; obtain authorization before deleting generated profiles, killing leftovers or pushing recovery snapshots. Trace generated setup to its actual authoring turns before removal.
11. Continue one deliverable end to end when authorized, retaining other goals and ownership seams. Reobserve remote heads, CI and deployment independently; hashing surviving files does not retroactively establish their tested revision.
12. Report every owner ask as done, partial, plan-only or not started with evidence, then advance an eligible gap within scope. Lead with the owed deliverable, save a durable consolidated handoff and name remote-writing next steps explicitly.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
