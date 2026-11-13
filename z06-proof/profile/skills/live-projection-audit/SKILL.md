---
name: live-projection-audit
description: "Use when auditing live dashboard accuracy read-only."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [observability, dashboard, audit, recovery]
---

# Read-only live projection audit

## When to Use

Use when recovering a dashboard or checking whether its displayed metrics accurately represent live agents, services, hosts, workstreams or resources without changing the system.

## Recover the actual implementation

- Record the supplied repository's HEAD, status and worktree registry; follow installed plugin symlinks and process cwd before assuming that clone is the running implementation. A newer detached checkout can coexist with an older main clone.
- Distinguish native Desktop routes, web manifest routes, static artwork and unrelated applications. Prove the exact page and API separately.
- Check launch profile, installation and explicit activation independently. A linked plugin may be disabled or installed only in another profile. Respect a no-start/no-restart boundary.

## Trace source to rendered claim

- Inventory every requested surface before sampling. Separate implementation, source reachability, data age, schema compatibility, workload health and UI truth.
- Stat sources before running collectors: JSONL tail helpers may read whole files and SQLite counts may scan large archives. Audit import side effects, disable bytecode, use bounded subprocesses and strict read-only aggregate SQL.
- Exercise the unchanged collector. If aggregation crashes, preserve the exception and reproduce snapshot/health routes with an in-memory ASGI client; then run independent collectors separately. Never monkeypatch a fake green snapshot.
- Compare actual field names/nesting: ts versus timestamp, nested outcomes/usage, and canonical databases versus the first filesystem glob hit. Print only metadata, sanitized aggregates and times, not transcripts or secrets.
- Check filesystem mount identity; a mount-parent directory can report the root filesystem rather than the data drive.
- Compare live service APIs and canonical ledgers with the files consumed by the dashboard. A fresh generated_at or existing file does not establish source freshness.

## Verify UI semantics without side effects

- Test null-to-zero coercion, empty-source economics and stale-event animation. Missing pricing is unknown, not free. Historical receipts cannot establish live execution stages.
- Check process matching for substring false positives and whitespace in comm names. Process presence is not active work; receipt traces are not agents.
- Check web component registration against the actual host contract. Syntax-valid informational script injection is not a working dashboard.
- If GUI interaction is forbidden, label visual conclusions as source-derived or isolated contract probes, not observed rendering.
- Compress a network into bounded source groups with inspectable meaning, coverage and provenance; keep grouping edges distinct from authoritative process/session/task joins and retain unknown rather than deriving a global total.
- Test keyboard drills without manually refocusing after navigation: removed buttons can strand focus on the document. Restore focus on drill/back, then prove ordinary polling preserves both focus and stable selection.
- Preserve the latest successful selected detail and its source envelope when a later poll removes the node; retaining only click-time data silently discards newer evidence. Label it last-known, not completed.
- Treat an empty non-success HTTP body as unavailable, never as a measured zero-row metric inventory. Keep bounded readiness attempts in diagnostic receipts separate from uninterrupted source availability, and do not restart the producer to obtain a green screenshot.

## Finish with evidence

- Recheck repository and endpoint state; preserve existing work.
- Report exact SHAs, file:line citations, sample windows, actual test results and a complete coverage matrix including missing adapters.
- If offline, say no healthy current URL exists. Give the exact configured target and distinguish starting the backend from the activation/code/UI repairs necessary for a usable dashboard. Do not present a startup-only command as a fix for multiple verified blockers.
