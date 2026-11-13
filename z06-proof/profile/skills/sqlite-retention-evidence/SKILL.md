---
name: sqlite-retention-evidence
description: "Use when proving SQLite retention, size or write changes."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [sqlite, testing, retention, evidence]
    related_skills: [upstream-contribution, test-driven-development]
---

# Bounded SQLite retention evidence

## When to Use

Use for SQL retention fixes involving scan cost, sequence windows, catch-up throughput, or single-writer stalls, especially when reviewing a reporter-supplied patch without publication.

## Procedure

1. Pin the production base and proposed patch independently. Inspect issue comments and timelines: an explicit assignment still owns the work when the assignees array is empty. Verify the reporter's actual identity rather than copying attribution from a downstream test PR.
2. Reproduce three separate properties: query-plan work, retention semantics after age-created sequence holes, and per-run catch-up capacity. A compile error in an imported regression is not behavioral RED; match the current test package and fixture namespace first.
3. Execute `EXPLAIN QUERY PLAN` using the actual generated query and production driver. A COUNT-based full scan can dominate a bounded DELETE even when its row limit is small.
4. Define sequence-window semantics explicitly. After age pruning creates holes, keeping the newest N sequence values is not keeping exactly N physical rows. Exercise real persistence and assert retained sequence IDs.
5. Seed more eligible rows than the batch limit. A fixture whose entire excess already fits in one batch cannot detect removal of LIMIT. Verify multiple bounded deletes and a final no-op. Count age-prune and size-prune statements separately: one loop iteration may execute two bounded transactions, so a size-only deletion budget is not the aggregate per-run ceiling. Exercise their combined budget through the real janitor and store methods, and distinguish queued-writer progress from a latency SLA.
6. Edit SQL sources and run the repository's pinned generator. For sabotage, mutate source queries, regenerate, run the behavioral regression, restore the source, regenerate again, and compare original generated-file hashes. Never hand-edit generated implementation files.
7. Mutation-check the per-run batch budget, count-vs-sequence query, and physical transaction limit independently. Classify a named test failure as caught; build errors and timeouts are inconclusive.
8. Run complete affected suites on the final clean commit, preserving the repository's CI test sharding. A serial migration race suite can exhaust the per-package timeout even while every completed test passes; retain that timeout receipt and reconcile the union of sharded top-level test names against `go test -race -list .` before calling the suite complete. In a Go workspace, `GOWORK=off` can select different dependency versions. When preserving tracked workspace checksums, copy the workspace declaration into owned scratch and use resolved absolute module directories; symlink aliases can fail workspace-membership checks. Record selected module versions.
9. Benchmark exact old/new SQL on scratch-only file-backed databases with realistic indexes. Queue an INSERT probe through the same single-connection `database/sql` writer pool as cleanup, recording latency percentiles, raw samples, pool waits, removed rows per batch, and query plans. Equal-work query comparisons should use the same number and size of batches. Preserve parameter-order changes from generation.
10. Report driver/runtime versions, database sizes, cache/WAL settings, trial order, shared-host load, and synthetic limitations. A measured sub-second maximum at a few million rows is not proof that production can never stall at tens of millions. Do not touch a user's live database or claim their reported measurements as yours.
11. For size claims ("retention or eviction saves X"), apply the policy to a `VACUUM INTO` copy, `VACUUM` it, and report the real file size. Logical column bytes miss index pages, page slack (`dbstat.unused`) and record overhead, and these can be a third or more of the file. Reconcile the class totals with the file through `dbstat` before publishing. Measure the baseline after the existing compaction tool has run, so its savings are not credited to the new change.
    - Also check `PRAGMA auto_vacuum` on the **target** database and report the in-place size next to the vacuumed one: the file bytes, `freelist_count` and used bytes (file minus freelist) right after the deletion, with no VACUUM. On `auto_vacuum` = NONE (0), deleted rows become freelist pages. The file does not shrink, and `PRAGMA incremental_vacuum` does nothing. Switching modes needs a full VACUUM, which usually cannot run while the server holds the database. The honest claim is then "the saving lands after the offline VACUUM tool runs; until then it is reusable headroom", not a smaller file.

12. For event-sourced logs, deleting superseded snapshot rows changes semantics beyond size: consumers insert entities at their first row, replay resumes by sequence, and readers may fetch rows by command id. Keep the first row and move the newest body into it, never delete a stream's newest row, and make resumes from cursors inside a folded range fall back to a snapshot via a per-stream watermark (a global one penalizes every idle stream). Only fold types whose apply writes no OTHER entity (a last-writer-wins side effect such as "active child" flips when bodies move earlier), never delete the last row that sets a derived "updated at" (events like "visited" keep the previous value, and so does any event whose apply re-writes the parent row from its current state rather than from its own timestamp, such as a link sync: audit every parent-event type's apply in both the server and the client), settle by a head sequence sampled before a monotonic wait rather than by wall-clock timestamps, and re-check the watermark after reading the replay, because a fold committing between the check and the read hides the final body. Every reader that reads from a held cursor needs the watermark check, not just the resume path: a lazily started live tail (started only after the client acks a snapshot or replay) can begin long after its cursor was taken. So check after each page read and fail retryably, so the client resubscribes and gets a snapshot. Prove it with per-table rebuild digests in rowid order on a real copy (after counting how many seed cases actually exercise each risky shape) plus a rebuild-vs-live row diff that must match the unfolded arm's, a whole-projection replay comparison against the unfolded log, an every-cursor replay test, a fold-between-check-and-read test through the real resume path, and an A/B showing identical wire bytes plus a stale-cursor reconnect phase. T3-specific recipe: t3code-upstream-contribution `references/event-log-compaction.md`.

13. For footprint work (ids, indexes, page slack), measure before proposing: dbstat slack vs row-size histogram, id bytes by family, index usage from captured real SQL + EQP, then simulate each candidate on its own vacuumed copy. Page size is often the largest storage-only lever. Recipe and lever table: `references/footprint-levers.md`.

14. For any change that may alter bytes written (page size, checkpoint/WAL settings, commit batching), measure writes with a per-file syscall tap and split them into WAL frames per commit vs checkpoint copy-back before choosing knobs; measure the one-time VACUUM conversion cost from a WAL-mode copy. Before batching commits, attribute each commit to its writer from the server's span trace (must equal the tap's commit count) and replay writer timings against candidate windows. Recipe and decision rules: `references/write-amplification.md` (includes the group-commit window A/B: power-check arm, memory-tight interleaved runner, cross-SHA pooling, how to read coalescing shifts).

15. Targeted tests on a memory-pressured host can die with exit 143 (SIGTERM from the pressure guard) before printing results; never pipe them through `tee` (it hides the exit code). Wait for RAM and low stall, then retry with `--maxWorkers=1 --no-file-parallelism`, and keep the passing log as the receipt.

## Receipt

Include exact base/head, file hashes, source-patch hash and attribution, commands/exits/log paths, expected RED failures, restored GREEN, mutation verdicts, benchmark inputs/results, remote CI status, and publication/ownership holds. Keep local review replication distinct from a new upstream carrier.
