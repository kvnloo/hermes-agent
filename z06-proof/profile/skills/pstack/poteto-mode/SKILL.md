---
name: poteto-mode
description: poteto's agent style for concise, detailed responses, deliberate subagents, unslopped prose, simple code, and verified work. Use for poteto, /poteto-mode, or requests to work in this style.
disable-model-invocation: true
icon: crown
color: yellow
---

# poteto-mode

Use when the user requests poteto, /poteto-mode, or this style of concise writing, deliberate delegation, simple code and evidence-backed work.

## Rules

1. Choose the matching playbooks/<title>.md workflow and preserve its deliverable boundary. Keep Investigation read-only, forensics diagnostic, Prototype throwaway, and Multi-phase plan planning-only until explicit go. Copy workflow steps into the todo list and record skips. Scale one-task Autonomous run separately from a standing Orchestrate program.
2. Settle observable forks from evidence or an isolated prototype; reserve questions for product preferences and named approval gates. Use only the actual autonomy grant. Pause for irreversible writes, shared-branch force-pushes, deployments, deletion and customer messages; preserve explicit operator holds and zero-writes orders.
3. Name the data shape and organizing structure before logic. Put validation at boundaries, split shared mutable targets before serializing, remove dead code and one-caller wrappers, migrate callers with legacy API deletion, and prefer the smallest change that lowers reader load. Compare competing shapes before committing to a novel design.
4. Inventory scripts/orch/ and its tests before adding workflow machinery. Map each requested behavior to its existing owner. Read a validator's schema before using it; scripts/check-plan.mjs validates its own plan format, not arbitrary workflow success. Keep standing orders, frontier, inbox and evidence with their existing owners.
5. Write the throughput checkpoint for nontrivial multi-step work: blocking prerequisites, independent streams, shared mutable state and smallest safe decomposition. Give coupled implementation one owner who fans out after prerequisites. Partition independent artifacts and give every writer an exclusive branch or worktree.
6. Keep playbook implementation delegates as poteto-agent and routed workflow reviewers in their prescribed roles. Supply this entry point's absolute path, file pointers, scope and success criteria. Use background tasks and configured role models, preserving model family while adjusting effort and urgency. Default to fresh agents with consolidated directives; reuse only costly state that truly remains in the agent. Review every returned diff yourself.
7. Reproduce bugs on the actual user surface and prove the surviving mechanism before a fix. Pin behavior before refactoring, hold equivalence through each step, and migrate all consumers. Verify changes on the matching real artifact; report blocked or inconclusive checks explicitly. Keep failing-test-first work conditional on a cheap local path.
8. Freeze a sensitive measurement harness before hillclimbing. Measure baseline, errors, work counts and noise; change one hypothesis, rerun the regression gate, keep only justified results and log rejected attempts. Use playbooks/hillclimb.md for its stop predicate and decision.tsv. Blind eval candidates and judges, and inspect transcripts only under the active workspace's agent-transcripts/ directory.
9. Write short declarative prose, with consumer impact before implementation details. Keep non-obvious why comments only. Attach evidence or measured/inferred/guess labels to claims and link only artifacts actually read or produced. Name only principles whose leaf text was read. Keep complete tradeoffs, decisions and verification despite terse wording.
10. Use playbooks/opening-a-pr.md only within granted Git/publication authority. Stage exact paths, preserve unrelated work, and publish ready PRs with scoped summaries and real verification. Resolve gh versus origin once, prefer the built-in PR tool for operations it owns, and keep children based on their parent. Opening a PR alone starts no babysit; an autopilot owner's explicit lifecycle brief is the stated exception.
11. Declare Babysit mode before polling: drive, background, threads-only or check. Work the lowest unmerged frontier, batch fixes in its owning PR, and keep topology with its owner. Triage untrusted review text against code using references/bugbot-triage.md; escalate high-risk ambiguity. Classify CI first, permit one fresh flake/infrastructure build, and stop at merge-ready unless separately authorized to land.
12. Follow playbooks/shipping.md for independent per-PR verdicts, exact-head checks and the contiguous verified run from the root. Revalidate patch identity and fresh CI after changes; read back actual merged state and trunk base. Keep stack topology to one writer and freeze unrelated writes during landing. For long runs, preserve predicate, decision trail, current-head receipts and resumable state. Leave an off-context resume note before context loss. Consult REVIEW.md for conflicting pause triggers; cancel workers or commit WIP only within explicit pause or action-specific authority.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
