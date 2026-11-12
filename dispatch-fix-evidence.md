# Unclaimed reviewer dispatch fix evidence

## Root cause addressed

The dispatcher skipped explicit `reviewer` assignees before claim because no real reviewer profile existed. The task remained `ready` with only an ephemeral `skipped_nonspawnable` result.

## Durable correction

- Provisioned `/workspace/hermes-home/profiles/reviewer` by isolated config/skill clone from `canary-worker`; gateway remains stopped and no alias/ingress was created.
- Removed reviewer fallback providers so exact task-pinned provider/model failures stay visible.
- Verified required `hermes-agent` and `evidence-bound-artifact-ops` skills are installed.
- Persisted diagnostic-only task fields: `ready_since`, `last_considered_at`, `dispatch_attempt_count`, `dispatch_reason`, and `dispatch_sla_alerted_at`.
- Added reason codes for unassigned, nonspawnable profile, global/profile capacity, respawn guard, and claimable paths in both ready and review lanes.
- Added one coalesced `dispatch_claim_sla` event/result per ready episode after 300 seconds. No notifier, fallback queue, scheduler, or Telegram fanout was added.
- Unknown explicit assignees are never mapped to `canary-worker`.

## Canary and regression evidence

Commit: `dc5ac92697`

Passing canonical test runs:

- 24 passed: dispatch-health synthetic reviewer canary, review lifecycle, per-profile capacity.
- 32 passed, 1 Windows-only skipped: DB migration/backcompat plus dispatch health.
- 36 passed, 1 failed then fixed, 1 Windows-only skipped: DB/default-assignee/tick-hook/dispatch-lock batch; the sole failure was a minimal-schema migration fixture and was corrected with a core-column guard.
- `git diff --check` and Python compile passed.

The bounded synthetic canary proves: a high-priority missing-profile poison head records `nonspawnable_profile`; a valid reviewer task is claimed/spawned; completion reaches `done`. Global capacity records every waiting task without claiming it. SLA emission is idempotent across subsequent ticks.

No live dispatcher/gateway was restarted or activated. The real reviewer profile is visible in `profile list` with gateway `stopped`; the dependent independent-review card will exercise normal dispatcher activation only after this parent completion releases it.

## Rollback

1. Revert commit `dc5ac92697`; additive telemetry columns are safe to leave in existing SQLite boards and are ignored by old code.
2. Stop any reviewer worker, then remove only `/workspace/hermes-home/profiles/reviewer` using the supported profile-delete flow if Captain chooses to retire the role.
3. No task statuses, leases, existing runs, or explicit assignees need rewriting. No fallback cards were created.
