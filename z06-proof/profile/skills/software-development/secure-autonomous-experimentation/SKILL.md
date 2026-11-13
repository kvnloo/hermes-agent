---
name: secure-autonomous-experimentation
description: "Use when agents optimize code against automated evaluators."
version: 1.4.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [agents, sandboxing, evaluation, autoresearch, security, worktrees]
    related_skills: [requesting-code-review, test-driven-development, systematic-debugging]
---

# Secure Autonomous Experimentation

Build and review optimization loops in which an untrusted proposal agent edits code and an external evaluator decides KEEP or REVERT. Treat proposal execution, benchmark machinery, baseline state, Git metadata, and process lifetime as separate security boundaries.

## When to Use

- Autoresearch or overnight optimization loops
- Agents proposing performance, visual, model, or algorithm changes
- Tournament branches/worktrees with automated acceptance
- Any loop where generated code is evaluated and committed without immediate human review

## Core Architecture

1. **Separate control and experiment state.** Keep each objective on its own branch, worktree, baseline, history, budget, evaluator, and editable-path policy.
2. **Commit control-plane code first.** Create child experiment worktrees only after orchestrator/evaluator files exist in a committed parent revision.
3. **Run proposals in disposable clones.** Do not expose the real worktree or shared Git directory as writable. On Linux, use Bubblewrap with a read-only root and a disposable clone bind-mounted at the expected repository path.
4. **Use a private PID namespace.** `--new-session` or process-group killing alone does not contain `setsid` descendants. Use `--unshare-pid`; verify a detached delayed writer dies before import.
5. **Import files, not Git state.** After proposal exit, require sandbox HEAD/branch/index invariance. Enumerate regular files independently, reject symlinks and policy files, and copy only validated allowlisted deltas into the real worktree.
6. **Evaluate externally and fail closed.** Proposal agents never self-accept. Missing, malformed, stale, foreign, or wrong-shot evidence rejects the candidate.
7. **Re-baseline accepted HEAD for each run.** A restarted loop must compare against the current accepted branch tip, not stale historical state.

## Baseline and Git Integrity

- Store baseline evidence outside candidate-writable project paths, preferably private Git metadata.
- Bind baseline identity to repository common-dir, loop, expected branch, and exact HEAD.
- Hash baseline bytes before and after untrusted execution.
- Do not rely only on `git status`: it misses ignored files, other refs, hooks, config, and many index flags.
- In a disposable clone, Git mutations are harmless only if no Git state is imported and the clone is destroyed.
- Check newly created paths against the **real repository's immutable ignore policy** using `git check-ignore --no-index`; never trust mutable sandbox `.gitignore` or `.git/info/exclude` state.
- Reject edits to `.gitignore`, `.gitattributes`, `.gitmodules`, evaluator code, benchmark definitions, score definitions, preset routing, profiling code, and capture APIs.

## Benchmark Integrity

- Freeze exact benchmark identity: shot names, full camera definitions, setup-function source, dimensions, presets, seeds, and profiling provenance.
- Record benchmark metadata from trusted external tooling, not candidate-supplied summaries.
- Recheck protected paths and repository fingerprint after evaluator/judge execution.
- Use deterministic metrics where possible and independent hard guards where objectives conflict.
- Treat source-level anti-gaming scans as defense-in-depth, not a complete sandbox. Reject concrete environment-conditioned behavior while permitting ordinary APIs used unconditionally. Pair every rejection rule with a benign acceptance test to prevent making proposals unusable.
- For browser/WebGL FPS claims, retain raw samples, positively prove real-GPU and actual drawing-buffer identity, separate authored-time motion from real-time pacing, and require a physical-machine baseline plus an independent rerun. See `references/browser-performance-regression-harness.md` for the audit checklist, deterministic matrix, schema, fail-closed gates, baseline semantics, and simulated-versus-physical evidence boundary.
- For stateful ML/inference servers, distinguish cold load, compile warm-up, resident execution, and result-cache hits; preserve decoded-output hashes; account for full model residency; and invalidate paging or externally contaminated runs rather than publishing a false winner. See `references/stateful-ml-runtime-benchmarking.md` for cache-busting, telemetry, precision-evidence, quality-gate, and reporting rules.

## Process and Server Safety

- Wrap proposal, judge, browser, and server trees with explicit timeouts.
- Outer timeout must include every sequential command allowance plus cleanup margin.
- Refuse to reuse an occupied/unowned benchmark port.
- Clear inherited URL/server override environment variables.
- Kill the full namespace/process tree on timeout, signal, readiness failure, and normal proposal completion before inspecting files.

## Workstation Resource Isolation

Treat unrelated machine activity as benchmark-integrity evidence, not ordinary score noise:

- Freeze configured competing workload cgroups while preserving the active evaluator ancestry.
- Require several consecutive quiet CPU/GPU samples before measurement; missing telemetry fails closed.
- Continuously monitor external per-process CPU/GPU activity and memory/I/O PSI during measurement; invalidate contaminated evidence before acceptance. Kernel reclaim threads such as `kswapd` are pressure evidence, not processes to suspend.
- Keep proposal reasoning outside the exclusive window; isolate each baseline and evaluator measurement instead of disconnecting the desktop for an entire research budget.
- Prefer cgroup-v2 freezing to broad `SIGSTOP`; preserve pre-existing frozen state, journal cleanup privately, and thaw only scopes the pipeline froze. If an explicitly armed exclusive mode must pause same-user work in root-owned service cgroups, limit PID signaling to non-TTY processes and bind every record to process start time.
- Acquire the recovery journal atomically and record owner PID plus start time. A second live evaluator must reject rather than treating the first evaluator's journal as stale and thawing its workloads.
- Install cleanup handlers immediately after acquiring the journal and before the first freeze/stop. Keep the journal whenever thaw/resume cannot be verified; diagnostics or audit-write failures must never bypass cleanup.
- Separate remote-safe mode from an explicit desktop-exclusive toggle. Never silently weaken GPU thresholds merely because the compositor or remote stream prevents quiescence.

