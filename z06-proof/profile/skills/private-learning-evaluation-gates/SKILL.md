---
name: private-learning-evaluation-gates
description: "Use when building private learning evaluation gates."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [learning, evaluation, privacy, testing]
---

# Private learning evaluation gates

## When to Use

Use for local randomized learning pilots, held-out assessment, tutor intervention approval policies, and their privacy/producer contract tests.

## Procedure

Build vertical executable slices with synthetic fixtures before integrating a peer corpus. Keep production observations absent until an explicitly approved human study actually occurs.

- Hash the full corpus, matching blocks, seed, allocation algorithm and evaluation protocol into an immutable manifest. Allocate distinct matched concepts with one condition per concept; reject duplicate material, changed seeds, corpus drift and crossover. Never append new concepts or silently migrate a started cohort.
- Keep allocation, held-out questions/rubrics, responses and approvals in owner-only flat files outside tracked source. Verify that a canonical data directory inside a repository is ignored rather than rejecting all Git ancestors. Refuse symlink inputs and atomically publish immutable files.
- Separate preview approval from the first actual study event. Anchor follow-ups to each concept's actual study start, not preview/approval creation. Compute due windows on demand without becoming a second scheduler. Missing or future results are not observations.
- Issue novel recall before transfer and discrimination, one question at a time. Discrimination options can cue free recall if the whole packet is exposed together. Keep answers and error-driven practice feedback inaccessible during the experiment.
- Treat confidence/gap reports as self reports, external rubric assessments as scores, and held-out scenario transfer as distinct from unobserved workplace outcomes. Show missingness, the exact retention rule, recorded time denominators and small-sample uncertainty; do not impute missing human data.
- Reserve event IDs across pending responses and all other event types, not just exported records. Exact retries dedupe; a pending response UUID reused for a study event must fail before scoring/export can collide.
- Validate producer envelopes through the actual consumer normalizer without opening its analytics database. Document any explicit internal-condition to wire-enum mapping; do not silently rename allocations.
- Label local template proposals as deterministic heuristics, not model results. Require a bound human approval plus experiment/confound eligibility before exposing intervention content. Never auto-apply real-card edits or introduce an unapproved provider.
- Test the real read-only HTTP/CLI boundary, including blocked mutations, arbitrary paths, withheld answers, stale corpus rejection and no start marker. Loopback binding alone does not justify wildcard CORS; use an explicit allowed origin and Host validation.
- Preserve superseded unstarted previews when a protocol changes; issue a new version and keep the original immutable. Report software verification separately from human dogfood and psychometric validation.
