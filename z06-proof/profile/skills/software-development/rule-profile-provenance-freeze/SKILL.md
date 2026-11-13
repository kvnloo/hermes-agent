---
name: rule-profile-provenance-freeze
description: Use when freezing rules against an existing engine.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [rules, provenance, testing, audit]
    related_skills: [github, grounded-citations, test-driven-development]
---

# Rule-profile provenance freeze

## When to Use

Use for a documentation/provenance slice that compares an existing engine to an authoritative external rule edition without changing gameplay. Do not use this audit workflow as a substitute for TDD when implementation fixes are authorized.

## Procedure

1. Read issue acceptance, sibling boundaries, repository instructions and existing research before editing. Treat prior research as leads, not accepted authority.
2. When the canonical checkout is dirty or must keep its HEAD, create a sibling worktree from the exact requested SHA. Hash protected research/database files first. Do not reset, stash, clean, rebase or prune to simplify isolation.
3. Re-fetch official sources with verified TLS. Record final URL, UTC retrieval time, status, bytes, SHA-256, edition and printed-page versus PDF-page numbering. Commit brief checked quotations and paraphrases, not copyrighted source bundles.
4. Keep one canonical data artifact. Each semantic group needs scope, source IDs/rules/pages, current behavior, classification, conformance, baseline code anchors, exact test declarations and explicit gaps. Pin anchors to the audited commit because comment edits move lines.
5. Separate helper-only behavior from integrated behavior. A fault token, test title, same-assumption differential oracle or source scan is not independent rule conformance. Read assertions and inspect call sites.
6. Execute public-API diagnostic tapes to distinguish comments, actual behavior and missing inputs. Record counterexamples in the required tracker without silently fixing the engine in a provenance-only slice.
7. Leave conflicting official wording or missing interpretations explicitly unknown. Separate general play, tournament officiating, scoring modes and per-player variants instead of inventing one global policy.
8. Reconcile top-level claims and historical design documents. For comment-only source edits, compare emitted JavaScript with comments removed using identical compiler options; still run required tests/typecheck. This comparison proves a source-change boundary, not gameplay correctness.
9. Preserve wall-clock test failures. Run an untouched baseline with identical settings before calling a failure pre-existing. Verify installed runner support before selecting a process-local worker limit, then run both baseline and candidate with that limit. Report unrestricted failures and controlled passes separately; never weaken assertions or edit test config merely to get green.
10. Compare database rows against the clean baseline; allow only task-owned additions/updates. Validate source hashes, page anchors, classifications, counts and the entire declared fault-token inventory programmatically.
11. Stage an explicit path allowlist, commit on the isolated branch, push only the authorized remote/ref, and read back remote SHA. Recheck canonical HEAD, branch and pinned hashes. A compare link is not a PR or merge.

## Delivery

Deliver the canonical profile, readable rule→code→test map and compact verification results. Keep PDFs, raw logs, probes and inventories in scratch. Disclose protected documentation edits that were denied and default-concurrency failures that remain. Never describe unknown policy or uncovered physical inputs as certified compliance.
