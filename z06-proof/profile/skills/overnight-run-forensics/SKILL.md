---
name: overnight-run-forensics
description: "Use when auditing agent work, continuity or run outcomes."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [evaluation, privacy, agentsview, statistics]
---

# Overnight agent-run forensics

## When to Use

Use for retrospective work accounting, continuity failures and clock-only agent completion studies that must keep source histories private. Load `agentsview-safe-source-retrieval` before opening the archive. Distinguish an accounting question from a causal investigation; evidence that a run stopped does not by itself explain why.

## Evidence boundaries

- Inspect source schemas through SQLite URI `mode=ro`, set `query_only=ON`, and read each database in one transaction. Never start AgentsView or invoke a migration-capable export to perform a read-only study. Record source metadata and WAL/SHM presence; live producers can change main-file metadata during a read transaction, so never claim a global immutable snapshot or infer that the reader caused an observed change.
- Treat AgentsView `ended_at` as last transcript activity, not an independent process exit. A two-hour silent tail needs a separate native exit timestamp; subtracting transcript endpoints fabricates evidence.
- Deduplicate mirrors using harness and native source-session IDs. Enrich exact matches with native exits rather than counting them twice. Resolve database aliases before scanning, and retain exclusion/duplicate counts that reconcile with scanned totals.
- Treat native close events as normal termination only, never as success. Require an independent source-reported success-like outcome for a completion surrogate. Do not call source-reported completion independently verified success or proof of no owner intervention.
- Join blocked events by exact session identity and timestamp. Run-specific admission-journal links can recover older attempts when the task's current session pointer has changed. A needs-owner snapshot's generation time, goal prose, worker, or project is not a raised-during-run event.

## Cross-harness failure audits (agent-outcomes ledger)

- Start from the existing ledger before mining raw histories: `operations/agent-outcomes/ledger.sqlite` (open `mode=ro`). It holds the `runs` table (`harness`, `lane`, `outcome`, `failure_class`, `owner_corrections`), `signals` (per-run signal counts) and `host_events`. Group `failure_class` by harness, lane and month. Report claimed-versus-verified explicitly: count `claimed_success` runs that have a `tests_fail` signal and no `tests_pass` signal.
- `host_events` counts journal lines, not victims. One OOM produces many lines. For distinct kills, count `~/.local/state/agent-oom/kills.jsonl` rows per day, class and comm. Report the protected-class victims separately.
- Back every failure class with one live read-only probe before naming a cause. Old reports go stale within days.
  - Fleet: `kubectl get nodes`, plus the node's cordon annotations and conditions.
  - Paid pools: `burn-pace --json`, reading `lanes.*.band` and `pace_ratio`.
  - Host: `free -g`, `swapon --show`, `df -h`.
  - Memory health: `memory-heal/STATUS.md`.
  - Phone senders: `chatgpt-driver/*/dispatches.jsonl`, grouped by status and normalized error.
- Per class, give: symptom, counts with dates, root cause, owning repo and issue state, why the previous fixes stalled, and where the work belongs. A recurring stall pattern is "built but not kept healthy": a probe that fails closed and alerts nobody silently removes capacity.

## Owner-ask audits ("were my asks actually addressed?")

