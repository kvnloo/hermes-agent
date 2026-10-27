# OOF-30 dispatch-health semantic rebase evidence

## Identity

- Authoritative parent: `c86197e60798801f62986e4e59460b1272d0c687`
- Approved dispatch-health source: `dea12172efe9259cf323bac2ad7016d22e00358e`
- Reviewed gateway attribution source: `b4ab5cc71c`
- Integration candidate: `47076b25b76ac14526750a06a1b03fb44da1bd27`
- Branch: `integration/t_7e69a38f`
- Worktree: `/workspace/zer0/oss/hermes-agent/.worktrees/t_7e69a38f`
- No deployment, restart, or live canary activation performed.

## Semantic mapping

### Dispatch-health fields and migration

Ported `ready_since`, `last_considered_at`, `dispatch_attempt_count`, `dispatch_reason`, and `dispatch_sla_alerted_at` into the live `Task`, schema, additive migration, and ready/review backfill paths. Task truth, claims, leases, and run identity remain unchanged.

### Episode resets

Ported the single `_begin_dispatch_wait_episode` reset across dependency/manual promotion, stale/manual reclaim, request-review/request-changes/reopen/unblock, timeout, stale-running, orphan reconciliation, crashed-worker recovery, and spawn-failure retry. All five diagnostic fields reset atomically in the surrounding state-transition transaction.

### Bounded health persistence and SLA

Ported one batched `_record_dispatch_considerations` writer transaction, capped at 128 samples. Reason-change events remain coalesced and claim-SLA alerts remain once per waiting episode. Least-recently-considered ordering rotates zero-capacity batches fairly.

Measured zero-capacity behavior with 135 queued tasks: each tick used exactly three fixed writer transactions (two existing maintenance writes plus one dispatch-health batch), rather than one transaction per queued task. Two ticks rotated coverage across all 135 tasks without a claim or spawn.

### OOF-30 coexistence

Preserved the live host-wide `max_in_progress` accounting, memory-derived default cap, live critical/elevated memory guard, per-profile caps, and ready/review lane reservation. Conflict resolution uses the live shared `spawn_budget`/`ready_budget` rather than the older source branch's `running_count + spawned` checks.

Added health recording to OOF-30-only early deferrals:

- global/host capacity: `global_capacity`
- critical memory guard: `memory_pressure:critical`
- per-profile cap: `profile_capacity`

Capacity and memory early exits use the same bounded/fair 128-row batch. Conflict tests prove a capped profile does not block an available profile and critical memory produces bounded, rotating health telemetry with zero spawns.

### Gateway PID attribution

Included the separable `b4ab5cc71c` fix: globally discovered service PIDs are included only for `all_profiles=True`; profile-scoped status continues to use its profile PID file and profile-aware process scan. Focused test proves another profile's service PID is not adopted.

## Diff scope and hashes

Only four implementation/test paths changed:

- `hermes_cli/kanban_db.py`
- `tests/hermes_cli/test_kanban_dispatch_health.py`
- `hermes_cli/gateway.py`
- `tests/hermes_cli/test_gateway.py`

Diff: 488 insertions, 5 deletions. The five deletions are conflict replacements in dispatcher capacity flow and the gateway service-PID loop; no file was modified or deleted outside this scope.

- `kanban_db.py` diff SHA-256: `07e34317d24176be4204859da5672e90c9bf5496f4fa71b930eba53ac7651190`
- `gateway.py` diff SHA-256: `e2922a937c79a0fd824ab5b8aff004780845fd45b4d10bf54c5f56ff9e373916`
- Candidate `kanban_db.py` SHA-256: `41627d08c0e417a221c0c9690c80033568786703b9276c6587aec3c6385f31a7`
- Candidate `gateway.py` SHA-256: `f3626655da421fe40f65f4b779fee41c5a2889cba448e8b907d527551a1aa41b`

The live checkout was never written. A final read-only `git status --short` at `/workspace/zer0/oss/hermes-agent` returned clean; therefore there were no dirty dashboard-dist or untracked `memory_tencentdb` bytes present there to hash at verification time. This integration neither removed nor modified any such path.

## Verification

Canonical wrapper used with `HERMES_PYTHON=/workspace/hermes-home/hermes-agent/venv/bin/python`.

Combined approved matrix plus live OOF-30 and gateway attribution:

- 18 test files
- 161 passed
- 0 failed
- 4 host-inapplicable skips

Coverage included dispatch health, review lifecycle, per-profile caps, memory guard, dispatch lock, writer contention, promotion, claim-lock reclaim, default assignee, dispatch hooks, DB/migration/repair, core lifecycle, worker lifecycle, worktree isolation, and gateway PID attribution.

Final conflict-focused dispatch-health run after transaction instrumentation:

- 8 passed
- 0 failed

Additional checks:

- `python -m py_compile hermes_cli/kanban_db.py hermes_cli/gateway.py`: passed
- `git diff --check`: passed
- Worktree status after commit: clean before generating this evidence document
