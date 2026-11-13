---
name: github
description: "GitHub via gh CLI: PRs, issues, reviews, repos, auth."
version: 2.0.0
author: Ben Barclay (benbarclay), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [github, gh, git, pull-requests, issues, code-review, repos, auth, ci]
    category: software-development
    related_skills: [codebase-inspection, requesting-code-review]
---

# github

Use when working with GitHub authentication, issues, PRs, reviews, repositories, Projects or CI through gh.

## Rules

1. Preflight gh auth once per session; prefer gh, then gh api for missing endpoints. Use references/auth.md for failures; a cached GET does not establish shell authentication.
2. Read bodies and complete relevant discussions before acting. For full audits include reviews and inline replies, reconcile pagination/counts, then return decisions and evidence limits, not a message inventory.
3. Sweep duplicate issues/PRs and inspect available labels before creation. Identify remembered forks from README behavior and parent metadata, keeping social-link provenance unverified.
4. Keep update audits read-only and ordinary PR reviews private unless publication is authorized. Apply the owner-repo fix/push/re-review workflow only within the governing task's write scope; see references/code-review.md.
5. Honor O17 maintainer backoff. Lift it only with explicit owner authorization and an ack using canonical repository casing; flag conflicting bypass recipes rather than treating them as permission.
6. Check gh-pace before bulk/polling reads; hold or hard-throttle stops direct REST reads. Use local clones, ghcache and the contribution archive; avoid API polling loops and REST retries before reset. See references/api-budget.md.
7. Keep issue fixes scoped: verify premise/design intent, define acceptance, prove regression tests fail without the fix, check siblings and run repository gates. See references/issue-to-pr.md.
8. Publish only intended files and branches within authorization; disable tag following. Verify PR head/base/diff and remote branch. Treat merge, release-branch promotion and clean-tree deployment as separate gates.
9. Verify CI, merge, release and issue state with fresh exact-target reads. Report absent/skipped/cancelled checks; bind findings to head SHA and separate baseline from introduced failures.
10. Verify repository/project privacy before writing. Keep private reports, credentials, raw logs and local paths out of payloads; retain sanitized evidence keys locally. Preserve unknown entitlement/auth facts as blockers.
11. For Projects, exhaust discovery, preserve human fields/views, rediscover uncertain creates and verify semantic configuration plus rerun idempotence. Leave dates and UI gates unset without evidence; see references/projects-v2.md.
12. Keep attribution edits append-only with fresh full-body reads and byte readback. Verify rendered attachments and reproducible contribution counts. For GPT reviewers, use fx/pi read-only lanes under the owner's 2026-11-04 harness rule; parent-verify base/head findings.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
