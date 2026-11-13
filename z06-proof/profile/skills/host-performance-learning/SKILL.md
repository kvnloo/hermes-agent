---
name: host-performance-learning
description: Use when improving Kevin's PC or ongoing host optimizer.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [performance, systemd, k3s, telemetry, autoresearch]
    related_skills: [home-k3s-fleet, dotfiles-desktop-work, privacy-first-activity-telemetry, owner-context-sweep]
---

# Operated host performance learning

Kevin wants a continuously operated, personalized optimization system, not another one-time audit or proposal. Treat deployment, event-triggered continuation, evidence retention, pause/rollback and source integration as separate acceptance gates. Do not equate an observer or a fixed microbenchmark with general autonomous optimization.

## When to Use
Use for PC-wide performance, personalized resource learning, recurring host/fleet failures, or continuation of the operated host optimizer.

## Existing implementation
- Source: `.files` feature worktree `/mnt/zer0models/worktrees/files-host-optimizer`, branch `feat/host-optimizer-20261103` (inspect current Git state; do not assume pushed or merged).
- Runbook: `docs/fleet/HOST-OPTIMIZATION.md` there.
- CLI: `~/.local/bin/host-optimizer` resolves into a stamped release. `status`, `pause`, `resume`; service/path `host-optimizer.{service,path}`.
- Private evidence: `/mnt/zer0models/sft-svlm/data/telemetry/activity/host-optimizer/` (`latest.json`, bounded `history.json`, ranked but unexecuted `experiments.json`, reused `fleet-steward/`). Deployment and audit receipts: `/mnt/zer0models/workspace/zer0/data/operations/host-optimizer-20261103/`.
- Narrow deployment uses existing `scripts/apply-agent-oom --host-optimizer [--apply]`, not a broad host reapply. Complete closure and links are declared in `config/host/groot.toml`.

## Operating boundaries
1. Load `home-k3s-fleet`, `dotfiles-desktop-work`, `privacy-first-activity-telemetry`, and `owner-context-sweep` before extending it. Reconcile live ownership before modifying any shared service.
2. Reuse the existing fleet-health observations and canonical job-spool events; do not add another polling timer or scheduler. Native harnesses stay native; K3s/Kueue own cluster allocation, Kerdoios placement, and each harness its session lifecycle.
3. Observe local numeric resource/accounting and derived cross-harness failure signals only. Raw prompts, tool arguments, credentials, screenshots and personal activity titles are not collected by this learner. Keep private state on the canonical mounted bulk disk with restrictive permissions.
4. Current automatic mutation is ONLY repairing known legacy 1-core/2-core agent CPU ceilings; weights, memory, security, interactive sessions and arbitrary services are untouched. Other findings are proposals until paired accepted-task evidence and rollback qualify an actuator.
5. The fixed daily CPU replay is idle-gated, finite and checkpointed. It validates a single CPU-policy lever, not production task speed or an autonomous research-agent loop. Busy hosts must hold rather than stress or bypass the gate. LLM continuation still follows the owner's native `/goal` rule; do not substitute an unbounded paid shell supervisor.
6. Read live `latest.json` freshness/coverage/errors, `.path` enablement, service journal/runtime/MemoryPeak and source-byte provenance before reporting. Test pause/resume and actual event-driven refresh. A oneshot being inactive after success is normal; an enabled path is not proof that samples advanced.
7. Keep historical analysis cheap: cache unchanged logs, coalesce refresh after changed jobs, and expose source age/pending changes. Do not repeatedly rescan huge history at every event. Counter deltas require same boot/fresh intervals, parent/child cgroups must not be summed, and lifetime pod restarts are not restart rates.

## Recurrence lessons
- Earlier cluster-steward PR 46 explicitly never activated live infrastructure; green fixtures and an open draft did not deliver the operated system. AgentSys research likewise recorded a host-recorder plan rather than installing it. Check source -> deployed bytes -> producer -> consumer -> outcome before declaring requests fulfilled.
- Audit aggregate quota, future worker prefix drop-in AND explicit launch arguments together. Prefix drop-ins can override transient scope command flags; a real canary injecting a runtime property after launch verifies repair while preserving memory limits.
- `fleet probe` must parse full JSON documents before falling back to a final compact JSON line: Boat `limits` emits pretty multi-line JSON. The old last-line-only parser converted healthy Boat capacity into recurring health failures. Preserve failed-transport refusal and never print raw stderr.
- Report tick health from the journal distribution (`journalctl --user -u host-optimizer.service | grep HOST_OPTIMIZER`: errors= counts and the runtime_s spread), not from the first tick. Under IO pressure the AgentsView harness probe hits its 4 s sqlite deadline on a large share of ticks, and runtime stretches from <1 s to over a minute. Confirm by timing `harness_summary` directly while the host is idle before calling it broken.
- A failed fleet-health aggregate can reflect groot disk pressure while MBP and phones remain healthy. Preserve that signal; never weaken thresholds merely to turn the unit green. Follow safe-cleanup ownership checks before reclaiming files.

## Find the disk-pressure source before tuning
- Sample per-device throughput from `/proc/diskstats` and per-PID `read_bytes`/`write_bytes` from `/proc/<pid>/io` over 5–10 s. Do this before blaming hardware. On 2026-11-03 the data SSD (sdb, 92% full) was 100% busy from three sources. (1) `agent-telemetry-refresh` copied every multi-GB Hermes state.db to scratch every 30 min (fixed: healthy WAL stores are opened `mode=ro` in place and the spend scan is incremental by message id). (2) Agents ran unscoped `rg`/`find` over `/mnt/zer0models` (fixed with `loc`). (3) `ctx search` full-scanned a 58 GB lexical index (owner decision pending).
- SIGKILLed oneshot jobs leak their `TemporaryDirectory`; 40 GB of state.db copies had piled up in `/mnt/zer0models/tmp/agent-telemetry-refresh`. Check `fuser` and age before removing a job's own scratch dirs, and keep a receipt.
- `loc NAME` (.files `scripts/loc`, hourly `loc-index.timer`) answers name lookups across /home, /workspace and /mnt/zer0models in ~0.1 s. The system plocate db prunes `/mnt`, and an equivalent `find` exceeded 120 s.
- A host-optimizer tick that exceeds `TimeoutStartSec=120` while its fleet-steward child sits in D state on btrfs extent reads is a true IO-starvation signal. Do not raise the timeout to hide it.

## Extend toward the full ask
Reuse the saved AutoKernel AgentSys council plan and original profile before designing new experiments. The host optimizer (.files) is the observer/actuator; experiments on agent behaviour run in the autokernel AgentSys keep/revert loop (`council-autoresearch-loops` → `references/agentsys-loop.md`). Never tell Kevin "the autokernel loop exists" from the observer alone. Add per-tool timing/critical-path joins through Tokenomics, frozen evaluation through z0evals, and one reversible actuator at a time. Require correctness, p90, privacy and workload-fit guards; no universal speedup claims from microbenchmarks, parser heuristics or a running collector. Report remaining scope plainly, and preserve an owned, actionable experiment queue instead of ending with optional questions that stall already-authorized work.
