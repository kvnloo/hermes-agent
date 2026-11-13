---
name: unified-memory-operations
description: "Use when testing, fixing or explaining unified memory."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [memory, agentsview, z0intelligence, recall, uniichat, qualification]
    related_skills: [terminal-agent-orchestration, agentsview-safe-source-retrieval, session-recovery]
---

# unified-memory-operations

Use when explaining, testing or repairing unified memory, recovering original owner intent, or auditing cross-harness recall and configuration pruning.

## Rules

1. Recover relevant established workflows from original owner messages before asking for repetition. Treat memory as evidence rather than authority: hydrate promising events, reject machine-launched worker briefs as owner speech, label pasted plans, and verify reported success against artifacts. Preserve lean/stock settings without restoring removed hooks incidentally.
2. Query the available memory search/fetch tool first and record its query/result before direct history fallback. Use the installed read-only archive backend before HTTP fallback. For unavailable transport, use ctx search '<terms>' --refresh off --content-scope transcript --limit 5 --format json, then ctx show event <id> --format json against the discovered real root. Broaden implausibly narrow filters and disclose fallback coverage.
3. Read operations/memory-heal/STATUS.md, heal.jsonl and incidents/ before health changes. Put invariants/remedies in .files config/host/memory-system-intent.toml and scripts/memory-heal. Keep --check free of receipts and state writes, daemons restartable, and long resumable jobs restartable rather than escalated. Preserve installer ownership and verify release symlinks after deployment.
4. Diagnose misses separately as coverage, ranking, wiring or startup. Check sync freshness, newest sessions, project grants and the running checkout before retrieval quality. Use z0int memory sources for derived root inventories; use real provider-specific paths and verify indexed content, not registration alone. Inspect machine-text tiers and FTS matched fields before calling a miss missing coverage.
5. Resolve the exact process owning the affected CLI, API or messaging session. Qualify correction capture, store freshness, adapter loading and actual injected messages.api_content separately. Test startup changes in a fresh isolated process and coordinate shared-owner restarts. Preserve on-demand recall independently of optional injection.
6. Run the real in-harness matrix before scoring quality. Record surface access, returned evidence and original-source answer for each harness, with transcript/event IDs opened independently. Use python3 /mnt/zer0models/workspace/zer0/data/operations/memory-repair-20261025/recall_check.py for its declared checks and mutation-test new checks. Keep blank-state replay results separate from tool availability and organic usage.
7. Route every replay claude -p call through memory-replay-eval/quota.py and quota.run. Keep at most two machine-wide MEMEVAL_CLAUDE_SLOTS, preserve --par, and stop all eval processes for 30 minutes on the first rate limit. Record new re-explain complaints as incidents rather than assuming broader transcript search fixes correction capture.
8. Preserve host memory and IO admission. Keep ctx-import's measured job peak plus desktop reserve and its skip receipts; move work off-peak or off-host instead of lowering the gate. Check /proc/pressure/io, per-process IO, ctx throttles, refresh state and snapshots. Time before/after real queries and report a failed probe as not fixed; a cgroup cap or systemd sandbox alone establishes no host capacity or tool containment.
9. Follow references/history-sources.md for bounded user-message scans, read-only databases, harness-specific filtering and deduplication. Treat source lists as generated. Follow references/architecture.md to verify actual roots, releases and provider configuration, preserving credentials, grants and transcripts. Reuse current memory components while the in-harness matrix is red.
10. Present configuration fixes as exact diffs in FIXES.md for owner approval. For an approved retrieval fix, save original bytes in applied/, record live read-only gold-query ranks, patch, prove a regression test passes new code and fails the original, then rerun ranks and attach receipts. Check FTS schema before snippet() column indexes and route untracked installed edits back to their source owner.
11. Audit owner requirement through source/candidate commit, release, running process, client-loaded version and real user journey. Inspect peer sessions and existing artifacts before assigning duplicate work. Compare disk config, loaded hooks and injected context in a fresh process; preserve credentials, functional tools and essential protections, and inspect installers for automatic reintroduction.
12. Drive UniiChat through its own commands and the intended local server, using references/uniichat-driving.md. Keep imports on disk-backed TMPDIR and probes on a copy server. Bound /goal and import work with burn-pace --json, pass/usage ceilings and checks at least every 30 minutes; pause when pace leaves under-burn or on-pace. Stop exact owned PIDs/units, preserve login decisions, and recheck live unit state and latest log immediately before reporting.

## Details

- [Topic index and original reference pointers](references/detail-index.md). Consult the relevant topic for commands, examples, and incident evidence.
- [Dropped rules](../../DROPPED.md) and [semantic review](../../REVIEW.md). Review unresolved conflicts before promotion.