See `references/workstation-benchmark-isolation.md` for the two-mode design, cgroup freezer protocol, continuous watchdog, evidence schema, and verification matrix.

## Required Adversarial Tests

Check these into the repository rather than relying on one-off shell probes:

- benign allowlisted edit imports successfully
- protected edit rejected
- proposal commit/staging/branch mutation rejected
- ignored-source injection rejected, including skip-worktree plus altered sandbox ignore policy
- baseline tampering cannot affect real baseline
- detached `setsid` descendant cannot race copy-back
- obfuscated benchmark-conditioned branch rejected
- ordinary unconditioned runtime API accepted
- malformed evaluator/judge evidence rejected
- stale/unowned server rejected
- missing or above-threshold CPU/GPU/memory-PSI/I/O-PSI telemetry rejects before measurement
- external CPU/GPU activity or pressure during measurement invalidates evidence
- a concurrent evaluator cannot acquire the live owner's journal or thaw its workloads
- stale isolation state thaws only pipeline-frozen cgroups and preserves pre-frozen scopes
- cgroup freeze and thaw wait for actual `cgroup.events` completion; unknown state retains the recovery journal
- watchdog permits exact evaluator descendants even when browsers move into dynamically created app scopes, without blanket-whitelisting unrelated same-cgroup workloads
- short-lived external CPU/GPU bursts cannot pass between watchdog samples unnoticed
- same-user non-TTY fallback in root-owned service cgroups is explicitly armed, PID/start-time bound, and verified resumed
- every optional exclusive-mode fallback/helper is invoked by a focused test, so undefined or unarmed paths cannot hide behind default-mode coverage

Run unit tests, syntax checks, typecheck/lint, isolated production build, evaluator smoke, real benchmark smoke, and an independent blocker-only review after the final edit. During a live multi-agent review, re-snapshot HEAD/status/diff before the verdict; commits and worktree edits can move concurrently, invalidating stale line numbers. Prefer build output in an ignored or temporary directory so verification does not dirty tracked artifacts.

## Integration Canary Before Full Runs

A secure loop is not operationally proven until it survives the current product architecture. Keep the control plane committed separately, create a canary branch from a coherent committed product SHA, apply the pipeline there, rerun all gates, baseline one specialist, and execute one bounded trial before enabling the overnight budget.

Dynamic benchmark registries require special care: pass the manifest's frozen expected subset explicitly into benchmark tools and reject missing requested cases. Registry growth should not make an evaluator measure a superset and then fail strict equality, nor should it silently expand a frozen contract.

See `references/integration-canary-pattern.md` for moving-branch selection, worktree/gitlink safety, explicit frozen-subset routing, one-trial KEEP/REVERT proof, and accidental-branch-mutation recovery.

## Review Loop

- Ask reviewers for concrete branch corruption, false acceptance, regression acceptance, or loop-breaking failures.
- Fix the class of vulnerability, then add the reviewer's exact exploit as a durable test.
- Re-run all gates after every hardening edit; never cite stale green verification.
- When a security rule blocks benign behavior, narrow it around conditioned use and add both attack-rejection and benign-acceptance tests.

## Pitfalls

- A quiet preflight without continuous monitoring can miss a workload that starts during the benchmark.
- Freezing only transient competitor commands misses helpers launched after enumeration. Use watchdog evidence to identify and freeze the persistent desktop-shell/service launcher in explicit exclusive mode, then rerun the full benchmark rather than only a short readiness check.
- Treating kernel reclaim threads as ordinary competitors leads to unsafe fixes or false positives. Gate `/proc/pressure/memory` and `/proc/pressure/io`; never attempt to suspend `kswapd`.
- Validating only the union of benchmark cases across target and guard presets can accept incomplete evidence. Enforce the frozen case set independently for every measured preset.
- Broad per-PID `SIGSTOP`/`SIGCONT` can leave interactive terminal jobs stopped by job-control signals such as `SIGTTOU`; prefer cgroup-v2 freezing.
- Thawing every recorded cgroup can undo a freeze that predated the benchmark. Record prior state and thaw only scopes changed by the pipeline.
- Wrapping the entire autoresearch run in desktop-exclusive isolation can disconnect the user for hours while the proposal agent thinks. Isolate baseline/evaluator windows only.
- Working-tree fingerprints that use `--exclude-standard` miss ignored injection.
- A baseline under ignored `runs/` remains proposal-writable.
- A detached child can escape a process group with `setsid` unless a PID namespace contains it.
- Cloning into the source repository's `.git/` can interfere with private state; use a separate temporary directory.
- Comparing full Unix permission bits across clones causes false deltas; Git preserves only the executable bit.
- Async child exit callbacks can let Node terminate before security checks finish; await child completion and validation at top level.
- Regexes banning all `performance`, `window`, or timer usage make legitimate rendering proposals unusable. Detect conditioned environment observation and test benign APIs.

## Reference

See `references/proposal-sandbox-pattern.md` for the concrete threat model, import sequence, and regression matrix distilled from a production autoresearch hardening session.
