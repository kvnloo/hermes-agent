---
name: git-isolated-contribution-guards
description: Use when isolating worker Git contributions.
version: 0.1.0
platforms: [linux]
---

# git-isolated-contribution-guards

Use when coordinating isolated worker contributions to read-only source with parent-owned integration.

## Rules

1. Read the cohort ownership/resource brief first. Write deliverables only in the assigned lane; use only authorized tiny fixture repositories for tests.
2. Inspect real Git read-only with GIT_OPTIONAL_LOCKS=0. Obtain separate authority for worktree administration, staging, commits, stashes, resets or cleanup.
3. Default to per-lane staging when source Git is read-only. Measure actual resource use and admit heavy builds separately; worktree isolation grants neither resource capacity nor Git permission.
4. Allocate exact paths under parent control. Reject equality and ancestor overlap, malformed literal paths before normalization, links, unsupported types and undeclared payloads.
5. Pin full base HEAD, Git object preimages and payload hashes. Validate affected index entries and current worktree bytes without legitimizing dirty inputs; preserve unrelated staged and untracked content.
6. Separate mutable WIP, sealed hash-bound candidates and parent-issued acceptance receipts. Treat preflight as review readiness; establish parent custody rather than trusting an actor flag.
7. Keep preflight read-only. Reserve locking, immediate revalidation, exact-diff review and readback for parent promotion; leave promotion and rollback machinery with its owning lane.
8. Prove behavior using real tiny Git fixtures under the cooperative light-check lock. Cover valid patches, path/ownership refusals, dirty or staged collisions, links, stale bases, sealing and Git patch consumption.
9. Audit every outgoing commit and message before publication, not just the tip diff. Block disclosure-risk pushes when history cleanup lacks authority; preserve the branch and never rewrite a concurrent worker's history silently.
10. Report measured tests/resources, source-state before/after, exact deliverable paths, unimplemented boundaries and the next parent action separately from proposed adoption.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