1. Pull Kevin's human messages for the window from every profile's `state.db` (`mode=ro`). Drop gateway notices, background-process completions and relays, which are not human asks.
2. Classify each ask: done-verified (with live evidence), superseded, in progress, open, or waiting on Kevin. A reply is not completion, and an agent's "done" with no run against the real target is unverified.
3. Report counts first, then the gaps: asks never touched, unverified "done" claims, and items parked on Kevin. For each parked item, check whether it is actually reversible or already approved; if so, take it, because asking again is the failure.
4. Report outcomes Kevin cares about (results, numbers, what's unblocked). Never present internal plumbing fixes (ports, displays, helper bugs) as wins, and never list a fix he already asked for as a pending decision.

## Continuous-work audits

- Enumerate local profile stores and resolve filesystem aliases before making an all-Hermes claim. Separate direct owner messages, cron prompts, cross-harness worker dispatches and remote-only evidence; do not credit another harness's work to the audited agent.
- Deduplicate compaction copies by stable tool-call identity, not only timestamp/content: transcript rewriting can give copied calls new timestamps. Deduplicate original owner messages by timestamp plus full-text hash, retaining every source row ID.
- Stream the full retained observer JSONL into a compact time-window identity/timing index and reconcile it with native messages, cron execution rows and output files. Keep trace-only calls and missing completions explicit; a scheduler claim that never started is not a work run.
- Measure native turn envelopes with matched pre_llm_call/post_llm_call events and union overlaps. Label this turn occupancy, not productive time or whole-fleet utilization. Do not count background admission waits, scan lifetimes, scheduled monitor wakeups or first-to-last transcript spans as continuous implementation.
- Prefer native event timestamps over narrative report clocks, and fix the requested cutoff before aggregation. Separate code written, config installed, tests actually executed, retrospective test receipts and verified user-facing delivery.
- Inspect resource contention and remote child lifetime when a run launched disk surveys or builds. Read-only work can still disrupt peers; a timeout around SSH does not by itself prove the remote command stopped.
- Trace a suspected early stop from the original owner instruction through the assistant-authored continuation prompt, native exit reason, effective budget and exact pause/stop tool call. Separate a normal model final response, scheduler veto, user interruption and exhausted runtime limit; each requires a different repair.
- Recover historically loaded skill text and automation payloads from native tool results before attributing behavior to present files. Record when instructions changed, because a later skill edit cannot explain an earlier decision.
- Check native goal/loop state for the exact affected session rather than citing unrelated prior goals or a configured maximum. A missing goal is a missing continuation backstop, not evidence that natural-language delegation was invalid.
- Keep policy influence distinct from forced termination. A normal text stop rules out an exhausted turn budget at that boundary, but does not prove injected instructions were irrelevant. Label prompt-clutter or version-regression explanations as unproven until a matched comparison supports them.
- Keep the retrospective read-only with respect to production: report paused jobs and failed gates without silently resuming jobs, changing grants or performing the original assignment.

## Features and validation

- Compute regex features internally from the initial dispatch prompt, with an explicit timestamp eligibility rule. Do not mine later prompts or export raw text. Mark mutable lifetime model/provider summaries unavailable unless an immutable dispatch record exists.
- Count strictly preceding launches; simultaneous starts are not known prior starts. Declare concurrency thresholds before looking at results, and distinguish observed start counts from actual parallel load.
- Keep unknown outcomes out of both successes and failures. Report total, labeled n, and missingness for every bucket; apply minimum-cell rules to labeled n.
- Purge training rows whose outcomes were not observable strictly before the held-out week's boundary. Start-week ordering alone leaks future labels when sessions span weeks; use independent outcome-observation timestamps, conservatively exclude unknown timing, and test a corpus where every label arrives after every test dispatch. Preserve whole-lineage/night isolation while purging. Align the boundary with the declared night-date rollover (Monday noon for noon-anchored nights), not a different calendar convention.
- Bound mutable retrospective outcome/termination summaries by extraction read time unless a reliable historical observation event exists. A native exit timestamp does not establish when a later outcome annotation became available. A one-time snapshot may consequently have zero eligible historical folds; withhold fitting rather than backdating labels. Retain endpoint lower bounds and test delayed owner/termination evidence, unknown/equal-boundary availability, later-week admission, and an ordinary fit.
- Anchor night dates consistently across midnight and DST. Validate in forward weekly blocks, not random splits. Exclude entire lineage groups spanning weeks from cross-validation if needed to preserve both weekly/night grouping and one held-out fold per work item. Missing eligible folds is a reason to withhold fitting, not weaken the split.
- Keep restart/evening-cut diagnostics out of dispatch-time predictors and binary outcomes. Project proximity plus resume keywords does not prove same-task identity or intent; retain such counts as explicitly insufficient proxies.
- Do not infer necessary hard readiness gates from retrospective associations. Withhold coefficients/AUC when labels, classes, time blocks, or interval support are inadequate. Report selection and source-availability confounding even when a descriptive comparison rejects a harmful association.

## Privacy and execution

- Store only derived records and frozen receipts outside all Git worktrees, directories 0700 and files 0600. Refuse symlinks, check resolved Git ancestors, hash the export, and verify its hash before analysis. Keep hashed linkage keys private too.
- Stream SQLite rows and serialization, retaining only compact derived metadata for sorting. Measure child peak RSS using Python `resource` when a system `time` executable is absent.
- Run synthetic fixtures and actual local extraction/analysis. If an unscoped pytest command lacks existing repository dependencies, use the exact command from the study directory with the repository root on PYTHONPATH, and separately run the dependency-complete repository suite. Do not disguise collection failures as passing tests.
- Publish only allowlisted code, synthetic fixtures, methodology, and authorized aggregates. Bind the PR evidence receipt to the exact tested head, keep the PR draft when required, and verify remote state and the full body after creation.
